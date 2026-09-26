#!/usr/bin/env node
/**
 * mos-geo-schema-scraper: save the live JSON-LD of every page as one pure-JSON file.
 *
 * Plain Node 18+ ESM. No dependencies.
 *
 * Sources (pick one):
 *   --sf-csv <file>      Screaming Frog Custom Extraction export (free, default route)
 *   --sf-html <folder>   Screaming Frog stored HTML (Bulk Export > Web > All Page Source)
 *   --source apify       Apify actor `logiover/json-ld-schema-meta-tag-extractor`
 *                        (paid, about $0.006 a URL; for people without a Screaming Frog licence)
 *
 * Output (the schema/ folder is a stable current-state mirror, no -2 suffix):
 *   <schema>/raw/<page-type>/<slug>.json                   one array of JSON-LD blocks per page ([] if none)
 *   <schema>/raw/_sf-runs/YYYY-MM-DD-<epoch>.json          run record for a Screaming Frog source
 *   <schema>/raw/_apify-runs/YYYY-MM-DD-batch-<epoch>.json full Apify response
 *   <schema>/competitors/<name>/...                        with --competitor
 *
 * <schema> resolves like every mos-geo skill:
 *   one-brand brain  campaigns/geo/YYYY-MM/schema/
 *   agency brain     campaigns/geo/YYYY-MM/<brand-slug>/schema/
 *   no brain         outputs/geo/YYYY-MM/<brand-slug>/schema/   (relative to cwd)
 *   --out <dir>      overrides all of the above
 *
 * Run with --help for flags.
 */

import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs';
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { join, resolve, dirname, isAbsolute, basename } from 'node:path';
import { homedir } from 'node:os';

const ACTOR_ID = 'logiover~json-ld-schema-meta-tag-extractor';
const COST_PER_URL = 0.006;
const LIST_LIMIT = 50; // rows printed before "... and N more"

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
  node scripts/run.mjs --brand <name> --sf-csv <custom-extraction.csv> [options]
  node scripts/run.mjs --brand <name> --sf-html <page-source-folder> [options]
  node scripts/run.mjs --brand <name> --source apify --url <url>... [options]

