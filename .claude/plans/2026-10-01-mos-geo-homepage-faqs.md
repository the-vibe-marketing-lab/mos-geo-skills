---
status: plan, awaiting Richard's go
date: 2026-10-01
skill: mos-geo-homepage-faqs
repo: ~/Desktop/mos-geo-skills
origin: Steve Toth, "LLM-Friendly Homepage FAQ Generator" custom GPT
sample: .claude/plans/steve-toth-homepage-faq-sample.md
---

# Plan: mos-geo-homepage-faqs

**Input:** brand name + URL. Nothing else is required.
**Output:** 12 to 20 homepage FAQs written so an LLM can lift any one answer and still know
who it is about, plus the FAQ block as paste-ready HTML, `FAQPage` JSON-LD, a research note,
and an approval tab in the month's `brand-audit-master.xlsx`.

---

## 1. Reverse engineering the GPT's output

### 1.1 The three-part envelope

1. **Research preamble.** States how thin the independent evidence is, names the
   **disambiguation** it did ("the unrelated MarTech event that uses the same name"), and lists
   the source types it trusted (website, community, member activity, course materials) and the
   6 themes it found.
2. **The FAQ set.** 20 Q&As.
3. **Closing note.** Explains that outcome claims ("gets cited") were framed as method, not
   result, because the brand's own site says proof is still being developed.

The preamble and closing note are not decoration. They are the GPT's audit trail: an evidence
ledger (themes to sources) and a claims policy. We keep both, as files, not chat.

### 1.2 The answer formula (every one of the 20 follows it)

| Rule | Evidence in the sample |
|---|---|
| **Exactly one sentence** | 20 of 20 |
| **Opens with the full entity name as subject** (brand, or product + "is The Vibe Marketing Lab's ...") | 20 of 20. Never "It", "We", "Yes" |
| **No Yes/No opener**, even on yes/no questions | "Does ... help brands get cited?" answered "The Vibe Marketing Lab teaches strategies for ..." |
| **Restates the question's key terms** in the answer | "GEO and AI SEO?" → "teaches generative engine optimization, or GEO, alongside traditional SEO" |
| **Expands acronyms once** | "generative engine optimization, or GEO" |
| **~25 to 45 words**, built as subject + verb + list of 3 to 6 concrete nouns + purpose clause | "…covering brand visibility, technical website structure, content planning, and practical methods…" |
| **Third person, present tense** | 20 of 20 |
| **Names real platforms and tools** (entity anchoring) | ChatGPT, Google AI, Claude, Perplexity, Claude Code, Codex |
| **Capability verbs, not outcome verbs**: teaches, helps, shows, is designed to, focuses on | "teaches strategies for improving", never "gets you cited" |
| **No numbers, prices, member counts or dates** | 0 numbers in 20 answers |
| **No superlatives, no guarantees** | none |

### 1.3 Question formula

Written the way a buyer types into ChatGPT. Brand name in every question except the product
questions. Five patterns:

- `What is {Brand}?` / `What is {Product}?` (definition)
- `Does {Brand} {capability}?` (capability, the bulk: 10 of 20)
- `Is {Brand} {useful for | based on} {X}?` (fit and proof)
- `Can {Brand} help me {job}?` / `Can I see {X}?` (job to be done)
- `Do I need {prerequisite} to use {Brand}?` and `Who is {Brand} for?` (objection and audience)

### 1.4 Coverage buckets (the hidden selection logic)

| Bucket | Count in sample | Purpose for an LLM |
|---|---|---|
| Identity / definition | 1 | The canonical one-liner |
| Flagship product | 2 | Product entity tied to the brand entity |
| Core capabilities | 7 | "Does X do Y" retrieval matches |
| Proof / methodology | 4 | Why trust it: real accounts, build in public, practice over theory, human + AI |
| Audience fit | 4 | Agencies, in-house, no-code, who it's for |
| Resources | 1 | What you actually get |
| Differentiator | 1 | Tool-agnostic, files you control |

**Deliberately absent:** price, member count, founder, competitors, location. Volatile or
unverifiable facts are left out, same instinct as the AI Info Page's "consult the official
source" line. Our version keeps that exclusion and adds a founder question only when the
founder is a verifiable public entity (it helps entity linking and the GPT's omission looks
like a gap, not a choice).

### 1.5 Where the GPT is weak (what we fix)

