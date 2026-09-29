---
name: mos-geo-dealbreakers
description: >
  Dealbreaker Detector: read a brand's public website, community, marketplace listing and
  reviews the way a sceptical, qualified buyer would, and list every reason they'd walk away
  or stall — weak proof of the core outcome, unclear pricing or tiers, setup burden,
  unfinished product, risk and data questions, team/agency gaps, measurement, integrations,
  audience fit, support — each one backed by a verified quote from a saved page or by the
  pages checked, rated by severity, tagged by buyer persona, with the 3 to 7 to fix first,
  the objections already handled, an FAQ draft and rows in the GEO brand audit workbook.
  USE WHEN the user says "dealbreaker detector", "dealbreakers", "deal breakers", "buyer
  objections", "what would stop someone buying", "why aren't people converting", "what
  questions would a prospect have", "objection audit", "what are the downsides of our offer",
  "what would ChatGPT say is wrong with us", "poke holes in our offer from a buyer's view",
  "/mos-geo-dealbreakers", or pastes a GPT dealbreaker output and wants it redone properly,
  for their own brand, a client, or a competitor.
  NOT FOR testing what AI engines currently say about a brand (use mos-geo-brand-360),
  writing the sourced fact sheet for AI assistants (use mos-geo-ai-info), attacking a
  strategy or plan rather than a live offer (use RedTeam), or writing the FAQ page copy
  itself (hand the FAQ draft to a copywriting skill).
---

# Dealbreaker Detector

You are producing a **client deliverable**: a candid list of the reasons a qualified buyer
would say no to this offer, built only from what a buyer can see in public. The client acts
on it (proof assets, a pricing page, FAQs, policy docs), so every line has to survive the
client asking "where does it say that?"

The method is Steve Toth's (Notebook Agency). This skill is an independent implementation,
not affiliated with or endorsed by them.

## Why the rules are strict

A dealbreaker report that invents an objection gets the whole report thrown out, and a
report that states "there is no X" when X exists on a page you didn't read is worse. The
popular GPT version of this does both occasionally. So:

1. **Every finding is typed and evidenced** (`references/method.md` section 4): `stated`
   and `contradicted` findings quote a page you saved; `absent` findings list the pages
   you checked; `inferred` findings give a reason and can never be critical.
2. **The report is built, never hand-written.** You write `data/findings.json`;
   `dealbreakers.py build` verifies every quote against the saved page text and renders
   the report, the FAQ draft and the CSV. It refuses to render while anything fails.
3. **"A buyer cannot verify X", never "X doesn't exist."** The dealbreaker is the
   unanswered question.

Why it's GEO work: buyers now ask ChatGPT, Perplexity and AI Mode "what are the downsides of
X" and "X pricing", and the assistant answers from whatever is public. Unanswered
dealbreakers get answered by someone else, or come back as "unclear". Say that. Don't
promise it earns citations: nothing has measured that.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | Inputs | Website, extra surfaces, own or competitor mode; run folder created |
| 1 | Crawl | `data/crawl.json` has the buying pages (pricing, about, FAQ, terms) or you know why not |
| 2 | Off-site sweep | Community, reviews and indexed posts searched; useful pages saved with `add` |
| 3 | Read as a buyer → findings.json | Personas named; 6 to 10 categories walked |
| 4 | Build | `build` passes with no `[FAIL]`; five findings spot-checked by you |
| 5 | Review with the user | Priorities and anything sensitive agreed |
| 6 | Workbook | Dealbreakers tab filled, Checklist ticked, priorities on Initiatives (own mode) |

Set `SKILL=<this skill's folder>`. Run everything from the user's project so the run folder
lands in their brain:

```bash
RUN=$(python3 "$SKILL/scripts/dealbreakers.py" path --brand "<brand>")
mkdir -p "$RUN"
```

Run folders follow the other mos-geo skills: `campaigns/geo/YYYY-MM/dealbreakers/` in a
one-brand brain, `campaigns/geo/YYYY-MM/<brand>/dealbreakers/` in an agency brain,
`outputs/geo/YYYY-MM/<brand>/dealbreakers/` with no brain, `-2` on a repeat run.
`brand-audit-master.xlsx` sits one level up.

```
<run folder>/
  dealbreakers-report.md     the deliverable
  faq-draft.md               one question per answerable dealbreaker; unknowns marked [CLIENT TO ANSWER]
  data/                      findings.json (you write it), findings.csv, crawl.json,
                             sitemap-urls.txt, pages/ (saved text of every page read)
```

Never commit a run folder into this pack: it holds client data.

---

## Stage 0: Inputs

Ask in one message, skipping anything the user already gave:

- **Website URL** (required).
- **Other surfaces a buyer sees**: community (Skool, Circle, Discord invite page),
  marketplace or app store listing, pricing page on another domain, review profiles.
- **Own brand / client, or competitor?** Competitor mode writes no Initiatives rows and the
  tab is named after the competitor.
- **Known objections**, if they have them: sales-call notes, DMs, refund reasons. Real buyer
  language beats anything you infer. If the brain has a copy-research bank or avatar file,
  read it for objections and personas instead of asking.

## Stage 1: Crawl

```bash
python3 "$SKILL/scripts/dealbreakers.py" crawl --url <website> --out "$RUN" \
  --extra <community about page> --extra <listing URL>
```

`--extra` takes one URL each time; repeat the flag for more.

The crawl reads robots.txt, sitemaps and the homepage's nav and footer, ranks buying pages
(pricing, about, FAQ, features, case studies, terms, refunds, security, integrations,
community) above blog posts, and saves up to 40 pages as text in `data/pages/`. It also
saves the homepage as it looked about 12 months ago from the Wayback Machine, which is how
you spot positioning drift (`--wayback-months 0` to skip).

