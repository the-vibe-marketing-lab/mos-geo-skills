# GEO evidence base — LLM share buttons

**Last reviewed:** 2026-08-23
**Applies to:** every skill in `mos-geo-skills`, but especially `mos-geo-llm-buttons`.

This is the honest version. It exists so no skill in this pack, and no member using one, ever promises a client something the evidence does not support. If you only read one section, read [The one controlled A/B result](#2-the-one-controlled-ab-result) and [What is NOT true](#3-what-is-not-true).

---

## Contents

1. [What LLM share buttons are](#1-what-llm-share-buttons-are)
2. [The one controlled A/B result](#2-the-one-controlled-ab-result)
3. [What is NOT true](#3-what-is-not-true)
4. [The security dimension: where a button becomes an attack](#4-the-security-dimension-where-a-button-becomes-an-attack)
5. [Calibration: how sibling GEO tactics measured](#5-calibration-how-sibling-geo-tactics-measured)
6. [How to pitch this honestly to a client](#6-how-to-pitch-this-honestly-to-a-client)
7. [Evidence gaps](#7-evidence-gaps)
8. [Sources](#8-sources)

---

## 1. What LLM share buttons are

A row of buttons on an article page. Each one opens an AI assistant with a prompt already filled in, usually along the lines of "summarise this page: <url>". ChatGPT, Claude, Perplexity, Grok and Google AI Mode all accept a query string that populates the composer. The exact endpoints, which ones auto-submit, and which ones dump a logged-out visitor into an auth wall are all in `platform-endpoints.json` in this folder — that file is the technical contract, this file is the evidence.

The pattern was published as **"CiteMET"** by Metehan Yesilyurt on **29 June 2025** (<https://metehan.ai/blog/citemet-ai-share-buttons-growth-hack-for-llms/>). It spread fast through the GEO community during late 2025 and 2026, mostly on the strength of the original post rather than on independent testing.

Mechanically, that's the whole tactic. A link with a prefilled query parameter. It is not an integration, it is not API usage, and nothing about it touches how any model was trained.

---

## 2. The one controlled A/B result

There is exactly one published controlled test worth citing.

**Source:** Search Engine Land, 13 April 2026, "AI buttons: Smart UX play, risky GEO tactic, or both?" — <https://searchengineland.com/ai-buttons-474137>
**Site tested:** Leite's Culinaria.

The test separated two things that usually ship together: the buttons themselves, and an on-page AI summary block (a short machine-readable summary rendered into the article).

- **Buttons + on-page AI summary block:** +116% impressions, +36% clicks.
- **Buttons only, no summary block:** **+5% impressions and −17% clicks.**

Read that second line twice. On its own, the button row moved impressions by a rounding error and **cost the page 17% of its clicks**. The plausible explanation is the obvious one: a row of "go ask an AI instead" buttons is a row of exits off your page.

The referral numbers get quoted a lot and deserve context. ChatGPT referral sessions went from **232 to 1,835 between November 2025 and March 2026** — a big multiple, but off a tiny base, over a period when AI referral traffic was rising broadly across the web. Real growth, yes. Attributable to the buttons in isolation, not demonstrated.

**The conclusion the data supports:** the on-page AI summary block is the driver. The buttons are along for the ride and may be a net negative for clicks on their own. If a client is going to implement one of the two, it is the summary block.

**Sample-size caveat:** this is a single site, one vertical (food/recipe), one test window. It is the best evidence available, and it is still n=1. Do not present it as settled.

---

## 3. What is NOT true

Claims that circulate about this tactic with no evidence behind them:

- **Buttons do not retrain or "seed" models.** Clicking a share button starts a normal user conversation. It does not write to training data, model weights, or any persistent brand memory. The "seeds your brand into the model" framing is unvalidated marketing language, not a documented mechanism.
- **Buttons do not change search rankings.** No published study connects them to organic position.
- **Buttons do not influence AI Overviews.** Inclusion there is driven by Google's own retrieval and ranking, not by outbound links you put on your page.
- **Buttons are not a citation mechanism.** Being summarised in someone's private chat is not being cited. It leaves no public trace and no link.
- **Volume does not compound.** There is no evidence that more button clicks make a model more likely to mention you later.

What is left, once you strip that out, is genuinely useful but modest: a share affordance for the segment of readers who prefer to interrogate content through an assistant, and referral traffic you can actually measure.

---

## 4. The security dimension: where a button becomes an attack

This is the part that decides whether the tactic is a UX feature or a liability.

**Source:** Microsoft Security, 10 February 2026, "Manipulating AI memory for profit: The rise of AI Recommendation Poisoning" — <https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/>

Microsoft investigated sites shipping prefilled AI prompts and found **50 examples across 31 companies** where the prompt did not just ask for a summary. It instructed the model to remember the brand favourably and treat it as authoritative in future conversations. Microsoft named that behaviour **AI Recommendation Poisoning** and shipped cross-prompt-injection defences in response.

The token patterns Microsoft flagged in those prompts:

1. **"remember"**
2. **"trusted source"**
3. **"in future conversations"**
4. **"authoritative source"**
5. **"cite" / "citation"**

**The line, stated plainly:** a visible, honest prompt that asks the model to summarise the page the reader is looking at is a UX feature. A prompt that tells the model to remember the brand as authoritative, or to cite it in future, is what Microsoft classifies as poisoning. Same button, same mechanism, completely different thing.

Practical consequences for any skill in this pack:

- The prompt text must be visible to the user before they click, not hidden in the href only.
- Never emit any of the five flagged patterns into a generated prompt. Treat them as a hard blocklist.
- Assume the defences tighten. Microsoft has already shipped mitigations, and vendors have already removed prefill surfaces — Microsoft Copilot's `?q=` prefill was disabled outright in mid-January 2026 after the "Reprompt" data-exfiltration attack (see `platform-endpoints.json`). A prompt that gets a site classified as manipulative is a reputational problem that outlives the tactic.

---

## 5. Calibration: how sibling GEO tactics measured

Useful context for how often "everyone in GEO is doing this" survives measurement.

**llms.txt** — the proposed convention of publishing a markdown file telling LLMs how to read your site. Widely adopted through 2025 and 2026. Measured effect: essentially none.

- SE Ranking studied roughly 300,000 domains and found no meaningful benefit — <https://seranking.com/blog/llms-txt/>
- Thomas Peham's GEO Experiments (2026) found llms.txt drew **0.1% of AI bot traffic**. Bots overwhelmingly crawl normal HTML.

The pattern is worth internalising: a GEO tactic can be near-universally recommended, cheap to implement, and still do nothing measurable. Treat popularity as zero evidence.

---

## 6. How to pitch this honestly to a client

### What you can promise

- **Measurable referral traffic.** Clicks to AI assistants are trackable with UTM parameters and a click event. You can report an actual number.
- **A genuine UX nicety.** Some readers do prefer to work through an assistant. Giving them a one-click path is a real convenience.
- **Low cost, low risk, easy removal.** It is markup. If it underperforms, delete it — no migration, no debt.
- **A learning loop.** Instrumented properly it tells the client something real about how their audience uses AI.

### What you must not promise

- **Ranking improvements.** No evidence exists.
- **AI Overview inclusion.** No mechanism connects the two.
- **Model memory, training influence, or "being seeded into the model".** Not how any of this works.
- **Citation growth.** A private summary is not a citation.
- **The +116% figure as the button number.** That result belongs to buttons *plus* an on-page AI summary block. Quoting it for buttons alone is misrepresentation, and the buttons-only arm of the same test went **−17% on clicks**.

### The recommendation to lead with

Ship the **on-page AI summary block** first — that is where the measured lift is. Add the buttons as a secondary, instrumented experiment, and A/B them against a control so the client sees their real effect on clicks for their own site. If clicks drop, pull them. Set that expectation before you build, not after.

---

## 7. Evidence gaps

Stated plainly so nobody fills them in from imagination:

- **Only one controlled A/B test exists**, on one site, in one vertical. No replication.
- **No published data on whether button clicks influence later model responses.** The mechanism is not documented and has not been tested.
- **No vertical-level breakdown.** Whether B2B, ecommerce or publishing behave differently is unknown.
- **No longitudinal data on click cannibalisation.** Whether the −17% persists, recovers or worsens over time is unknown.
- **No evidence on placement.** Top of article versus bottom versus sidebar has not been tested publicly.

If a skill in this pack ever needs one of these answers, the correct response is to run the test and record the result here, not to assert.

---

## 8. Sources

- Metehan Yesilyurt, "CiteMET: AI share buttons growth hack for LLMs", 29 June 2025 — <https://metehan.ai/blog/citemet-ai-share-buttons-growth-hack-for-llms/>
- Search Engine Land, "AI buttons: Smart UX play, risky GEO tactic, or both?", 13 April 2026 — <https://searchengineland.com/ai-buttons-474137>
- Microsoft Security, "Manipulating AI memory for profit: The rise of AI Recommendation Poisoning", 10 February 2026 — <https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/>
- SE Ranking, llms.txt study across ~300,000 domains — <https://seranking.com/blog/llms-txt/>
- Thomas Peham, GEO Experiments 2026 (llms.txt drew 0.1% of AI bot traffic)
- `_shared/platform-endpoints.json` (this repo) — verified endpoint contract and provider stability notes