1. **No sources shown.** Themes are asserted; we make every FAQ cite the page(s) it came from.
2. **Guessable facts.** "enterprise and small-business environments", "Codex" may or may not be
   on the site. Our lint fails any named tool, product or number not in the input bundle.
3. **US spelling for an Australian brand.** We write in the brand's locale.
4. **Repetition.** Three answers say nearly the same thing (practical, real accounts, build in
   public). We add a near-duplicate check.
5. **No homepage fit.** 20 is long for a homepage. We output a ranked set: top 8 for the
   homepage, the rest for an FAQ page or the AI Info Page.
6. **No links.** The GPT's answers are dead ends. Ours carry contextual internal links to the
   brand's own pages (section 2.5), so a reader, a crawler and an engine can each follow the
   answer to the page that proves it.
7. **No brand voice.** The GPT writes every brand in the same register. Ours takes the
   brand's tone of voice into account inside the fixed answer formula (section 2.6).

---

## 2. What we build

A new top-level skill folder, `mos-geo-homepage-faqs/`, cloned in structure from
`mos-geo-ai-info-generator/` (same Steve Toth → skill pattern, same run-folder rules, same
provenance lint, reuses the `mos-geo-ai-info` crawler).

```
mos-geo-homepage-faqs/
  SKILL.md
  references/
    faq-anatomy.md                    # section 1 of this plan, as rules
    question-bank.md                  # the 5 patterns x 7 buckets, with slots
    source-sample-steve-toth-gpt.md   # the sample, verbatim
  scripts/
    faqs.py                           # path | crawl | research | gather | lint | render | workbook
    test_faqs.py
```

### 2.1 Pipeline (brand + URL in, one short interview only for what's missing)

| # | Stage | Command | Gate |
|---|---|---|---|
| 0 | Run folder + preflight | `faqs.py path --brand`, `faqs.py doctor` | `campaigns/geo/YYYY-MM/homepage-faqs/` (same rules as siblings); `doctor` checks Scrapling is installed and prints the one-line install if not |
| 1 | Crawl own site with **Scrapling** | `faqs.py crawl --url` | Scrapling `Fetcher` first, `StealthyFetcher` / `DynamicFetcher` for blocked or JavaScript-only sites. Sitemap + homepage nav + crawl, up to 50 pages. Writes `data/pages/*.md` (text for the facts) and `data/link-inventory.csv` (URL, status, canonical, indexable, title, H1, meta description, page type, word count) |
| 2 | Reuse audit context | `faqs.py gather` | pulls in, if they exist this month: `ai-info/` page, `ai-info-draft/page.md`, `brand-360-report/`, the Brand Truth Review corrections, plus the brain if run inside one (its voice/brand files included) |
| 2b | **Brand + voice interview** | Claude, one round | Asks only what steps 1 and 2 didn't answer (see 2.6). Answers saved to `data/interview.md` and re-gathered as inputs |
| 3 | Off-site research + disambiguation | Claude, with WebSearch | `data/research.md`: third-party mentions, reviews, and **same-name entities to avoid**. Writes the preamble's "sparse evidence" honestly |
| 4 | Evidence ledger | Claude | `data/ledger.json`: themes → source URLs → first-party / third-party |
| 5 | Question set | Claude, from `question-bank.md` | ~30 candidates across the 7 buckets → pick 12 to 20 |
| 6 | Write | Claude | `faqs.md` in the section 1.2 formula and the brand's voice, each FAQ tagged with its ledger theme |
| 6b | **Internal links** | `faqs.py links` then Claude | Script shortlists the 3 best-matching pages per answer from `link-inventory.csv` (BM25 on title, H1, meta and body). Claude picks at most one link per answer and an anchor copied verbatim from the answer. Saved as `data/links.json` (see 2.5) |
| 7 | **Lint (the gate)** | `faqs.py lint --final` | see 2.2. Must print `Result: PASS` |
| 8 | Render | `faqs.py render` | `faqs.html` (`<details>` accordion, no external assets), `faqpage.jsonld`, `research-note.md` (preamble + closing note), `handover.md` |
| 9 | Workbook | `faqs.py workbook` | ticks Checklist, adds **Homepage FAQs** tab, adds a publish row on Initiatives |

