#!/usr/bin/env node
/**
 * mos-geo-schema-scraper: bulk JSON-LD extractor via the Apify actor
 * `logiover/json-ld-schema-meta-tag-extractor`.
 *
 * Plain Node 18+ ESM. Native fetch, no dependencies.
 *
 * Output (the schema/ folder is a stable current-state mirror, no -2 suffix):
 *   <schema>/raw/<page-type>/<slug>.json                 one array of JSON-LD blocks per page ([] if none)
 *   <schema>/raw/_apify-runs/YYYY-MM-DD-batch-<epoch>.json  full Apify response
 *   <schema>/competitors/<name>/...                      with --competitor
 *
 * <schema> resolves like every mos-geo skill:
 *   one-brand brain  campaigns/geo/YYYY-MM/schema/
 *   agency brain     campaigns/geo/YYYY-MM/<brand-slug>/schema/
 *   no brain         outputs/geo/YYYY-MM/<brand-slug>/schema/   (relative to cwd)
 *   --out <dir>      overrides all of the above
 *
 * Run with --help for flags.
 */

import { readFileSync, existsSync, statSync } from 'node:fs';
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { join, resolve, dirname, isAbsolute } from 'node:path';
import { homedir } from 'node:os';

const ACTOR_ID = 'logiover~json-ld-schema-meta-tag-extractor';
const COST_PER_URL = 0.006;

const VALID_PAGE_TYPES = [
  'homepage',
  'about-page',
  'pillar-pages',
  'guides',
  'author-pages',
  'products',
  'collections',
  'blog-posts',
];

const HELP = `mos-geo-schema-scraper (scripts/run.mjs)

Usage:
  node scripts/run.mjs --brand <name> [--url <url>...] [--urls <file>] [options]
  node scripts/run.mjs --out <schema-dir> [--url <url>...] [--urls <file>] [options]

Where the files go (one of):
  --brand <name>        Brand name. Resolves the schema/ folder from the brain
                        (campaigns/geo/YYYY-MM/[<brand>/]schema/) or, with no
                        brain, outputs/geo/YYYY-MM/<brand>/schema/ under the cwd.
  --out <dir>           Use this schema/ folder instead.
  --date YYYY-MM-DD     Month to file under (default: today).

URLs (at least one source, except with --print-path):
  --url <url>           Single URL (repeatable)
  --urls <file>         Newline-delimited URL file (# comments and blank lines ignored)

Options:
  --page-type <type>    Force the subfolder for every URL. One of:
                          ${VALID_PAGE_TYPES.join(' | ')}
                        Omit it to classify each URL from its path.
  --competitor <name>   Write to schema/competitors/<name>/ instead of raw/
  --force               Overwrite existing per-page files
  --country <ISO>       Pin the Apify proxy country (e.g. AU)
  --print-path          Print the resolved schema/ folder and exit
  --dry-run             Print URL -> page-type/slug -> file and any collisions.
                        No API call, no token needed.
  -h, --help            Show this help

Token: APIFY_TOKEN from the environment, else the "token" field of
~/.apify/auth.json (written by \`apify login\`).

Cost: about $${COST_PER_URL} per URL, one batched actor run per invocation.`;

function localDate() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// ---- args --------------------------------------------------------------------

function parseArgs(argv) {
  const a = {
    brand: '', out: '', date: '', urls: [], urlsFile: '', force: false, country: '',
    pageType: '', competitor: '', printPath: false, dryRun: false,
  };
  const need = (i, flag) => {
    const v = argv[i];
    if (v === undefined || v.startsWith('--')) throw new Error(`${flag} needs a value`);
    return v;
  };
  for (let i = 2; i < argv.length; i++) {
    const f = argv[i];
    if (f === '--url') a.urls.push(need(++i, f));
    else if (f === '--urls') a.urlsFile = need(++i, f);
    else if (f === '--brand') a.brand = need(++i, f);
    else if (f === '--out') a.out = need(++i, f);
    else if (f === '--date') a.date = need(++i, f);
    else if (f === '--page-type') {
      const v = need(++i, f);
      if (!VALID_PAGE_TYPES.includes(v)) {
        throw new Error(`Invalid --page-type "${v}". Must be one of: ${VALID_PAGE_TYPES.join(', ')}`);
      }
      a.pageType = v;
    } else if (f === '--competitor') a.competitor = need(++i, f);
    else if (f === '--force') a.force = true;
    else if (f === '--country') a.country = need(++i, f);
    else if (f === '--print-path') a.printPath = true;
    else if (f === '--dry-run') a.dryRun = true;
    else if (f === '--help' || f === '-h') {
      console.log(HELP);
      process.exit(0);
    } else throw new Error(`Unknown flag "${f}". Run with --help.`);
  }
  if (!a.date) a.date = localDate();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(a.date)) throw new Error(`--date must be YYYY-MM-DD, got ${a.date}`);
  if (!a.brand && !a.out) throw new Error('--brand <name> is required (or pass --out <dir>)');
  return a;
}

