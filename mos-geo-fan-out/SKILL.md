---
name: mos-geo-fan-out
description: >
  For 1 to 500+ pages of a site, find the searches AI engines actually run (query fan-out)
  for the prompts each page should win, measure whether the page is cited today, and produce
  a per-page fix list to raise citability. Re-runnable later (`retest`) to measure lift.
  Runs on DataForSEO LLM Responses (fan_out_queries) and LLM Mentions (prompt discovery);
  see references/evidence.md for what was verified live and what this does not prove.
  USE WHEN the user says "query fan-out", "fan out", "fan-out analysis", "citability",
  "page citation gaps", "what does ChatGPT search for", "why isn't this page cited",
  "close the citation gap", "/mos-geo-fan-out", or hands over a page or a list of pages and
  asks why an AI engine isn't citing them. NOT FOR brand-level visibility (does ChatGPT know
  the brand at all) - use mos-geo-brand-360. NOT FOR bulk citation scraping for outreach
  lists, simulating a multi-turn buyer journey, or auditing whether a crawler can read a
  page's HTML (that's a different failure mode - the page might be perfectly crawlable and
  still never searched for).
---

# Fan-Out

You are diagnosing **why a specific page is or isn't cited** by AI engines, at the level of
the actual searches those engines run - not whether the brand is known in general
(`mos-geo-brand-360`) and not whether a crawler can technically read the HTML
(`mos-geo-ai-info`, `pm-ai-crawl-page-simulator`).

## The rule this skill exists to protect

**Query fan-out coverage is a hypothesis for citation lift, not a proven cause.** Every
report this skill writes says so, in the report itself. Nothing here proves that adding a
missing fan-out's content raises citations - it ranks where the page's own content or
retrieval status is the most likely blocker today, and `retest` exists so a client can
measure the actual before/after themselves. Read `references/evidence.md` before promising a
client anything this pack has not verified.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | Preflight | Credentials + model check pass; cost estimate is under `--max-spend` |
| 1 | Pages | Every page fetched and parsed (title, H1, H2/H3, main text) |
| 2 | Prompts | User reviewed `data/prompts.csv` (or passed `--yes`) |
| 3 | Run | `data/results.jsonl` saved, live, once, under the spend cap |
| 4 | Analyse | `data/clusters.csv` and `data/pages-summary.csv` written |
| 5 | Report | `fan-out-report.md` and `pages/<slug>.md` written |
| 6 | Workbook | `brand-audit-master.xlsx` has a Fan-Out tab and Initiatives rows |
| 7 | Retest (later) | A new run's citation rate is diffed against this baseline |

Set `SKILL=<this skill's folder>`, get the run folder, then run every subcommand with
`--out "$RUN"` (or `--start` for `path` itself):

```bash
RUN=$(python3 "$SKILL/scripts/fanout.py" path --url "<first page URL>")
```

Same MarketingOS-aware logic as `mos-geo-brand-360`'s `path`: inside a one-brand brain it
returns `campaigns/geo/YYYY-MM/fan-out/`; inside an agency brain it adds a site-slug folder;
outside a brain it returns `outputs/geo/YYYY-MM/<site>/fan-out/`. A second run in the same
month gets `fan-out-2`, and so on - nothing is overwritten. Every run folder holds:

```
<run folder>/
  fan-out-report.md      the client-facing report (built by `report`)
  pages/<slug>.md         per-page prompts, fan-outs and fixes
  data/
    pages.json             the fetched pages index (data/pages/<slug>.json each)
    prompts.csv             page_url, prompt_id, prompt, source, intent
    results.jsonl           one row per (engine, prompt, run)
    raw/<sha1>.json         the exact raw response for one (engine, model, prompt, run)
    clusters.csv            one row per (page, prompt, fan-out cluster)
    pages-summary.csv       one row per page: citation baseline, top gap
```

Never invent another location. Run folders can hold client data: never commit them into
this pack (`data/raw/` especially - it is bulky and nothing reads it after the run).

---

## Stage 0: Preflight

```bash
python3 "$SKILL/scripts/fanout.py" preflight --env-file <path to .env> \
  --pages <planned page count> --prompts <planned prompts per page> --runs 3 \
  --engines chat_gpt --max-spend 25
```

Checks credentials, that every enabled engine's model (and the generator model) still exists
at DataForSEO, resolves `--country` to a location code, and prints a cost estimate for the
planned run. **Refuses before making any network call** if the estimate is over
`--max-spend`. On a `GONE` model, pick a current name from the list it prints and update
`config/engines.json`.

## Stage 1: Pages

```bash
python3 "$SKILL/scripts/fanout.py" pages --url "<page URL>" --out "$RUN"
# or, for many pages:
python3 "$SKILL/scripts/fanout.py" pages --sitemap "<sitemap.xml URL>" \
  --include "<regex>" --limit 50 --out "$RUN"
```

Fetches each page (stdlib `urllib`, a browser user-agent, 10 workers by default) and extracts
title, H1, H2/H3 headings and main body text with nav/header/footer/script/style stripped.
Non-200 pages are skipped with a logged reason, not silently dropped. Every page is cached at
`data/pages/<slug>.json`; pass `--refresh` to force a refetch.

## Stage 2: Prompts

```bash
python3 "$SKILL/scripts/fanout.py" prompts --out "$RUN" --yes
# add real observed buyer questions too (an extra LLM Mentions call per page):
python3 "$SKILL/scripts/fanout.py" prompts --out "$RUN" --discover --yes
```

