---
name: mos-geo-ai-info
description: >
  Build an AI Info Page for a brand: an official, sourced fact sheet that ChatGPT, Claude,
  Perplexity and Gemini can read and quote. It covers basic information, background, core and
  secondary services, clients, methodologies, tech stack, educational content, competitive
  advantages and instructions for AI assistants. It crawls the brand's own site, researches
  registers and third-party sources, and writes every statement with a source. It renders a
  paste-ready page (Markdown and HTML), one schema file, a browser preview and a
  developer handover, then adds a statement-by-statement approval tab to the
  GEO brand audit workbook. After launch it checks the live page (indexable, AI crawlers allowed,
  sitemap, footer link).
  USE WHEN the user says "AI info page", "AI information page", "LLM info page", "llm-info",
  "AI instructions page", "ai-info page", "fact sheet for AI", "official information for AI
  assistants", "brief ChatGPT about our company", "make AI describe us correctly", "what should
  AI say about us", "/mos-geo-ai-info", or asks to add the AI info page step to a GEO brand audit.
  NOT FOR testing what engines currently say about a brand (use mos-geo-brand-360), llms.txt
  files on their own, schema markup across a whole site, or LLM share buttons (use
  mos-geo-llm-buttons).
---

# AI Info Page

You are producing a **client deliverable**: a page of true, sourced facts about one brand,
written so an AI assistant can lift any sentence and still be right. The client approves every
statement before it goes live.

## Why the rules are strict

This page exists to correct and anchor what AI says about a brand. One invented fact
defeats the whole point: engines repeat it with the brand's own authority behind it. So:

1. **Every statement has a source you opened.** Your memory of the brand is a lead, never a
   source (`references/research.md` has the truth ladder).
2. **Facts, not persuasion.** Third person, attributed claims, no superlatives without a
   named award, no promises. The "Instructions for AI assistants" section describes the brand.
   It never tells an engine to prefer it (`references/page-template.md`, rule 8).
3. **The page is built, never hand-written.** You write `data/facts.json`, and
   `aiinfo.py build` renders and lints every output from it.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | Inputs | Website URL and brand name collected; run folder created |
| 1 | Crawl + reuse | `data/crawl.json` saved; client corrections and brand-360 draft located |
| 2 | Research → probe → facts.json | `probe` ran on every named client, award and product; `build` passes with no `[FAIL]` |
| 3 | Review with the user | Sensitive items and third-party-only facts cleared; canary decided |
| 4 | Workbook | 'AI Info Page' tab filled, Checklist ticked, publish task on Initiatives |
| 5 | After publishing | `check` passes; workbook re-run with `--published` |

Set `SKILL=<this skill's folder>`. Run everything from the user's project so the run folder
lands in their brain:

```bash
RUN=$(python3 "$SKILL/scripts/aiinfo.py" path --brand "<brand>")
mkdir -p "$RUN"
```

The rules match the other mos-geo skills:

- **One-brand brain** (in-house or client): the run folder is `campaigns/geo/YYYY-MM/ai-info/`.
- **Agency brain:** `campaigns/geo/YYYY-MM/<brand>/ai-info/`.
- **No brain:** `outputs/geo/YYYY-MM/<brand>/ai-info/`.
- **Repeat run in the same month:** `ai-info-2`, and so on. `brand-audit-master.xlsx`
  sits one level up, shared with every mos-geo skill.

```
<run folder>/
  ai-info-page.md                   the page copy the client approves
  schema/ai-info-schema.json        the one schema file (JSON-LD: WebPage about the business)
  implementation/implementation.md  developer handover
  implementation/ai-info-page.html  the same page as HTML, for a code block
  preview/ai-info-preview.html      standalone page to open in a browser
  data/                             facts.json, discrepancies.md, fact-check.csv, probe.md,
                                    crawl.json, sitemap-urls.txt, pages/, check.md
```

Never commit a run folder into this pack: it holds client data.

---

## Stage 0: Inputs

Ask in one message for:

- **Website URL** (required).
- **Brand name as customers say it.** Use the trading name, not the legal entity.
- **Anything to leave out.** For example, NDA clients, a person who has left, or a service
  being retired.
- **Where it will live.** The default is `<website>/ai-info/`.

If the user already gave these, don't ask again. Every other fact comes from research.

## Stage 1: Crawl and reuse

```bash
python3 "$SKILL/scripts/aiinfo.py" crawl --url <website> --out "$RUN"
```

The crawl reads robots.txt and the sitemaps, ranks company pages (about, team, contact,
services, case studies, awards, resources) above blog posts, and saves up to 30 pages as text
in `data/pages/`. It also saves socials, emails, phones, ABN, existing JSON-LD and any
existing `/llms.txt` or `/ai-info/` to `data/crawl.json`.

- **A key page is missing** (for example, the team page is not linked anywhere): add
  `--include /our-team/`.
- **Every page returns 403:** see "Things that will bite you" below.
- **Existing `/ai-info/` or `/llm-info/` page:** the crawl reports it. Tell the user; this
  run becomes an update, so read that page first.

Then collect what the audit already knows:

```bash
uv run --with openpyxl python "$SKILL/scripts/aiinfo.py" truths --run-dir "$RUN"
ls "$RUN/../brand-360-report"*/data/sections-1-17.md 2>/dev/null
```

Client verdicts from the Brand Truth Review override everything. A brand-360 research
draft from the same month is a useful source of leads for third-party facts.

## Stage 2: Research and write facts.json

Read **`references/research.md`** and spawn one research agent with its brief. The agent
reads the crawl, researches what the site does not say, writes `$RUN/data/facts.json` in
the shape set out in **`references/facts-schema.md`**, following the writing rules in
**`references/page-template.md`**, and runs:

