---
name: mos-geo-llm-buttons
description: >
  Build a complete, client-ready LLM share buttons package for a website — scrape the client's
  site first, detect its stack, extract its brand palette, then generate an implementation
  brief, a code reference, and a live in-brand HTML demo. LLM share buttons are the row of
  buttons at the top of an article that open ChatGPT, Claude, Perplexity, Grok or Google AI
  Mode in a new tab with a summarise-this-page prompt already typed. USE WHEN the user says
  "llm buttons", "LLM share buttons", "AI share buttons", "ask AI about this page", "chat with
  ChatGPT button", "summarise in ChatGPT button", "GEO buttons", "AI share bar", "share to AI",
  "citemet", "CiteMET", "add AI buttons to a client site", or describes the outcome without the
  jargon — "put buttons on our articles that open ChatGPT with the page already loaded", "let
  readers send our guides straight into an AI", "one click so someone gets our article
  summarised by AI", "seed our URLs into ChatGPT conversations", "the thing those comparison
  sites have at the top of their guides". Also use when someone asks what we would scope, quote
  or hand over for an LLM-buttons engagement. NOT FOR structured data and schema markup (use
  pm-schema-optimisation), auditing how AI systems currently read or cite a site (use
  pm-ai-extraction-audit), or writing an SEO content brief (use rdg-seo-brief).
---

# LLM share buttons

You are producing a **client deliverable**, not a live deployment: three files a member can
send to their client's dev team under their own agency's name, plus a demo the client can open
in a browser and approve before a single line ships.

Deliver work that is ready to paste. Never hand over an instruction to write code we could have
written for them — that is the difference between a deliverable and homework.

## The site comes first — this is a hard prerequisite

Two decisions in this pipeline are made *for* you by the client's site, not by you:

1. **The stack decides the route.** WordPress gets a plugin file and a hook; everything else
   gets a component. Guessing this wrong means the entire code reference is unusable.
2. **The site's CSS supplies the brand tokens.** The buttons ship in the *client's* palette.
   Invented colours are the single fastest way to have a deliverable rejected.

So there is no path through this skill that starts with a blank page. If you do not have a URL,
stop and ask for one. Do not offer to "build a generic version they can restyle" — that is the
deliverable failing quietly.

## Pipeline

| # | Stage | Gate before moving on |
| --- | --- | --- |
| 0 | Preflight — URL, agency name, brand name | A reachable URL exists |
| 1 | Recon — detect the stack | Stack named, or explicitly `[VERIFY]` |
| 2 | Brand extraction — palette and type | User confirmed via AskUserQuestion |
| 3 | Route decision — WordPress or custom | One route file read, not both |
| 4 | Scope map — URL patterns to topic phrases | Out-of-scope list written down |
| 5 | Prompt build | Prompt passes the blocked-token check |
| 6 | Code generation | Endpoints match the shared contract |
| 7 | Deliverables — three files | Demo opens and renders in brand |

---

## Stage 0 — Preflight

Collect three things before anything else:

- **Client URL.** Required. Refuse to proceed without it, for the reasons above.
- **The member's agency name.** Every deliverable is white-labelled to them — their name on the
  cover, never ours. A member sending a client a document branded with someone else's agency is
  a worse outcome than no document.
- **The client / brand name.** It goes inside the prompt itself as `{BRAND}`, so it has to be
  the name the client wants an AI assistant to repeat back — the trading name, not the legal
  entity.

Ask for all three in one turn. Do not interrogate across three messages.

## Stage 1 — Recon

```bash
bash scripts/recon.sh <url>
```

The script walks a cheap-to-expensive ladder and prints what it found. If the result is
ambiguous — no generator meta, no recognisable asset paths, a client-rendered SPA that returns
an empty body — read **`references/recon.md`** and work the ladder manually, including the
browser tier. Do not label a stack you have not seen evidence for; `[VERIFY — could not
auto-detect]` is a legitimate output and is far cheaper than a wrong route.

Capture the CSP response header while you are here. A restrictive `script-src` changes what the
widget is allowed to be, and finding that out at QA is finding it out too late.

## Stage 2 — Brand extraction