// ---- brain resolution (kept in step with mos-geo-internal-links/scripts/links.py) ----

function isFile(p) {
  try { return statSync(p).isFile(); } catch { return false; }
}

// A worktree's .git is a file: "gitdir: <main>/.git/worktrees/<name>". Walk up to
// the .git folder and return the main checkout, so a worktree inherits the brain.
function mainCheckout(gitFile) {
  const m = readFileSync(gitFile, 'utf8').trim().match(/^gitdir:\s*(.+)$/m);
  if (!m) return null;
  let raw = m[1].trim();
  const drive = raw.match(/^([A-Za-z]):[\\/](.*)$/);
  if (drive && process.platform !== 'win32') raw = `/mnt/${drive[1].toLowerCase()}/${drive[2]}`;
  raw = raw.replace(/\\/g, '/');
  let gitdir = isAbsolute(raw) ? raw : resolve(dirname(gitFile), raw);
  for (let d = gitdir; ; d = dirname(d)) {
    if (d.split('/').pop() === '.git') return dirname(d);
    if (dirname(d) === d) return null;
  }
}

function brainConfig(root) {
  const own = join(root, '.mos', 'config.yaml');
  if (isFile(own)) return own;
  const git = join(root, '.git');
  if (isFile(git)) {
    const main = mainCheckout(git);
    if (main && isFile(join(main, '.mos', 'config.yaml'))) return join(main, '.mos', 'config.yaml');
  }
  return null;
}

function findBrain(start) {
  for (let d = start; ; d = dirname(d)) {
    if (brainConfig(d)) return d;
    if (existsSync(join(d, '.git'))) return null;
    if (dirname(d) === d) return null;
  }
}

function brainMode(brain) {
  const config = brainConfig(brain);
  if (!config) return 'in-house';
  const m = readFileSync(config, 'utf8').match(/["']?mode["']?\s*:\s*["']?([a-z-]+)/);
  return m ? m[1] : 'in-house';
}

