# mos-geo-skills

Claude Code skills for GEO work — Generative Engine Optimisation. Built for The Vibe Marketing Lab.

GEO is the messy new corner of search where the "engine" is an LLM rather than a results page. A lot of what gets sold as GEO is guesswork. The skills in this pack are the opposite: each one ships with the evidence behind it, including the bits that say "this does less than people claim".

## What's in here

| Skill | What it does |
|---|---|
| `mos-geo-llm-buttons/` | Generates a row of "ask an AI about this page" share buttons for an article — ChatGPT, Claude, Perplexity, Grok, Google AI Mode — each opening with a pre-filled summarise-this-page prompt. |

More skills get added as flat folders at the top level of this repo. One folder per skill, each with its own `SKILL.md`. Add the folder, re-run `setup.sh`, done.

## `_shared/`

Cross-skill reference material. Not a skill, never linked into `~/.claude/skills/`, but every skill in the pack reads from it.

- `platform-endpoints.json` — the verified deep-link contract for each AI assistant (endpoint, query param, whether it auto-submits, whether it needs a login). Every entry was tested live, not copied off a blog. Treat this as the single source of truth and re-verify before any client build.
- `geo-evidence.md` — the honest evidence base for LLM share buttons. What the one controlled A/B test actually found, what the tactic does not do, and where the line sits between a UX feature and something Microsoft classifies as an attack. Read this before you pitch the tactic to anyone.
- `logo-policy.md` — per-provider trademark position on putting AI company logos on a button. Short version: wordmarks by default, logos opt-in.

## Install

Skills live in `~/.claude/skills/`. This repo keeps them under version control and junctions them into place, so you edit here and Claude Code picks the change up straight away.

```bash
git clone <this-repo> ~/Desktop/mos-geo-skills
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
4. Run `bash setup.sh`.

## A note on honesty

These skills touch client work. The evidence base is deliberately unflattering in places — buttons on their own measured a 17% drop in clicks in the only controlled test we have. That's in `_shared/geo-evidence.md` in plain sight, because getting caught overselling costs more than the tactic is worth.
