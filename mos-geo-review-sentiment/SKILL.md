---
name: mos-geo-review-sentiment
description: >
  Read every third-party review a brand has and turn it into three things a client can act on: a
  sentiment report (star rating, rating spread, monthly trend, per-platform table, reply rate and
  reply speed), word clouds of the phrases customers actually use (praise and complaints shown
  separately, interactive version with quotes), and a fix report that ranks the complaints by how
  much they hurt, each with verbatim quotes and links, an owner, a fix, a GEO action and a metric to
  watch. Finds the profiles itself (Trustpilot, Google Maps, ProductReview, G2, Capterra, Reddit,
  Facebook and more), shows a picker with review counts and cost before anything is scraped, pulls
  only what the user picks through pinned Apify actors, labels every review against an approved
  aspect taxonomy (TypeSafe Jev, or Claude in session) and computes every number in code. Adds a
  Review Fixes tab and Initiatives to the GEO brand audit workbook.
  USE WHEN the user says "review sentiment", "brand sentiment", "review analysis", "analyse our
  reviews", "what are customers saying", "what do customers say about [brand]", "what do customers think of [brand]", "check the review sites", "Trustpilot
  analysis", "Google reviews analysis", "ProductReview analysis", "G2 reviews", "review audit",
  "word cloud of reviews", "review word cloud", "what are people complaining about", "fix our
  reviews", "unreplied reviews", "/mos-geo-review-sentiment", or asks for the deep version of
  Brand 360's sentiment section. NOT FOR testing what AI engines say about a brand (use
  mos-geo-brand-360), sentiment write-ups for a single product page or PDP, or writing replies to
  reviews (out of scope for v1; this skill lists the unreplied ones).
---

# Review Sentiment

You are producing a **client deliverable**: what customers say about a brand across every review
site, and the complaints worth fixing first. It is the deep version of Brand 360 section 4. Brand
360 runs a few searches; this skill reads every review.

## The rules this skill exists to protect

1. **Nothing is scraped before the user picks the profiles and approves the cost.** Discovery and
   stats are free or cents. `scrape` refuses without `--approve-usd` at or above the estimate.
2. **The model never does maths.** Labels come from Jev or Claude; every count, average, share,
   trend and priority score comes from `reviews.py aggregate`.
3. **The taxonomy is locked before labelling**, so categories cannot drift between batches.
4. **Quotes are verbatim**, with a link to the public review. Root causes are written as
   hypotheses. No reviewer name is ever stored (authors are a salted hash).
5. **No GEO claim without a source.** The only claims about AI engines citing review sites are the
   ones in `_shared/geo-evidence.md` section 11. Do not add others in prose.

## Pipeline

| # | Stage | Who | Gate before moving on |
|---|---|---|---|
| 0 | Preflight | script | `APIFY_TOKEN` resolves; pinned actors exist; picked actors smoke-tested |
| 1 | Discover profiles | script | `data/candidates.json` from predictable URLs, the brand site's links, one Google search |
| 2 | Profile stats | script | Each candidate read once (free) for rating, review count, latest review |
| 3 | **User picks platforms** | **user** | Multi-select from the picker table; picking confirms the entity; cost approved |
| 4 | Scrape | script | `data/reviews.jsonl` in one schema, deduped; failures reported per platform |
| 5 | Taxonomy | Claude, **user approves** | 8 to 15 aspects locked in `data/taxonomy.json` |
| 6 | Label + spot check | Jev (Claude fallback) | Every review with text labelled; spot check at least 85% agreement |
| 7 | Aggregate, word clouds, report | script + Claude | `fix-notes.json` written; report, fix report, clouds, CSV built |
| 8 | Workbook | script | Review Fixes tab, Initiatives rows, Checklist ticked |

Set `SKILL=<this skill's folder>` and `R="python3 $SKILL/scripts/reviews.py"`. Get the run folder
from the user's project:

```bash
RUN=$($R path --brand "<brand>")
```

