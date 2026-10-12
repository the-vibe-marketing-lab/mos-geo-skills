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

Star-only reviews (no text) count toward ratings and reply rates, not toward aspects or clouds.

## Numbers (all from `aggregate`, never from a model)

- **Average star rating**: mean of `rating` over platforms with `stars: true` in
  `config/platforms.json`. Reddit and Facebook never count.
- **Net sentiment**: per review, the mean of its aspect polarities; positive if above 0, negative
  if below. Net = (positive - negative) / reviews that name at least one aspect. Range -1 to +1.
- **Reply rate**: replied / reviews on platforms where owners can reply (`replies: true`).
  Reported overall and for 1 to 2 star reviews. **Median reply time** in days, where both dates exist.
- **Aspect volumes**: mentions, positive (polarity >= +1), negative (<= -1), neutral, share of
  reviews with text.
- **Fix priority** for each aspect with at least one negative mention:
  `volume share × average severity × recency weight × visibility weight × (1 + share unreplied)`.
  Volume share = negative mentions / reviews with text. Severity weights, the recency window and
  weight, and visibility weights are in `config/scoring.json`. Visibility weight is above 1.0 only
  for platforms with a sourced line in `_shared/geo-evidence.md` section 11.
- **Trend** per issue: negative mentions in the last 3 months against the 3 before;
  rising / falling / flat with a 20% band.
- **Quotes** per issue: up to 3, strongest feeling about that aspect first, then the reviews with
  the fewest other complaints, then the newest.

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

Write it for the top 5 issues at least. Rules: every claim comes from the quotes or the numbers;
root causes are labelled guesses; Australian spelling; no em dashes; no hype words ("game-changer",
"unlock", "skyrocket"); never promise AI citations. Missing notes fall back to neutral defaults and
`report` lists which issues still need them.

## `review-sentiment-report.md`

Frontmatter, then: headline (rating, net sentiment, replies, biggest complaint, most praised, the
unreplied count), rating spread, trend by month with a sparkline, the platform table (analysed
against the profile total), top 5 praised aspects with a clean example, top 5 complaints, the word
clouds, "Why this matters for AI answers" (fixed wording, sourced to `geo-evidence.md` section 11),
and a methods note: sample, date range, cap, exclusions, labelling source, spot-check result, the
priority formula with its weights, and the Apify and labelling cost from the run records.

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

`wordcloud-positive.png`, `wordcloud-negative.png` and `wordcloud.html`. Praise = 4 to 5 stars (or
positive labels where there are no stars); complaints = 1 to 2 stars (or negative labels). Phrases
are bigrams and trigrams scored with log-odds and a pooled Dirichlet prior, so a phrase used equally
by happy and unhappy customers scores near zero. Size = distinctiveness; the HTML shows the count,
the share of that side and three quotes on hover or keyboard focus, plus a table view. Colours are
the dataviz reference diverging pair (blue praise, red complaints), validated on light and dark
surfaces; the HTML follows the system colour scheme.

## Workbook

`brand-audit-master.xlsx` at the month root. **Review Fixes** tab: rank, aspect, problem, negative
reviews, share, trend, priority, owner, fix, GEO action, metric, an example quote and link, then
Client verdict (Agree / Partly agree / Disagree / Already fixed) and Client notes, which survive a
re-run. **Initiatives**: the top issues (config `initiatives.top_issues`, at least
`min_negative_mentions` each) plus "Reply to N unreplied 1 to 2 star reviews", ICE-scored, with no
duplicates on re-run. **Checklist**: the `mos-geo-review-sentiment` row ticked.
