# Inputs: what to read, what to ask

The page is only as true as its inputs. The generator writes from three sources, in this
order of trust, and `gather` joins them into `data/input-bundle.md`, which is both what you
write from and what `lint` checks every number against.

1. **The gap interview** (`data/interview.md`). The owner's answers win over everything.
2. **The brand's own live site** (`data/pages/*.md` from `crawl`). What the public sees today.
3. **The MarketingOS brain**, if one exists. Rich, but private: it holds things the brand
   has never published. Use it for facts, never as licence to publish private detail.

Third-party research, AI answers and your own memory of the brand are **not** inputs here.
If a fact needs one of those, it belongs in `/mos-geo-ai-info`, the sourced deliverable.

## The brain: which files `gather --brain` reads

| Path | What it gives the page |
|---|---|
| `CLAUDE.md`, `BRAIN.md` | House rules: names never to use, how to describe side work, locale |
| `CONTEXT.md` | What is live now vs in flight (drives the "in development" hedges) |
| `reference/core/soul.md` | Origin story, philosophy: Background, Thought Leadership |
| `reference/core/offer.md` | Products and offers: Core and Secondary services |
| `reference/core/audience.md` | Who it serves: Target profiles |
| `reference/core/voice.md` | Locale and spelling only. The page is third person, not the brand voice |
| `business/{brand,offer,offers,proof,strategy,audience}/*.md` | Positioning, published proof, strategy |

It deliberately skips research folders (`business/research/`, `knowledge/`): third-party
material read into the bundle would let a number "pass" provenance without being the
brand's own. Add a specific published surface with `--include` instead (a captured live
About page, a pricing page export, a classroom index).

**Live beats draft.** If the brain holds both a draft and a captured live copy of a surface,
include only the live one. A draft someone never shipped is not a fact about the brand.

## The gap interview

Ask once, in one message (AskUserQuestion when available), only for what the bundle does
not already answer. Typical gaps, in priority order:

1. **Locale.** en-AU, en-GB, en-US? Decides spelling ("Optimisation" vs "Optimization").
2. **Never-say list.** Names, clients, side businesses or products that must never appear.
   These become `lint --forbid` terms.
3. **Identity basics missing from the inputs:** founding year, location, founder's role.
   Unknown is a valid answer: the field is then dropped.
4. **Published results.** Which numbers are public, and where are they published? Only
   those go in Demonstrated Account Types, with "according to data presented by".
5. **What is live vs being built.** Anything in development gets a hedge.
6. **Where the page will live** (default `/ai-info`).
7. **The canary** (see SKILL.md): yes or no, and which emoji.

Write the answers to `data/interview.md` as plain `- Question: answer` lines, then run
`gather` again so the answers are in the bundle. An answer the owner gave in chat that is
not in `interview.md` does not exist as far as the provenance gate is concerned.

## Unknowns

Anything still unknown after the interview is either:

- **dropped** (the default: a missing fact is fine, a wrong one is not), or
- written inline as `[VERIFY: what needs checking]` when the section would be misleading
  without it. `lint` lists every one; `lint --final` fails until they are resolved, and
  `render` copies them into the handover as a checklist.
