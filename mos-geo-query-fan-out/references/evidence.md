# Evidence: query fan-out and citation coverage

Last verified live: 2026-09-25. This file is the honesty backstop for the whole skill -
every claim the pipeline or the report makes traces back to something on this page.

## What was verified live

- **DataForSEO LLM Responses** `POST /v3/ai_optimization/chat_gpt/llm_responses/live` with
  `[{user_prompt, model_name, web_search:true}]` returns `tasks[0].result[0].fan_out_queries`
  (an array of strings) plus citations in `items[].annotations[]` (see `scripts/fanout.py`'s
  `dfs_fanout_call`, and `mos-geo-brand-360/scripts/brand360.py`'s `citation_list`, which this
  skill reuses the shape of).
- **DataForSEO LLM Scraper** (the ChatGPT app endpoint) returned `fan_out_queries: null` on
  4/4 runs for the same prompt. **Do not use the scraper for fan-out** - only LLM Responses
  (the model API) returns it.
- **DataForSEO LLM Mentions** `POST /v3/ai_optimization/llm_mentions/search/live` with
  `[{target:[{keyword, search_scope:["fan_out_queries"]}], platform:"chat_gpt", location_code,
  language_code, limit}]` returns real user questions (`items[].question`) whose fan-outs
  contain the keyword, with their `fan_out_queries`. $0.105/call; `total_count` 76 for
  "share buttons" on the run that verified this. Used by `prompts --discover` for prompt
  discovery, not for the fan-out measurement itself.
- **Standard (queue) mode** can take up to 72h and still bills the LLM cost. This pack only
  uses Live, with a thread pool.
- **Fan-out varies run to run.** One run is a snapshot; stability across `--runs` (default 3)
  repeats is an estimate, not a guaranteed rate.
- **Observed pattern (Aug 2026+):** most ChatGPT fan-outs are `site:` queries or quoted exact
  strings. A `site:<vendor-domain>` fan-out cannot be won by a third-party page - that's why
  `analyse` classifies and excludes it (`site_vendor`) rather than scoring it as a gap.
- **Real example**, page `https://thevibemarketinglab.com/guides/geo/llm-share-buttons/`:
  3 prompts, 15 fan-outs, 11 were `site:` vendor-doc queries, page cited 0/3. The page
  contained `chatgpt.com/?q=` but not `claude.ai/new?q=` or `perplexity.ai/search/new?q=`,
  which were exact-string fan-outs. That gap is exactly what `analyse`'s `exact_string` /
  `missing` classification is built to catch.

## Model comparison for the fan-out call (verified live 2026-09-25, one prompt)

The fan-out call (`run`, engine `chat_gpt`) is the one that costs real money per (prompt x
run). This pack tested four DataForSEO LLM Responses models on the same prompt, web search
on, to pick a default:

| Model | Cost/call | Fan-outs returned | Notes |
|---|---|---|---|
| `gpt-5.6-luna` (**default**) | $0.024 | 6 | Matched terra's exact-string and `site:` queries at roughly a third of the cost. |
| `gpt-5.6-terra` | $0.044-0.062 | 3-8 | The richest fan-out set observed; selectable with `run --model gpt-5.6-terra` when the extra cost is worth it (e.g. a final report for a client). |
| `gpt-5.4-mini` | $0.032 | - | Missed the exact-string fan-outs terra and luna both caught. Costs more than luna for a worse result on this test - not recommended for fan-out. |
| `gpt-5.4-nano` | $0.014 | 4 | Vaguer fan-outs, also missed exact strings. Fine as the **prompt-generation** model (`generator_model` in `config/engines.json`, closed-book, no fan-out needed) - not for the fan-out call itself. |

`gpt-5.6-luna` is the default in `config/engines.json` (`cost_estimate.engine_call: 0.03`
covers it with headroom). Pass `run --model gpt-5.6-terra` (or any other live model name) to
override per run without editing the config - useful for a side-by-side comparison on a page
that matters. This is one prompt on one day: re-check with `preflight` before trusting a
model name months from now, and re-run the comparison if a report depends on picking the
cheapest model that still catches exact strings.

## What this pack does not claim

- **Fan-out coverage is a hypothesis for citation lift, not a proven cause.** No controlled
  test in this pack (or cited by it) has measured whether adding a fan-out query's exact
  string, or a matching H2, actually raises citation rate. `report` says this explicitly, and
  `retest` exists to let a real client measure it themselves, before/after a fix ships.
  Treat every "fix" in the report as a bet, not a guarantee - see `_shared/geo-evidence.md`
  for how thin the evidence is for adjacent GEO tactics (llms.txt moved nothing measurable
  across ~300,000 domains; LLM share buttons alone cost Leite's Culinaria 17% of clicks in
  the one controlled test that exists).
- **One run is a snapshot.** `--runs` (default 3) gives a stability estimate, not certainty.
  Fan-out queries change run to run even for the identical prompt.
- **Coverage is a heuristic token match**, not a citation guarantee. A page can cover a
  fan-out's tokens and still not be cited (retrieval, domain authority and dozens of other
  signals also matter) - that's why `analyse --serp` and the `EARN_RETRIEVAL` fix exist: a
  page that isn't in the top 20 organic results for an open fan-out won't get fixed by
  content alone.
- **`site:` fan-outs aimed at another domain are unwinnable by design.** They are excluded
  from the winnable list, not scored as a missed opportunity.

## Sources

- DataForSEO API docs and live responses, verified 2026-09-25 (this pack's own calls -
  see `scripts/fixtures/*.json` for the exact shapes tests are built against).
- `mos-geo-brand-360/references/providers.md` - the sibling skill's provider notes; this pack
  follows the same DataForSEO conventions (Basic auth, retry codes, location resolution).
- `_shared/geo-evidence.md` - the pack-wide evidence base for adjacent GEO tactics.