It follows the pack convention: `campaigns/geo/YYYY-MM/review-sentiment/` inside a client or
in-house brain (agency brains add a brand folder; no brain gives `outputs/geo/YYYY-MM/<brand>/`),
with `brand-audit-master.xlsx` one level up. Running `path` again for the same brand in the same
month returns the same folder, so a session can resume; pass `--new` for a fresh
`review-sentiment-2`.

**The user already has the reviews?** Skip stages 1 to 4 and import them (JSONL or CSV in the
common schema from `references/report-spec.md`; an `author` column is hashed, never stored):

```bash
$R import --run-dir "$RUN" --file <their file> --brand "<brand>" --domain <domain>
```

It rejects rows with an unknown platform, a rating outside 1 to 5, an unreadable date or no text
and no rating, dedupes, and records the run as a user-supplied sample. Every report then says
"user-supplied sample of N reviews; selection method unknown", never "newest N per platform".
Continue at stage 5.
Run folders hold client data: never commit them into this pack.

## Stage 0: Inputs and preflight

Ask in one message for: the **brand name** as customers say it, the **domain** (required: it
stops us scraping a different company with the same name), the **country** (default AU, it decides
the platform list) and, optionally, the **industry** in plain words ("SaaS", "local gym",
"ecommerce furniture"; SaaS brings in G2 and Capterra). Cap defaults to 500 reviews per platform,
newest first; `all` is allowed and still shows the cost first.

```bash
$R preflight
```

Keys come from the project `.env` (or `--env-file`), then the environment, and are never printed.
`TYPESAFE_API_KEY` is optional. Only actors with a `last_smoke_tested` date are offered in the
picker. If one the user needs is untested or old, run (cents):

```bash
$R preflight --smoke --platforms trustpilot,productreview
```

An actor that fails: find the store alternative with the most 30-day runs, update
`config/actors.json` (input template, price, start fee) and record why in its `notes`.

## Stage 1: Discover

```bash
$R discover --run-dir "$RUN" --brand "<brand>" --domain <domain> --country AU --industry "<industry>" --dry-run
$R discover --run-dir "$RUN" --brand "<brand>" --domain <domain> --country AU --industry "<industry>"
```

Order: predictable URLs (Trustpilot by domain, Reddit search), then every review-site link and
`sameAs` entry on the brand's home page. The home page is also read for the brand's **regional
sites** (hreflang alternates, footer links and store-picker URLs, e.g. `.co.uk`, `.eu`, `.com`);
each becomes its own Trustpilot row with its country. Then **one** Apify Google search run: a
`site:` query for each platform still missing plus one open `"<brand>" reviews` query, each reading
up to 3 results pages (`pages_per_query` in `config/actors.json`; about $0.0045 a page on the FREE
tier, and the dry run prints the maximum first). Results that do not name the brand are dropped.
The open query also counts **retailer** results (Amazon, Priceline, Boots and the rest in
`config/platforms.json`): retailer reviews are out of scope for v1, and the picker and the report
say so when retailers show up. `--no-search` skips the paid step.
`--include-employer` adds Glassdoor and Indeed (reported separately). If the user knows a profile
URL the search missed, add it to `data/candidates.json` by hand before `stats`.

## Stage 2: Stats (free)

```bash
uv run --with "scrapling[fetchers]" python $SKILL/scripts/reviews.py stats --run-dir "$RUN"
```

Reads each page once: Trustpilot's page data, JSON-LD `aggregateRating`, review dates, the Google
snippet as a fallback. Scrapling is an optional free fallback for pages that block plain requests
(Trustpilot does); without it those rows show `?`. Google Maps and Reddit cannot be read without a
scrape. Duplicate URLs that land on the same profile collapse into one row.

## Stage 3: The picker (the user decides)

```bash
$R estimate --run-dir "$RUN" --max-per-platform 500
```