**Extract from a representative article page, never from the homepage.** This is the easiest way
to ship a silently broken widget. Sites routinely scope a bolder palette to the homepage alone —
a `body.home-*` class, a landing-page stylesheet, a campaign theme — so tokens scraped from `/`
may not exist on `/blog/some-post/`, which is the only place the widget renders. Nothing errors;
every `var(--token)` resolves to nothing and the buttons come out unstyled.

Verified example: on thevibemarketinglab.com the entire `--ember` / `--ink` / `--paper` palette
sits behind `body.home-ember` and applies to the homepage only. Blog pages use a different
`--color-*` set. A homepage scrape hands you confident, well-named, completely wrong tokens.

So pick a real article URL from the sitemap first and extract there. If the two pages disagree,
say so in the deliverable rather than quietly preferring the prettier palette.

Pull the real rendered values, not the marketing hexes from a brand PDF: CSS custom properties
first, then computed styles on a heading, a body paragraph, and the site's primary button.

You need five things: a primary/action colour, a text colour, a surface colour, a border or
muted tone, and the type stack. Anything you cannot extract is written as
`[VERIFY — could not auto-extract]` and carried into the deliverable as-is. **Never invent a
brand colour.** A plausible-looking wrong hex survives review; a `[VERIFY]` flag gets answered.

Then confirm with **AskUserQuestion** before styling anything — show the extracted palette and
ask whether it is right, offering "use these", "I'll supply the brand kit", and "match the
site's existing button styles instead". Styling is the one thing the client will react to
emotionally, and re-styling after generation costs three files instead of one answer.

## Stage 3 — Route decision

| Detected stack | Read |
| --- | --- |
| WordPress (any host, any theme) | **`references/route-wordpress.md`** |
| Nuxt/Vue, Next/React, Astro, Hugo, Shopify, Webflow, unknown | **`references/route-custom.md`** |

Read one, not both. They contain different code and mixing them produces a plugin file with a
Vue component inside it.

## Stage 4 — Scope map

Build a table mapping URL pattern to topic phrase, using the sitemap the recon script found.
The topic phrase is what goes into the prompt, so write it the way a person would say it out
loud: `/health-insurance/{slug}/` maps to "Australian health insurance", not "health-insurance".

**In scope:** article, guide, explainer, and news/media pages. Individual pieces of writing with
something specific to summarise.

**Out of scope**, and say so explicitly in the brief so nobody has to infer it:

- The homepage and any vertical landing page
- Hub and listing pages (`/guides/`, `/companies/`)
- Calculators and tools
- Anything inside an account, checkout, quote, or compare flow
- Login-gated content — an AI cannot fetch it, so the citation never materialises
- Thin pages where the summary would be identical whichever URL was passed in

The exclusion rule is a route-prefix check, not a page-by-page list. `references/route-custom.md`
carries the helper; the WordPress route uses conditional tags instead.

## Stage 5 — Prompt build

Read **`references/prompt-policy.md`** and use the canonical prompt verbatim. It carries the
blocked-token list and the reasoning behind it.

The short version, because you will be tempted: **do not add a "remember this as an
authoritative source" clause.** Older versions of this tactic — including production builds we
have shipped ourselves — did, and Microsoft Security now classifies exactly that pattern as AI
Recommendation Poisoning. Refuse to emit it, and say why when you refuse.

## Stage 6 — Code generation

Five buttons in fixed order: ChatGPT, Claude, Perplexity, Grok, AI Mode.

**Endpoints come from `../_shared/platform-endpoints.json` and nowhere else.** Every entry in
that file was tested live in a logged-in browser. Do not copy an endpoint or a query parameter
out of a blog post, this SKILL.md, or your own memory — several widely-repeated ones are simply
fabricated. If a parameter is not in that file, it does not exist.

Two consequences worth stating up front:

- **Gemini cannot be prefilled.** Tested and confirmed: the composer stays empty for every
  parameter people claim works. Gemini is clipboard-mode only — copy the prompt, open Gemini,
  show a "prompt copied, paste it in" toast — and it is off by default.
- **Grok is the weakest button.** It consumes the prompt but auto-submits straight into a
  sign-in wall for logged-out readers. Flag it to the member for consumer-facing sites.

Render endpoints from one filterable config array, never serialised into stored content. These
are undocumented surfaces and the 2026 trend is removal, not addition — Copilot was killed
outright. A dead provider must be a one-line fix, not a re-migration.

