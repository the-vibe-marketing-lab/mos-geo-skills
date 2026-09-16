# Providers: keys, setup and cost

Two accounts power the engine run. Both are pay-as-you-go, and neither needs a contract.

| Provider | What it covers | Key |
|---|---|---|
| **OpenRouter** | Closed-book pass (ChatGPT, Gemini, Claude, Grok) and API answers with each provider's own web search (plus Perplexity Sonar) | `OPENROUTER_API_KEY` |
| **Bright Data** | What users see in the consumer apps: ChatGPT, Perplexity, Gemini, Google AI Mode, Copilot. Plus Google AI Overviews via the SERP API. | `BRIGHTDATA_API_KEY`, `BRIGHTDATA_SERP_ZONE` |

Keys are read from environment variables, or from a `.env` file passed with `--env-file`.
Copy `.env.example` somewhere outside this repo. Never commit a key.

## OpenRouter setup

1. Create an account at openrouter.ai and add credit.
2. Create a key at openrouter.ai/keys.
3. Run `preflight`. It confirms the key and that every model in `config/engines.json` exists.

Web search uses `"engine": "native"`, so each model searches with its own provider's search,
the closest API equivalent to the consumer product. Never switch it to Exa: that is a
different index and skews the "can it find the brand" result. Perplexity Sonar always
searches, so it gets no plugin and sits out the closed-book pass.

## Bright Data setup

1. Create an account at brightdata.com. New accounts get 5,000 free credits a month, shared
   across the scraper and SERP APIs.
2. Copy the API key from Account settings.
3. **For AI Overviews only:** add a SERP API zone in the dashboard and put its name in
   `BRIGHTDATA_SERP_ZONE`. Without it the script skips the AI Overview phase and says so.

The app scrapers are triggered as one batch per engine, then polled until the snapshot is
ready. Dataset IDs live in `config/engines.json`, verified on 2026-09-16 against Bright
Data's docs and its own GitHub repos. The Grok scraper is listed as unavailable and ships
disabled.

## Cost of one run (estimate, not measured)

Default prompt set: 3 closed-book, 10 search prompts.

| Phase | Calls | Rough cost |
|---|---|---|
| Closed-book | 4 engines x 3 | a few cents in tokens |
| API search | 5 engines x 10 | tokens plus about $0.005 to $0.014 per search call (OpenRouter's listed search prices on 2026-09-16) |
| App | 5 scrapers x 10 = 50 records | about $0.08 at $1.50 per 1,000, or free inside the monthly credits |
| AI Overviews | 10 searches | about $0.01, or free inside the monthly credits |

Expect well under $2 per brand. Check `preflight` output and the OpenRouter dashboard after
the first real run, then replace this estimate with the measured figure.

## When a phase fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `GONE` in preflight | OpenRouter retired a slug | Pick the current model from the loaded list and edit the config |
| `HTTP 401` / `403` | Wrong or unfunded key | Re-copy the key; add credit |
| `HTTP 429` | Rate limit | Re-run just that phase with `--workers 2` |
| App phase: `trigger failed` | Wrong dataset ID or no credits | Check the ID in the Bright Data scraper library |
| App answers empty, no error | Undocumented output field | Open one record in `raw/app/<id>.json` and add the field name to `answer_fields` |
| Snapshot ended as `failed` | Bright Data could not reach the app | Re-run `--phases app` later |
