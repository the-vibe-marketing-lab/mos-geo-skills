---
name: mos-geo-schema-optimisation
description: >
  Turn a Screaming Frog structured data export into a tight, client-ready schema markup
  optimisation brief as a landscape Word document. It audits what schema the site ships today,
  picks the 3 to 5 highest-impact gaps, and writes: a cover, an Executive summary, three Current
  state audit tables (crawl overview, schema types deployed, page template breakdown), one
  4-column Schema recommendations table (Page | Currently implemented | Template with
  [Placeholder] slots | Example filled with the brand's real values) and short Notes. Values that
  need checking become real Word margin comments that survive upload to Google Docs. When
  mos-geo-schema-scraper has already saved the live rendered schema for this brand, that is used
  for the "currently implemented" column.
  USE WHEN the user says "schema optimisation", "schema brief", "structured data brief", "schema
  markup audit", "schema report", "schema recommendations", "/mos-geo-schema-optimisation", or
  hands over a Screaming Frog structured data CSV, or mentions "structured data" alongside
  "Screaming Frog", "crawl" or "audit".
  NOT FOR pulling the live schema from a list of URLs (use mos-geo-schema-scraper first), one
  schema file for a brand's AI Info Page (use mos-geo-ai-info), writing the final optimised JSON
  files for every page, or promising AI citations from schema (the evidence does not support it:
  _shared/geo-evidence.md, section 9).
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
  - Edit
  - WebFetch
  - WebSearch
  - AskUserQuestion
---

# Schema optimisation brief

You produce a **short, dev-ready schema brief as a landscape DOCX**: what the site ships today,
the 3 to 5 schemas that matter most, and for each one a template the developer maps to the CMS
plus a worked example filled with the brand's real values.

Set `SKILL=<this skill's folder>` and run from the user's project so files land in their brain.

## Format philosophy (read first)

The deliverable has this exact section order:

1. Cover page
2. **Executive summary**: 1 to 2 short paragraphs. What was crawled, the high-level diagnosis,
   what this document delivers.
3. **Current state**: three small audit tables
   - Crawl overview (2 columns) plus a one-sentence assessment
   - Schema types currently deployed (3 columns: Type | Pages | Assessment)
   - Page template breakdown (4 columns: Template | Pages | Current Schema | Content Type),
     consolidated
4. **Schema recommendations**: the main deliverable. One **4-column** table (Page / Schema Type |
   Schema Implemented Currently | Schema Template Recommendation | Schema Recommendation /
   Example), top 3 to 5 schemas.
5. **Notes**: 1 to 3 short lines (validation tools, compliance flags).

**No pre-delivery checklist section.** Every internal QA item lives as an inline Word comment
anchored to the JSON-LD value it applies to (`{{COMMENT:...}}...{{/COMMENT}}`). The strategist
walks the margin comments, verifies or fixes each one, then resolves and deletes it.

The four recommendation columns:

- **Page / Schema Type**: label plus an example page URL.
- **Schema Implemented Currently**: the raw current JSON-LD ("Not set" if absent).
- **Schema Template Recommendation**: a clean template with `[Placeholder]` markers for
  CMS-driven fields. The developer maps these to CMS variables.
- **Schema Recommendation / Example**: the same schema filled with the brand's real values.
  Values that need verification are wrapped in `{{COMMENT:text}}value{{/COMMENT}}` and become
  Word margin comments.

What's gone (do not bring back):

- A "why schema matters" stats block
- GEO impact essays per schema type
- A phased implementation roadmap
- A multi-tool validation walkthrough
- Separate "rich results earned" or "critical missing schema" tables
- High / Medium / Low priority badges
- Multi-paragraph implementation notes per recommendation
- A bullet-list summary of issues (it lives in the Executive summary paragraph)

The input shape, with every marker in use, is `assets/example-brief-data.json` (a fictional
brand, Harbour Meal Co). Read it before building a brief.

## Where the files go

The brief lives in the same `schema/` folder as `mos-geo-schema-scraper`, so the live schema and
the brief sit together:

| Situation | schema folder |
| --- | --- |
| One-brand brain | `campaigns/geo/YYYY-MM/schema/` |
| Agency brain (`mode: agency` in `.mos/config.yaml`) | `campaigns/geo/YYYY-MM/<brand-slug>/schema/` |
| No brain | `outputs/geo/YYYY-MM/<brand-slug>/schema/` |

Resolve it with the scraper's script (it needs no token for this):

```bash
RUN=$(node "$SKILL/../mos-geo-schema-scraper/scripts/run.mjs" --brand "<brand>" --print-path)
mkdir -p "$RUN/brief"
```

```
schema/
  raw/<page-type>/<slug>.json      live schema from mos-geo-schema-scraper (if run)
  brief/brief-data.json            THIS SKILL: the brief's content
  brief/YYYY-MM-DD-schema-optimisation-brief.docx   (" - v2", " - v3" on regeneration)
```

Never commit a schema folder into this pack: it holds client data.

## Schema scoping rules

### Cap at 3 to 5 schemas per brief

Pick the **top 3 to 5 highest-impact schemas** for this site. Never more than 5. Most briefs land
at 3.

Selection heuristic:

- Ecommerce: Organization + Product + (optionally CollectionPage or BreadcrumbList)
- Multi-location service: Organization (with subOrganization) + LocalBusiness + (optionally
  Service or BreadcrumbList)
- Content or blog-heavy: Organization + BlogPosting + (optionally WebSite)
- Single-location service business: Organization + LocalBusiness + Service

Skip types that earn no rich result and add no real entity clarity for this brand. Add schema
for impact, not completeness.

### Lean fields, no kitchen sink

Include **only the fields the developer can populate from the CMS**. Do not pad with optional
properties that look thorough and will never be filled in.

- **Organization:** `@context`, `@type`, `@id`, `name`, `url`, `logo`, `description`, `sameAs`,
  `contactPoint`. Skip `foundingDate`, `founders`, `acceptedPaymentMethod`,
  `parentOrganization` unless genuinely meaningful.
- **LocalBusiness:** `@context`, `@type`, `name`, `url`, `image`, `description`, `address`,
  `geo`, `telephone`, `openingHoursSpecification`, `priceRange`, `areaServed`,
  `parentOrganization` (if an Organization exists), `sameAs`. Skip `hasOfferCatalog` unless
  there are distinct, marketable service tiers.
- **Product:** `@context`, `@type`, `name`, `url`, `image`, `description`, `sku`, `brand`,
  `offers` (`priceCurrency`, `price`, `availability`, `url`), `aggregateRating` only when genuine
  third-party reviews exist. Skip a `review` array unless there is real review data to template.
- **BlogPosting:** `@context`, `@type`, `headline`, `description`, `mainEntityOfPage`, `image`,
  `datePublished`, `dateModified`, `author`, `publisher`. Skip full `@graph` nesting unless the
  site already uses it.
- **BreadcrumbList:** `@context`, `@type`, `itemListElement` with 2 or 3 items.

If you find yourself adding a 14th property, stop and remove the bottom five. A good Product
block has about 8 top-level properties.

### `[Placeholder]` markers (Template column)

Any field the developer fills from CMS data uses `[Placeholder]` syntax:

- `"telephone": "[Main Phone Number]"`
- `"streetAddress": "[Street Address]"`
- `"sameAs": ["[Facebook URL]", "[Instagram URL]", "[LinkedIn URL]"]`

The renderer styles `[Anything]` in the Template column italic Ember so developers can scan for
fill-in slots. Use plain, descriptive labels: they double as the field name the developer looks
for.

### `{{COMMENT:...}}` markers (Example column): real Word comments

Where a value needs verification before delivery, wrap it:

```
"telephone": "{{COMMENT:Verify this is the current customer service line}}+61 2 5550 1234{{/COMMENT}}",
```

That becomes a Word margin comment anchored to the value, which carries into Google Docs as a
comment thread. The value gets a yellow highlight. Use it for unverified phone numbers,
addresses and business numbers, prices that may have changed, social profile URLs you could not
confirm, `aggregateRating` values that need fresh third-party numbers, and staff or founder
names that need confirming.

If you cannot find a value at all, keep `[Placeholder]` in the Template column and write
`[REVIEW: needs from client]` in the Example column. It renders bold on a Sun highlight.

## Workflow

### Step 1: Gather context

1. Read the CSV the user provides (Screaming Frog, Bulk Export → Structured Data → All, with
   structured data extraction and validation turned on in the crawl config).
2. Identify the brand from the domain.
3. If you are in a MarketingOS brain, read the brain's business context files (brand, what it
   sells, proof) before writing a word. Do not invent paths: look for the business or brand
   context the brain actually has. Outside a brain, ask the user for the essentials.
