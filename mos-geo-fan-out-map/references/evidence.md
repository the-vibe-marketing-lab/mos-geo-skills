# Evidence: predicted, inventory-wide fan-out

Last verified live: 2026-09-28. This file is the honesty backstop for the whole skill.

## What was verified live

- **Gemini API** `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  with header `x-goog-api-key`, `generationConfig: {temperature: 0.3, responseMimeType:
  "application/json"}` returns a JSON object matching the prompt's requested shape in
  `candidates[0].content.parts[0].text`. Verified live against
  `https://thevibemarketinglab.com/guides/geo/llm-share-buttons/` on `gemini-flash-latest`:
  ~2.5k total tokens, ~4s wall time, a clean JSON payload with a plausible primary entity,
  3 buyer prompts and 10 fan-outs, correctly split between covered (heading-matched) and
  uncovered topics.
- `gemini-flash-lite-latest` is a faster/cheaper fallback on the same endpoint - pass
  `--model gemini-flash-lite-latest` to `predict` to use it; not benchmarked head-to-head
  against `gemini-flash-latest` in this pack yet.
- The Gemini Flash free tier covers this skill's usage pattern (one call per page, no
  search grounding) - see Google's current published rate limits before a very large
  inventory run and pass `--rpm` to stay under them.

## Method credit

The core method - ask a model to predict a page's query fan-out and score its own
coverage, from the page's own content, no live search - is adapted from Metehan
Yesilyurt's Screaming Frog custom JS script:
https://github.com/metehan777/screaming-frog-query-fan-out

This pack's version differs in three ways: it runs standalone (no Screaming Frog license
required), it extends the prompt to also ask for typed fan-outs (`related` / `implicit` /
`comparative` / `procedural` / `refinement`) and per-fan-out evidence, and it adds a
site-wide clustering pass across every page's predictions to surface inventory-level
content gaps and overlap - Metehan's original script is per-page only.

## What this pack does not claim

- **Predicted fan-out is a hypothesis, not an observed search.** No search engine or AI
  assistant was actually queried. The model is pattern-matching "what would someone search
  for, given this page" from its training data - it has not run a real search and has not
  seen what ChatGPT, Google AI Mode or any other engine actually retrieves for this page
  today. Nothing in this pack observes that yet - see "What this skill is for" below.
- **Predicted fan-out is biased toward what the page already says.** A model reading a
  page's headings and body text tends to imagine searches that page would answer well -
  that is the single biggest known failure mode of this method. It means this skill
  systematically UNDER-reports real content gaps (a page can look like it "covers"
  everything relevant, when in fact AI engines are fanning out to entirely different
  topics the page's own text never gave the model a reason to imagine). Site-wide gap
  clustering helps partially - a gap only a couple of pages predict at all, and none
  cover, is still worth writing - but it cannot see topics no page's content ever hinted at.
- **Coverage is the model's own judgement of its own predictions.** `yes` / `partial` /
  `no` is Gemini scoring itself against the page text it was given in the same call, not a
  separate, verified check, and not deterministic or reproducible run to run. Treat a
  `yes` as "the model thinks so", not fact.
- **One call per page, no repeats.** This skill does not currently re-call the model to
  check how stable a prediction is run to run (a repeated-run stability estimate - ask N
  times, see how often the same fan-out shows up - is a possible future improvement). A
  single call is a snapshot of one model's one guess.
- **Site-wide clustering is a token-Jaccard heuristic** (>= 0.6 overlap): near-duplicate
  wording merges; a genuinely-related topic worded very differently across pages will not.

## What this skill is for

Triage, not truth. It is cheap and fast enough to run across an entire inventory (hundreds
of pages) to rank which pages are worth spending real verification time on, and to surface
candidate content gaps worth a human look. It is never the final word on what an AI engine
actually searches for or cites - confirm any priority page by hand: run its buyer prompts
through a real ChatGPT or Google AI Mode session and see what it actually searches for and
cites. A paid, DataForSEO-backed observed-fan-out skill (`mos-geo-query-fan-out`) is
planned for this pack to automate that confirmation step - it has not shipped yet, so treat
every prediction here as a lead, not a verified fact.

## Sources

- Gemini API docs and this pack's own live call, verified 2026-09-28 (see
  `scripts/fixtures/sample-page.html` for the fixture the offline tests are built against;
  no live response fixture is checked in, since nothing in `data/raw/` is ever committed).
- Metehan Yesilyurt, Screaming Frog query fan-out script (method credit above).
