---
name: mos-geo-homepage-faqs
description: >
  Research and write sourced, entity-first homepage FAQs for a brand or the Homepage FAQs
  step of a GEO Brand Audit. Produces ranked copy, an HTML accordion, matching FAQPage
  JSON-LD, a developer handover and an approval workbook tab. Use for homepage FAQ
  generation or improving an existing FAQ block; use the other pack skills for a full
  AI Info Page, AI visibility testing or a site-wide schema audit.
---

# Homepage FAQs

An independent implementation inspired by observed outputs of Steve Toth's homepage FAQ
GPT (SEO Notebook). The October 1 sample uses 20 one-sentence answers; the October 10 live
run produced 15 two-sentence answers, all brand-first, with general sources and eight
homepage recommendations. This skill deliberately uses shorter, one-sentence answers.
These observations do not recover private instructions or prove a universal GPT formula. This skill adds source review, locale, links and Brand Audit approval.
It does not require access to the GPT. Install the whole mos-geo-skills pack: the helper uses
the sibling AI Info crawler and shared workbook template. Python 3.10+ is required;
openpyxl is needed for the workbook, and Scrapling is optional.

**Which skill?** This one writes the FAQ block for a homepage (and an FAQ page). For a full
fact sheet about the brand, use `/mos-geo-ai-info`. Running it first this month gives
better FAQs for free, because stage 2 reads them.

## Hard rules

1. **Never invent.** Every number and every capitalised tool, product or platform name must
   appear in the public bundle (`data/public-bundle.md`). `lint` fails the run otherwise. This checks presence, not factual entailment: read the
   actual cited passage for each clause, including uncapitalised service and outcome claims.
   No supporting passage, no FAQ. Save the review in `data/evidence-review.md` with the
   question, source URL, short supporting excerpt, retrieval date and any limitation.
2. **One sentence, entity first.** Each answer is one sentence of 20 to 55 words that opens
   with the brand or a product name. Never `Yes`, `No`, `It`, `We`, `Our` or `You`. Full
   formula: `references/faq-anatomy.md`.
3. **Capability, not outcome.** teaches, helps, shows, is designed to, focuses on. Never
   gets you cited, will rank, guarantees, best, #1.
4. **No volatile facts.** No prices, member counts, numbers or dates unless the user asks and
   `--allow-volatile` is passed.
5. **Provenance lint is the gate.** Nothing is handed over until source review is complete
   and `lint --final` prints `Result: PASS`. Render requires its receipt for the current
   copy, inputs, research and links; any edit requires lint again. A pass is a mechanical
   check, not verification that every claim is true.
6. **Links never rewrite answers.** A link anchors on words already in the answer. If no
   phrase fits, the answer ships without a link.
7. **Public data only.** Only published or explicitly approved information. Anything
   private from a brain, and everything on the never-say list, stays out (`--forbid`).
8. **Brand locale.** Spell for the brand's market (en-AU, en-GB, en-US). The observed GPT outputs mixed spelling conventions; use a consistent local register.

## Pipeline

Set `SKILL=<this skill's folder>` and `F="python3 $SKILL/scripts/faqs.py"`. Exact flags for
every subcommand: `$F <sub> --help`.

| # | Stage | Command | Gate before moving on |
|---|---|---|---|
| 0 | Run folder + preflight | `$F path --brand`, `$F doctor` | `$RUN` exists; `doctor` passes or its install line was shown |
| 1 | Crawl own site | `$F crawl --url --run-dir` | `data/pages/*.md` and `data/link-inventory.csv` exist |
| 2 | Reuse audit context | `$F gather --run-dir [--brain] [--include]` | `data/input-bundle.md` exists |
| 2b | Brand + voice interview | Claude, one round | `data/interview.md` written, `gather` re-run |
| 3 | Research + disambiguation | Claude, WebSearch | `data/research.md` written, with a public `## Summary`; `gather` re-run |
| 4 | Source review | Read cited passages | `data/evidence-review.md` supports every claim; FAQ metadata indexes its sources |
| 5 | Question set | Claude, `references/question-bank.md` | 12 to 20 questions picked from about 30 |
| 6 | Write | Claude, `references/faq-anatomy.md` | `faqs.md` written, every FAQ tagged with its sources |
| 6b | Internal links | `$F links --run-dir`, then Claude | links written inline in `faqs.md` |
| 7 | Lint (the gate) | `$F lint --run-dir --brand ... --final` | `Result: PASS` |
| 8 | Render | `$F render --run-dir --url --forbid` | `faqs.html`, `faqpage.jsonld`, `research-note.md`, `handover.md` |
| 9 | Workbook | `$F workbook --run-dir` | Checklist ticked, Homepage FAQs tab, Initiatives row |

