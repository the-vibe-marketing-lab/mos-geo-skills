---
name: mos-geo-brand-360
description: >
  Produce a 360° Brand Intelligence Report for any brand from just its name and industry, and
  test whether AI engines actually know it, can find it, cite it and recommend it. Researches 17
  sections (company, products, competitors, sentiment, personas, content, AI relevance, socials,
  hiring, media, legal and security, community, go-to-market, comparison pages, late-stage buyer
  questions, off-site truth consistency, summary), then asks ChatGPT, Claude and Gemini with no
  search (closed-book), the same engines plus Perplexity with web search, and what real users see
  in the ChatGPT and Gemini apps, Google AI Mode and Google AI Overviews, once each, through
  DataForSEO (OpenRouter and Bright Data as automatic fallbacks), and scores it all in an AI
  Visibility Scorecard.
  USE WHEN the user says "brand 360", "brand intelligence report", "brand brain", "is my brand
  known by AI", "does ChatGPT know my brand", "can AI find my brand", "AI brand visibility",
  "LLM brand audit", "what do LLMs say about [brand]", "entity audit", "brand GEO audit",
  "360 brand report", "/mos-geo-brand-360", or hands over a brand name and asks how AI search
  sees it. NOT FOR auditing whether AI crawlers can read a specific page (use
  pm-geo-ai-crawl-page-simulator or pm-geo-ai-extraction-audit), multi-turn buyer-journey
  simulations (use pm-geo-icp-journey-reporter), building LLM share buttons (use
  mos-geo-llm-buttons), or bulk citation scraping for outreach (use
  pm-geo-brand-citation-prompt-scrape).
---

# Brand 360

You are producing a **client deliverable**: a researched brand intelligence report plus hard
evidence of how AI engines see the brand today.

## The two rules this skill exists to protect

1. **Inputs are `{brand_name}` and `{industry}`. Nothing else.** Never ask for the domain,
   founder, location or products before the run, and never put them in a prompt. The test is
   whether the engines can find the brand from its name and category. A clue in the prompt
   measures the clue.
2. **Every prompt runs once.** No repeats, no accuracy scoring against a fact sheet. The
   client reviews the answers. The report says plainly that each answer is a snapshot.

If this session already knows the brand (project files, memory, a previous chat), do not let
that knowledge into the prompts or the research brief. Say in the report header whether the
researcher had prior context.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | Inputs + preflight | Brand name and industry collected; `preflight` passes |
| 1 | Prompt set | User approved the 13 prompts |
| 2 | Engine run + research (in parallel) | `data/results.jsonl` saved; sections 1 to 17 drafted |
| 3 | Summarise | `visibility-report.md` written |
| 4 | Confirm the entity | User picked their real website (after the run) |
| 5 | Write the report | `assemble` builds `brand-360-report.md` without refusing |
| 6 | Fill the workbook | `workbook` ran; `brand-audit-master.xlsx` sits at the month root |

Set `SKILL=<this skill's folder>`, then get the run folder from the script, run from the
user's project:

```bash
RUN=$(python3 "$SKILL/scripts/brand360.py" path --brand "<brand>")
```

All GEO work in a MarketingOS brain lives under `campaigns/geo/YYYY-MM/`, one subfolder
per skill, with the month's audit workbook at the month root:

```
campaigns/geo/2026-09/
  brand-audit-master.xlsx   the client deliverable, filled by every mos-geo-* skill
  brand-360-report/         this skill's run folder (`$RUN`)
  llm-buttons/              mos-geo-llm-buttons, and so on
```

- **Inside an in-house or client brain** (any folder under one that holds `.mos/config.yaml`)
  `path` returns `campaigns/geo/YYYY-MM/brand-360-report/`. A one-brand brain needs no
  brand folder: the brain *is* the brand.
- **Inside an agency HQ brain** (`mode: agency`) it adds the brand:
  `campaigns/geo/YYYY-MM/<brand-slug>/brand-360-report/`. Prefer the client's own brain.
- **Anywhere else** it returns `outputs/geo/YYYY-MM/<brand-slug>/brand-360-report/`.
- A second run in the same month gets `brand-360-report-2`, and so on. Nothing is overwritten.

Note: the current `mos validate` still expects dated `campaigns/YYYY/MM/...` folders,
so it flags this layout until the engine adopts platform-first campaigns.

