---
name: mos-geo-schema-scraper
description: >
  Pull the live JSON-LD schema markup from one URL or a list of URLs and save it as one pure-JSON
  file per page: the "before" snapshot of a schema rebuild. It runs the Apify actor
  `logiover/json-ld-schema-meta-tag-extractor`, which renders each page in a real browser behind a
  proxy, so it sees schema injected by Google Tag Manager or JavaScript that a plain fetch misses.
  Pages are sorted into folders by type (homepage, about page, pillar pages, guides, author pages,
  products, collections, blog posts), a page with no schema gets an empty array `[]`, and the full
  Apify response is archived. It can also snapshot a competitor's pages. About $0.006 per URL.
  USE WHEN the user says "scrape schema", "extract schema", "get current schema", "extract
  JSON-LD", "scrape structured data", "schema baseline", "what schema is on these pages", "schema
  audit" with a list of URLs, "/mos-geo-schema-scraper", or pastes URLs and asks for their schema
  markup.
  NOT FOR writing the schema optimisation brief from a Screaming Frog export (use
  mos-geo-schema-optimisation, the next step), writing one schema file for a brand's AI Info Page
  (use mos-geo-ai-info), whole-site crawls of thousands of URLs, or pages behind a login.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
---

# Schema scraper

**Step 1 of a schema rebuild: record what is live today.**

You pull the rendered JSON-LD from a list of URLs and save it exactly as found, one file per page.
That is the OLD state. The rewrites (`optimised/`) and the brief come later; they need the same
filenames so the old and new versions line up side by side.

The Apify actor renders each page in real Chrome behind a proxy, so it catches schema injected by
Google Tag Manager or JavaScript. Each URL costs about $0.006.

Set `SKILL=<this skill's folder>` and run from the user's project so files land in their brain.

## Where the files go

Same brain rules as the other mos-geo skills. A folder is a MarketingOS brain when it (or, for a
git worktree, its main checkout) has `.mos/config.yaml`; `mode: agency` in that file means each
brand gets its own folder.

| Situation | schema folder |
| --- | --- |
| One-brand brain | `campaigns/geo/YYYY-MM/schema/` |
| Agency brain | `campaigns/geo/YYYY-MM/<brand-slug>/schema/` |
| No brain | `outputs/geo/YYYY-MM/<brand-slug>/schema/` (under the current folder) |
| `--out <dir>` | that folder, whatever else is true |

Unlike other mos-geo skills there is **no `-2` suffix** for a repeat run in the same month. The
schema folder is a stable current-state mirror: `raw/homepage/homepage.json` and
`optimised/homepage/homepage.json` must share a name.

```
schema/
  raw/<page-type>/<slug>.json                 THIS SKILL: live schema, pure JSON, [] if none
  raw/_apify-runs/YYYY-MM-DD-batch-<epoch>.json  full Apify response for the run
  competitors/<name>/<page-type>/<slug>.json  THIS SKILL with --competitor
  optimised/                                  human rewrites (not this skill)
  brief/                                      mos-geo-schema-optimisation
```

Print the resolved folder without scraping anything:

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" --print-path
```

Never commit a schema folder into this pack: it holds client data.

## Workflow

### 1. Pre-flight

Node 18 or newer is the only runtime needed (`node --version`). The script has no dependencies.

Check for an Apify token without printing it:

```bash
if [ -n "$APIFY_TOKEN" ]; then echo "Apify: APIFY_TOKEN is set"
elif [ -f "$HOME/.apify/auth.json" ]; then echo "Apify: token in $HOME/.apify/auth.json"
else echo "MISSING: no Apify token"; fi
```

If it is missing, stop and tell the user:

> No Apify token found. Either set `APIFY_TOKEN` in your environment, or run `apify login`
> (install the CLI first with `npm install -g apify-cli`), which saves the token to
> `~/.apify/auth.json`. Then run this again.

Do not attempt a paid run without a token.

### 2. Confirm the brand and collect the URLs

Ask which brand this is for (it names the folder) unless it is obvious from the brain. Then ask
for the URLs: one, or a pasted list (one per line; blank lines and lines starting with `#` are
ignored). For a long list, save it to a text file outside the pack and pass `--urls <file>`.

### 3. Dry run, then ask before spending

Always run a dry run first. It needs no token and makes no API call:

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" --dry-run \
  --url "https://harbourmeals.example/" \
  --url "https://harbourmeals.example/about-us/"