### 0. Run folder and preflight

```bash
RUN=$($F path --brand "<brand>")   # from inside the user's brain, or pass --start <brain>
mkdir -p "$RUN"
$F doctor
```

Same rules as every mos-geo skill: `campaigns/geo/YYYY-MM/homepage-faqs/` in a one-brand
brain, a brand folder in an agency brain, `outputs/geo/YYYY-MM/<brand>/homepage-faqs/` with
no brain, and `-2`, `-3` for a repeat run. Never write a run folder into this pack. If
`doctor` says Scrapling is missing, show its one-line install and carry on; `crawl` falls
back to the `mos-geo-ai-info` crawler.

### 1 and 2. Crawl and gather

`crawl` reads the sitemap, homepage navigation and links (up to 50 pages): text to
`data/pages/`, and each URL's status, canonical, indexability, title, H1 and page type to
`data/link-inventory.csv`. `gather` writes two files:

- `data/public-bundle.md`: the crawl, `--include` files, `data/interview.md` and the `## Summary`
  of `data/research.md`. This is what `lint` checks provenance against. An `--include` draft
  counts as public only if it is published or client-approved.
- `data/input-bundle.md`: all of that plus, when present this month, the AI Info Page or draft,
  the Brand 360 report, Brand Truth Review corrections and the brain. Use it for context and
  voice. A fact found only here is private: `lint` fails it and warns where it was found.

Brain files are for voice only, never a source for a public claim. Blocked site or no brain:
say so and carry on.

### 2b. Brand + voice interview (one round, gaps only)

Read the bundle first, then run the same-name web search from stage 3 so question 3 can go
in the same round. Ask **only** what the bundle does not answer, **once**, and give a
suggested answer drawn from the site with every question. Use the AskUserQuestion tool when
it is available (one question per item, suggestion as the first option); otherwise a short
numbered list.

1. **Tone of voice:** three words for how the brand sounds, plus words it never uses.
   Skipped when the brain has a voice file.
2. **Locale / spelling:** en-AU, en-GB or en-US, suggested from `<html lang>` and the domain.
3. **Same-name check:** "I found {other entity} with a similar name. Is that you?" Asked only
   when the research finds one.
4. **Never-say list:** claims, clients or terms that must not appear.
5. **Flagship products** to lead with, only when the site has more than 3.
6. **Founder question:** include "Who founded {Brand}?" Yes or no. Only when a founder is
   publicly named.

"Skip" on any question means the suggested default is used and recorded as a default in
`research-note.md`. This skill's compact format stays consistent: voice changes word choice and warmth, not
structure. The original GPT varies between runs. Write answers to `data/interview.md`, then re-run `gather`. If the bundle answers
everything, ask nothing.

### 3. Research and disambiguation

With WebSearch, look for third-party mentions (press, directories, podcasts, community
posts), reviews, and **same-name entities to avoid** (an event, a company or a product that
shares the name). Write `data/research.md` in two parts:

- `## Summary` (**public**): the themes the evidence supports, how the brand differs from any
  same-name entity (by its own specifics, never naming the other entity), and one honest
  sentence on how sparse the independent evidence is. This is the only part that reaches
  `research-note.md` and the public bundle, so write nothing here you would not publish.
- Everything else (**private working notes**): sources found with URLs, the same-name
  entities, dead ends. Never rendered. Never cite people-data brokers (ZoomInfo, SignalHire,
  Wiza, RocketReach, Apollo, Lusha, ContactOut); render strips them anyway.

Never invent a testimonial theme to fill a gap. Re-run `gather` afterwards.

### 4. Sources are the ledger

There is no separate ledger file. Each FAQ's `sources:` list in its metadata comment is the
source index, and `lint` fails any FAQ without one. `data/evidence-review.md` records the
passage-level check; a URL alone does not prove an answer. Label brand-owned profiles on
third-party platforms first-party. An audit draft, interview assumption or AI-generated
research summary cannot independently corroborate a claim; follow it to a public source
or record explicit client approval. Preserve unreleased, premium and conditional status
rather than turning a roadmap item into an available feature.

### 5 and 6. Pick questions, then write faqs.md