Optional flags, never required: `--brain`, `--count`, `--locale` (default read from
`<html lang>` then the domain), `--forbid`, `--demand` (pull real brand questions from
DataForSEO PAA / Ahrefs question keywords to re-rank candidates, off by default).

### 2.2 Lint rules (deterministic, fails the run)

- 12 to 20 FAQs; every question ends `?`; no duplicate or near-duplicate questions (token overlap).
- Each answer is **one sentence**, **20 to 55 words**.
- Each answer **starts with the brand name or a known product name**; no `Yes`, `No`, `It`, `We`, `Our`, `You`.
- **Provenance:** every number, and every capitalised tool/product/platform name, appears in the input bundle. (Kills the GPT's guessable facts.)
- No guarantee or outcome-promise language (`guarantee`, `will rank`, `get cited`, `#1`, `best`), no superlatives, no em dashes.
- No prices, member counts or dates unless `--allow-volatile`.
- Every FAQ carries a ledger theme with at least one source URL.
- Bucket coverage: identity, audience and at least 3 capability FAQs present.
- Locale spelling check (reuse the generator's word list).
- Warn (not fail) on answers that share more than 60% of their nouns with another answer.
- **Links:** every link target is in `link-inventory.csv` with status 200, indexable and
  self-canonical; no link to the homepage itself (the FAQs live there); the anchor text appears
  verbatim in its answer; the anchor is 2 to 6 words and not generic ("click here", "learn
  more", the bare brand name); at most one link per answer; no one target used more than twice;
  at least half the answers carry a link when the inventory has matching pages (warn below that).
- **Voice:** fails on any term in the brand's never-say list; warns when an answer breaks a
  voice rule that can be checked in code (banned words, spelling, emoji).

### 2.3 Workbook: "Homepage FAQs" tab

One row per FAQ, following the `AI Info Page` tab pattern in `mos-geo-ai-info/scripts/aiinfo.py`:

`# | Placement (Homepage / FAQ page) | Question | Answer | Bucket | Source URL(s) | Evidence (first/third party) | Link target | Anchor | Client verdict (Approve / Edit / Remove) | Edited version | Notes`

Plus: `skills.json` entry (category **Brand Optimisation**, feeds tab "Homepage FAQs,
Initiatives"), rebuild `brand-audit-template.xlsx`, and a tab-order update so the tab sits
after "AI Info Page".

### 2.4 Evidence, said plainly

Add a section to `_shared/geo-evidence.md` before we pitch it. What we can say: FAQ blocks are
ordinary on-page text that search-backed engines can retrieve and quote; self-contained Q&A
answers are easy to lift. What we must not say: that FAQ schema earns rich results (Google
restricted FAQ rich results to authoritative government and health sites in August 2023) or
that engines weight FAQs specially. The build executor finds and cites the primary sources;
if a claim can't be sourced, it doesn't go in. Internal links are sold as helping people and
crawlers find the pages that back up each answer, not as a way to earn AI citations. That
matches how `mos-geo-internal-links` is pitched.

### 2.5 Internal links

- **Why:** each answer becomes a way into the page that proves it. Search crawlers pick up
  descriptive anchors from the homepage, the site's strongest page. A reader who wants more gets
  one click to it.
- **How:** the Scrapling crawl builds the inventory. The script shortlists 3 candidates per
  answer, and Claude chooses one target plus an anchor phrase already in the answer. The
  answer is never reworded to fit a link, the same rule `mos-geo-internal-links` uses.
- **Where they show up:** `<a href>` in `faqs.html`; the same `<a>` inside `acceptedAnswer.text`
  in `faqpage.jsonld` (schema.org allows basic HTML there); markdown links in `faqs.md`; and
  "Link target" + "Anchor" columns on the workbook tab so the client can approve or remove
  each link.
- **What's excluded:** external links, links to pages behind a login, paginated or tag
  archives, and any URL that redirects.

### 2.6 Brand + voice interview (because this ships publicly)

The skill is for anyone who installs the pack, not just us, so it can't assume a MarketingOS
brain exists. Brand + URL stays the only required input. After the crawl and gather, Claude
asks **one round** of questions, **only for gaps**, and offers a suggested answer drawn from
the site for each one:

1. **Tone of voice:** 3 words for how the brand sounds, plus words it never uses. Skipped
   if the brain has a voice file.
2. **Locale / spelling** (en-AU, en-GB, en-US), with a suggestion from `<html lang>` and the
   domain.
3. **Same-name check:** "I found {other entity} with a similar name. Is that you?" Asked only
   when the research finds one.
4. **Never-say list:** claims, clients or terms that must not appear (for example a
   side business, or a client under NDA).
5. **Flagship products** to lead with, if the site has more than 3.
6. **Founder question:** include "Who founded {Brand}?" Yes or no.

The FAQ formula stays fixed (third person, one sentence, entity first). Voice changes word
choice, examples and warmth, not the structure. "Skip" on any question means the default is
used and recorded in `research-note.md`.

---

## 3. Build units

| Unit | Owner | Files (one writer each) | Depends on |
|---|---|---|---|
| U1 Skill docs | executor A | `SKILL.md`, `references/*` | this plan |
| U2 Script + tests | executor B | `scripts/faqs.py` (incl. Scrapling crawl, link inventory, `links` shortlist, link lint), `scripts/test_faqs.py` | U1's anatomy (can start in parallel from this plan) |
| U3 Workbook + README | executor C | `skills.json`, `build_template.py`, `brand-audit-template.xlsx`, `README.md` | none |
| U4 Evidence | executor D | `_shared/geo-evidence.md` (new section) | none |
| U5 Dogfood | me | run on The Vibe Marketing Lab, diff against Steve's output | U1 to U4 |
| U6 Review | 2 read-only reviewers | correctness lens + "does it beat the GPT" lens | U5 |

U1 to U4 run in parallel in one worktree branch `feat/mos-geo-homepage-faqs` (the repo has
uncommitted work on `feat/mos-geo-schema`; we branch from it without touching those files,
except appending to `skills.json` and `README.md`, which U3 owns).

## 4. Done means

- [ ] `/mos-geo-homepage-faqs` with only "The Vibe Marketing Lab" + `https://thevibemarketinglab.com` produces the full run folder with no questions asked.
- [ ] `lint --final` PASS on the dogfood run; `test_faqs.py` green, including one test that feeds in Steve's raw answers and expects the provenance check to flag anything not on the site.
- [ ] Dogfood output covers every bucket Steve covered, in AU spelling, with a source per FAQ, and the disambiguation note names the same-name MarTech event if research finds it.
- [ ] `brand-audit-master.xlsx` in the dogfood month has a ticked Checklist row, a Homepage FAQs tab and an Initiatives row; `build_template.py` rebuild is clean.
- [ ] Scrapling crawl of the dogfood site produces `link-inventory.csv`; at least half the answers carry a verified internal link, and lint rejects a planted link to a redirect and a planted anchor that isn't in its answer.
- [ ] Interview asks only for gaps: run once inside the TVML brain (voice file present → no tone question) and once from an empty folder (tone question asked).
- [ ] The skill folder holds no TVML- or Richard-specific content apart from the labelled sample.
- [ ] README table row + `geo-evidence.md` section, every claim sourced.

## 5. Decisions I made (say if you want them changed)

1. **Name:** `mos-geo-homepage-faqs`, matching the pack's naming.
2. **One short interview, only for gaps** (updated 2026-10-01 for public release). Brand + URL
   is still the only required input. Tone of voice, locale, the same-name check, the never-say
   list, flagship products and the founder question are asked only when the site and brain
   don't answer them (section 2.6).
7. **Scrapling is the crawler**, with the ai-info crawler as a fallback when Scrapling isn't
   installed. `doctor` tells public users how to install it.
8. **Internal links:** at most one per answer, anchor copied verbatim from the answer, target
   checked live, and nothing rewritten to fit a link (section 2.5).
9. **Public-release hygiene:** nothing about TVML or Richard in the skill folder except the
   preserved Steve Toth sample (clearly labelled). Every paid or optional tool degrades
   gracefully. The README states the evidence plainly.
3. **Count:** up to 20 (Steve's default), ranked, with the top 8 marked for the homepage.
4. **Founder question** included only when the founder is publicly verifiable.
5. **Schema shipped** as `FAQPage` JSON-LD for machine readability, sold honestly (no rich
   result promise).
6. **Reads the month's AI Info Page and Brand 360 report** when present, so running it after
   those two gives better FAQs for free.

Estimated build: about 4 to 5 hours of executor time for U1 to U4, then 30 to 45 minutes for
the dogfood run and review.
