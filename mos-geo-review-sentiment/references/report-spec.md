# Report spec

What each output contains, where every number comes from, and the one file Claude writes by hand.

## The common review schema (`data/reviews.jsonl`)

| Field | Notes |
|---|---|
| `id` | Stable: the platform's own review id when the actor gives one, else author hash + date + text |
| `platform` | Registry id (`trustpilot`, `productreview`, `google_maps`, `g2`, `capterra`, `reddit` ...) |
| `profile_url` | The picked profile |
| `review_url` | The public review where the platform has one; else the profile (ProductReview, Capterra) |
| `rating` | 1 to 5, or null (Reddit, Facebook recommendations) |
| `date` | `YYYY-MM-DD` the review was published |
| `title`, `text` | As written; whitespace collapsed. G2 text is "Likes: ... Dislikes: ..."; Capterra adds Pros and Cons |
| `owner_reply`, `reply_date` | The brand's public reply, if any |
| `lang` | When the platform gives it |
| `author_hash` | Salted SHA-256 (16 hex). Never the name |
| `place_name`, `place_id`, `place_address`, `place_country` | Optional, Google Maps only: which place the review is on. Used to keep only the brand's own place |
| `product` | Optional, `brand_site` only: the product handle the review sits on (`site` for store reviews) |

Star-only reviews (no text) count toward ratings and reply rates, not toward aspects or clouds.
Strings like "None" or "null" in actor output are treated as empty, never stored as text.

`brand_site` (label "Brand site (product pages)") holds the brand's own product-page reviews. It
gets its own platform row, and Methods says they are collected and moderated by the brand
(selection bias), with the widget's own total, organic count and star split when known.

## Numbers (all from `aggregate`, never from a model)

- **Average star rating**: mean of `rating` over platforms with `stars: true` in
  `config/platforms.json`. Reddit and Facebook never count.
- **Net sentiment**: per review, the mean of its aspect polarities; positive if above 0, negative
  if below. Net = (positive - negative) / reviews that name at least one aspect. Range -1 to +1.
- **Reply rate**: replied / reviews on platforms where owners can reply (`replies: true`), shown
  per platform first. The overall figure leaves out the brand's own site when nobody replies there
  (thousands of unreplied product-page reviews would bury the real rate), and says so.
  Reported overall and for 1 to 2 star reviews. **Median reply time** in days, where both dates exist.
- **Aspect volumes**: mentions, positive (polarity >= +1), negative (<= -1), neutral, share of
  reviews with text.
- **Fix priority** for each aspect with at least one negative mention:
  `volume share × average severity × recency weight × visibility weight × (1 + share unreplied)`.
  Volume share = negative mentions / reviews with text. Severity weights, the recency window and
  weight, and visibility weights are in `config/scoring.json`. Visibility weight is above 1.0 only
  for platforms with a sourced line in `_shared/geo-evidence.md` section 12.
- **Trend** per issue: negative mentions in the last 3 months against the 3 before;
  rising / falling / flat with a 20% band, but only when both windows have at least 10 mentions
  (`trend.min_mentions`). Below that the report says "too few to call".
- **Monthly table**: months with fewer than 5 reviews (`monthly_min_reviews`) are left out, and a
  line above the table says the sample is the newest N per platform, so month-to-month movement is
  not a trend.
- **Praise**: only aspects with more positive than negative mentions, ranked by net share
  ((positive - negative) / mentions). The headline and the table show positive and negative counts
  side by side ("7 positive / 3 negative"), so a top complaint can never read as a strength.
- **Quotes** per issue: up to 3. A review qualifies only if it is labelled negative for the aspect
  AND one of its sentences matches this aspect's words (label, description, optional `keywords`)
  better than any other aspect the review is labelled with, with a negative word in it. The
  excerpt starts at that sentence and runs on while it fits, stopping before a sentence about a
  different issue; cuts are marked "…". Order: strongest feeling, fewest other complaints, newest.
  In priority order, a review already quoted under another issue is used again only when there is
  no other candidate. An issue with no qualifying sentence shows no quote rather than a wrong one.