Every run folder has the same shape:

```
<run folder>/                (campaigns/geo/YYYY-MM/brand-360-report/)
  brand-360-report.md      the finished report (built by `assemble`; supplementary)
  visibility-report.md     the engine summary (written by `summarise`)
  data/                    prompts.json, results.jsonl, run-meta.json, domains.csv,
                           sections-1-17.md (research draft), header.md and
                           section-18.md (your report parts), brand-truth-review.csv
                           (client review rows), raw/ (per-call API responses)
```

Never invent another location. Run folders can hold client data: never commit them into
this pack. `data/raw/` is bulky and nothing reads it after the run, so add it to the
project's `.gitignore` (or delete it) before committing.

---

## Stage 0: Inputs and preflight

Ask for both inputs in one message: the **brand name** as customers say it, and the
**industry** in plain words (for example "AI SEO education", "gym marketing agency",
"Australian health insurance"). Do not ask for anything else.

```bash
python3 "$SKILL/scripts/brand360.py" preflight --env-file <path to .env>
```

It checks the credentials, that every model in `config/engines.json` still exists at
DataForSEO (and at OpenRouter, the fallback), and prints which provider chain will serve
each surface. On a `GONE` model, pick a current name from the list it prints and update the
config.

**DataForSEO is the primary provider and is enough on its own.** OpenRouter and Bright Data
only step in when a DataForSEO call fails. If a surface shows `NO PROVIDER`, stop and point
the user to **`references/providers.md`**.

## Stage 1: Prompt set

Read **`references/prompt-set.md`** and write `$RUN/data/prompts.json`: 3 closed-book, 5 branded
and 5 unbranded prompts, built from the two inputs only. Show all 13 to the user and ask for
approval with AskUserQuestion before spending anything. Then preview the plan:

```bash
python3 "$SKILL/scripts/brand360.py" run --brand "<brand>" --industry "<industry>" \
  --prompts "$RUN/data/prompts.json" --out "$RUN" --country AU --env-file <.env> --dry-run
```

`--country` is the buyer's market (two letters, default AU).

## Stage 2: Engine run and research, in parallel

Start the engine run in the background (drop `--dry-run`). DataForSEO calls take 5 to 60
seconds each and run six at a time; a Bright Data fallback batch can add several minutes.

While it runs, spawn **one** research agent with the Research brief from
**`references/report-spec.md`**, filled with the two inputs and nothing else. It writes
sections 1 to 17 with numbered references. Save its output as `$RUN/data/sections-1-17.md`.

The run ends with a count of failed calls. Retry only what failed, for example
`--phases app --only google-aio`: the latest answer for each prompt wins, so a retry never
pays for the surfaces that already worked. Section 7 of `visibility-report.md` lists anything that
still failed.

## Stage 3: Summarise

```bash
python3 "$SKILL/scripts/brand360.py" summarise --run-dir "$RUN" --alias "<short name>"
```

Add `--alias` for common short forms or acronyms of the brand. Then read
**`$RUN/visibility-report.md`** for the engine data. Never read `data/results.jsonl`,
`data/domains.csv` or `data/raw/` into context: they are large, and the summary carries
everything the report needs (the one exception is a single raw record when debugging a
fallback, below). Add `--no-excerpts` if there
are many engines and the file is long.

## Stage 4: Confirm the entity (after the run)

Now, and only now, ask the user which website is theirs. Use AskUserQuestion with the
non-platform domains from `visibility-report.md` section 3 as options (plus "none of these").
Then re-run the summary with labels and link checks:

```bash
python3 "$SKILL/scripts/brand360.py" summarise --run-dir "$RUN" --alias "<short name>" \
  --own-domain <their domain> --competitor <domain> --competitor <domain> --check-links
```

Competitors are the rivals' own domains from Section 3 and from the unbranded answers. A
rival that only lives on a platform (a Skool group, a YouTube channel) stays classed as
platform; name it in the prose instead.

This answer labels rows. It never changes what the engines said.

## Stage 5: Write the report

The report is **assembled, never hand-built**, so every run has exactly the same shape.

1. Read **`references/report-template.md`** and the scoring rules in
   **`references/report-spec.md`**.
