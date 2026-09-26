---
name: mos-geo-schema-scraper
description: >
  Save the live JSON-LD schema markup of every page on a site as one pure-JSON file per page: the
  "before" snapshot of a schema rebuild. Free by default: it reads a Screaming Frog crawl, either a
  Custom Extraction export (every `<script type="application/ld+json">` pulled by XPath) or the
  stored HTML, with JavaScript rendering on so schema added by Google Tag Manager or JavaScript is
  caught. Pages are sorted into folders by type (homepage, about page, pillar pages, guides, author
  pages, products, collections, blog posts), a page with no schema gets an empty array `[]`, broken
  JSON-LD is kept and flagged, and a run record is saved. It can also snapshot a competitor's
  pages. No Screaming Frog licence? An optional Apify fallback renders a URL list for about $0.006
  a URL.
  USE WHEN the user says "scrape schema", "extract schema", "get current schema", "extract
  JSON-LD", "scrape structured data", "schema baseline", "what schema is on these pages", "schema
  audit" with a crawl or a list of URLs, "/mos-geo-schema-scraper", or hands over a Screaming Frog
  custom extraction export or saved page HTML and asks for the schema.
  NOT FOR writing the schema optimisation brief from Screaming Frog's structured data export (use
  mos-geo-schema-optimisation, the next step; both can share one crawl), writing one schema file
  for a brand's AI Info Page (use mos-geo-ai-info), or pages behind a login.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
---

# Schema scraper

**Step 1 of a schema rebuild: record what is live today.**

You save the rendered JSON-LD of each page exactly as found, one file per page. That is the OLD
state. The rewrites (`optimised/`) and the brief come later; they need the same filenames so the
old and new versions line up side by side.

The default route costs nothing: a Screaming Frog crawl the user runs on their own machine. Apify
is only a fallback for people without a paid Screaming Frog licence, which JavaScript rendering,
custom extraction and stored HTML all need.

Set `SKILL=<this skill's folder>` and run from the user's project so files land in their brain.
Node 18 or newer is the only runtime (`node --version`); the script has no dependencies.

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
  raw/_sf-runs/YYYY-MM-DD-<epoch>.json        run record: source file, counts, skipped pages
  raw/_apify-runs/YYYY-MM-DD-batch-<epoch>.json  full Apify response (fallback only)
  competitors/<name>/<page-type>/<slug>.json  THIS SKILL with --competitor
  optimised/                                  human rewrites (not this skill)
  brief/                                      mos-geo-schema-optimisation
```

Print the resolved folder without reading anything:

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" --print-path
```

Never commit a schema folder into this pack: it holds client data.

## Workflow

### 1. Send the crawl settings first

One crawl feeds both schema skills, so set it up once. Send this list as the first message,
before asking for anything else. In Screaming Frog, **before** pressing Start:

1. **Configuration > Custom > Custom Extraction:** add an extractor named `JSON-LD`, type
   **XPath**, expression `//script[@type="application/ld+json"]`, and choose **Extract Inner
   HTML**. Screaming Frog writes one column per match (`JSON-LD 1`, `JSON-LD 2` ...).
2. **Configuration > Spider > Rendering:** set **JavaScript**. This is what catches schema added
   by Google Tag Manager or a JavaScript framework.
3. **Configuration > Spider > Extraction:** tick **Store HTML** and **Store Rendered HTML**
   (optional, but it lets the stored-HTML route below run as a cross-check). While there, tick
   the **JSON-LD** structured data options with validation if the brief will follow:
   `mos-geo-schema-optimisation` reads the Structured Data export from the same crawl.
4. Crawl the site (**Mode > Spider**), or only the pages that matter (**Mode > List**, paste the
   URLs).
5. Tip: **File > Configuration > Save As** keeps these settings as a `.seospiderconfig` for next
   time, which is also what Screaming Frog's command line needs (`--config`).

### 2. Ask for the files, in one message

- **The Custom Extraction export:** the **Custom Extraction** tab, filter **All**, Export (CSV).
  Or, if they stored HTML instead:
- **The stored HTML:** **Bulk Export > Web > All Page Source**. Don't rename the files: they map
  to URLs by their canonical tag, and the file name is only the fallback. Where both
  `original_` and `rendered_` copies exist, the rendered copy wins.
- **The brand name** (it names the folder), unless the brain makes it obvious.
- Optional: a list of URLs to limit the output to. Without one, every crawled page is written.

### 3. Dry run

