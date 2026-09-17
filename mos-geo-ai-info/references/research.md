# Research: where the facts come from

## The truth ladder

When two sources disagree, the higher one wins. Record the conflict in your hand-back.

1. **Client corrections.** Use the "correct version" from the month's Brand Truth Review
   (`aiinfo.py truths`) and anything the user tells you in this session. Drop any claim the
   client marked Inaccurate or Out of date.
2. **The brand's own site as it is today.** Use `data/pages/*.md` from the crawl.
3. **Official registers and the brand's own profiles.** For example: ABN Lookup (AU),
   Companies House (UK), OpenCorporates, the LinkedIn company page, and Google Business
   Profile.
4. **Reputable third parties.** For example: award organisers' own winner lists, trade
   press, event programmes, and reviews on named platforms.
5. **Never use** AI answers, including this session's own memory of the brand, scraped
   directory copies, or anything you can't open and quote.

If this session already "knows" the brand, that knowledge is a lead to check. It is never a
source. A fact with no URL behind it does not go on the page.

## Research agent brief

Spawn **one** research agent with this brief. Fill in the braces. If subagents aren't
available, work through it yourself.

```
You are researching facts for an AI Info Page about {brand} ({website}). An AI Info
Page is a public fact sheet that AI assistants read to describe the brand accurately.
Accuracy beats coverage: a missing fact is fine, a wrong fact is not.

Inputs, all in {run_dir}:
- data/crawl.json: the crawl summary (pages, socials, emails, phones, ABN, JSON-LD).
- data/pages/*.md: text of the brand's key pages. Read the about, team, contact, services,
  case-study, awards and resources pages first; skim the rest.
- {truths}: client corrections. These override everything.
- {brand360}: an earlier brand-360 research draft, if present. Treat it as leads, not
  sources; re-open any URL you rely on.

Then search the web for what the site doesn't say. Stop once each topic below has one
source; don't keep collecting.
- legal name and registration (ABN Lookup / company register)
- LinkedIn company page (URL, headcount band, locations)
- founder and leadership (LinkedIn, press)
- awards (the organiser's own winner list)
- press coverage, events the brand runs or speaks at
- review platforms (name, rating, count, date seen)
- namesakes: search the brand name on its own and with its category. List any other
  business, product or term with a similar name that an engine could blend in (open each one;
  note its domain). They feed the "Not to be confused with" guidance line.

One-page sites: the crawl fetches everything, but there may be only one or two pages.
Lean on the brand's own profiles (community platform, LinkedIn, GitHub, marketplace
listings) as first-party sources and mark them `first_party: true`. When two first-party
numbers disagree (a stale homepage counter against a live platform count), use the live
one, round it ("about 300 members"), and report the conflict.

Write {run_dir}/data/facts.json following references/facts-schema.md exactly, and the
writing rules in references/page-template.md. Every basic field and paragraph cites
source ids; every source has a URL you opened. Name clients only if the brand publishes
them itself. Self-reported claims use "{brand} states that …".

List every client, award, product, programme and event you name in "probe_terms", then run:
  python3 {skill}/scripts/aiinfo.py probe --run-dir {run_dir}
Read data/probe.md and the new data/pages/probe-*.md files. Add what those pages publish
(older case studies especially). A term with no page on the site needs a third-party
source or it comes out.

Record every place where sources disagree in "discrepancies" (each value with its URL, the
value you used, and the site fix). Pages missing from the XML sitemap go in too.

Then run:  python3 {skill}/scripts/aiinfo.py build --run-dir {run_dir}
and fix every [FAIL] until it builds. Leave [warn] lines you disagree with and say why.

Hand back, in under 250 words:
- facts you could not source (left out)
- the discrepancies you recorded, and any you could not settle (the user decides those)
- statements that rest only on third-party sources
- anything that looks sensitive (a named client, a person's details, pricing)
```

## Checking the draft before you show it

Open `data/fact-check.csv` and `ai-info-page.md`, and spot-check five statements against
their source URLs, focusing on the ones with numbers, awards and client names. If any is
wrong, fix `facts.json` and build again. Unless the user asks, don't read every page file
into your own context; the research agent already has.
