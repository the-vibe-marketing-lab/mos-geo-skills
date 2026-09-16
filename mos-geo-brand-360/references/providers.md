# Providers: keys, setup, fallback and cost

**DataForSEO is the primary provider** for every surface. OpenRouter and Bright Data are
fallbacks: the script tries providers in the order set in `config/engines.json`
(`provider_order`) and moves to the next one when a provider has no credentials or a call
fails. Each result records which provider served it (`Via` column in `visibility.md`).

| Surface | Primary (DataForSEO) | Fallback |
|---|---|---|
| ChatGPT (API) | LLM Responses `chat_gpt` | OpenRouter `openai/gpt-chat-latest` |
| Claude (API) | LLM Responses `claude` | OpenRouter `~anthropic/claude-sonnet-latest` |
| Gemini (API) | LLM Responses `gemini` | OpenRouter `~google/gemini-flash-latest` |
| Perplexity (Sonar API) | LLM Responses `perplexity` | OpenRouter `perplexity/sonar` |
| ChatGPT (app) | LLM Scraper `chat_gpt` | Bright Data ChatGPT scraper |
| Gemini (app) | LLM Scraper `gemini` | Bright Data Gemini scraper |
| Google AI Mode | SERP API `google/ai_mode` | Bright Data AI Mode scraper |
| Google AI Overviews | SERP API `google/organic` with `load_async_ai_overview` | Bright Data SERP API (needs a SERP zone) |
| Grok (API), Perplexity (app), Copilot (app) | not offered | Optional extras, off by default. Switch on in the config. |

Credentials are read from environment variables, or from a `.env` file passed with
`--env-file`. Copy `.env.example` somewhere outside this repo. Never commit a key.

## DataForSEO setup (primary)

1. Create an account at dataforseo.com and add funds.
2. Copy the API login and password from API Access in the dashboard. These are not your
   website login.
3. Run `preflight`. It checks every configured model against DataForSEO's free model lists
   and resolves `--country` to a location code.

Things verified live on 2026-09-16:

- LLM Responses returns `items[type=message].sections[].text`; citations are in
  `annotations[]`. Claude splits one answer into many small sections; the script joins
  them.
- Gemini cites `vertexaisearch.cloud.google.com` redirect links. The script follows one
  redirect to the real URL, and falls back to the citation title (Gemini sets it to the
  source domain).
- `fan_out_queries` (the searches the engine ran) comes back for the API models and the
  ChatGPT app. The summary lists them in section 6.
- `user_prompt` is capped at 500 characters. The script refuses longer prompts.
- Perplexity takes no `web_search` field; Sonar always searches.
- Google occasionally returns error 40101 (Internal SE Server Error). The script retries
  once; if it still fails, re-run just that surface with `--only google-aio --phases app`.

## OpenRouter setup (fallback for models)

Create a key at openrouter.ai/keys and add credit. Web search uses `"engine": "native"`,
so each model searches with its own provider's search. Never switch it to Exa: that is a
different index and skews the "can it find the brand" result.

## Bright Data setup (fallback for apps)

1. Create an account at brightdata.com (5,000 free credits a month).
2. Copy the API key from Account settings.
3. For the AI Overviews fallback only: add a SERP API zone and put its name in
   `BRIGHTDATA_SERP_ZONE`.

App scrapers are triggered as one batch per engine and polled until ready, which can take
several minutes. Dataset IDs live in `config/engines.json`. The Grok scraper is listed as
unavailable by Bright Data and is not configured.

## Cost of one run

Measured on 2026-09-16 with 1 closed-book + 2 search prompts across the 8 default
surfaces: **$0.38 on DataForSEO for 21 calls.** The model calls with web search cost the
most (about $0.02 to $0.04 each, mostly search tokens). App calls cost $0.004 each, and AI
Overviews $0.004 including the async overview fee.

Scaled to the default prompt set (3 closed-book, 10 search prompts): roughly **$1.50 to
$2.50 per brand**. That is an extrapolation from the small run; replace it with the
figure from `visibility.md` after the first full run.

## When a call fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `GONE` in preflight | The provider retired the model name | Pick a current name from the list preflight prints and edit the config |
| `HTTP 401` | Wrong credentials | DataForSEO uses the API login/password, not the dashboard login |
| `task 40200` / `40210` | DataForSEO balance too low | Add funds |
| `task 40101` | Google-side error | Already retried once; re-run with `--only <id>` |
| `HTTP 429` | Rate limit | Re-run the failed surface with `--only <id> --workers 2` |
| Bright Data `trigger failed` | Wrong dataset ID or no credits | Check the ID in Bright Data's scraper library |
| Bright Data answers empty, no error | Undocumented output field | Open one record in `raw/app/brightdata-<id>.json` and add the field name to `answer_fields` |