function slugify(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function schemaDirFor(args, cwd) {
  if (args.out) return resolve(args.out);
  const month = args.date.slice(0, 7);
  const slug = slugify(args.brand);
  const brain = findBrain(resolve(cwd));
  if (brain && brainMode(brain) !== 'agency') return join(brain, 'campaigns', 'geo', month, 'schema');
  if (brain) return join(brain, 'campaigns', 'geo', month, slug, 'schema');
  return join(resolve(cwd), 'outputs', 'geo', month, slug, 'schema');
}

// ---- URL -> folder + filename ------------------------------------------------

/**
 * Classify a URL into a page-type folder when --page-type is not supplied.
 * Conservative: anything ambiguous falls back to "guides".
 */
function classifyUrl(url) {
  const path = new URL(url).pathname.replace(/\/+$/, '');
  if (path === '' || path === '/') return 'homepage';
  if (/\/about(-us)?$/i.test(path)) return 'about-page';
  if (/\/author\//.test(path)) return 'author-pages';
  // Shopify storefront taxonomy
  if (/^\/products\//.test(path)) return 'products';
  if (/^\/collections\//.test(path)) return 'collections';
  if (/^\/blogs\//.test(path)) return 'blog-posts'; // /blogs/<blog>[/<article>] = post or listing
  const segments = path.split('/').filter(Boolean);
  if (segments.length === 1) return 'pillar-pages';
  return 'guides';
}

function urlToSlug(url) {
  const path = new URL(url).pathname.replace(/^\/+|\/+$/g, '');
  if (!path) return 'homepage';
  // 1) path separators -> `--` (the canonical depth marker)
  // 2) any other non-alphanumeric run -> a single `-`
  // 3) trim leading/trailing hyphens
  // Do NOT collapse `-+` to `-`: that destroys the `--` depth separator.
  return path
    .replace(/\//g, '--')
    .replace(/[^a-z0-9-]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();
}

// ---- io ----------------------------------------------------------------------

async function fileExists(p) {
  try { await access(p); return true; } catch { return false; }
}

async function loadUrlsFromFile(p) {
  const txt = await readFile(p, 'utf-8');
  return txt.split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
}

function loadToken() {
  if (process.env.APIFY_TOKEN) return process.env.APIFY_TOKEN.trim();
  const authPath = join(homedir(), '.apify', 'auth.json');
  if (!isFile(authPath)) {
    throw new Error(
      `No Apify token. Set APIFY_TOKEN, or run \`apify login\` (install the CLI first with \`npm install -g apify-cli\`) so ${authPath} exists.`
    );
  }
  const parsed = JSON.parse(readFileSync(authPath, 'utf-8'));
  if (!parsed.token) throw new Error(`No "token" field in ${authPath}`);
  return parsed.token;
}

function describeBlock(b) {
  if (!b || typeof b !== 'object') return typeof b;
  if (Array.isArray(b['@graph'])) {
    const inner = b['@graph'].map((g) => (g && typeof g === 'object' ? g['@type'] : '?')).filter(Boolean);
    return `@graph(${inner.map((t) => (Array.isArray(t) ? t.join('+') : t)).join('+')})`;
  }
  const t = b['@type'];
  if (Array.isArray(t)) return t.join('+');
  if (t) return t;
  if (Object.keys(b).length === 0) return '{} EMPTY-SCRIPT';
  return '<no-@type>';
}

// ---- main --------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv);
  const schemaDir = schemaDirFor(args, process.cwd());

  if (args.printPath) {
    console.log(schemaDir);
    return;
  }

  const allUrls = [...args.urls];
  if (args.urlsFile) allUrls.push(...(await loadUrlsFromFile(args.urlsFile)));
  if (allUrls.length === 0) throw new Error('No URLs provided. Use --url <url> (repeatable) or --urls <file>.');
  for (const u of allUrls) {
    try { new URL(u); } catch { throw new Error(`Not a valid URL: ${u}`); }
  }

  const rawRoot = args.competitor
    ? join(schemaDir, 'competitors', slugify(args.competitor))
    : join(schemaDir, 'raw');
  const runsDir = join(rawRoot, '_apify-runs');

  const targets = allUrls.map((url) => {
    const pageType = args.pageType || classifyUrl(url);
    const slug = urlToSlug(url);
    return { url, pageType, slug, file: join(rawRoot, pageType, `${slug}.json`) };
  });

  const seen = new Map();
  for (const t of targets) {
    if (seen.has(t.file)) {
      throw new Error(`Two URLs map to the same file ${t.pageType}/${t.slug}.json:\n  ${seen.get(t.file)}\n  ${t.url}`);
    }
    seen.set(t.file, t.url);
  }

  const hits = [];
  for (const t of targets) if (await fileExists(t.file)) hits.push(t);

  if (args.dryRun) {
    console.log(`Schema folder: ${schemaDir}`);
    console.log(`Writing to:    ${rawRoot}\n`);
    for (const t of targets) {
      const flag = hits.includes(t) ? (args.force ? '  (exists, --force will overwrite)' : '  (EXISTS, would refuse)') : '';
      console.log(`  ${t.url}\n    -> ${t.pageType}/${t.slug}.json${flag}`);
    }
    console.log(`\n${allUrls.length} URL(s), approx cost $${(allUrls.length * COST_PER_URL).toFixed(3)}. Dry run: nothing sent to Apify.`);
    return;
  }

  if (hits.length > 0 && !args.force) {
    console.error('\nExisting files would be overwritten:');
    for (const c of hits) console.error(`  ${c.pageType}/${c.slug}.json  <- ${c.url}`);
    console.error('\nRe-run with --force to overwrite (commit or copy the old files first if you need them).');
    process.exit(2);
  }

  const token = loadToken();
  console.log(`Scraping ${allUrls.length} URL(s) via ${ACTOR_ID}...`);

  const proxyConfiguration = { useApifyProxy: true };
  if (args.country) proxyConfiguration.apifyProxyCountry = args.country.toUpperCase();

  // Start the run ASYNC and poll. The run-sync endpoint hard-caps at 300s,
  // which a real-browser render of a large batch (50+ URLs) blows past,
  // returning an empty dataset that looks like "zero schema everywhere".
  // Do not switch this back to run-sync-get-dataset-items.
  const startRes = await fetch(`https://api.apify.com/v2/acts/${ACTOR_ID}/runs?token=${token}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ startUrls: allUrls.map((url) => ({ url })), proxyConfiguration }),
  });
  if (!startRes.ok) {
    const text = await startRes.text();
    throw new Error(`Apify run start failed: ${startRes.status} ${text.slice(0, 500)}`);
  }
  const startJson = await startRes.json();
  const runId = startJson.data.id;
  const datasetId = startJson.data.defaultDatasetId;
  let status = startJson.data.status;
  const t0 = Date.now();
  const TERMINAL = ['SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'];
  while (!TERMINAL.includes(status)) {
    await new Promise((r) => setTimeout(r, 5000));
    const st = await fetch(`https://api.apify.com/v2/actor-runs/${runId}?token=${token}`);
    if (!st.ok) continue; // transient; keep polling
    status = (await st.json()).data.status;
    process.stdout.write(`\r  run ${runId}: ${status}  (${Math.round((Date.now() - t0) / 1000)}s)        `);
  }
  process.stdout.write('\n');
  if (status !== 'SUCCEEDED') throw new Error(`Apify run ended with status ${status} (run ${runId}).`);

  const dsRes = await fetch(`https://api.apify.com/v2/datasets/${datasetId}/items?token=${token}`);
  if (!dsRes.ok) {
    const text = await dsRes.text();
    throw new Error(`Apify dataset fetch failed: ${dsRes.status} ${text.slice(0, 500)}`);
  }
  const items = await dsRes.json();

  await mkdir(runsDir, { recursive: true });
  const archivePath = join(runsDir, `${args.date}-batch-${Date.now()}.json`);
  await writeFile(archivePath, JSON.stringify(items, null, 2) + '\n');

  // Match on the URL as sent, falling back to a trailing-slash-insensitive match.
  const norm = (u) => u.replace(/\/+$/, '');
  const byUrl = new Map(targets.map((t) => [t.url, t]));
  const byNorm = new Map(targets.map((t) => [norm(t.url), t]));
  const summary = [];
  for (const item of items) {
    const target = byUrl.get(item.url) || byNorm.get(norm(item.url || ''));
    if (!target || target.done) continue;
    target.done = true;
    const blocks = Array.isArray(item.jsonLd) ? item.jsonLd : [];
    await mkdir(join(rawRoot, target.pageType), { recursive: true });
    await writeFile(target.file, JSON.stringify(blocks, null, 2) + '\n');
    summary.push({ pageType: target.pageType, slug: target.slug, count: blocks.length, types: blocks.map(describeBlock) });
  }

  console.log('\nResults:');
  const width = Math.max(40, ...summary.map((s) => `${s.pageType}/${s.slug}.json`.length));
  for (const s of summary) {
    const marker = s.count === 0 ? 'EMPTY     ' : `${s.count} block(s)`;
    const typeStr = s.types.length ? `[${s.types.join(', ')}]` : '';
    console.log(`  ${`${s.pageType}/${s.slug}.json`.padEnd(width)}  ${marker}  ${typeStr}`);
  }
  const missing = targets.filter((t) => !t.done);
  if (missing.length) {
    console.log('\nNo result returned (no file written, not charged):');
    for (const t of missing) console.log(`  ${t.url}`);
  }

  console.log(`\nWritten to: ${rawRoot}`);
  console.log(`Full batch archived: ${archivePath}`);
  console.log(`\nApprox cost: $${(summary.length * COST_PER_URL).toFixed(3)} (${summary.length} URL x ~$${COST_PER_URL}).`);
}

main().catch((err) => {
  console.error('ERROR:', err.message);
  process.exit(1);
});