Show `picker.md` to the user as a table. Columns: platform (linked), reviews on the profile, average
rating, reviews in the last 12 months (`>=N` when only the first page was visible), latest review,
how many we would scrape, estimated cost (store price plus the actor's start fee), the AI-citation
note (only where `geo-evidence.md` has a source; otherwise blank) and the check column:

- `⚠ partial match` or `⚠ name/domain mismatch`: the profile name or site does not fully match the
  brand. Say so plainly. It might be a reseller, a different country's company, or a namesake.
- `? not checked`: the page could not be read (Google Maps search URLs scrape the first place
  Google returns, so confirm the place).
- `Actor not smoke-tested yet`: not offered.

Then ask with **AskUserQuestion, `multiSelect: true`**: "Which of these profiles are <brand>'s, and
should be scraped?". Each option label is the pick id; the description is platform, reviews,
rating and est. cost. AskUserQuestion takes up to 4 options per question and 4 questions per call,
so group by platform when there are more than 4 rows, and leave out unscrapable rows. Picking a
profile is the entity confirmation. Then confirm the total cost in a second question (approve /
lower the cap / cancel). Never pick on the user's behalf.

## Stage 4: Scrape

```bash
$R scrape --run-dir "$RUN" --pick trustpilot-1,productreview-1,reddit-1 --max-per-platform 500 --dry-run
$R scrape --run-dir "$RUN" --pick trustpilot-1,productreview-1,reddit-1 --max-per-platform 500 --approve-usd <approved total>
```

Picked profiles run in parallel. Each is capped twice (the actor's row cap and Apify's spend cap).
A failing platform is reported and the rest are saved; retry it alone with `--pick <id> --append`.
Raw actor output goes to `data/raw/` with reviewer names redacted; every Apify run's real cost
(from the run record) goes to `data/run-cost.json`. Reddit results that do not name the brand are
dropped. Common schema: `references/report-spec.md`.

## Stage 5: Taxonomy (the user approves)

```bash
$R taxonomy sample --run-dir "$RUN"
```

Read `data/taxonomy-sample.md` (about 150 reviews, stratified by platform and star band) and follow
`references/taxonomy-guide.md` to propose 8 to 15 aspects, each with an id, label, a one-sentence
description of what it covers, and an owner (ops / product / support / marketing). Show them to the
user as a short table and ask for approval with AskUserQuestion (approve / edit). Save the approved
set to `data/taxonomy-proposed.json`, then lock it:

```bash
$R taxonomy lock --run-dir "$RUN" --file "$RUN/data/taxonomy-proposed.json"
```

## Stage 6: Label and spot check

```bash
$R label --run-dir "$RUN" --dry-run      # payloads only, no network
$R label --run-dir "$RUN"                 # Jev, cached in data/jev_cache.jsonl
```

Jev answers per review: whether each aspect is mentioned (Noul), the feeling about it (Score,
-2 to +2), the worst consequence (Choice: none / minor / cost money / safety or legal) and whether
they say they are leaving. Cost is about $0.0002 a review (`data/jev_usage.json`). Re-runs are free
from the cache.

**No TypeSafe key?** Label in session instead: read the reviews in batches of about 40 from
`data/reviews.jsonl`, write one line per review to `data/labels-claude.jsonl` in the shape shown in
`references/taxonomy-guide.md`, then `$R label --run-dir "$RUN" --import "$RUN/data/labels-claude.jsonl"`.
The importer rejects unknown ids, aspects and out-of-range values.

**Spot check (required):**

```bash
$R label --run-dir "$RUN" --spot-check 30
```

Show the user `data/spot-check.md` and ask for a yes or no per item (or ask them to mark the ones
that are wrong). Record it: `$R label --run-dir "$RUN" --spot-result 27/30`. Under 85%: fix the
aspect descriptions that caused the misses, `taxonomy lock --force`, `label --redo`, and check again.
The report states the result.

## Stage 7: Aggregate, word clouds, report

```bash
$R aggregate --run-dir "$RUN"
uv run --with wordcloud --with matplotlib python $SKILL/scripts/reviews.py wordcloud --run-dir "$RUN"
```

`aggregate` writes `data/aggregate.json`: rating spread, monthly trend, platform table, reply rate
and median reply time, aspect volumes, and the fix priority for every negative aspect. The fix list
is ranked by score only. Separately, every review whose own words name an injury, a hazard or a
legal or regulator step (cut, burn, rash, "hurt his back carrying", Fair Trading, ACCC, lawyer,
recall; never figurative "ruined my back") is listed one by one in a **Read first** box at the top
of the fix report and in the report headline, with reviews the model labelled safety/legal but whose
text names none flagged as likely over-labels:

`priority = volume share × average severity × recency weight × visibility weight × (1 + share unreplied)`

Weights live in `config/scoring.json` and are printed in the report. Reddit (and any platform with
`stars: false`) never counts toward the star average.

Word clouds score two- and three-word phrases praise against complaints (log-odds with a pooled
prior), drop stopwords and the brand's own name, and need a phrase in at least 2 reviews. Add
`--block <word>` for product names that crowd the cloud, and `--min-count 1` on very small runs.

Then read `data/aggregate.json` (the `fixes` list) and the quotes it points to, and write
`data/fix-notes.json` for **every issue in the fix list**, not just the top 5 (shape in
`references/report-spec.md`): a one-line problem, the likely root cause **as a hypothesis**, a
concrete fix the owner could schedule, the GEO action and the metric to watch. All five fields,
every issue. A low-ranked issue still gets a real fix, even a small one ("add sizing to the
pillow page"), never "to agree with the owner".
Plain, specific, Australian spelling, no em dashes, no hype. Then:

```bash
$R report --run-dir "$RUN"
```

It writes `review-sentiment-report.md`, `fix-report.md` and `unreplied-negatives.csv` (every 1 to 2
star review with no owner reply, newest first: the quickest win in the report). If any issue still
has a missing note field it prints them and **exits non-zero**: write the missing notes and re-run.
`--allow-placeholders` writes a draft anyway (exit 0), never for a client.

## Stage 8: Workbook

```bash
uv run --with openpyxl python $SKILL/scripts/reviews.py workbook --run-dir "$RUN"
```

Creates `brand-audit-master.xlsx` in the month folder from the pack template if needed, adds a
**Review Fixes** tab (one row per issue, a Client verdict dropdown that survives re-runs), adds the
top issues and the unreplied-reviews task to **Initiatives** (no duplicates on re-run), and ticks the
Checklist row. Hand over: the workbook, the headline numbers, the top three fixes, and the count of
unreplied negatives.

## Reference map

| File | Read it when |
|---|---|
| `references/taxonomy-guide.md` | Stage 5 every time, and for in-session labelling |
| `references/report-spec.md` | Stage 7 (fix-notes shape, report sections, the common schema) |
| `references/privacy.md` | A client asks what is stored, or before sharing any data file |
| `config/actors.json` | An actor fails, prices change, or a new platform is added |
| `config/platforms.json` | Adding a platform, or discovery misses one |
| `config/scoring.json` | The client wants different weights |

## Things that will bite you

**Start fees dominate small runs.** Trustpilot charges about $0.04 and ProductReview about $0.09 per
run before any review. A 30-review test costs mostly start fees; a 500-review run is mostly reviews.

**Apify refuses a low spend cap on some actors** (Trustpilot $0.45, ProductReview and Google search
$0.50). That is a ceiling, not a charge; the row cap is what limits spend. The floors are in
`config/actors.json`.

**ProductReview has one listing per product, plus a store listing.** The store listing ("<brand>
online store") is about the company; product listings are about one product. Pick deliberately.

**Google Maps candidates from a search URL scrape the first place Google returns.** Only pick one
when the brand has a real place, and say which one in the report.

**Trustpilot redirects regional profiles** (koala.com to au.koala.com). The stats step follows the
redirect and shows the final name; check it is the right country.

**Google caps the reviews it shows per place**, and some actors stop early. The platform table shows
how many were analysed against the profile total; say so when they differ.

**Nothing brand-specific belongs in this skill.** Brands, domains and taxonomies live in the run
folder. If you are about to write a client name into any file under this folder, that is the bug.