4. Ask who the brief is **prepared by** (`client.preparedBy`). Default to the brain owner's
   business name if the brain records it; otherwise ask. Never hardcode an agency name.
5. Ask only what is essential: which section the crawl covers (only if the URLs are ambiguous),
   and any pages to include or exclude.

### Step 2: Parse the crawl data

Read `references/schema-knowledge.md` for type mapping and rich result eligibility. Reference it,
don't reproduce it: the brief carries none of that knowledge.

From the CSV, calculate:

- Total URLs, indexable count, error and warning counts, rich result counts, unique schema types
  → `crawlOverview` plus a one-sentence assessment naming the most important observation
- Per schema type found: where it's deployed and whether it's misapplied, thin or correct →
  `currentSchemaTypes`
- URLs grouped into page templates by URL pattern, consolidated to 5 to 8 rows →
  `pageTemplates`
- Major wrong types (Article on product pages) and major missing types (no Product on product
  pages). These drive both the Executive summary and the recommendations.

**Prefer the rendered schema when it exists.** If `schema/raw/` exists for this brand this month
(from `mos-geo-schema-scraper`), use those files for the "Schema Implemented Currently" column:
they are the rendered, JavaScript-inclusive state, where a Screaming Frog crawl without
JavaScript rendering can miss schema injected by a tag manager. Where the two disagree, say so in
the assessment. If there is no `raw/` folder and the crawl was not rendered, consider offering
to run the scraper on the 3 to 5 example pages first (about $0.006 each).

