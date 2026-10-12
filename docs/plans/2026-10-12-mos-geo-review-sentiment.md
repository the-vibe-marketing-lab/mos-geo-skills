# Plan: `mos-geo-review-sentiment`

Status: draft for Richard's sign-off. Nothing built yet.

## What it does

You give it a brand. It finds every third-party review profile the brand has and pulls the reviews through Apify. You get three deliverables:

1. **Sentiment report**: overall score, rating spread, which way it's trending, a breakdown by platform, and how often the brand replies.
2. **Word cloud**: the phrases customers actually use, coloured by sentiment, with praise and complaints shown on separate maps.
3. **Fix report**: the problems ranked by how much they hurt. Each one carries verbatim quotes with links, who owns the fix, and what to watch to know it worked.

It's the deep version of Brand 360's section 4 ("Brand Sentiment"). Brand 360 runs a few searches. This one reads every review.

## Why it belongs in the GEO pack

ChatGPT, Perplexity and AI Overviews pull from Trustpilot, G2, ProductReview and Reddit when they describe a brand, so a recurring complaint on those sites can end up in the AI's answer. The report should say this carefully. Add the sources to `_shared/geo-evidence.md` before the skill claims it. No source, no claim.

## Inputs

- `brand_name` (required)
- `domain` (required). Unlike Brand 360, this skill isn't testing whether the AI can find the brand. Here the domain stops us scraping a different company that shares the name.
- `country`: defaults to AU, which decides the platform list
- `industry`: optional, used to pick platforms (SaaS → G2 and Capterra, local business → Google Maps, ecommerce → Trustpilot and ProductReview)
- `--max-per-platform`: defaults to 500, newest first

## Pipeline

| # | Stage | Who does it | Gate before moving on |
|---|---|---|---|
| 0 | Preflight | script | `APIFY_TOKEN` resolves; pinned actor IDs in `config/actors.json` still exist |
| 1 | Discover profiles | script | Candidate profiles from (a) predictable URLs, e.g. `trustpilot.com/review/{domain}`, (b) the brand's own `sameAs` schema and footer links, (c) one Apify Google Search run for the rest. No DataForSEO |
| 2 | Profile stats | script | Each candidate page read once (free fetch, not a scrape) for rating, review count and latest review date from its own schema or markup |
| 3 | **User picks platforms** | **Richard** | Multi-select from a table: platform, reviews, avg rating, reviews in last 12 months, latest review, est. scrape cost, AI-citation note, ⚠ if name/domain only partly match. Picking a profile also confirms it is the brand's |
| 4 | Scrape | script | Only the picked profiles. `data/reviews.jsonl` in one common schema, deduped |
| 5 | Classify | Jev / Claude | Every review tagged with aspect, polarity and severity against a **locked** taxonomy |
| 6 | Aggregate | script | Every number is computed in code. The model never does maths |
| 7 | Render | script + Claude | Report, word clouds and fix list written |
| 8 | Workbook | script | "Review Fixes" tab added to `brand-audit-master.xlsx`, Initiatives rows added, Checklist row ticked |

### Stage 1: platform registry

`config/platforms.json`, one entry per platform: domain pattern, the `site:` query, which countries and industries it applies to, the Apify actor key, and whether it has star ratings.

Starting set:

- **Ratings**: Google Maps, Trustpilot, ProductReview.com.au, G2, Capterra, TrustRadius, Yelp, Facebook, App Store, Google Play, Amazon
- **Discussion, no stars**: Reddit. Analysed for sentiment but kept out of the average rating
- **Opt-in**: Glassdoor and Indeed. These are employer reviews, so they go in a separate section

Discovery needs no DataForSEO key: predictable URLs and the brand's own links first (free), then one Apify Google Search run for whatever is left (cents). Members need only an Apify token.

### Stage 4: Apify actor map

`config/actors.json` pins each actor ID, its input template, its price per 1,000 reviews, and the date it was last smoke-tested. Actors drift, so the preflight runs a 5-review smoke test on each one before the full run.

Before writing this file we need to pick the actual actors in the Apify Store. Check run counts, recent updates and price. Don't trust the actor names in this plan.

Common review schema: `platform, profile_url, review_url, rating, date, title, text, owner_reply, reply_date, lang, author_hash`. Author names are hashed. They're never needed for analysis, and keeping them is a privacy risk.

### Stage 5: classification (the core of the skill)

1. Claude reads a sample of about 150 reviews stratified by platform and rating, then proposes an aspect taxonomy of 8 to 15 aspects (e.g. delivery, refunds, support response time, product quality, price, onboarding).
2. **Richard approves the taxonomy**, then it's locked. This stops the categories drifting between batches.
3. Each review gets labelled with `aspects[]`, a polarity of −2 to +2 for each aspect, a severity (minor annoyance / cost them money / safety or legal), and whether the reviewer says they're leaving.
4. Jev handles the labelling, the same way internal-links and topic-clusters use it. Claude is the fallback. Labels go to `data/labels.jsonl`, so re-running the aggregate step costs nothing.
5. Spot check: 30 random labels are shown for a yes/no. Under 85% agreement, fix the taxonomy and relabel.

### Stage 6: scoring the fixes

Each negative aspect gets a priority score, and every input is computed in code:

`priority = volume share × average severity × recency weight (last 6 months counts 2×) × visibility weight (platforms AI engines cite count more) × (1 + share left unreplied)`

All the weights go in `config/scoring.json` so they're visible and easy to change, and the report states them.

### Stage 7: outputs

`campaigns/geo/YYYY-MM/review-sentiment/`:

- `review-sentiment-report.md`: headline score, rating spread, monthly trend line, platform table, reply rate and reply speed, top 5 praised aspects and top 5 complaints, a short methods note covering sample size, date range and what was excluded
- `wordcloud-positive.png`, `wordcloud-negative.png`, and `wordcloud.html` (interactive: hover a phrase to see its count and three quotes). It's built on **bigrams and trigrams scored against a background**, not single words. A single-word cloud just says "great" and "service". Load `dataviz` before building it
- `fix-report.md`: issues in priority order. Each has the problem in one line, how many reviews and what share, the trend, 2 to 3 verbatim quotes with links, the likely root cause (flagged as a guess), the owner (ops / product / support / marketing), the fix, the GEO action (reply publicly, put an answer on-site, FAQ), and the metric to watch
- `unreplied-negatives.csv`: every 1 to 2 star review with no owner reply, newest first. This is the quickest win in the whole report
- `data/`: raw JSONL, labels, taxonomy, run record with cost

## Folder layout

```
mos-geo-review-sentiment/
  SKILL.md
  config/  platforms.json  actors.json  scoring.json
  references/  report-spec.md  taxonomy-guide.md  privacy.md
  scripts/  reviews.py  (subcommands: path, preflight, discover, estimate, scrape, aggregate, wordcloud, report, workbook)
            test_reviews.py
```

One script with subcommands, matching `brand360.py`. Register the skill in `_shared/brand-audit/skills.json` and rebuild the template.

## Build order and time

| Step | What | Estimate |
|---|---|---|
| 1 | Pick and smoke-test Apify actors for the 6 core platforms (Google Maps, Trustpilot, ProductReview, G2, Capterra, Reddit) | 2 hrs |
| 2 | `platforms.json` + discover + profile stats + picker | 2 hrs |
| 3 | Scrape + normalise + dedupe + cost estimate | 3 hrs |
| 4 | Taxonomy + Jev labelling + spot check | 3 hrs |
| 5 | Aggregate + priority score + tests | 2 hrs |
| 6 | Word clouds + report templates | 3 hrs |
| 7 | Workbook tab + SKILL.md + README row | 1.5 hrs |
| 8 | End-to-end on one real brand, review it, fix issues | 2 hrs |

About two days of executor time. Steps 1 and 2 can run in parallel. After step 8, a separate reviewer agent (not the builder) checks the fix report against the raw reviews.

## Out of scope for v1

- Competitor benchmark (same pipeline run on 2 to 3 competitors, then a side-by-side). Strong v2, roughly 4 hours on top
- Writing reply drafts for unreplied reviews
- Scheduled monthly re-runs and trend tracking across runs

## Risks

- **Wrong entity**: handled by the stage 3 picker (⚠ flags) and domain matching
- **Actor drift or breakage**: pinned IDs, smoke test in preflight, and one failed platform never stops the rest of the run
- **Cost blowout**: approve-before-spend estimate and a per-platform cap
- **Google Maps caps reviews per place**: the report states how many came back against the total shown on the profile
- **Privacy and terms**: hash authors. The client report quotes review text with a link to the public review and never publishes the raw dataset
- **Overclaiming the GEO link**: no claim goes into the report without a source in `geo-evidence.md`

## Decisions (2026-10-12, defaults taken when the build started)

1. Name: `mos-geo-review-sentiment`
2. Default cap 500 per platform, newest first; `--max-per-platform all` lifts it, the cost estimate still shows first
3. Competitor benchmark: v2

## Cost to run (Apify store prices pulled 2026-10-12, FREE tier, USD)

| Platform | Actor (pinned) | Per review |
|---|---|---|
| Google Maps | `compass/Google-Maps-Reviews-Scraper` | $0.0006 |
| Trustpilot | `memo23/trustpilot-scraper-ppe` | $0.00075 |
| ProductReview.com.au | `abotapi/product-reviews-australia-scraper` (55 users, flag as fragile) | $0.002 |
| G2 | `memo23/g2-scraper` | $0.00175 |
| Capterra | `azzouzana/capterra-reviews-scraper` | $0.001 |
| Reddit (posts + comments) | `harshmaur/reddit-scraper` | $0.002 |
| Facebook | `apify/facebook-reviews-scraper` | $0.0025 |
| Yelp | `web_wanderer/yelp-reviews-scraper` | $0.0003 |
| App Store | `thewolves/appstore-reviews-scraper` | $0.0001 |
| Discovery | `apify/google-search-scraper` | $0.0045 per results page |

Jev tagging: ~$0.042 per million input tokens, so about $0.05 for 3,000 reviews.

Typical runs at the 500 cap:
- Local business (Google Maps, Facebook, ProductReview, Reddit): ~$1.80
- Ecommerce (Trustpilot, ProductReview, Google Maps, Reddit, Facebook): ~$2.20
- SaaS (G2, Capterra, Trustpilot, Reddit): ~$2.80
- Worst case, 6 platforms all at 500: under $5. Apify's free plan includes $5 of credit a month.
