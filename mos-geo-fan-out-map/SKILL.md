---
name: mos-geo-fan-out-map
description: >
  For a site's whole content inventory (a sitemap or a URL list), predicts each page's
  query fan-out with Gemini Flash (free tier, no search), scores each page's own coverage
  of those fan-outs, and writes a site-wide map: which pages to optimise and which topics
  across the inventory have no page at all. Free and fast - meant to run BEFORE the paid
  sibling `mos-geo-query-fan-out`, which then gets OBSERVED fan-out (DataForSEO, live ChatGPT
  calls) on just the pages this skill prioritises. Method adapted from Metehan Yesilyurt's
  Screaming Frog query fan-out script; see references/evidence.md for what this predicts
  vs what it actually observes. USE WHEN "map fan-out across the site", "inventory
  fan-out", "content audit for AI search", "which pages should we optimise for AI",
  "site-wide fan-out", "free fan-out", "content gaps for AI search", "what topics are we
  missing", "/mos-geo-fan-out-map", or the user hands over a sitemap or a list of pages
  and asks where to focus GEO effort. NOT FOR observed fan-out or live citation checks on
  a single page that's already being written or optimised - that's `mos-geo-query-fan-out`
  (paid, DataForSEO, actually queries ChatGPT). NOT FOR brand-level visibility (does
  ChatGPT know the brand at all) - use `mos-geo-brand-360`. NOT FOR auditing whether a
  crawler can read a page's HTML - use `mos-geo-ai-info` / `pm-ai-crawl-page-simulator`.
---

# Fan-Out Map

You are triaging **an entire content inventory** - which pages are worth optimising for AI
search, and which topics have no page at all - cheaply enough to run across hundreds of
pages before spending a cent on the paid, DataForSEO-backed `mos-geo-query-fan-out`. This skill
never talks to a real search engine or a real AI assistant's search pipeline: it asks
Gemini Flash to *predict* what an engine would search for, from the page's own content,
and to score its own guess. Read `references/evidence.md` before promising a client
anything this predicts.

## The rule this skill exists to protect

**These fan-outs are predicted by a model from the page's own content, not observed
searches.** They are biased toward topics already on the page - a model reading a page
tends to imagine searches that page would answer, so it systematically under-reports real
content gaps. Every report this skill writes says so, at the top, every time. Use it to
prioritise; use `mos-geo-query-fan-out` to confirm.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | Preflight | Key present, model reachable, page count known, time estimate printed |
| 1 | Pages | Every page fetched and parsed into layout-aware chunks -> `data/pages.jsonl` |
| 2 | Predict | `data/predictions.jsonl` written; a re-run with unchanged pages makes 0 calls |
| 3 | Report | `fan-out-map.md`, `pages/<slug>.md` and `data/fan-out-map.csv` written |
| 4 | Workbook (optional) | `brand-audit-master.xlsx` has a Fan-Out Map tab and Initiatives rows |

Set the run folder once, then pass `--out "$RUN"` to every subcommand:

```bash
RUN=$(python3 "$SKILL/scripts/fanmap.py" path --url "<first page URL>")
```

Same MarketingOS-aware logic as the sibling skills: inside a one-brand brain it returns
`campaigns/geo/YYYY-MM/mos-geo-fan-out-map/`; inside an agency brain it adds a site-slug
folder; outside a brain it returns `outputs/geo/YYYY-MM/<site>/mos-geo-fan-out-map/`. A
second run in the same month gets `-2`, and so on - nothing is overwritten. Every run
folder holds:

```
<run folder>/
  fan-out-map.md          the site-wide report (built by `report`)
  pages/<slug>.md          per-page entity, prompts, fan-out table, gaps
  data/
    pages.jsonl            one JSON object per fetched page (data/pages/<slug>.json cache)
    predictions.jsonl       one JSON object per page's Gemini prediction
    raw/<sha1>.json         cached, validated Gemini response for (url, content hash, model)
    fan-out-map.csv         one row per page x fan-out
```

Never invent another location. `data/raw/` and `data/pages/` are bulky and hold nothing a
client needs to see - never commit a run folder into this pack.

---

## Stage 0: Preflight

```bash
python3 "$SKILL/scripts/fanmap.py" preflight --env-file <path to .env> \
  --sitemap "<sitemap.xml URL>" --include "<regex>" --limit 50 --concurrency 4 --rpm 30
```

Checks `GEMINI_API_KEY` is present (masked), makes one tiny call to confirm the model is
reachable, discovers the real page count from `--sitemap`/`--urls`/`--url` (or takes a
manual `--pages N`), and prints an estimated token total and wall-clock time (~2.5k tokens
and ~4s per page, observed live - see `references/evidence.md`). Pass `--rpm` to see the
estimate change once a rate cap is in play.

## Stage 1: Pages

```bash
python3 "$SKILL/scripts/fanmap.py" pages --sitemap "<sitemap.xml URL>" \
  --include "<regex>" --limit 50 --out "$RUN"
# or a plain list of URLs:
python3 "$SKILL/scripts/fanmap.py" pages --urls urls.txt --out "$RUN"
# or a single page:
python3 "$SKILL/scripts/fanmap.py" pages --url "<page URL>" --out "$RUN"
```