**Location pages are not always LocalBusiness pages.** A service area page targeting a suburb
without a physical office there gets `Service` with `areaServed`, not `LocalBusiness` with an
invented `PostalAddress`. LocalBusiness is only for real premises.

### Step 3: Pick the top 3 to 5 schemas

Apply the heuristic above. If you cannot justify a 4th or 5th, stop at 3. For each, fill all four
columns:

- **Label:** the schema plus the template and page count, e.g. "Product schema (Product pages,
  ~120 pages)", with `examplePage` set to a specific URL
- **current:** the raw JSON-LD live today, or "Not set"
- **template:** the lean template with `[Placeholder]` markers
- **recommended:** the same schema filled with real researched values, with `{{COMMENT:...}}`
  on anything to verify

### Step 4: Write the sections

**Executive summary** (about 150 words, 2 short paragraphs, or 3 very short ones):

1. What this brief is and what was crawled, in one sentence ("This brief audits ... based on a
   Screaming Frog extraction of X URLs (Y indexable).")
2. The diagnosis: the current pattern, where it falls short, why it matters.
3. What the brief delivers: template-level JSON-LD for N priorities, plus any industry
   compliance note.

Short sentences. No inflated phrasing ("ready-to-deploy code snippets using @id
cross-referencing to build a connected entity graph"). Be direct.

**Crawl overview**: 2-column table (Metric | Value): Total URLs Crawled, Indexable URLs,
Non-Indexable URLs (with reason, e.g. "2 (noindex)"), Pages with Schema Errors, Pages with
Schema Warnings, Rich Result Warnings, Rich Result Errors, Pages Earning Rich Result Features,
Unique Schema Types Found. Follow it with a one or two-sentence italic assessment of the most
important observation.

**Schema types currently deployed**: one row per type. The Assessment column is the value: say
where it's misapplied ("on 13 product pages and 6 landing pages; only right on the 41 blog
posts"), what's missing when it's thin ("site-wide but missing sameAs, logo and contactPoint"),
or that it's correct ("correct where present; extend to the remaining N pages"). One or two
short sentences each.

**Page template breakdown**: **consolidated** to 5 to 8 rows. Standard groupings: Homepage;
Product pages; Product listing / category pages; Blog posts; Blog category pages; Service /
landing pages; Location pages (only for real premises); Utility pages (privacy, terms, contact,
about). Only give FAQ, review or video pages their own row if they matter to the
recommendations.

**Schema recommendations**: one row per recommendation. For templates with many similar pages,
one row represents the template with an example URL.

**Notes**: 1 to 3 short lines, only ones that apply. Examples:

- "Validation: after deploy, test each changed template in Google's Rich Results Test
  (search.google.com/test/rich-results) and the Schema Markup Validator (validator.schema.org)."
- "Reviews: aggregateRating values must come from a verified third-party review platform, never
  self-rated."
- "Indexability: schema changes need no URL changes and no redirects."

### Step 5: Write brief-data.json and generate the DOCX

Write the brief to `$RUN/brief/brief-data.json` in the shape of `assets/example-brief-data.json`:

- `client`: `name`, `url`, `preparedBy`, `date` (e.g. "September 2026")
- `outputFilename`: `YYYY-MM-DD-schema-optimisation-brief.docx`
- `executiveSummary` (array of paragraphs), `crawlOverview`, `crawlOverviewAssessment`,
  `currentSchemaTypes`, `pageTemplates`, `schemaRows`, `footerNotes`
- Optional `commentAuthor` and `commentInitials`. They default to `client.preparedBy` and its
  initials.

`current`, `template` and `recommended` can be strings (use `\n` for line breaks) or JSON
objects, which are pretty-printed.

Install the renderer's one dependency the first time (Node 18 or newer):

```bash
[ -d "$SKILL/scripts/node_modules" ] || (cd "$SKILL/scripts" && npm install --silent)
node "$SKILL/scripts/generate-docx.js" --data "$RUN/brief/brief-data.json" --out "$RUN/brief"
```

The script prints the path of the DOCX. It never overwrites: if the file exists (a regeneration
after the user has seen v1), it saves ` - v2`, ` - v3` and so on, which also stops Word and
Google Drive showing a stale cached copy. Give the user the path; do not try to open it.

### Step 6: Tick the checklist

If the month's audit workbook already exists (`brand-audit-master.xlsx` in the folder that
holds `schema/`), tick this skill's row:

```bash
if [ -f "$RUN/../brand-audit-master.xlsx" ]; then
  uv run --with openpyxl python "$SKILL/../_shared/brand-audit/tick_checklist.py" \
    --skill mos-geo-schema-optimisation --run-dir "$RUN" \
    --note "schema brief in schema/brief/"
fi
```

## Formatting rules (DOCX)

`scripts/generate-docx.js` handles all formatting. Do not change these without a reason:

- **Orientation:** landscape A4. The script passes `width: 11906, height: 16838, orientation:
  PageOrientation.LANDSCAPE`; `docx` v9 swaps them internally, so the output XML is
  `<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>`. Passing pre-swapped dimensions
  renders portrait in Google Docs with content overflowing.
- **Margins:** 1440 DXA all round, usable width 13958 DXA.
- **Table widths:** DXA only, never percentages. The 4-column table sums to 13950 DXA
  (1800 + 2700 + 4725 + 4725).
- **Palette: MarketingOS Ember, paper (print) variant.**
  - Ink `#0d0b0a`: headings, code text, and the fill of every table header row (Paper text)
  - Paper `#faf7f2`: the label gutter column and the first column of audit tables
  - Ember `#c96442`: H1 section banners (Ink text on Ember, the accessible pairing) and
    `[Placeholder]` tokens (italic)
  - Sun `#f4c24b`: highlight behind "Not set" and `[REVIEW:]`, which render bold Ink. Status
    only, never decoration.
  - Borders `#d9d2c8`, body text `#2a2320`, secondary text `#5e544d`
  - Comment anchors keep Word's yellow highlight
- **Fonts:** Bricolage Grotesque for the cover title, H1 and H2; Figtree for body text and
  tables; Roboto Mono 9pt for JSON-LD (Ember has no monospace face, and Roboto Mono renders in
  Google Docs). Word substitutes a similar font if one is not installed.
- **Headings** are sentence case. H1 23pt on an Ember banner, H2 17pt Ink, cover title 28pt.
- **JSON-LD columns** sit on plain white.
- **Credit:** a small "Built with MarketingOS" line on the cover and in the footer.

## Quality checklist (before writing brief-data.json)

- [ ] 3 to 5 schemas in the recommendations table, never more than 5
- [ ] JSON-LD is lean (about 8 top-level properties for Product, similar elsewhere)
- [ ] Every row has a `template` with `[Placeholder]` markers and a `recommended` with real
      values
- [ ] `{{COMMENT:...}}` anchored to every value the strategist must verify
- [ ] Executive summary is about 150 words
- [ ] Page template breakdown is 5 to 8 rows
- [ ] Each `currentSchemaTypes` assessment says what's wrong (misapplied, thin, missing
      properties), not just what's there
