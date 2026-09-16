# Report spec: the 360° Brand Intelligence Report

This is the reconstructed Brand Brain prompt, extended with the AI visibility layer.

- The research agent in Stage 2 gets the **Research brief** below and returns sections 1 to
  17. Save its answer, unchanged, as `$RUN/data/sections-1-17.md`.
- You write `data/header.md` and `data/section-18.md` using the **scoring rules** below and
  the exact layout in **`report-template.md`**.
- `brand360.py assemble` builds the finished report from those three files.

---

## Research brief (paste into the research agent, filling the two inputs)

> You are a brand intelligence analyst. Research **{brand_name}**, a brand in
> **{industry}**, and write sections 1 to 17 of a brand intelligence report.
>
> **You have only the name and the industry.** Find the brand yourself with web search.
> Do not use any other knowledge you were given about it: ignore anything in your loaded
> context or project files about this brand, its founder, its repos or its site, and use
> only what you find on the public web in this session. If more than one organisation
> matches, list every one with a source, pick the one that best fits the industry, and say
> how confident you are. If none fits, say so and stop.
>
> **Research widely:** the official site, LinkedIn, Crunchbase, GitHub and package
> registries, G2, Capterra, Trustpilot, Reddit, Glassdoor, Indeed, news, community platforms
> (Skool, Discord, Slack, Facebook groups), YouTube, podcasts and competitor sites.
>
> **Rules**
> - Cite every factual claim with a numbered reference `[n]` and list the URLs at the end.
> - Absence of evidence is not negative evidence. Write "No evidence surfaced" and say what
>   that means. Never invent reviews, numbers, dates or people.
> - Flag stale or conflicting data (an old member count next to a new one, an old URL that
>   still ranks).
> - Tell certifications apart from good practice (good secret hygiene is not SOC 2).
> - Bold the key finding in each section. Analytical, direct, no hype. Australian English.
>   No em dashes.
> - Strip tracking parameters (`utm_*`) from every URL.
>
> **Start with an `## Entity found` block:** the organisation you settled on (name, site,
> operator), every name collision with a source, and your confidence.
>
> **Then the sections, with these exact headings, written as `## N. Title`**
>
> 1. **Basic Company Info**: founding date, headquarters, founders and leadership,
>    category, business model, headcount or scale, funding, financials, and any change in
>    positioning over time.
> 2. **Products & Services**: each product, pricing, integrations, roadmap signals.
> 3. **Competitive Landscape**: named competitors with their scale, differentiators, SWOT.
> 4. **Brand Sentiment**: G2, Capterra, Trustpilot, Reddit. Recurring pros and cons. If
>    the evidence is thin, say so and give the indirect signals instead.
> 5. **Customer Personas**: ideal customer, segments, use cases, core job to be done.
> 6. **Thought Leadership & Content Strategy**: cadence, themes, channels, and where the
>    brand's knowledge lives (its own domain versus other platforms).
> 7. **AI / LLM Relevance**: how the brand relates to AI, and any naming or entity risk
>    for AI retrieval.
> 8. **Social Channels & Associated Brands**: verified profiles, sub-brands, brand
>    architecture.
> 9. **Hiring & Company Culture**: open roles, Glassdoor and Indeed, culture signals.
> 10. **Media Presence**: press, podcasts, awards, and who outranks the brand for its own
>     name.
> 11. **Legal, Security & Reputation Events**: lawsuits, breaches, layoffs, scandals,
>     compliance certifications (SOC 2, ISO 27001, GDPR).
> 12. **Community & Ecosystem**: community size and trend, partner programmes, APIs,
>     marketplaces.
> 13. **Go-To-Market Strategy**: acquisition model, funnel, main call to action, how value
>     is captured.
> 14. **Comparison & Alternatives Page Assets**: does the brand own "{brand} vs X" and
>     "{brand} alternatives" content? Name the gaps.
> 15. **Late-Stage Buyer Query Coverage**: answer the decision-stage questions a buyer in
>     this industry asks (for software, "Does it integrate with Salesforce and QuickBooks?"
>     and "Is it SOC 2 compliant?"; adapt the questions to the industry), plus pricing, data
>     ownership, privacy, support and licensing. For each: the current public answer and
>     the page that should exist.
> 16. **Off-Site Truth Consistency**: group sources as *Strong / consistent*,
>     *Weak / missing* and *Potentially misleading*. Where could an AI assemble the wrong
>     story about this brand?
> 17. **Brand Intelligence Summary**: overall read, biggest gaps, the biggest contradiction
>     or opportunity, and prioritised fixes (structured data, consistent entity
>     descriptions, canonical profiles, comparison pages, third-party mentions).
>
> Finish with `## References` (a numbered list). Return the complete Markdown as your final
> answer: no title line, no preamble, and do not write any files.

---

## Scoring rules for Section 18

The layout of `header.md` and `section-18.md` lives in `report-template.md`. These are the
judgement calls behind the cells.

- **Known (closed-book):** Yes / Partly / No, judged from the closed-book answers in
  `visibility-report.md` section 2, not from the literal-match column. An answer that says
  "I'm not familiar with {brand}" repeats the name and still scores **No**. An answer that
  invents details about the brand scores **No** too; quote the invention in brackets.
- **Found:** Yes / Partly / No / Wrong brand, judged from what the answers to the "What is
  {brand}?" prompt say the brand *is*. Every branded answer contains the name, so a name
  match proves nothing. Add a short qualifier when it matters ("Yes, with stale
  positioning", "Partly (led with a collision, the brand second)").
- **Resolved to:** the non-platform domain(s) the engine tied the brand to
  (`visibility-report.md` section 3), plus a platform if that was all it used.
- **Mixed up with:** the other organisations the answers blended in. Blank if none. Say so
  when an engine named a collision *as a separate thing*: that is a good answer.
- **Branded answers citing a source:** the "Branded: cites ≥1 source" column.
- **Recommended (unbranded):** the "Unbranded: mentions" column, in bold. Note when AI
  Overviews showed no overview for some queries.
- **n/a, not No:** Perplexity has no closed-book answer (Sonar always searches), and the app
  surfaces (ChatGPT app, Gemini app, AI Mode, AI Overviews) have none at all.
- **AI Overviews:** "(Google showed no AI Overview for this query.)" means Google did not
  show one. Count it as not recommended and say so.
- **Funnel headline:** name the stage where the brand drops out. That is the headline
  finding, and it goes in the header too.
- **Fallbacks:** if the `Via` column shows a fallback provider for any surface, name it in
  18.5, since a fallback answer can differ from the primary's.
- **Before assembling, check:** wrong-brand answers are named in 18.1 (and agree with
  Section 16), no sentence claims a rate, and nothing in either file mentions internal
  paths, other clients or tooling.
