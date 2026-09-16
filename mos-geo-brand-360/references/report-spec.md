# Report spec: the 360° Brand Intelligence Report

This is the reconstructed Brand Brain prompt, extended with the AI visibility layer. The
research agent in Stage 2 gets the **Research brief** below. You (the orchestrator) write
Section 18 and the header from `visibility.md`.

---

## Research brief (paste into the research agent, filling the two inputs)

> You are a brand intelligence analyst. Research **{brand_name}**, a brand in
> **{industry}**, and write sections 1 to 17 of a brand intelligence report.
>
> **You have only the name and the industry.** Find the brand yourself with web search.
> Do not use any other knowledge you were given about it. If more than one organisation
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
> - Strip tracking parameters (`utm_*`) from every URL.
>
> **Sections (use these exact headings)**
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
> Finish with the numbered reference list. Return Markdown only.

---

## Header (you write it)

- Brand, industry, research date.
- **Entity found:** the organisation the research agent settled on, plus every name
  collision it found, each with a source.
- **What the engines found:** one line from `visibility.md` section 3 (did the engines
  land on the same organisation the research agent did?).
- A one-line note: "Every AI prompt was asked once. Treat single answers as a snapshot."

## Section 18: AI Visibility Scorecard (you write it from `visibility.md`)

### 18.1 Engine by engine

| Engine | Surface | Known (closed-book) | Found | Resolved to | Mixed up with | Cited sources | Recommended (unbranded) |
|---|---|---|---|---|---|---|---|

- **Known:** Yes / Partly / No. Judge from the closed-book answers in `visibility.md`
  section 2, not from the literal-match column: an answer that says "I'm not familiar with
  {brand}" repeats the name and still scores No.
- **Found:** Yes / No / Wrong brand, from the branded search answers.
- **Resolved to:** the non-platform domain(s) the engine tied the brand to (section 3).
- **Mixed up with:** other organisations the answer blended in. Blank if none.
- **Cited sources:** how many branded answers cited at least one source.
- **Recommended:** unbranded answers that named the brand, as `x/5`.

The API surface has no *Known* entry for Perplexity (Sonar always searches), and the app
surfaces (ChatGPT app, Gemini app, AI Mode, AI Overviews) have none at all: they only exist
with search on. Write `n/a`, not No. For AI Overviews, "(Google showed no AI Overview for
this query.)" means Google did not show one; score that as not found, and say so.

### 18.2 The funnel

One line per stage, counting engines: **Known → Found → Cited → Recommended**. Name the
stage where the brand drops out; that is the headline finding.

### 18.3 Who gets recommended instead

From section 4 of `visibility.md`: the brands and domains the engines named for the
unbranded prompts. These are the real competitors in AI answers, and they may differ from
the competitors in Section 3.

### 18.4 Sources the engines trust

The top cited domains from `visibility.md` section 5, grouped as own / platform /
competitor / third-party, with any dead links called out. Third-party domains cited often
are the outreach list.

### 18.5 What this does not tell you

- Every prompt ran once. AI answers change between runs, so one miss is not a pattern.
- Accuracy is for the client to judge. This report shows what the engines said; it does
  not score whether each statement is true.
- The app surface reflects a logged-out user in one location. Signed-in users with
  history may see different answers.
- Name any surface a fallback provider served (the `Via` column), since a fallback answer
  can differ from the primary's.
