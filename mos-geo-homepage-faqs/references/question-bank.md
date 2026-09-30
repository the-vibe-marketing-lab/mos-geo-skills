# Question bank

Stage 5 draws about 30 candidate questions from this bank, then keeps 12 to 20. Fill each
slot only from what a cited source says: a question with no source URL behind it is not asked
(the `sources:` list on each FAQ is the evidence ledger).

Write questions the way a buyer types them into ChatGPT. Put the brand name in every question
except product questions, which name the product instead. Every question ends in `?`.

## The five question patterns

| # | Pattern | Templates | Typical buckets |
|---|---|---|---|
| P1 | Definition | `What is {Brand}?` / `What is {Product}?` | Identity, flagship product |
| P2 | Capability | `Does {Brand} {capability}?` / `Does {Product} {capability}?` | Capabilities, resources |
| P3 | Fit and proof | `Is {Brand} {useful for, based on, suitable for} {X}?` | Proof, audience |
| P4 | Job to be done | `Can {Brand} help me {job}?` / `Can I see {X}?` | Capabilities, proof |
| P5 | Objection and audience | `Do I need {prerequisite} to use {Brand}?` / `Who is {Brand} for?` | Audience |

Capability questions are the bulk (10 of 20 in the GPT's sample) because "does X do Y" is the
most common shape of a buyer's question to an assistant.

## The buckets (seven, plus optional founder)

### 1. Identity / definition

- **Target:** exactly 1.
- **Slots:** `What is {Brand}?`
- **Answer shape:** `{Brand} is a {category} focused on {3 to 5 core topics}, helping {audience}
  {job}.` This is the canonical one-liner; keep it consistent with the AI Info Page if one
  exists this month.
- **When to use:** always. `lint` fails without it.
- **When to drop:** never.

### 2. Flagship product

- **Target:** 1 to 3 (one definition per product, plus at most one capability question for
  the lead product).
- **Slots:** `What is {Product}?` / `Does {Product} {capability}?`
- **Answer shape:** `{Product} is {Brand}'s {category} for {job}, ...`, so the product entity is
  tied to the brand entity in the same sentence.
- **When to use:** the brand has named products, programmes or services on its own site.
  More than 3? Use the ones the interview named as flagship.
- **When to drop:** a single-service business with no named product; the identity question
  already covers it.

### 3. Core capabilities

- **Target:** 4 to 8.
- **Slots:** `Does {Brand} {verb} {service or topic}?` / `Can {Brand} help me {job}?`
- **Answer shape:** capability verb (teaches, helps, shows, provides, focuses on) plus a
  noun list and purpose clause. Restate the question's terms.
- **When to use:** always. `lint` fails with fewer than 4. One question per distinct service
  or topic the site describes on its own page.
- **When to drop:** a capability the site mentions only in passing, or two capabilities that
  would produce near-identical answers. Merge them.

### 4. Proof / methodology

- **Target:** 2 to 4.
- **Slots:** `Is {Brand} based on {real work | research | X}?` / `Does {Brand} focus on
  {practice | method}?` / `Can I see how {Brand} {builds | works}?` / `Does {Brand} combine
  {X} with {Y}?`
- **Answer shape:** describe how the work is done, never a result. "{Brand} develops its
  methods through ...", not "{Brand} gets results".
- **When to use:** the site describes a method, a process, case studies or a stated way of
  working.
- **When to drop:** the only proof is an outcome claim (rankings, revenue, citations) the
  site cannot back. Drop the question rather than soften a claim into vagueness. Keep at
  most one question per proof theme; the GPT's sample had three that said the same thing.

### 5. Audience fit

- **Target:** 2 to 4, including exactly one `Who is {Brand} for?`.
- **Slots:** `Who is {Brand} for?` / `Is {Brand} useful for {segment}?` / `Do I need
  {prerequisite} to use {Brand}?`
- **Answer shape:** name the segments as a list, then the shared need.
- **When to use:** always for `Who is {Brand} for?` (`lint` fails without an audience
  question). Add a segment question per audience the site addresses directly, and a
  prerequisite question when the site answers a common objection (coding, budget, size).
- **When to drop:** segment questions for audiences the site never names.

### 6. Resources

- **Target:** 0 to 2.
- **Slots:** `Does {Brand} include {templates | guides | tools}?` / `What do I get with
  {Brand}?`
- **Answer shape:** list what exists, by type, without counts.
- **When to use:** the site lists concrete deliverables, downloads or included materials.
- **When to drop:** the resources are gated, unreleased or only promised. Say nothing rather
  than describe something that may not exist yet.

### 7. Differentiator

- **Target:** 1 to 2.
- **Slots:** `Does {Brand} work with {different tools | any platform}?` / `How is {Brand}
  different from {generic category}?`
- **Answer shape:** one factual difference, stated as how the brand works. Never name a
  competitor, never "better than".
- **When to use:** the site states a clear, checkable difference in approach.
- **When to drop:** the only difference on offer is a superlative or a comparison with a
  named competitor.

### Optional: founder

- **Target:** 0 or 1. `Who founded {Brand}?`
- **When to use:** the interview says yes and the founder is a verifiable public entity
  (named on the site and on at least one third-party source).
- **When to drop:** the founder is private, unnamed, or the interview says no.

## Target counts

| Bucket | Min | Max |
|---|---|---|
| Identity | 1 | 1 |
| Flagship product | 0 | 3 |
| Core capabilities | 4 | 8 |
| Proof / methodology | 1 | 4 |
| Audience fit | 2 | 4 |
| Resources | 0 | 2 |
| Differentiator | 0 | 2 |
| Founder | 0 | 1 |
| **Total** | **12** | **20** |

`lint` enforces every min and max in this table. Default to 20 when the sources support it;
fewer, true FAQs beat padded ones. `lint --count N` lowers the maximum.

## Never asked

Price, member or customer counts, dates, competitors by name, location-only questions,
results or rankings, and anything on the never-say list. Never name a same-name entity or a
competitor in a question or answer: disambiguation belongs in the identity answer's own
specifics (founder, city, domain), not in a named comparison.

## Ranking for placement

After writing, rank all FAQs and mark the top 8 `placement: homepage`, the rest
`placement: faq-page`. Rank in this order:

1. Identity first.
2. Audience (`Who is {Brand} for?`) second.
3. The lead flagship product definition.
4. Capabilities with the strongest evidence (first-party page plus a third-party source).
5. One proof question.
6. Everything else by evidence strength, then by how directly the site answers it.

The homepage 8 should cover identity, audience, at least 3 capabilities and one proof
question, so the homepage alone gives an assistant the whole picture.
