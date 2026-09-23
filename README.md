# mos-geo-skills

Claude Code skills for GEO work — Generative Engine Optimisation. Built for The Vibe Marketing Lab. It's a companion pack to the MarketingOS engine (`pipx install marketing-os`): same `mos-*` naming, and it installs alongside the engine's own skills in `~/.claude/skills/`.

GEO is the messy new corner of search where the "engine" is an LLM rather than a results page. A lot of what gets sold as GEO is guesswork. The skills in this pack are the opposite: each one ships with the evidence behind it, including the bits that say "this does less than people claim".

## What's in here

| Skill | What it does |
|---|---|
| `mos-geo-brand-360/` | A 360° Brand Intelligence Report from just a brand name and industry, plus an AI Visibility Scorecard: whether ChatGPT, Claude, Gemini, Perplexity, Google AI Mode and AI Overviews know the brand, find it, cite it and recommend it. Runs on DataForSEO, with OpenRouter and Bright Data as automatic fallbacks (`mos-geo-brand-360/references/providers.md`). |
| `mos-geo-ai-info/` | An AI Info Page: a sourced, client-approved fact sheet about the brand for ChatGPT, Claude, Perplexity and Gemini (basic information, background, services, clients, methods, advantages, guidance for AI assistants). Crawls the brand's site (Scrapling as an optional fallback for blocked or JavaScript-only pages), searches it for every named client and award to catch pages the sitemap misses, records every place the site contradicts itself with the fix, renders a paste-ready page (Markdown and HTML), one schema file, a browser preview and a developer handover, each in its own folder, adds an approval tab to the audit workbook, and checks the live page after launch. Evidence and limits: `mos-geo-ai-info/references/publishing.md`. |
| `mos-geo-llm-buttons/` | Generates a row of "ask an AI about this page" share buttons for an article — ChatGPT, Claude, Perplexity, Grok, Google AI Mode — each opening with a pre-filled summarise-this-page prompt. |
| `mos-geo-internal-links/` | Internal link audit and recommendations. Reads a Screaming Frog crawl and the saved HTML, separates true in-body links from table-of-contents, author box, related-post and template links, and reports orphans, deep pages, links to redirects and errors, and anchor conflicts. Then a BM25 shortlist per article section, TypeSafe's Jev to judge target, sentence and a verbatim anchor, and code-enforced rules and budgets produce a list for human review. Sold as discovery and context, not as a way to earn AI citations (`mos-geo-internal-links/SKILL.md`). |
| `mos-geo-schema-scraper/` | Saves the live JSON-LD of every page as one pure-JSON file (`[]` when a page has none), sorted by page type: the "before" snapshot for a schema rebuild, or for a competitor's site. Free: it reads a Screaming Frog crawl (a JSON-LD custom extraction or the stored HTML, with JavaScript rendering so tag-manager schema is caught), and flags broken JSON-LD. No Screaming Frog licence? An opt-in Apify fallback renders a URL list for about $0.006 a URL. |
| `mos-geo-schema-optimisation/` | Turns a Screaming Frog structured data export into a landscape Word brief: what schema the site ships today, the 3 to 5 schemas that matter most, and for each a template for the developer plus an example filled with the brand's real values, with anything unverified raised as a Word margin comment. Sold on accuracy and rich result eligibility, not AI citations (evidence: `_shared/geo-evidence.md`, section 9). |

More skills get added as flat folders at the top level of this repo. One folder per skill, each with its own `SKILL.md`. Add the folder, re-run `setup.sh`, done.

## `_shared/`

Cross-skill reference material. Not a skill, never linked into `~/.claude/skills/`, but every skill in the pack reads from it.

- `platform-endpoints.json` — the verified deep-link contract for each AI assistant (endpoint, query param, whether it auto-submits, whether it needs a login). Every entry was tested live, not copied off a blog. Treat this as the single source of truth and re-verify before any client build.
- `geo-evidence.md` — the honest evidence base for LLM share buttons (sections 1 to 8) and for schema markup (section 9). What the one controlled A/B test actually found, what the tactic does not do, and where the line sits between a UX feature and something Microsoft classifies as an attack. Read this before you pitch the tactic to anyone.
- `brand-audit/` — the blank audit workbook template, its skill registry, the script that builds it, and `tick_checklist.py` for skills to mark their row done.
- `logo-policy.md` — per-provider trademark position on putting AI company logos on a button. Short version: wordmarks by default, logos opt-in.