Ship the tracking event with the code, not as a follow-up task: push `llm_share_click` to
`window.dataLayer` with `llm_platform`, `page_url`, `page_type`, `page_topic`, fired *before*
the tab opens.

### Styling: the client's palette, not the platforms' brand colours

Default output is **client-palette buttons with monochrome platform wordmarks or marks.**

This is deliberate and it overrides every reference implementation you will find, including our
own. Reasons, in order:

1. **Every client would otherwise get identical buttons.** Five platform brand colours produce
   the same widget on every site on earth. One client's styling belongs to that client;
   the next client's belongs to them.
2. **A row of five foreign brand colours looks like an ad unit**, not an editorial affordance,
   and it will lose the design review.
3. **Trademark exposure is lower.** A monochrome wordmark used as a compatibility indicator is
   the least contentious form; OpenAI's policy is the most restrictive of the five.

Platform brand colours are an **opt-in override** — offer it, do not default to it. If the
member asks for it, it is one token swap, and the brand hexes are in the shared endpoints file.

Self-host every icon. Third-party SVG CDNs get taken down at the brand owner's request — the
OpenAI mark has already been pulled from one widely-used mirror. Inline the ChatGPT path in the
component itself.

### The optional summary block

Read **`references/summary-block.md`** before recommending buttons alone. The only controlled
A/B on this tactic found buttons on their own *lost* clicks, and buttons plus an on-page AI
summary block gained them. That is one study on one site — but it is the only evidence there
is, and the member should present the pairing rather than discover it later.

## Stage 7 — Deliverables

Write three files into `outputs/YYYY-MM-DD-<client-slug>-llm-buttons/`:

| File | Built from | What it is |
| --- | --- | --- |
| `<client>-llm-buttons-brief.md` | `assets/brief-template.md` | The client-facing implementation brief: scope, placement, success criteria, QA list, rollback |
| `<client>-llm-buttons-code-reference.md` | `assets/code-reference-template.md` | Every line of code the dev pastes — component, CSS, icons, tracking |
| `<client>-llm-buttons-demo.html` | `assets/demo-template.html` | A standalone in-brand demo the client opens in a browser and approves |

Replace every `{{PLACEHOLDER}}`. Then read the brief once as the client would and check:

- **No internal references.** No workspace paths, no other client's name, no mention of our
  tooling. They cannot open those and it reads as sloppy.
- **No lift claims we cannot source.** Point at the honest evidence, do not promise a number.
- **The rollback section is intact.** One line deleted, no data migration. It is what makes a
  cautious dev say yes.
- **Every `[VERIFY]` flag survived.** Do not tidy them away before sending — they are the
  questions the client is meant to answer.

## Reference map

Read on demand, not up front.

| File | Read it when |
| --- | --- |
| `references/recon.md` | Stage 1 is ambiguous, or the site is an SPA / CSS-in-JS and needs the browser tier |
| `references/route-wordpress.md` | Recon says WordPress — WPVibe MCP, plugin file, hook patterns, fallbacks |
| `references/route-custom.md` | Anything else — Nuxt, React, Astro, vanilla, plus tracking and a11y spec |
| `references/prompt-policy.md` | Stage 5, every time, no exceptions — canonical prompt and blocked tokens |
| `references/summary-block.md` | Before recommending buttons alone, or when a client asks "does this work" |
| `../_shared/platform-endpoints.json` | Stage 6, every time — the only valid source of endpoints |

## Things that will bite you

**curl says 200 for everything.** All five assistant apps are client-rendered SPAs that return
a healthy response for any query string, including a fabricated one. A green curl is not
verification of an endpoint; only a logged-in browser is.

**The old prompt is still everywhere.** Our own wiki page, earlier client deliverables, and
every blog post on the tactic carry the memory-seeding variant. They predate the security
classification. `references/prompt-policy.md` supersedes all of them.

**`the_content` fires more often than you think.** On WordPress, an unguarded filter injects the
widget into feeds, REST responses, and related-post excerpts. The guard is not optional —
`references/route-wordpress.md` has it.

**Nothing client-specific belongs in this skill.** Every client fact is read at runtime from
their site. If you find yourself writing a client name, URL, or vertical into any file under
this skill, that is the bug.