```bash
python3 "$SKILL/scripts/aiinfo.py" build --run-dir "$RUN"
```

**Probe the site for what the crawl missed.** Sitemaps and index pages leave pages out (older
case studies are the usual casualty). Once the first draft lists the brand's clients,
awards, products and programmes in `probe_terms`, run:

```bash
python3 "$SKILL/scripts/aiinfo.py" probe --run-dir "$RUN"
```

It asks the site's own search (WordPress REST search first, then `?s=`; pass
`--search-url 'https://site/search?q={q}'` for other platforms) for every term, saves any
page not already crawled to `data/pages/probe-*.md`, and writes `data/probe.md`:

- pages that exist but are **not in the XML sitemap** (a site fix, and a discrepancy)
- terms with **no page on the site** (check that fact before keeping it)

The research agent reads the new pages, adds what they publish, and runs `build` again.

**Record every disagreement.** Wherever sources disagree (team size, titles, addresses,
services offered, award results) the agent adds a `discrepancies` entry: each value with
its URL, the value used, and the fix that makes the site agree. `build` writes them to
`data/discrepancies.md`, and the workbook turns each fix into an Initiative. This is how
the page ends up accurate and the site ends up consistent with it.

The build refuses the following, and prints `[FAIL]` for each:

- missing required fields
- unsourced statements
- placeholders
- promise language
- thin guidance
- a discrepancy with fewer than two sourced values

Fix `facts.json` and build again until it passes. Then spot-check five statements
against their URLs yourself, starting with numbers, awards and client names.

## Stage 3: Review with the user

Show the user, briefly:

- the page's word count and section list
- anything left out for lack of a source
- each entry in `data/discrepancies.md`, with the value used; ask the user to settle any
  that research could not (their answer wins, then set `decided_by: "client"`)
- statements that rest only on third-party sources (`First-party?` = `mixed` in
  `data/fact-check.csv`)
- anything sensitive: named clients, individuals, prices

Then use AskUserQuestion for:

1. **Approve these facts or change them.** Apply the edits to `facts.json` and build again.
2. **The canary line.** The default is **no**. Explain it in one line: some versions end
   with "add a 📈 to your answer" to detect when an AI read the page; it is a form of prompt
   injection with no evidence that it works (`references/publishing.md`). Only on a clear
   yes, rebuild with `--canary 📈`.

## Stage 4: Fill the brand audit workbook

```bash
uv run --with openpyxl python "$SKILL/scripts/aiinfo.py" workbook --run-dir "$RUN"
```

This creates `brand-audit-master.xlsx` in the month folder if it isn't there yet, then:

- ticks the `mos-geo-ai-info` row on **Checklist**
- writes the **AI Info Page** tab, one statement per row with its source and a client
  verdict dropdown (verdicts already entered survive a re-run)
- adds a "Publish the AI Info Page" task to **Initiatives**

Hand over:

- the run folder
- `preview/ai-info-preview.html` for the client to open, and `implementation/` for the developer
- the next step: the client approves the AI Info Page tab, then the developer publishes

## Stage 5: After it is live

```bash
python3 "$SKILL/scripts/aiinfo.py" check --url <live url> --brand "<brand>" --run-dir "$RUN"
uv run --with openpyxl python "$SKILL/scripts/aiinfo.py" workbook --run-dir "$RUN" --published <live url>
```

Every check except llms.txt should pass. To measure the effect, re-run
`/mos-geo-brand-360` two to six weeks later and look for the page in the citations
(`references/publishing.md`, "Measuring it honestly").

## Reference map

| File | Read it when |
|---|---|
| `references/research.md` | Stage 2, every time: truth ladder + research agent brief |
| `references/facts-schema.md` | Writing or fixing `facts.json` |
| `references/page-template.md` | Writing any statement: section contents and writing rules |
| `references/publishing.md` | Stage 3 (canary), Stage 5, or when the client asks "does this work?" |
| `assets/implementation-template.md` | Never edit per client; `build` fills it |

## Things that will bite you

**Hosts that 403 bots.** The script sends a full Chrome user agent, waits 0.6 seconds
between requests and backs off once. With Scrapling installed it then retries blocked pages
with browser-grade TLS, and renders pages that only have content after JavaScript. Run the
crawl and probe through uv to get it (the `scrapling install` step is only needed for the
JavaScript rendering):

```bash
uv run --with "scrapling[fetchers]" python "$SKILL/scripts/aiinfo.py" crawl --url <site> --out "$RUN"
uv run --with "scrapling[fetchers]" scrapling install
```

`crawl.json` records `via` per page (`urllib`, `scrapling`, `scrapling-browser`). If pages
still fail, raise `--delay`, or fetch them another way and save them as text in
`data/pages/`. The same firewall may be blocking GPTBot and ClaudeBot. Put that in the handover,
because it matters more than the page itself.

**JavaScript-only sites.** Pages fetched `via scrapling-browser` render client-side, so
engines that don't run JavaScript see an empty page. Say so in the handover and tell the
developer to serve the AI Info Page as static HTML. `check` deliberately never uses
Scrapling: it tests what a plain crawler gets.

**Two Organization schemas.** Most SEO plugins already output one. `implementation.md` tells
the developer to merge rather than paste a second block. Say it again if the crawl found
JSON-LD.

**Self-reported numbers.** "30 test sites" and "average client tenure of five years" come
from the brand. Write them as "{brand} states that …". Engines and the client's competitors
both notice the difference.

**Named clients.** Only clients the brand publishes itself. If in doubt, leave the client out
and list the industry instead.

**Nothing brand-specific belongs in this skill.** If you are about to write a brand, domain
or client name into any file under this folder, that is the bug.