- [ ] No fields the brand cannot populate
- [ ] "Schema Implemented Currently" uses `schema/raw/` where it exists
- [ ] No other brand's name, no internal paths, no claim about AI citations

## Principles

**Tight beats comprehensive.** A 6-page brief that gets implemented beats a 25-page brief that
sits in a shared drive.

**Quality over quantity.** Every property must be one the developer can actually populate. The
best independent study so far found thin, generic schema cited by AI engines less often than
attribute-rich schema, and no better than having none (Growth Marshal, February 2026, n=730
citations; another study found no link at all). Details and sources: `_shared/geo-evidence.md`,
section 9. Sell schema on accuracy and rich result eligibility, never on citations.

**Schema must match the primary page content.** No FAQPage on a non-FAQ page, no Product on a
category landing page. Google's structured data policies require markup to describe visible
content, and a policy breach can cost the page its rich result eligibility through a manual
action.

**No self-reviews.** Never mark up a business's own reviews of itself as `aggregateRating` or
`Review`. If you recommend `aggregateRating`, note it must come from a verified third-party
platform (Google reviews, Trustpilot, ProductReview and similar).

**The same product every time.** Landscape, cover, Executive summary, Current state (three
tables), Schema recommendations (four columns), Notes. No checklist page, no essays, no roadmap,
no badges, and no new sections from one brief to the next.

## Related skills

- **`mos-geo-schema-scraper`**: run first to save the live, rendered schema into `schema/raw/`.
- **`mos-geo-ai-info`**: one schema file for the brand's AI Info Page.
- **`mos-geo-brand-360`**: what AI engines actually say about the brand.