Drafts 5-8 buyer prompts per page: a cheap closed-book DataForSEO call (`generator_model` in
the config, default `gpt-5.4-nano`) asked to cover what-is, how-to, best/compare, problem and
cost intents from the page's title, headings and an excerpt. With `--discover`, also pulls
up to 3 real user questions per page via DataForSEO LLM Mentions, keyed on `--keyword` (or a
`url,keyword` CSV via `--keywords-csv`, or the page's own H1). Without `--yes` this only
prints the plan and cost estimate and spends nothing - **review `data/prompts.csv` before
`run`**; trim or edit it by hand if a generated prompt is off-target.

## Stage 3: Run

```bash
python3 "$SKILL/scripts/fanout.py" run --prompts "$RUN/data/prompts.csv" --out "$RUN" \
  --runs 3 --max-spend 25 --env-file <.env>
```

Every prompt x `--runs` (default 3) x every enabled engine (default: ChatGPT only), live,
with web search on, through a thread pool (`--workers`, default 10). **Every call is cached**
at `data/raw/<sha1>.json` keyed by (engine, model, prompt, run index) - re-running this
command resumes and never re-bills a call that already succeeded. Spend is tracked live
against `--max-spend` and the run **stops mid-batch**, not just before it starts, the moment
the cap would be exceeded; unfinished jobs are simply retried next time (raise the cap, or
run again later). Pass `--model gpt-5.6-terra` (or any other current model name) to override
the config's default model (`gpt-5.6-luna`) for a comparison run - see
`references/evidence.md` for what each model costs and catches. `config/engines.json` also
supports Claude, Gemini and Perplexity through the same LLM Responses family; enable one
there or pass `--only <id>`.

## Stage 4: Analyse

```bash
python3 "$SKILL/scripts/fanout.py" analyse --out "$RUN"
# optional: check Google rank for open/exact_string clusters (extra live SERP calls, cached)
python3 "$SKILL/scripts/fanout.py" analyse --out "$RUN" --serp --env-file <.env>
```

Normalises and clusters near-duplicate fan-outs, classifies each cluster (`site_vendor`,
`site_own`, `exact_string`, `open`), scores whether the page already covers it
(`exact` / `heading` / `partial` / `missing`), and records the citation baseline (share of
runs citing the page, share citing the domain, top competitor domains). Full method,
including exactly how clustering and coverage are computed and their limits:
**`references/method.md`**.

## Stage 5: Report

```bash
python3 "$SKILL/scripts/fanout.py" report --out "$RUN"
```

Writes `fan-out-report.md` (citation baseline, top winnable gaps ranked by stability x
missing coverage, method and limits) and one `pages/<slug>.md` per page (its prompts, stable
fan-outs with type/coverage/rank, and a typed fix: `ADD_EXACT_STRING`, `ADD_SECTION`,
`EARN_RETRIEVAL`, `SKIP_VENDOR`). Plain English, no hype - if a page has no stable winnable
gaps, the report says that plainly instead of manufacturing one.

## Stage 6: Fill the workbook

```bash
uv run --with openpyxl python "$SKILL/scripts/fanout.py" workbook --out "$RUN"
```

Adds a **Fan-Out** tab (one row per page x stable cluster) and ICE-scored rows on
**Initiatives** to `brand-audit-master.xlsx` one level above `$RUN` (creating it from the
pack template if it isn't there yet), then ticks the `mos-geo-fan-out` row on **Checklist**
via `_shared/brand-audit/tick_checklist.py`. `site_vendor` (unwinnable) clusters never get an
Initiative.

## Stage 7: Retest (measure the actual lift, later)

```bash
python3 "$SKILL/scripts/fanout.py" retest --baseline <earlier run folder> --out "$RUN2" \
  --env-file <.env>
```

Re-runs the **exact same prompts** from an earlier run's `data/prompts.csv` in a new folder
and writes `data/retest-diff.csv`: baseline citation rate, new citation rate, and the delta,
per page. This is the only thing in this pack that measures whether a fix actually worked -
run it weeks after the fixes ship, not the same day.

## Reference map

| File | Read it when |
|---|---|
| `references/evidence.md` | Before making any claim to a client; before picking or comparing a model |
| `references/method.md` | Stage 4, every time - clustering, classification, coverage, the four fixes |
| `config/engines.json` | A model is `GONE`, a model should be switched on/off, or the cost estimate looks wrong |
| `.env.example` | Setting up `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` |

## Things that will bite you

**The DataForSEO LLM Scraper does not return fan-out queries.** Only LLM Responses (the
model API, used by `run`) does. Don't reach for the scraper here even though other skills in
this pack use it.

**`user_prompt` is capped at 500 characters.** `run` truncates to fit; `prompts`' generator
call prioritises headings over the page excerpt to fit the same cap - a long page's excerpt
gets cut, not the headings.

**Fan-out varies run to run.** `--runs` (default 3) is a stability *estimate*, not a
guarantee. Don't quote a single run's fan-out list as "the" searches for a page.

**Coverage under-counts on purpose.** No stemming, no synonyms - "buttons" and "button" are
different tokens. A `missing` verdict can be a real gap or just a strict tokenizer; read the
fan-out and the page section side by side before writing a fix into a client deliverable.

**Nothing here proves citation lift.** `retest` is how you find out for real.