## The audit workbook: `brand-audit-master.xlsx`

`_shared/brand-audit/brand-audit-template.xlsx` is the working sheet for a GEO brand audit. All GEO work in a brain lives under `campaigns/geo/YYYY-MM/`, one subfolder per skill (`brand-360-report/`, `llm-buttons/`), with the month's workbook at the root as `brand-audit-master.xlsx`. Skills create it there on first use and fill it in: `mos-geo-brand-360` ticks its Checklist row, fills Brand Truth Review and adds the report and visibility data as tabs; `mos-geo-ai-info` ticks its row, adds an **AI Info Page** tab (one statement per row for the client to approve) and a publish task on Initiatives; other skills tick their row with `_shared/brand-audit/tick_checklist.py`. Upload the master to Google Sheets or open it in Excel.

- **Checklist**: one row per `mos-geo-*` skill, with its GitHub link, how to run it, where its output is saved, a status dropdown and a Done tick box.
- **Brand Truth Review**: one row per factual claim from the brand-360 report. The client marks each claim Accurate / Partly accurate / Inaccurate / Not sure / Out of date and writes the correct version. `mos-geo-brand-360` writes these rows to `data/brand-truth-review.csv`, and its `workbook` step puts them into the tab (keeping any verdicts already entered).
- **Initiatives**: ICE-scored fixes that come out of the audit.

The workbook is generated, never hand-edited. When a skill is added to this pack, add it to `_shared/brand-audit/skills.json` and rebuild:

```bash
uv run --with openpyxl python _shared/brand-audit/build_template.py
```

## Install

Skills live in `~/.claude/skills/`. This repo keeps them under version control and junctions them into place, so you edit here and Claude Code picks the change up straight away.

```bash
git clone https://github.com/the-vibe-marketing-lab/mos-geo-skills.git ~/Desktop/mos-geo-skills
cd ~/Desktop/mos-geo-skills
bash setup.sh
```

Check what it would do first with `bash setup.sh --dry-run`. Nothing gets written on a dry run.

The installer is idempotent. Run it again after adding a skill and it links the new one, reports the rest as already linked, and never clobbers a link pointing somewhere else.

### Why the folders are flat

Every skill directory sits at the **top level** of this repo. No grouping folders, no `skills/` wrapper, no nesting.

That's not a style preference. Claude Code discovers skills by enumerating the immediate children of `~/.claude/skills/` and looking for a `SKILL.md` in each one. It does not walk deeper. Verified on this machine: across 227 installed skills there is not a single nested `SKILL.md`, and both known installers only ever list immediate children.

So `~/.claude/skills/mos-geo-llm-buttons/SKILL.md` is found. `~/.claude/skills/mos-geo-skills/mos-geo-llm-buttons/SKILL.md` is invisible — no error, no warning, the skill just never shows up. If a skill isn't loading, that's the first thing to check.

## Contributing a skill to this pack

1. Create a new top-level folder, `mos-geo-<thing>/`, with a `SKILL.md` inside it.
2. If it makes a factual claim about what GEO tactics achieve, back it in `_shared/geo-evidence.md` with a source URL, or don't make the claim.
3. Add a row to the table above.
4. Add the skill to `_shared/brand-audit/skills.json` and rebuild the workbook (see above).
5. Run `bash setup.sh`.

## A note on honesty

`mos-geo-brand-360` asks each engine every prompt once and says so in the report. AI answers change between runs, so a single answer is a snapshot, never a rate. The report shows what the engines said and leaves judging accuracy to the client.

These skills touch client work. The evidence base is deliberately unflattering in places — buttons on their own measured a 17% drop in clicks in the only controlled test we have. That's in `_shared/geo-evidence.md` in plain sight, because getting caught overselling costs more than the tactic is worth.