Free and writes nothing. It reads the export, prints how many pages it found, each URL with its
page-type folder, filename and block count, which rows are skipped and why, and any file that
already exists:

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" --sf-csv <custom_extraction_all.csv> --dry-run
node "$SKILL/scripts/run.mjs" --brand "<brand>" --sf-html <page source folder> --dry-run
```

Long lists are cut at 50 rows with a count of the rest. If files already exist (a re-baseline),
ask before overwriting with `--force`.

#### Page-type folders and slugs

Page type comes from the URL path unless `--page-type` forces one type for the whole run.

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
`-`, all lower case, query string ignored. Valid `--page-type` values: `homepage`, `about-page`,
`pillar-pages`, `guides`, `author-pages`, `products`, `collections`, `blog-posts`.

When two crawled URLs land on the same file (`/page/` and `/page//`, or a `?preview=true`
copy), the one without a query string (then the shorter one) is kept and the other is listed as
skipped. If a target file already exists the whole run stops unless `--force` is passed.

### 4. Run it

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" --sf-csv <custom_extraction_all.csv>

# only some pages
node "$SKILL/scripts/run.mjs" --brand "<brand>" --sf-csv <csv> --urls <url list file>

# stored HTML instead of the extraction export
node "$SKILL/scripts/run.mjs" --brand "<brand>" --sf-html <page source folder>

# a competitor's crawl, saved beside the brand's own
node "$SKILL/scripts/run.mjs" --brand "<brand>" --competitor "<competitor name>" --sf-csv <csv>
```

Other flags: `--out <dir>` to choose the schema folder, `--date YYYY-MM-DD` to file under another
month, `--page-type <type>`, `--extractor <name>` if the extractor was not called `JSON-LD`.

The script:

1. Reads the export. From a CSV: the `Address` column plus every column named after the
   extractor (`JSON-LD`, `JSON-LD 1`, `JSON-LD 2` ...); blank cells are ignored; rows that are
   not status 200 HTML (or are marked Non-Indexable, where that column exists) are skipped and
   listed. From stored HTML: every `<script type="application/ld+json">`, whatever the case of
   the type or the order of the attributes.
2. Turns each script into one block: HTML comment and CDATA wrappers are stripped, then it is
   parsed as JSON. An empty script tag becomes `{}`. JSON that will not parse is kept as
   `{"_unparsed": "<raw text>"}` and flagged, because a broken block is a finding.
3. Writes `<slug>.json` into `raw/<page-type>/` (or `competitors/<name>/<page-type>/`).
4. Saves a run record to `raw/_sf-runs/YYYY-MM-DD-<epoch>.json`: source file, counts, every page
   written with its block count, skipped rows and the file-to-URL mapping notes.
5. Prints a summary: file, block count and the top-level `@type` of each block, then pages with
   and without schema, broken blocks and empty script tags.

Big crawls are fine: there is no cost, and the summary shows the first 50 rows plus counts.

### 5. Report

Quote the summary back and flag what matters:

- **Zero-schema pages.** An empty `[]` is a finding, especially on trust pages (about, author,
  contact).
- **Broken blocks** (`UNPARSED-JSON`). Invalid JSON in a script tag: search engines ignore it.
  High-priority fix.
- **Empty `{}` blocks** (`{} EMPTY-SCRIPT`). A JSON-LD script tag with nothing in it. Only the
  stored-HTML route can see these; an empty tag leaves a blank cell in the extraction export.
- **Duplicate blocks of the same type** (two `FAQPage` blocks on one page). Recommend
  consolidating into one.
- **`@graph` pages** (shown as `@graph(Organization+WebSite)`). Pages that use `@graph` with
  `@id` references well are the model to standardise across the site.
- **Invalid property names**, such as `sameAS` with a capital S.

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

End with the next step: *"Baseline saved. Next: `mos-geo-schema-optimisation` builds the brief
from the Structured Data export of the same crawl, and uses these files for the 'Schema
Implemented Currently' column."*

## No Screaming Frog licence? The Apify fallback

The free version of Screaming Frog cannot render JavaScript, run custom extraction or store HTML,
so it cannot feed this skill. The fallback is an Apify actor
(`logiover/json-ld-schema-meta-tag-extractor`) that renders each URL in real Chrome behind a
proxy. It needs a URL list and costs money, so it is opt-in.

**Cost.** About $0.006 per URL on Apify's free tier ($0.005 plus Apify's margin), charged per URL
scraped; failed URLs are not charged. 50 URLs is about $0.30, 100 about $0.60. For a whole site,
the Screaming Frog trial or licence is cheaper.

**Pre-flight.** Check for a token without printing it:

```bash
if [ -n "$APIFY_TOKEN" ]; then echo "Apify: APIFY_TOKEN is set"
elif [ -f "$HOME/.apify/auth.json" ]; then echo "Apify: token in $HOME/.apify/auth.json"
else echo "MISSING: no Apify token"; fi
```

If it is missing: set `APIFY_TOKEN`, or run `apify login` (install the CLI first with
`npm install -g apify-cli`), which saves the token to `~/.apify/auth.json`.

**Dry run, then ask before spending.** Show the mapping and the cost and get a clear yes:

```bash
node "$SKILL/scripts/run.mjs" --brand "<brand>" --source apify --dry-run --urls <url list file>
node "$SKILL/scripts/run.mjs" --brand "<brand>" --source apify --urls <url list file>
```

`--country AU` pins the proxy country (Apify only). The run is one batched actor call started
asynchronously and polled until it finishes; it deliberately does not use Apify's synchronous
endpoint, which cuts off at 300 seconds and returns an empty dataset on a large batch. The full
response is archived to `raw/_apify-runs/`. With Apify, two URLs that map to the same file stop
the run before anything is spent.

## Rules for the files

**Pure JSON only in `raw/`.** No markdown wrappers, no commentary, no `@type` summaries. Notes
belong in the conversation or a sidecar markdown file outside `raw/`. A side-by-side comparison
needs files of identical shape.

**No date prefix on per-page files.** `raw/homepage/homepage.json` and
`optimised/homepage/homepage.json` must share a name. Only the run records carry a date.

**Clean, comment-free deploy schema.** When the rewrites and the developer hand-off are drafted
later, the schema a developer copies must be the final output only. Strip every
`{% comment %}...{% endcomment %}`, `//`, `/* */` and `<!-- -->` from the schema to implement:
developers paste it verbatim, and a stray comment breaks JSON validators. Keep the reasoning
(metafield dependencies, assumptions, "verify before deploy" flags) in the surrounding spec rows or
prose, never inside the schema block. Beside each template, ship a worked example filled with one
real page's live data so the developer sees the final shape, not just the template syntax.

