---
name: mos-geo-brand-360
description: >
  Produce a 360° Brand Intelligence Report for any brand from just its name and industry, and
  test whether AI engines actually know it, can find it, cite it and recommend it. Researches 17
  sections (company, products, competitors, sentiment, personas, content, AI relevance, socials,
  hiring, media, legal and security, community, go-to-market, comparison pages, late-stage buyer
  questions, off-site truth consistency, summary), then asks ChatGPT, Gemini, Claude, Grok and
  Perplexity with no search (closed-book), the same engines with their own web search via
  OpenRouter, and the consumer apps (ChatGPT, Perplexity, Gemini, Google AI Mode, Copilot) plus
  Google AI Overviews via Bright Data, once each, and scores it all in an AI Visibility Scorecard.
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
| 2 | Engine run + research (in parallel) | `results.jsonl` saved; sections 1 to 17 drafted |
| 3 | Summarise | `visibility.md` written |
| 4 | Confirm the entity | User picked their real website (after the run) |
| 5 | Write the report | Section 18 filled from `visibility.md`; every flag intact |

Set `RUN=outputs/brand-360/<YYYY-MM-DD>-<brand-slug>` in the user's current project and
`SKILL=<this skill's folder>`. Run folders can hold client data: never commit them into this
pack.

---

## Stage 0: Inputs and preflight

Ask for both inputs in one message: the **brand name** as customers say it, and the
**industry** in plain words (for example "AI SEO education", "gym marketing agency",
"Australian health insurance"). Do not ask for anything else.

```bash
python3 "$SKILL/scripts/brand360.py" preflight --env-file <path to .env>
```

It checks the API keys and that every model in `config/engines.json` still exists on
OpenRouter. On a `GONE` model, pick the current equivalent from the list the check loads
and update the config. Missing keys: stop and point the user to
**`references/providers.md`**. The script runs without Bright Data (it skips the app and AI
Overview phases), but say so up front, because the report loses its "what real users see"
half.

## Stage 1: Prompt set

Read **`references/prompt-set.md`** and write `$RUN/prompts.json`: 3 closed-book, 5 branded
and 5 unbranded prompts, built from the two inputs only. Show all 13 to the user and ask for
approval with AskUserQuestion before spending anything. Then preview the plan:

```bash
python3 "$SKILL/scripts/brand360.py" run --brand "<brand>" --industry "<industry>" \
  --prompts "$RUN/prompts.json" --out "$RUN" --country AU --env-file <.env> --dry-run
```

`--country` is the buyer's market (two letters, default AU).

## Stage 2: Engine run and research, in parallel

Start the engine run in the background (drop `--dry-run`). The app phase polls Bright Data
and can take several minutes.

While it runs, spawn **one** research agent with the Research brief from
**`references/report-spec.md`**, filled with the two inputs and nothing else. It writes
sections 1 to 17 with numbered references. Save its output as `$RUN/sections-1-17.md`.

Phases can be re-run on their own with `--phases closed-book|api-search|app|aio`; the latest
answer for each prompt wins, so a failed engine can be retried without paying for the rest.

## Stage 3: Summarise

```bash
python3 "$SKILL/scripts/brand360.py" summarise --run-dir "$RUN" --alias "<short name>"
```

Add `--alias` for common short forms or acronyms of the brand. Then read
**`$RUN/visibility.md` only**. Never read `results.jsonl` or `raw/` into context: they are
large, and the summary carries everything the report needs. Add `--no-excerpts` if there
are many engines and the file is long.

## Stage 4: Confirm the entity (after the run)

Now, and only now, ask the user which website is theirs. Use AskUserQuestion with the
non-platform domains from `visibility.md` section 3 as options (plus "none of these").
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

Assemble `$RUN/brand-360-report.md`:

1. The header, per `references/report-spec.md`.
2. Sections 1 to 17 from the research agent, unchanged apart from fixing broken formatting.
3. **Section 18, the AI Visibility Scorecard**, written from `visibility.md` exactly as the
   spec lays out: the engine table, the funnel (Known → Found → Cited → Recommended), who
   gets recommended instead, trusted sources, and what the data does not tell you.
4. The numbered reference list.

Before handing over, check:

- **Known is judged from meaning, not the name match.** "I'm not familiar with X" is No.
- **Wrong-brand answers are called out** by name in 18.1 and Section 16.
- **No claim of a rate.** "2 of 5 engines" is fine; "40% of the time" is not.
- **No internal paths, other client names or tooling references** in the client copy.
- **`n/a` where a surface cannot answer** (Perplexity closed-book, every app closed-book).

Hand over the report path, the funnel line, and the one stage where the brand drops out.

## Reference map

| File | Read it when |
|---|---|
| `references/prompt-set.md` | Stage 1, every time |
| `references/report-spec.md` | Stage 2 (research brief) and Stage 5 (header + Section 18) |
| `references/providers.md` | Keys are missing, a phase errors, or the user asks about cost |
| `config/engines.json` | A model is `GONE`, or an engine should be switched on or off |

## Things that will bite you

**Bright Data's Grok scraper is listed as unavailable.** It ships disabled. Grok is still
covered on the API surface.

**Gemini, Copilot and Grok app output fields are undocumented.** The config tries several
field names. If an app phase returns answers that are empty but have no errors, open one
record in `raw/app/<scraper>.json` (just one) and add the real field name to
`answer_fields` or `citation_fields`.

**No AI Overview is a result.** Google shows overviews for some queries only. The script
records "(Google showed no AI Overview for this query.)" rather than an error.

**Model slugs go stale fast.** The `~…-latest` aliases track each provider's current model,
but OpenRouter retires slugs. `preflight` catches it before money is spent.

**Nothing brand-specific belongs in this skill.** Every brand fact is found at run time. If
you are about to write a brand, domain or client name into any file under this folder, that
is the bug.