Open `data/crawl.json`. If pricing, about, FAQ or terms are missing, find them from the
footer or a site search and `add` them. FAQ and help-centre hubs often list only the
question titles, with each answer one click deeper: `add` the answer pages for any question
you might call `absent`, or the finding is a crawl-budget artefact, not a buyer's gap. Blocked or JavaScript-only pages: see "Things that
will bite you".

## Stage 2: Off-site sweep

A buyer doesn't stop at the website, and neither do the assistants they ask. Search, then
save every page you intend to cite:

- `"<brand>" review`, `"<brand>" reddit`, `"<brand>" pricing`, `"<brand>" vs`,
  `"<brand>" alternatives`, `"<brand>" refund` or `cancel`
- `site:<community domain>/<group>` for indexed community posts (Skool, Circle and similar
  index public posts; they're where old pricing and old positioning linger)

```bash
python3 "$SKILL/scripts/dealbreakers.py" add --run-dir "$RUN" <url> <url>
# a page you could only read in a browser or with WebFetch:
python3 "$SKILL/scripts/dealbreakers.py" add --run-dir "$RUN" --url <url> --text-file <saved.txt>
```

Keep the queries you ran: an `absent` finding can list them as `search: <query>`.

Review platforms (Trustpilot, G2, Capterra, ProductReview) usually 403 a script. Read them
with WebFetch or the browser and save the text with `add --text-file`. A search engine's
summary of a review site is a lead, never a source: its numbers are often stale or wrong.
If you can't save the page, leave the review out.

## Stage 3: Read as a buyer, write findings.json

Read `references/method.md` now, all of it. Then:

1. **Write the offer summary** from the current pages: what is sold, to whom, at which price
   points. If the Wayback page or old community posts sell something different, that's
   `positioning_drift`, and often a dealbreaker in its own right.
2. **Name 2 to 4 personas** from the site's own "for" and "not for" copy.
3. **Walk 6 to 10 categories** from the menu, persona by persona, page by page. Look hardest
   at Proof & Results: does the evidence prove the outcome being sold, or an adjacent one?
   Traffic screenshots don't prove citations; testimonials about the community don't prove
   the method.
4. **Write the Category Credibility questions** in the voice of the sharpest buyer.
5. **Pick 3 to 7 priorities** and write `not_prioritised`.
6. **List what's already handled**, with quotes.

Write it to `$RUN/data/findings.json` following `references/findings-schema.md`. Copy quotes
from the files in `data/pages/`, not from memory of the page.

## Stage 4: Build

```bash
python3 "$SKILL/scripts/dealbreakers.py" build --run-dir "$RUN"
```

Fix every `[FAIL]` in `findings.json` and build again. The usual ones: a quote paraphrased
instead of copied, a cited URL never saved (run `add`), an `absent` finding with one checked
page, an `inferred` finding rated critical. Treat `[WARN]` as a question to yourself: more
than a quarter critical usually means inflation.

When it passes, open five findings yourself and check them against the saved page: every
critical one, then any number, price or date. A finding you can't stand behind comes out.

## Stage 5: Review with the user

Show, briefly: the priority list with fixes, the severity counts, the positioning drift if
any, and anything sensitive (named people, key-person risk, a competitor named in a review).
In own mode the report is candid about the user's own business, so ask before anything
leaves the room.

Then ask with AskUserQuestion:

1. **Priorities: keep, reorder or swap?** Apply the change to `findings.json` and build again.
2. **Anything they can answer now?** Their answer becomes `fix.answer`, sourced to a page
   only once it's published; until then leave it in the FAQ draft as the client's to write.

## Stage 6: Workbook

```bash
uv run --with openpyxl python "$SKILL/scripts/dealbreakers.py" workbook --run-dir "$RUN"
```

This creates `brand-audit-master.xlsx` in the month folder if needed, ticks the
`mos-geo-dealbreakers` row on **Checklist**, writes the **Dealbreakers** tab (one row per
finding with a client verdict dropdown; verdicts survive a re-run) and, in own mode, adds one
ICE-scored **Initiatives** row per priority.

Hand over the run folder, the report, and the next step: the client marks verdicts on the
tab, then `faq-draft.md` goes to a copywriting skill to become the FAQ page, and proof gaps
go on the content plan. Re-run in a month or after the fixes ship to see what's cleared.

## Reference map

| File | Read it when |
|---|---|
| `references/method.md` | Stage 3, every time: personas, category menu, evidence types, severity, fix types |
| `references/findings-schema.md` | Writing or fixing `findings.json`; what each `[FAIL]` means |

## Things that will bite you

**Hosts that 403 bots, and JavaScript-only pages** (community platforms often are). The
script sends a Chrome user agent and backs off; with Scrapling installed it retries with
browser-grade TLS and renders JavaScript:

```bash
uv run --with "scrapling[fetchers]" python "$SKILL/scripts/dealbreakers.py" crawl --url <site> --out "$RUN"
uv run --with "scrapling[fetchers]" scrapling install   # once, for JavaScript rendering
```

Still empty? Read the page in the browser or with WebFetch, save the text to a file, and
`add --text-file`. Note in the report's review that assistants which don't run JavaScript
may see the same empty page a plain crawler did; that is itself a dealbreaker for GEO.

**Dated numbers.** Member counts, founding prices and "beta" labels change monthly. Put the
date in the claim.

**Your own knowledge of the brand is a lead, never a source.** If you remember a price or a
feature, find the page and save it, or leave it out.

**The GPT version's output is a lead too.** If the user pastes one, treat each line as a
hypothesis to verify against saved pages; plenty will hold, some won't.

**Nothing brand-specific belongs in this skill.** If you are about to write a brand, domain
or client name into any file under this folder, that is the bug.