Draft about 30 candidates across the eight buckets in `references/question-bank.md` (seven,
plus an optional founder bucket), keep 12 to 20 within each bucket's min and max (`lint`
enforces the "Target counts" table; `--count N` lowers the maximum), then write `$RUN/faqs.md`
in the formula from `references/faq-anatomy.md`. Rank them and mark the top 8
`placement: homepage`, the rest `placement: faq-page` (ranking order is in the question
bank). Format, per FAQ:

```markdown
### Does {Brand} teach GEO?
{Brand} teaches generative engine optimisation, or GEO, ... [technical GEO audits](https://example.com/geo) ...
<!-- bucket: capability; placement: homepage; sources: https://example.com/geo, https://news.example.org/x; evidence: third-party -->
```

`sources` are the URLs the answer came from. `evidence` is `first-party` (only the brand's own
pages), `third-party` (independent sources only) or `mixed` (both). `third-party` and `mixed`
need at least one source off the brand's domain, or `lint` fails. The script's docstring is authoritative on format.

### 6b. Internal links

`$F links --run-dir "$RUN"` writes `data/link-candidates.json`: the 3 best-matching pages per
answer from the inventory. For each answer, Claude picks **at most one** target from those 3
and an anchor of 2 to 6 words copied **verbatim** from the answer, then writes the markdown
link inline in `faqs.md`. Inline links are the source of truth; `data/links.json` is optional
(render applies it, and a link in both places counts once). No link to the homepage, no generic
anchor ("learn more", the bare brand name), no target used more than twice. No fitting phrase
means no link. Never reword the answer.

### 7. Lint

```bash
$F lint --run-dir "$RUN" --brand "<brand>" --products "<Product A>,<Product B>" --locale en-AU --forbid "<term>" --final
```

Pass the same `--forbid` list to `render`: a never-say term or data-broker URL in any rendered
file (`faqs.html`, `faq-page.html`, `faqpage.jsonld`, `handover.md`, `research-note.md`) fails
`render`, and `lint` re-checks the rendered files when they exist.

It fails on count, format, provenance, outcome and volatile language, missing buckets or
sources, bad links, near-duplicate questions, never-say terms and em dashes; it warns on
answer overlap, voice slips and thin link coverage. Fix and re-run until `Result: PASS`.

### 8 and 9. Render and workbook

`$F render --run-dir "$RUN" --url https://<domain>/` writes `faqs.html` (a `<details>` accordion, no external assets), `faqpage.jsonld`,
`research-note.md` (the research `## Summary`, cited sources and claims policy) and `handover.md`. `$F workbook --run-dir
"$RUN"` adds the Homepage FAQs approval tab and an Initiatives row to the month's workbook.

Pass the same `--forbid` terms to lint and render. If copy, source bundles, links, research
or the checker changes, rerun final lint before rendering. Confirm the homepage HTML and
JSON-LD contain the same questions and answers and FAQ-page-only questions are absent
from homepage schema. Workbook approval precedes publishing; generating these files does
not authorise a live site edit.

### Final message to the user

Keep it short: how many FAQs, the homepage 8 by question, how many carry links, the
same-name entity avoided (if any), interview defaults used, anything dropped for lack of a
source, the file paths, and the next step (client approves the workbook tab, then a developer
follows `handover.md`).

## Evidence and limits

Say this plainly when asked "does it work?": the FAQ text is ordinary page text that
search-backed engines can retrieve and quote, and a one-sentence answer that names the brand
is easy to lift whole. Nothing shows AI engines weight FAQ blocks specially. The `FAQPage`
JSON-LD is shipped for machine readability only: Google removed FAQ rich results from Search
entirely on 7 May 2026 (after limiting them to government and health sites in August 2023),
so no site gets a rich result from it. The only correlational study found pages with FAQs
averaging slightly fewer ChatGPT citations, not more (`_shared/geo-evidence.md`, section 10).
Internal links help readers and crawlers find the page that backs each answer; they are not
sold as a way to earn AI citations. Pack-wide evidence: `../_shared/geo-evidence.md`. Origin:
Steve Toth's "LLM-Friendly Homepage FAQ Generator" GPT, credited in the research note.

## Reference map

| File | Read it when |
|---|---|
| `references/faq-anatomy.md` | Before writing faqs.md, every time |
| `references/question-bank.md` | Stage 5: patterns, buckets, target counts, placement ranking |
| `references/source-sample-steve-toth-gpt.md` | To see the GPT's raw output. Copy the shape, never the facts |
| `scripts/faqs.py` | `--help` for every subcommand; its docstring is authoritative on the faqs.md format |

Nothing brand-specific belongs in this skill folder apart from the labelled GPT sample.