Source (one of):
  --sf-csv <file>       Screaming Frog Custom Extraction export (extractor named JSON-LD,
                        XPath //script[@type="application/ld+json"], Extract Inner HTML).
  --sf-html <folder>    Screaming Frog stored HTML (Bulk Export > Web > All Page Source).
  --source apify        Paid fallback without Screaming Frog: Apify real-browser actor,
                        about $${COST_PER_URL} per URL. Needs --url/--urls.
  --extractor <name>    Custom Extraction name to read from --sf-csv (default: JSON-LD)

Where the files go (one of):
  --brand <name>        Brand name. Resolves the schema/ folder from the brain
                        (campaigns/geo/YYYY-MM/[<brand>/]schema/) or, with no
                        brain, outputs/geo/YYYY-MM/<brand>/schema/ under the cwd.
  --out <dir>           Use this schema/ folder instead.
  --date YYYY-MM-DD     Month to file under (default: today).

URLs:
  --url <url>           Single URL (repeatable)
  --urls <file>         Newline-delimited URL file (# comments and blank lines ignored)
                        With a Screaming Frog source these are an optional filter; without
                        them every crawled page is written. Required with --source apify.

Options:
  --page-type <type>    Force the subfolder for every URL. One of:
                          ${VALID_PAGE_TYPES.join(' | ')}
                        Omit it to classify each URL from its path.
  --competitor <name>   Write to schema/competitors/<name>/ instead of raw/
  --force               Overwrite existing per-page files
  --country <ISO>       Pin the Apify proxy country (only with --source apify)
  --print-path          Print the resolved schema/ folder and exit
  --dry-run             Print URL -> page-type/slug -> file, block counts (Screaming Frog)
                        and collisions. Writes nothing, calls nothing.
  -h, --help            Show this help

Apify token: APIFY_TOKEN from the environment, else the "token" field of
~/.apify/auth.json (written by \`apify login\`).`;

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
    source: '', sfCsv: '', sfHtml: '', extractor: 'JSON-LD',
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
    else if (f === '--source') a.source = need(++i, f);
    else if (f === '--sf-csv') a.sfCsv = need(++i, f);
    else if (f === '--sf-html') a.sfHtml = need(++i, f);
    else if (f === '--extractor') a.extractor = need(++i, f);
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
  if (a.printPath) return a;

  const chosen = [a.sfCsv && 'sf-csv', a.sfHtml && 'sf-html', a.source === 'apify' && 'apify'].filter(Boolean);
  if (a.source && a.source !== 'apify') throw new Error(`--source must be "apify" (Screaming Frog is chosen with --sf-csv or --sf-html)`);
  if (chosen.length === 0) {
    throw new Error('Choose a source: --sf-csv <custom-extraction.csv>, --sf-html <page-source-folder>, or --source apify (paid).');
  }
  if (chosen.length > 1) throw new Error(`Pick one source, got: ${chosen.join(', ')}`);
  a.mode = chosen[0];
  if (a.country && a.mode !== 'apify') throw new Error('--country only applies with --source apify');
  return a;
}

// ---- brain resolution (kept in step with mos-geo-internal-links/scripts/links.py) ----

function isFile(p) {
  try { return statSync(p).isFile(); } catch { return false; }
}

function isDir(p) {
  try { return statSync(p).isDirectory(); } catch { return false; }
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
  const gitdir = isAbsolute(raw) ? raw : resolve(dirname(gitFile), raw);
  for (let d = gitdir; ; d = dirname(d)) {
    if (basename(d) === '.git') return dirname(d);
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

// Comparable form for filtering and matching: lower-case host, no fragment, no trailing slash.
function urlKey(u) {
  try {
    const x = new URL(u);
    return `${x.protocol}//${x.host.toLowerCase()}${x.pathname.replace(/\/+$/, '') || ''}${x.search}`;
  } catch {
    return u;
  }
}

// ---- JSON-LD parsing (shared by both Screaming Frog sources) -------------------

function decodeEntities(s) {
  return s
    .replace(/&quot;/g, '"').replace(/&#0*39;|&apos;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

/** One script body -> one block. Empty -> {}. Unparseable -> {_unparsed: raw}. */
function parseBlock(text) {
  let t = String(text).trim();
  t = t.replace(/^<!--/, '').replace(/-->$/, '').trim();
  t = t.replace(/^(\/\/\s*)?<!\[CDATA\[/, '').replace(/(\/\/\s*)?\]\]>$/, '').trim();
  if (!t) return { block: {}, flag: 'empty' };
  for (const candidate of [t, decodeEntities(t)]) {
    try { return { block: JSON.parse(candidate), flag: '' }; } catch { /* try next */ }
  }
  return { block: { _unparsed: String(text) }, flag: 'unparsed' };
}

// ---- source: Screaming Frog Custom Extraction CSV ----------------------------

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else q = false;
      } else field += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.length > 1 || (r[0] || '').trim() !== '');
}

function readSfCsv(file, extractor) {
  const text = readFileSync(file, 'utf8').replace(/^﻿/, '');
  const [header, ...body] = parseCsv(text);
  if (!header) throw new Error(`${file} is empty`);
  const col = (name) => header.findIndex((h) => h.trim().toLowerCase() === name.toLowerCase());
  const addr = col('Address');
  if (addr < 0) throw new Error(`${file} has no "Address" column. Export the Custom Extraction tab from Screaming Frog.`);
  const status = col('Status Code');
  const ctype = col('Content Type');
  const indexability = col('Indexability');
  const prefix = extractor.trim().toLowerCase();
  const exCols = header
    .map((h, i) => [h.trim().toLowerCase(), i])
    .filter(([h]) => h === prefix || (h.startsWith(prefix) && /^\s*\d+$/.test(h.slice(prefix.length))))
    .map(([, i]) => i);
  if (exCols.length === 0) {
    throw new Error(
      `${file} has no "${extractor}" columns (headers: ${header.join(', ')}). ` +
      'Set up the Custom Extraction named JSON-LD before crawling, or pass --extractor <name>.'
    );
  }
  const pages = [], skipped = [];
  for (const r of body) {
    const url = (r[addr] || '').trim();
    if (!/^https?:\/\//i.test(url)) continue;
    const code = status >= 0 ? (r[status] || '').trim() : '200';
    if (code !== '200') { skipped.push({ url, reason: `status ${code || 'unknown'}` }); continue; }
    if (ctype >= 0 && r[ctype] && !/html/i.test(r[ctype])) { skipped.push({ url, reason: `content type ${r[ctype]}` }); continue; }
    if (indexability >= 0 && /^non-indexable$/i.test((r[indexability] || '').trim())) {
      skipped.push({ url, reason: 'non-indexable' });
      continue;
    }
    const blocks = [], flags = [];
    for (const i of exCols) {
      const cell = r[i];
      if (cell === undefined || cell.trim() === '') continue;
      const { block, flag } = parseBlock(cell);
      blocks.push(block);
      if (flag) flags.push(flag);
    }
    pages.push({ url, blocks, flags });
  }
  return { pages, skipped, columns: exCols.map((i) => header[i]) };
}

// ---- source: Screaming Frog stored HTML ----------------------------------------
// File -> URL mapping follows mos-geo-internal-links/scripts/links.py (map_html_files):
// canonical tag first, then og:url, then the file name; when several files share a
// canonical, a file whose own name matches keeps it and the rest fall back to their name.

function normUrl(u) {
  if (!u) return null;
  let s = decodeEntities(u.trim());
  if (/^(mailto|tel|javascript|data|sms):/i.test(s)) return null;
  try {
    const x = new URL(s);
    if (!/^https?:$/.test(x.protocol)) return null;
    x.hash = '';
    x.host = x.host.toLowerCase();
    if (!x.pathname) x.pathname = '/';
    return x.toString();
  } catch {
    return null;
  }
}

/** Tie-breaker only: original_https_site.com_a_b_.html -> https://site.com/a/b/ */
function fnameToUrl(name) {
  const m = name.match(/^(?:original_|rendered_)?(https?)_(.+?)\.html?$/i);
  if (!m) return null;
  const rest = m[2];
  const cut = rest.indexOf('_');
  const host = cut < 0 ? rest : rest.slice(0, cut);
  const path = cut < 0 ? '' : rest.slice(cut + 1);
  let url = `${m[1]}://${host}/${path.replace(/_/g, '/')}`;
  // Screaming Frog percent-encodes the query in the file name (%3Fpreview%3Dtrue).
  try { url = decodeURIComponent(url); } catch { /* keep as is */ }
  return url;
}

function extractJsonLd(html) {
  const blocks = [], flags = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const type = m[1].match(/\btype\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/i);
    const t = type ? (type[1] ?? type[2] ?? type[3] ?? '') : '';
    if (t.trim().toLowerCase() !== 'application/ld+json') continue;
    const { block, flag } = parseBlock(m[2]);
    blocks.push(block);
    if (flag) flags.push(flag);
  }
  return { blocks, flags };
}

function readSfHtml(dir) {
  if (!isDir(dir)) throw new Error(`--sf-html folder not found: ${dir}`);
  // With JavaScript rendering on, Screaming Frog exports both original_ and rendered_
  // copies of a page. Rendered comes first so it wins: it carries tag-manager schema.
  const rank = (f) => (/^rendered_/i.test(f) ? 0 : 1);
  const files = readdirSync(dir).filter((f) => /\.html?$/i.test(f))
    .sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  if (files.length === 0) throw new Error(`No .html files in ${dir}. Export Bulk Export > Web > All Page Source.`);
  const info = files.map((f) => {
    const raw = readFileSync(join(dir, f), 'utf8');
    const head = raw.slice(0, 200000);
    const can = head.match(/<link[^>]+rel=["']canonical["'][^>]*href=["']([^"']+)/i) ||
      head.match(/<link[^>]+href=["']([^"']+)["'][^>]*rel=["']canonical/i);
    const og = head.match(/<meta[^>]+property=["']og:url["'][^>]*content=["']([^"']+)/i);
    return {
      file: f, raw,
      canonical: can ? normUrl(can[1]) : null,
      og: og ? normUrl(og[1]) : null,
      fname: normUrl(fnameToUrl(f) || ''),
    };
  });
  const groups = new Map();
  for (const i of info) {
    const key = i.canonical || i.og || i.fname;
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(i);
  }
  const pages = [], notes = [], unmapped = info.filter((i) => !(i.canonical || i.og || i.fname)).map((i) => i.file);
  const seen = new Set();
  for (const [url, items] of groups) {
    for (const it of items) {
      const key = items.length === 1 ? url : (it.fname === url ? url : (it.fname || it.og));
      if (!key || seen.has(key)) { notes.push(`${it.file}: same URL as an earlier file (${key || url}), skipped`); continue; }
      seen.add(key);
      if (it.fname && it.fname !== key) notes.push(`${it.file} -> ${key} (file name says ${it.fname})`);
      const { blocks, flags } = extractJsonLd(it.raw);
      pages.push({ url: key, blocks, flags, file: it.file });
    }
  }
  return { pages, skipped: unmapped.map((f) => ({ url: f, reason: 'no canonical, og:url or parsable file name' })), notes, files: files.length };
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
  if (Array.isArray(b)) return `[array of ${b.length}]`;
  if ('_unparsed' in b && Object.keys(b).length === 1) return 'UNPARSED-JSON';
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

function printList(rows, render) {
  rows.slice(0, LIST_LIMIT).forEach((r) => console.log(render(r)));
  if (rows.length > LIST_LIMIT) console.log(`  ... and ${rows.length - LIST_LIMIT} more`);
}

// ---- targets -------------------------------------------------------------------

/**
 * Attach page-type, slug and file to each page. Two pages that land on the same file:
 * with explicit URL lists that is an error; with a crawl, keep the URL without a query
 * string (then the shorter one) and report the rest.
 */
function buildTargets(pages, args, rawRoot, strict) {
  const byFile = new Map();
  const dropped = [];
  for (const p of pages) {
    const pageType = args.pageType || classifyUrl(p.url);
    const slug = urlToSlug(p.url);
    const t = { ...p, pageType, slug, file: join(rawRoot, pageType, `${slug}.json`) };
    const prev = byFile.get(t.file);
    if (!prev) { byFile.set(t.file, t); continue; }
    if (strict) throw new Error(`Two URLs map to the same file ${pageType}/${slug}.json:\n  ${prev.url}\n  ${t.url}`);
    const rank = (x) => [new URL(x.url).search ? 1 : 0, x.url.length];
    const [a, b] = [rank(prev), rank(t)];
    const keepNew = b[0] < a[0] || (b[0] === a[0] && b[1] < a[1]);
    const loser = keepNew ? prev : t;
    if (keepNew) byFile.set(t.file, t);
    dropped.push({ url: loser.url, reason: `same file as ${(keepNew ? t : prev).url}` });
  }
  return { targets: [...byFile.values()], dropped };
}

function applyFilter(pages, filterUrls) {
  if (!filterUrls.length) return { pages, missing: [] };
  const want = new Map(filterUrls.map((u) => [urlKey(u), u]));
  const kept = pages.filter((p) => want.has(urlKey(p.url)));
  const found = new Set(kept.map((p) => urlKey(p.url)));
  return { pages: kept, missing: filterUrls.filter((u) => !found.has(urlKey(u))) };
}

async function writePages(targets) {
  for (const t of targets) {
    await mkdir(dirname(t.file), { recursive: true });
    await writeFile(t.file, JSON.stringify(t.blocks, null, 2) + '\n');
  }
}

function printSummary(targets, rawRoot) {
  console.log(`\nResults (${targets.length} page(s)):`);
  const width = Math.max(40, ...targets.slice(0, LIST_LIMIT).map((s) => `${s.pageType}/${s.slug}.json`.length));
  printList(targets, (s) => {
    const n = s.blocks.length;
    const marker = n === 0 ? 'EMPTY     ' : `${n} block(s)`;
    const types = n ? `[${s.blocks.map(describeBlock).join(', ')}]` : '';
    return `  ${`${s.pageType}/${s.slug}.json`.padEnd(width)}  ${marker}  ${types}`;
  });
  const empty = targets.filter((t) => t.blocks.length === 0).length;
  const unparsed = targets.filter((t) => (t.flags || []).includes('unparsed'));
  const emptyScripts = targets.filter((t) => (t.flags || []).includes('empty'));
  console.log(`\nPages with schema: ${targets.length - empty}. Pages with none: ${empty}.`);
  if (unparsed.length) {
    console.log(`Broken JSON-LD (kept as {"_unparsed": ...}, a finding): ${unparsed.length} page(s)`);
    printList(unparsed, (t) => `  ${t.pageType}/${t.slug}.json  <- ${t.url}`);
  }
  if (emptyScripts.length) {
    console.log(`Empty JSON-LD script tags ({}): ${emptyScripts.length} page(s)`);
    printList(emptyScripts, (t) => `  ${t.pageType}/${t.slug}.json  <- ${t.url}`);
  }
  console.log(`\nWritten to: ${rawRoot}`);
}

async function guardCollisions(targets, args) {
  const hits = [];
  for (const t of targets) if (await fileExists(t.file)) hits.push(t);
  if (hits.length && !args.force && !args.dryRun) {
    console.error(`\n${hits.length} existing file(s) would be overwritten:`);
    printList(hits, (c) => `  ${c.pageType}/${c.slug}.json  <- ${c.url}`);
    console.error('\nRe-run with --force to overwrite (commit or copy the old files first if you need them).');
    process.exit(2);
  }
  return hits;
}

function printDryRun(targets, hits, args, schemaDir, rawRoot, withCounts) {
  console.log(`Schema folder: ${schemaDir}`);
  console.log(`Writing to:    ${rawRoot}\n`);
  const hitSet = new Set(hits);
  printList(targets, (t) => {
    const flag = hitSet.has(t) ? (args.force ? '  (exists, --force will overwrite)' : '  (EXISTS, would refuse)') : '';
    const count = withCounts ? `  ${t.blocks.length} block(s)` : '';
    return `  ${t.url}\n    -> ${t.pageType}/${t.slug}.json${count}${flag}`;
  });
}

// ---- main --------------------------------------------------------------------

async function runScreamingFrog(args, schemaDir, rawRoot, filterUrls) {
  const src = args.mode === 'sf-csv' ? readSfCsv(resolve(args.sfCsv), args.extractor) : readSfHtml(resolve(args.sfHtml));
  const { pages, missing } = applyFilter(src.pages, filterUrls);
  const { targets, dropped } = buildTargets(pages, args, rawRoot, false);
  const skipped = [...src.skipped, ...dropped];

  const sourceLabel = args.mode === 'sf-csv'
    ? `Screaming Frog Custom Extraction export ${resolve(args.sfCsv)} (columns: ${src.columns.join(', ')})`
    : `Screaming Frog stored HTML ${resolve(args.sfHtml)} (${src.files} file(s))`;
  console.log(`Source: ${sourceLabel}`);
  console.log(`Crawled HTML pages: ${src.pages.length}. Writing: ${targets.length}. Skipped: ${skipped.length}.`);
  if (filterUrls.length) console.log(`Filtered to ${filterUrls.length} URL(s) from --url/--urls; ${missing.length} not in the crawl.`);

  const hits = await guardCollisions(targets, args);
  if (args.dryRun) {
    printDryRun(targets, hits, args, schemaDir, rawRoot, true);
  } else {
    await writePages(targets);
    const runsDir = join(rawRoot, '_sf-runs');
    await mkdir(runsDir, { recursive: true });
    const record = {
      date: args.date,
      source: args.mode,
      input: resolve(args.mode === 'sf-csv' ? args.sfCsv : args.sfHtml),
      extractorColumns: src.columns || null,
      filter: filterUrls,
      counts: {
        pagesInCrawl: src.pages.length,
        written: targets.length,
        withSchema: targets.filter((t) => t.blocks.length).length,
        withoutSchema: targets.filter((t) => !t.blocks.length).length,
        blocks: targets.reduce((n, t) => n + t.blocks.length, 0),
        unparsedPages: targets.filter((t) => (t.flags || []).includes('unparsed')).length,
        skipped: skipped.length,
        filterMissing: missing.length,
      },
      pages: targets.map((t) => ({ url: t.url, file: `${t.pageType}/${t.slug}.json`, blocks: t.blocks.length, flags: t.flags || [] })),
      skipped,
      filterMissing: missing,
      mappingNotes: src.notes || [],
    };
    const recordPath = join(runsDir, `${args.date}-${Date.now()}.json`);
    await writeFile(recordPath, JSON.stringify(record, null, 2) + '\n');
    printSummary(targets, rawRoot);
    console.log(`Run record: ${recordPath}`);
  }
  if (skipped.length) {
    console.log(`\nSkipped (no file written): ${skipped.length}`);
    printList(skipped, (s) => `  ${s.url}  (${s.reason})`);
  }
  if (missing.length) {
    console.log('\nNot found in the crawl:');
    printList(missing, (u) => `  ${u}`);
  }
  if (args.dryRun) console.log('\nDry run: nothing written. Screaming Frog sources cost nothing.');
}

async function runApify(args, schemaDir, rawRoot, allUrls) {
  if (allUrls.length === 0) throw new Error('--source apify needs URLs: --url <url> (repeatable) or --urls <file>.');
  for (const u of allUrls) {
    try { new URL(u); } catch { throw new Error(`Not a valid URL: ${u}`); }
  }
  const { targets } = buildTargets(allUrls.map((url) => ({ url, blocks: [], flags: [] })), args, rawRoot, true);
  const hits = await guardCollisions(targets, args);
  if (args.dryRun) {
    printDryRun(targets, hits, args, schemaDir, rawRoot, false);
    console.log(`\n${allUrls.length} URL(s), approx cost $${(allUrls.length * COST_PER_URL).toFixed(3)}. Dry run: nothing sent to Apify.`);
    return;
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

  const runsDir = join(rawRoot, '_apify-runs');
  await mkdir(runsDir, { recursive: true });
  const archivePath = join(runsDir, `${args.date}-batch-${Date.now()}.json`);
  await writeFile(archivePath, JSON.stringify(items, null, 2) + '\n');

  const byKey = new Map(targets.map((t) => [urlKey(t.url), t]));
  const done = [];
  for (const item of items) {
    const t = byKey.get(urlKey(item.url || ''));
    if (!t || t.done) continue;
    t.done = true;
    t.blocks = Array.isArray(item.jsonLd) ? item.jsonLd : [];
    done.push(t);
  }
  await writePages(done);
  printSummary(done, rawRoot);
  const missing = targets.filter((t) => !t.done);
  if (missing.length) {
    console.log('\nNo result returned (no file written, not charged):');
    printList(missing, (t) => `  ${t.url}`);
  }
  console.log(`Full batch archived: ${archivePath}`);
  console.log(`\nApprox cost: $${(done.length * COST_PER_URL).toFixed(3)} (${done.length} URL x ~$${COST_PER_URL}).`);
}

async function main() {
  const args = parseArgs(process.argv);
  const schemaDir = schemaDirFor(args, process.cwd());
  if (args.printPath) {
    console.log(schemaDir);
    return;
  }
  const urls = [...args.urls];
  if (args.urlsFile) urls.push(...(await loadUrlsFromFile(args.urlsFile)));
  const rawRoot = args.competitor
    ? join(schemaDir, 'competitors', slugify(args.competitor))
    : join(schemaDir, 'raw');
  if (args.mode === 'apify') await runApify(args, schemaDir, rawRoot, urls);
  else await runScreamingFrog(args, schemaDir, rawRoot, urls);
}

main().catch((err) => {
  console.error('ERROR:', err.message);
  process.exit(1);
});