## Examples

**Whole site.** The user sends `custom_extraction_all.csv` from a 400-page crawl. Dry run: 398
pages, 2 skipped (301s). Run it. Report: "312 pages ship schema, 86 ship none, including the
About and Contact pages; 3 product pages have broken JSON-LD."

**A few pages from a big crawl.** Same export, `--urls` with the five priority URLs. Four
written, one "not found in the crawl": check it was crawled.

**Re-baseline after a deploy.** The developers changed the product template. New crawl, dry run
shows the product files already exist; ask, then run with `--force`. Tell the user to commit or
copy the old files first if they want the before-and-after.

## Troubleshooting

**"has no JSON-LD columns".** The Custom Extraction was not set up before crawling, or it has
another name (`--extractor <name>`). Custom extraction only applies to pages crawled after it is
added: set it up and crawl again.

**Every page comes back empty but the site has schema.** JavaScript rendering was off and the
schema is injected by a tag manager. Set Rendering to JavaScript and crawl again. To check one
page by hand, open it in a real browser, let it finish loading and view the rendered source
(developer tools, Elements panel).

**Stored HTML maps a file to the wrong URL.** The file is mapped by its canonical tag; pages
canonicalised elsewhere land on the canonical URL. The run record's `mappingNotes` lists every
case where the canonical and the file name disagree.

**Behind a login.** Neither route carries a logged-in session unless Screaming Frog is set up
with authentication.

**Apify: the whole batch returns 0 items but a single URL works.** Someone switched the script to
Apify's synchronous endpoint. Keep the async start-and-poll.

**Shopify stores.** `/products/`, `/collections/` and `/blogs/` get their own folders. For a List
mode crawl, build the URL list from the store's `sitemap.xml` index (`sitemap_products_*`,
`sitemap_collections_*`, `sitemap_blogs_*`).

## Where this sits

```
Step 1  Baseline the live schema          THIS SKILL (one Screaming Frog crawl)
Step 2  Brief: audit + recommendations    mos-geo-schema-optimisation (same crawl)
Step 3  Draft optimised/<page-type>/<slug>.json rewrites (human judgement: @id strategy, entity graph, typing)
Step 4  Side-by-side OLD vs NEW hand-off to the developers, batched into one drop
```

This skill stops at step 1.

## Related skills

- **`mos-geo-schema-optimisation`**: the next step. Builds the client-ready schema brief from the
  same crawl and prefers these files for the "currently implemented" column.
- **`mos-geo-internal-links`**: also reads Screaming Frog's stored HTML; one crawl with Store HTML
  on serves both.
- **`mos-geo-ai-info`**: writes one schema file for the brand's AI Info Page.
- **`mos-geo-brand-360`**: tests whether AI engines know, find and recommend the brand at all.