```

It prints each URL, the page-type folder and filename it maps to, any file that already exists,
and the approximate cost. Show that mapping and the cost to the user and get a clear yes before
the real run. If a file already exists, ask whether to overwrite it (`--force`).

#### Page-type folders and slugs

Page type comes from the URL path unless `--page-type` forces one type for the whole batch.

| URL path | Page type | File |
| --- | --- | --- |
| `/` | `homepage` | `raw/homepage/homepage.json` |
| `/about` or `/about-us/` | `about-page` | `raw/about-page/about-us.json` |
| any path containing `/author/` | `author-pages` | `raw/author-pages/team--author--sam-lee.json` |
| `/products/*` | `products` | `raw/products/products--weekly-box.json` |
| `/collections/*` | `collections` | `raw/collections/collections--vegan.json` |
| `/blogs/*` | `blog-posts` | `raw/blog-posts/blogs--news--meal-prep-tips.json` |
| one path segment, e.g. `/meal-plans/` | `pillar-pages` | `raw/pillar-pages/meal-plans.json` |
| anything deeper | `guides` | `raw/guides/meal-plans--family.json` |

Slugs: `/` in the path becomes `--`, any other run of non-alphanumeric characters becomes one
`-`, all lower case. Valid `--page-type` values: `homepage`, `about-page`, `pillar-pages`,
`guides`, `author-pages`, `products`, `collections`, `blog-posts`.

If two URLs map to the same file (for example with and without a trailing slash) the script
stops before spending anything. If a target file already exists it refuses the whole run unless
`--force` is passed.

### 4. Run the extractor

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" \
  --url "https://harbourmeals.example/" \
  --url "https://harbourmeals.example/about-us/"

node "$SKILL/scripts/run.mjs" --brand "<brand>" --urls <path to url list>

# a known set of one type
node "$SKILL/scripts/run.mjs" --brand "<brand>" --page-type products --urls <path to url list>

# a competitor's pages, saved beside the brand's own
node "$SKILL/scripts/run.mjs" --brand "<brand>" --competitor "<competitor name>" --urls <path>
```

Other flags: `--out <dir>` to choose the schema folder, `--date YYYY-MM-DD` to file under another
month, `--country AU` to pin the proxy country.

The script:

1. Reads the token from `APIFY_TOKEN`, else `~/.apify/auth.json`.
2. Starts ONE batched actor run for every URL (one call regardless of URL count), then polls it
   until it finishes. It deliberately does not use Apify's synchronous endpoint, which cuts off at
   300 seconds and returns an empty dataset on a large batch.
3. Writes `<slug>.json` into `raw/<page-type>/` (or `competitors/<name>/<page-type>/`): the array
   of JSON-LD blocks exactly as found, `[]` if none.
4. Archives the full Apify response to `raw/_apify-runs/YYYY-MM-DD-batch-<epoch>.json`.
5. Prints a summary: file, block count, and the top-level `@type` of each block.

### 5. Report

Quote the summary back and flag what matters:

- **Zero-schema pages.** An empty `[]` is a finding, especially on trust pages (about, author,
  contact).
- **Empty `{}` blocks** (shown as `{} EMPTY-SCRIPT`). A `<script type="application/ld+json">`
  with nothing in it is a broken implementation, not "no schema". High-priority fix.
- **Duplicate blocks of the same type** (two `FAQPage` blocks on one page). Recommend
  consolidating into one.
- **`@graph` pages** (shown as `@graph(Organization+WebSite)`). Pages that use `@graph` with
  `@id` references well are the model to standardise across the site.
- **Invalid property names**, such as `sameAS` with a capital S. Easy to miss, easy to fix.

Then tick the skill's row in the month's audit workbook, but only if that workbook already exists
(`brand-audit-master.xlsx` in the folder that holds `schema/`):

```bash
RUN=<the schema folder>
if [ -f "$RUN/../brand-audit-master.xlsx" ]; then
  uv run --with openpyxl python "$SKILL/../_shared/brand-audit/tick_checklist.py" \
    --skill mos-geo-schema-scraper --run-dir "$RUN" --status "In progress" \
    --note "live schema for <n> pages in schema/raw/"
fi
```

End with the next step: *"Baseline saved. Next: `mos-geo-schema-optimisation` turns a Screaming
Frog structured data export into the brief, and uses these files for the 'Schema Implemented
Currently' column."*

## Rules for the files

**Pure JSON only in `raw/`.** No markdown wrappers, no commentary, no `@type` summaries. Notes
belong in the conversation or a sidecar markdown file outside `raw/`. A side-by-side comparison
needs files of identical shape.

**No date prefix on per-page files.** `raw/homepage/homepage.json` and
`optimised/homepage/homepage.json` must share a name. Only the `_apify-runs/` archive carries a
date, because it is a run log.

**Clean, comment-free deploy schema.** When the rewrites and the developer hand-off are drafted
later, the schema a developer copies must be the final output only. Strip every
`{% comment %}...{% endcomment %}`, `//`, `/* */` and `<!-- -->` from the schema to implement:
developers paste it verbatim, and a stray comment breaks JSON validators. Keep the reasoning
(metafield dependencies, assumptions, "verify before deploy" flags) in the surrounding spec rows or
prose, never inside the schema block. Beside each template, ship a worked example filled with one
real page's live data so the developer sees the final shape, not just the template syntax.

## Examples

**One page.** "Get me the current schema for harbourmeals.example/awards/". Confirm the brand,
check the token, dry run (`raw/pillar-pages/awards.json`), get a yes, run it. Report: "awards.json,
0 blocks. The Awards page ships no schema, a good candidate for Organization plus an ItemList of
awards."

**A batch of five.** Confirm brand and token, dry run and show the mapping plus "about $0.03",
run once with all five URLs, report the table and flag empty blocks or duplicate types.

**Re-baseline after a deploy.** The developers changed `/meal-plans/`. The dry run shows
`raw/pillar-pages/meal-plans.json` already exists. Ask before overwriting; on a yes, run with
`--force`. Tell the user to commit or copy the old file first if they want the before-and-after.

## Troubleshooting

**"No Apify token."** Set `APIFY_TOKEN` or run `apify login`. If the `apify` command is missing,
`npm install -g apify-cli` first.

**Empty `jsonLd` for a page that visibly has schema.** The actor renders in real Chrome, so if it
still sees nothing:

- Geo-blocked: the page only serves schema to visitors from one country. Re-run with
  `--country AU` (or the right country).
- Behind a login: this actor carries no session cookies.
- Late injection: the schema arrives well after the page settles. Re-run once. If it is still
  empty, open the page in a real browser, let it finish loading and view the rendered source
  (developer tools, Elements panel) to see whether the schema is there at all.

**The whole batch returns 0 items but a single URL works.** Someone switched the script to
Apify's synchronous endpoint, which stops at 300 seconds. Keep the async start-and-poll.

**A block shows `<no-@type>` or `{} EMPTY-SCRIPT`.** `@graph(...)` means the entities are inside
a `@graph` array, which is fine. `{} EMPTY-SCRIPT` is an empty script tag: a broken
implementation to flag.

**"No result returned" for some URLs.** The actor could not load them (timeouts, blocks, 404s).
Nothing is written for those and they are not charged. Check the URL in a browser and re-run
just those.

**Shopify stores.** `/products/`, `/collections/` and `/blogs/` get their own folders. Build the
URL list from the store's `sitemap.xml` index, which Shopify splits into `sitemap_products_*`,
`sitemap_collections_*` and `sitemap_blogs_*`.

## Pricing

The actor charges per dataset item, which is one per URL scraped. Failed URLs are not charged.
Pay per event, no idle cost.

| Apify plan tier | Price per URL |
| --- | --- |
| Free | about $0.006 ($0.005 plus Apify's margin). Fine for typical 5 to 50 URL audits. |
| Bronze | slightly less |
| Silver and above | $0.0035 to $0.004 plus margin; only matters at sustained high volume |

A batch of 100 URLs is about $0.60. If someone asks for a whole-site audit (thousands of URLs),
pause and confirm: that belongs in Apify directly with a crawl budget, not in this skill, which
expects a curated list.

## Where this sits

```
Step 1  Baseline the live schema          THIS SKILL
Step 2  Brief: audit + recommendations    mos-geo-schema-optimisation
Step 3  Draft optimised/<page-type>/<slug>.json rewrites (human judgement: @id strategy, entity graph, typing)
Step 4  Side-by-side OLD vs NEW hand-off to the developers, batched into one drop
```

This skill stops at step 1.

## Related skills

- **`mos-geo-schema-optimisation`**: the next step. Builds the client-ready schema brief and
  prefers these files for the "currently implemented" column.
- **`mos-geo-ai-info`**: writes one schema file for the brand's AI Info Page.
- **`mos-geo-brand-360`**: tests whether AI engines know, find and recommend the brand at all.