Fetches each page (stdlib `urllib`, a browser user-agent, `--workers` threads, default 10)
and extracts **layout-aware chunks**, not just flat body text: `title` + `h1`, every
H2/H3 with up to 500 characters of the content that follows it (until the next heading),
up to 5 `<ul>`/`<ol>` lists (item text joined), and every JSON-LD `@type` on the page.
Non-200 pages are skipped with a logged reason, not silently dropped. Every page is cached
at `data/pages/<slug>.json`; pass `--refresh` to force a refetch. Writes the consolidated
`data/pages.jsonl`.

## Stage 2: Predict

```bash
python3 "$SKILL/scripts/fanmap.py" predict --out "$RUN" --env-file <.env> \
  --concurrency 4 --rpm 30
```

One Gemini call per page (`--model`, default `gemini-flash-latest`; pass
`--model gemini-flash-lite-latest` for the faster/cheaper fallback), asking for the page's
primary entity, 3 buyer prompts it should win, and 8-10 typed fan-outs
(`related`/`implicit`/`comparative`/`procedural`/`refinement`), each self-scored
`yes`/`partial`/`no` for whether the page's own content already covers it, plus gaps and
follow-up questions. `generationConfig.responseMimeType: "application/json"` asks Gemini
for structured JSON directly; the response is still validated against the expected shape
and **retried once** if it's malformed or doesn't match. A `429`/`503` backs off
exponentially (up to 5 attempts) before giving up on that page. `--rpm` caps the whole run
across every worker thread, not per-thread. **One bad page never kills the run** - it's
logged and skipped.

**Every call is cached** at `data/raw/<sha1>.json`, keyed by `(url, content hash, model)`.
Re-running `predict` after a `pages` re-fetch that changed nothing makes **zero** new
calls; a page whose extracted content changed gets a fresh key and a fresh call, everything
else is served from cache. Writes `data/predictions.jsonl`.

## Stage 3: Report

```bash
python3 "$SKILL/scripts/fanmap.py" report --out "$RUN" --top 10
```

Writes:

- **`fan-out-map.md`** - the honesty note (mandatory, every time), a site summary (pages
  predicted, average coverage score across every fan-out: `yes`=1, `partial`=0.5, `no`=0),
  the top `--top` **pages to optimise** (lowest average coverage of their own predicted
  fan-outs), **content gaps across the inventory** (fan-out clusters, token-Jaccard >= 0.6
  like the sibling skill, that NO page covers - new-content candidates), **possible
  overlap** (clusters 2+ pages both claim to cover - check for cannibalisation), and a
  **Next step** section with the exact `mos-geo-query-fan-out` command sequence to get OBSERVED
  fan-out on the priority pages before writing or optimising anything.
- **`pages/<slug>.md`** per page - entity, buyer prompts, the fan-out table
  (query/type/coverage/evidence), gaps, likely follow-ups.
- **`data/fan-out-map.csv`** - one row per page x fan-out, for a spreadsheet.

## Stage 4: Fill the workbook (optional)

```bash
uv run --with openpyxl python "$SKILL/scripts/fanmap.py" workbook --out "$RUN" --top 5
```

Adds a **Fan-Out Map** tab (distinct from the paid sibling's **Fan-Out** tab - one row per
page x fan-out, with the honesty note as a banner row, page/cluster coverage colour-coded
green/amber/red, and an "Uncovered site-wide" column) and ICE-scored **Initiatives** rows
(top `--top` lowest-coverage pages -> "Optimise `<page>`: run mos-geo-query-fan-out before
editing"; top `--top` uncovered clusters -> "New content candidate: `<cluster>`") to
`brand-audit-master.xlsx` one level above `$RUN` (creating it from the pack template if it
isn't there yet), then ticks the `mos-geo-fan-out-map` row on **Checklist**. **Idempotent**:
re-running replaces the Fan-Out Map tab wholesale and skips any Initiative that already
exists (matched by task text + source skill) - never duplicates a row. Pass an explicit
`--workbook <path>` to target a workbook outside the normal month-folder convention (e.g. a
one-off run); the Checklist tick still lands in that same file, not the default location.

## Reference map

| File | Read it when |
|---|---|
| `references/evidence.md` | Before making any claim to a client; before picking a model |
| `.env.example` | Setting up `GEMINI_API_KEY` |

## Things that will bite you

**This is prediction, not observation.** Nothing here has queried a real AI assistant or
search engine. See "The rule this skill exists to protect" above - it is not optional
framing, it belongs at the top of every report this skill writes and it must stay there.

**Predicted coverage is biased toward what's already on the page.** A model asked "what
would someone search for, given this page" tends to imagine searches that page already
answers. That means a `missing` verdict is more trustworthy than a `covered` one - if the
model says a page is missing something, believe it; if it says a page covers everything,
that's the method's blind spot, not a guarantee.

**Site-wide gap clustering under-counts real gaps.** It can only cluster fan-outs the
model actually predicted for SOME page in the inventory. A topic no page's content ever
hinted at will never appear as a predicted fan-out anywhere, so it can never show up as a
gap here either - this method finds "adjacent to something on the site" gaps, not "totally
absent from the site" gaps. For those, competitor content-gap analysis
(`pm-content-gap-analysis`) or a human topic audit is still needed.

**`--rpm` is a soft, thread-shared limiter**, not a hard API-side guarantee - it holds a
lock while it sleeps, so it throttles the whole run, not one thread at a time. Pick it
conservatively against whatever Google's current published Gemini Flash free-tier rate
limits are; `preflight`'s time estimate accounts for it if set.

**Nothing here proves an AI engine will actually search for or cite anything.** That's
what `mos-geo-query-fan-out`'s live DataForSEO calls are for - this skill's whole job is picking
which pages are worth spending that budget on.
