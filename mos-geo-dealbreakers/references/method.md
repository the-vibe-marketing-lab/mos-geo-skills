# Method: reading a site like a buyer who is looking for a reason to say no

Read this in Stage 3, every time, before you write a single finding.

## Contents

1. [What a dealbreaker is (and is not)](#1-what-a-dealbreaker-is-and-is-not)
2. [Personas](#2-personas)
3. [Category menu](#3-category-menu)
4. [Evidence types](#4-evidence-types)
5. [Severity](#5-severity)
6. [Priorities: the consequential few](#6-priorities-the-consequential-few)
7. [Already handled](#7-already-handled)
8. [Fix types](#8-fix-types)
9. [Writing rules](#9-writing-rules)

---

## 1. What a dealbreaker is (and is not)

A dealbreaker is a reason a **qualified** buyer would walk away, or stall, that they could
arrive at from public information alone. Qualified matters: "a vegan won't buy our whey"
is not a dealbreaker, it's targeting. "A lifter with a dairy intolerance can't find out
whether the isolate is lactose-free" is.

Three kinds of finding count:

- **Something the brand says** that disqualifies a buyer ("some lessons are still being
  built", "no refunds after 7 days").
- **Something a buyer needs and cannot find** (price of the top tier, what data leaves the
  laptop, how results are measured). The dealbreaker is the unanswerable question, not a
  claim that the thing doesn't exist. Say "a buyer cannot verify X from the public pages",
  never "X doesn't exist".
- **Something the public record contradicts** (the homepage says one price, a community
  post says another; old copy sells a different product).

Why this matters for GEO: buyers now put these exact questions to ChatGPT, Perplexity and
AI Mode ("what are the downsides of X", "is X worth it for agencies", "X pricing"). The
assistant answers from whatever is public. Where the brand hasn't answered, the answer
comes from a review site, a Reddit thread, or reads "unclear". That is a mechanism, not a
measured uplift: no controlled test shows that answering dealbreakers earns citations, so
never promise that it does.

Not dealbreakers: generic objections any offer in the category faces and the brand already
neutralises ("is this another expensive course?" when entry is free), style preferences,
and anything you would need insider knowledge to raise.

## 2. Personas

Before the categories, name 2 to 4 buyer personas from the site's own words: who it says
it's for, who it says it's **not** for (that section is gold), the case studies' job
titles, the pricing tiers' labels. Each persona gets an id, a label, one line on what they
need to be true before they buy, and a source URL.

Read every page once per persona. The agency owner and the solo marketer hit completely
different walls on the same pricing page. Tag each finding with the personas it blocks.
A finding that blocks nobody on your list is either a new persona or not a finding.

## 3. Category menu

Pick **6 to 10** categories that fit the business. Use these names verbatim where they fit
(the report gives each an emoji); invent a category only when none of these fits.

| Category | Ask of every page | Usually matters for |
|---|---|---|
| Proof & Results | Is there evidence the product produces the outcome being sold, not an adjacent outcome? Quantified before/after? ROI? | Everyone. Almost always the top category. |
| Product & Setup Requirements | What must the buyer have, learn, install or already know? Is it what they'd assume it is? | SaaS, courses, communities, equipment |
| Maturity & Completeness | Is anything unfinished, in beta, "coming soon", thin, recently pivoted? | New offers, communities, courses |
| Pricing & Offer Clarity | Can a buyer find the price of every tier, what's included, what changes later, total cost including required third-party tools? | Everyone |
| Risk & Guarantees | Refunds, cancellation, contracts, lock-in, warranties, trial terms | Everyone paying upfront |
| Data, Security & Compliance | Where does the buyer's data go? DPAs, SOC 2, privacy, regulated industries | B2B, SaaS, health, finance |
| Team & Enterprise Adoption | Seats, permissions, multi-client, SSO, procurement, SLAs, invoicing | B2B above solo size |
| Measurement & Attribution | How will the buyer know it worked? Variance, attribution, baselines | Marketing, SEO/GEO, coaching |
| Integrations & Ecosystem | Does it plug into what they already run? | SaaS, agencies, ecommerce platforms |
| Audience Fit | Who is this too basic, too advanced, wrong-channel, wrong-size or wrong-region for? | Everyone; mine the "not for" copy |
| Support & Service | Response times, access to humans, time zones, key-person dependency | Services, communities, B2B |
| Delivery & Fulfilment | Shipping times and costs, stock, regions, returns logistics | Ecommerce, physical goods |
| Ingredients, Safety & Claims | What's in it, testing, allergens, certifications, claim substantiation | Supplements, food, health, beauty |
| Location & Access | Hours, parking, booking, catchment, accessibility | Local businesses |
| Category Credibility | The sharpest questions an expert in the category would ask, in their own words | Anything sold on expertise |

**Category Credibility** is where this report earns its keep. Write 5 to 10 findings whose
`buyer_question` is in the voice of the most knowledgeable buyer ("Show me citation gains,
not SEO traffic gains"). Each is still a finding with evidence, usually `absent`.

## 4. Evidence types

Every finding carries exactly one. The build step enforces the rule in the right column.

| Type | Means | Build rule |
|---|---|---|
| `stated` | The brand's own public words create the objection | At least one source with a verbatim quote found in a saved page |
| `contradicted` | Two public sources disagree, or old copy sells something different | At least two sources, each with a verbatim quote found in a saved page |
| `absent` | A buyer needs this and the public pages don't answer it | `checked` lists at least two saved page URLs or `search:` queries you actually ran |
| `inferred` | A reasonable buyer concern given how the offer works, with no page to point at | `reason` required; severity can't be `critical` |

Prefer `stated` and `contradicted`: they're the ones a client can't argue with. `absent`
is only as strong as the pages you checked, so check the obvious homes first (pricing,
FAQ, about, terms, the footer). Keep `inferred` findings few; if a finding is mostly
opinion, raise it in the review conversation instead.

Third-party sources (reviews, Reddit, a comparison page) are fair evidence of what a buyer
sees. Save the page with `add` so the quote can be verified, and write "a review on <site>
says" in the claim.

## 5. Severity

| Severity | Test |
|---|---|
| `critical` | A qualified buyer who hits this stops. It goes to the heart of the promise: proof of the core outcome, the price, the thing they're paying for not existing yet. |
| `major` | A qualified buyer slows down, asks sales, or shortlists a competitor. |
| `minor` | Friction or a nice-to-have. Worth an FAQ line. |

Calibrate against the whole set. If more than a quarter of findings are `critical`, you're
inflating. A typical run lands at 3 to 6 critical, 10 to 20 major, the rest minor.

## 6. Priorities: the consequential few

After the categories, pick **3 to 7** finding ids (critical or major only) as the priority
list, ordered by how much conversion they cost. Then write `not_prioritised`: one or two
sentences on which obvious, generic objections you deliberately left off and why (usually
because the offer already neutralises them). This is what makes the report read like a
strategist wrote it rather than a checklist.

## 7. Already handled

List the objections the offer already neutralises, each with a quoted source. This keeps
the report honest in both directions and tells the client what to keep. Free entry,
explicit "not for" copy, candour about what's unfinished and owned data are typical.

## 8. Fix types

Each finding suggests one fix. The type drives the workbook's Initiatives category and ICE
ease score.

| Type | Use when the fix is |
|---|---|
| `faq` | Answering a question the brand can already answer truthfully |
| `pricing-page` | Publishing or clarifying prices, tiers, total cost |
| `proof-asset` | Producing evidence that doesn't exist yet (case study, screenshots, data) |
| `policy-doc` | Security, data handling, refund, SLA or compliance documentation |
| `positioning` | Rewriting who it's for, or retiring contradictory old copy |
| `product` | Changing the offer itself |
| `none` | An accepted trade-off; the brand should own it, not fix it |

Only fill `fix.answer` when every word of it is backed by `fix.answer_sources`. Otherwise
leave it out: the FAQ draft then asks the client, which is the point.

## 9. Writing rules

1. **Lead with the objection, in plain words.** One sentence in `claim`. The report bolds it.
2. **"A buyer cannot verify", not "there is no".** Absence of a page is not absence of the
   thing.
3. **Quote, don't paraphrase, in `sources`.** Short and verbatim, copied from the saved page
   text. The build checks it.
4. **Name the brand's own candour.** If the site admits a weakness, say so; it lowers
   distrust even when it doesn't remove the objection.
5. **No insults, no motives.** "Founder bandwidth could become a constraint" is a buyer's
   worry. "The founder is overstretched" is a claim you can't source.
6. **Date anything time-sensitive** (founding price, member count, beta), because it will
   change.
7. **Nothing brand-specific belongs in this skill's files.** Brand facts live only in the
   run folder.