2. Write `$RUN/data/header.md` and `$RUN/data/section-18.md` from `visibility-report.md`
   and the research draft, following the template line for line.
3. Build the report:

```bash
python3 "$SKILL/scripts/brand360.py" assemble --run-dir "$RUN" \
  --description "<First|Latest> /mos-geo-brand-360 audit of <short name>. 17-section brand research plus an AI Visibility Scorecard across <surfaces>. Headline - <headline>."
```

`assemble` writes `$RUN/brand-360-report.md`: frontmatter that passes the MarketingOS
contract, the title, your header, the snapshot note, sections 1 to 17 unchanged, your
Section 18, the reference list, and an appendix listing the exact prompts. It also adds
frontmatter to the research draft. If it refuses, fix the file it names and run it again;
never patch the report by hand.

Hand over the report path, the funnel line, and the one stage where the brand drops out.

## Stage 6: Fill the brand audit workbook (the deliverable)

The client deliverable is the month's workbook, `brand-audit-master.xlsx`, one level above
`$RUN`; the two `.md` files are supplementary. Two steps.

**1. Write the Brand Truth Review rows.** Clients check facts faster than prose, so write
`$RUN/data/brand-truth-review.csv` with one checkable claim per row and this header:

```
Topic,What the research / AI says,Where it came from,Said by (AI surfaces)
```

- **15 to 30 rows.** One fact per row, written as a plain statement the client can mark
  true or false ("Run by Jane Smith in Brisbane", not "Leadership").
- **Cover:** identity and founder, location, what is sold, price, audience, size or
  membership, positioning, competitors named, anything an engine got wrong or blended in
  from a name collision, and anything flagged stale or conflicting in Section 16.
- **Where it came from:** the report section and reference number (`Section 2 [3]`), or
  `Section 18 (visibility-report s3)` for engine answers.
- **Said by:** the AI surfaces that stated it, from `visibility-report.md`, or `Research`
  when only the research agent found it.

**2. Fill the workbook:**

```bash
uv run --with openpyxl python "$SKILL/scripts/brand360.py" workbook --run-dir "$RUN"
```

It creates `brand-audit-master.xlsx` in the month folder from the pack template if it is not
there yet (other skills' rows in an existing one survive), then:
ticks the `mos-geo-brand-360` row on **Checklist** (status, date, where the files are), fills
**Brand Truth Review** from the CSV, and rebuilds two tabs, **Brand 360 Report** and
**AI Visibility**, from the two markdown files with every table as a real sheet table.

Tell the user to upload the workbook to Google Sheets and send the client the Brand Truth
Review tab; every Inaccurate or Out of date verdict becomes an Initiative.

## Reference map

| File | Read it when |
|---|---|
| `references/prompt-set.md` | Stage 1, every time |
| `references/report-spec.md` | Stage 2 (research brief) and Stage 5 (scoring rules) |
| `references/report-template.md` | Stage 5, every time: the exact shape of `header.md` and `section-18.md` |
| `references/providers.md` | Keys are missing, a phase errors, or the user asks about cost |
| `config/engines.json` | A model is `GONE`, or an engine should be switched on or off |

## Things that will bite you

**Google sometimes throws error 40101 through DataForSEO.** The script retries once. If a
surface still fails, retry it alone with `--only`.

**Grok, the Perplexity app and Copilot are off by default.** DataForSEO does not offer them.
They can be switched on in the config and then run on OpenRouter (Grok) or Bright Data
(the two apps).

**Bright Data's Gemini and Copilot output fields are undocumented.** If a Bright Data
fallback returns empty answers with no error, open one record in
`data/raw/app/brightdata-<id>.json` (just one) and add the real field name to `answer_fields`.

**Note which provider served each answer.** The `Via` column in `visibility-report.md` shows it.
If a fallback served part of a surface, say so in 18.5: the fallback is the API or a
different scraper, so its answer can differ from the primary's.

**No AI Overview is a result.** Google shows overviews for some queries only. The script
records "(Google showed no AI Overview for this query.)" rather than an error.

**Model slugs go stale fast.** The `~…-latest` aliases track each provider's current model,
but OpenRouter retires slugs. `preflight` catches it before money is spent.

**Nothing brand-specific belongs in this skill.** Every brand fact is found at run time. If
you are about to write a brand, domain or client name into any file under this folder, that
is the bug.