- **Safety and legal (Read first)**: the fix list is ranked by priority score only. Any review whose
  own text names a food-safety problem (missing use-by date, undercooked or raw meat, food
  poisoning, mould, contamination), an injury (cut my hand, hurt his back, burn, rash), a hazard (unsafe,
  sharp edges, exposed wires) or a legal or regulator step (Fair Trading, ACCC, ombudsman, lawyer,
  tribunal, recall) is listed individually in a "Read first: safety and legal reports" box at the top
  of `fix-report.md`, with its quote, link, date and the aspect its sentence matches; the report
  headline summarises them. Figurative discomfort ("ruined my back", "pain in the neck", "killing
  me") does not count, nor does a negated mention ("never had an issue with contamination"). Injury
  and hazard words only count in a complaint (3 stars or fewer, a negative aspect, or a complaint
  word in the sentence): "great help straight out of hospital" is recovery, not harm. Reviews the model labelled `safety_legal` whose text names none of these are
  listed underneath as likely over-labels to check.
- **Sample caption**: per platform when they differ: "the newest N reviews per platform for
  Google Maps, Reddit; all 1,851 Brand site (product pages) reviews, imported uncapped"; "a user-supplied sample
  of N reviews; selection method unknown" for `import` runs.
- **Denominators**: always both, "60 labelled reviews (55 name an aspect)".
- **Small counts**: under 3 reviews is an individual report, never a pattern. The template writes
  "one negative review" / "two negative reviews", titles default to "<aspect>: single mentions",
  and `report` warns when a fix note uses pattern words ("cluster", "many", "reviewers are",
  "recurring", "several", "common") for an issue with fewer than 3 reviews.

## `data/fix-notes.json` (Claude writes this, stage 7)

```json
{
  "summary": "Two or three plain sentences for the top of the report: what the data shows. Optional.",
  "issues": {
    "<aspect id>": {
      "problem": "One line, in the customer's terms: 'Delivery days move after customers take a day off work'",
      "root_cause": "A hypothesis from the reviews, worded as one: 'Reviews mention lost boxes and day-before changes, which suggests the courier hand-off. Check by carrier and region.'",
      "fix": "What the owner would do, specific enough to schedule.",
      "geo_action": "Reply publicly / put an answer on-site / FAQ: what goes where, so engines have the brand's own account.",
      "metric": "What to count on the next run to know it worked.",
      "owner": "ops | product | support | marketing (optional; overrides the taxonomy)"
    }
  }
}
```

Write it for **every** issue in `aggregate.json` `fixes`, with all five fields. `report` exits
non-zero while any issue is on a placeholder (`--allow-placeholders` for drafts only). Rules: every claim comes from the quotes or the numbers;
root causes are labelled guesses; fewer than 3 reviews is "one reviewer" or "single mentions",
never "reviewers are" or "a cluster"; Australian spelling; no em dashes; no hype words ("game-changer",
"unlock", "skyrocket"); never promise AI citations.

## `review-sentiment-report.md`

Frontmatter, then: headline (rating, net sentiment, replies, biggest complaint, most praised, the
unreplied count), rating spread, trend by month with a sparkline, the platform table (analysed
against the profile total), top 5 praised aspects with a clean example, top 5 complaints, the word
clouds, "Why this matters for AI answers" (fixed wording, sourced to `geo-evidence.md` section 12),
and a methods note: sample, date range, cap, exclusions, labelling source, spot-check result, which
platforms' quotes link to the listing page rather than the individual review (ProductReview and
Capterra, whose scrapers return no per-review link), the priority formula with its weights, and the
Apify and labelling cost from the run records.

## `fix-report.md`

One section per issue in priority order: the problem, aspect and owner, how many and what share,
how many say they are leaving, the trend, the priority score broken into its five factors, 2 to 3
verbatim quotes with links, the root cause (marked as a hypothesis), the fix, the GEO action and
the metric to watch.

## `unreplied-negatives.csv`

Every 1 to 2 star review with no owner reply on a platform that allows replies, newest first:
date, platform, rating, title, text, link, the aspects it was labelled with, severity, and whether
the reviewer says they are leaving.

## Word clouds

`wordcloud-positive.png`, `wordcloud-negative.png` and `wordcloud.html`. Built from SENTENCES, not
whole reviews: a sentence takes the side of the labelled aspect it matches best (negative aspect =
complaint, positive = praise); a sentence about no aspect follows the stars (1 to 2 complaint, 4 to
5 praise when the review has no complaint). A review with no negative aspect and 3+ stars or no
stars (most Reddit chat) never feeds the complaint side. Counts are distinct review texts (the same
post under two ids counts once); a phrase needs at least 2 distinct reviews and at least one
star-rated one. Competitor names are dropped (capitalised names in Reddit thread titles, plus
`--block` or `block_words` in run-meta), as are phrases ending in a qualifier ("a little") and
fragments a longer phrase from the same reviews already covers ("fed eye" in "grass fed eye fillet"). Phrases
are bigrams and trigrams scored with log-odds and a pooled Dirichlet prior, so a phrase used equally
by happy and unhappy customers scores near zero. Overlapping fragments of one sentence ("take
another day", "day off work", "work to wait") collapse to the highest scoring one when they come
from mostly the same reviews. Size = distinctiveness; the HTML shows the count,
the share of that side and three quotes on hover or keyboard focus, plus a table view. Colours are
the dataviz reference diverging pair (blue praise, red complaints), validated on light and dark
surfaces; the HTML follows the system colour scheme.

## Workbook

`brand-audit-master.xlsx` at the month root. **Review Fixes** tab: rank, aspect, problem, negative
reviews, share, trend, priority, owner, fix, GEO action, metric, an example quote and link, then
Client verdict (Agree / Partly agree / Disagree / Already fixed), Client notes, and a Row key
(skill:brand:month:aspect id) that keeps verdicts attached when wording changes. **Initiatives**: the top issues (config `initiatives.top_issues`, at least
`min_negative_mentions` each) plus "Reply to N unreplied 1 to 2 star reviews", ICE-scored. Each Initiative carries the same row key in its Deliverable cell, so a re-run updates the
task and instructions in place (status, owner and ICE scores edited in the sheet are kept) instead
of adding a second row, even when a fix note's problem line was reworded. **Checklist**: the `mos-geo-review-sentiment` row ticked.
