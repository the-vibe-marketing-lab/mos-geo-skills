# Method: clustering, classification and coverage

How `scripts/fanout.py analyse` turns a pile of live fan-out queries into a per-page fix
list. Read this before trusting (or arguing with) a row in `fan-out-report.md`.

## 1. Clustering near-duplicate fan-outs

The same underlying search shows up worded slightly differently across runs ("best AI SEO
tools 2025" vs "best AI SEO tools 2026"). `cluster_queries` normalises each fan-out
(lowercase, strip 4-digit years, collapse whitespace), tokenises it, and greedily joins it to
the first existing cluster whose token set overlaps by Jaccard similarity >= 0.6, else starts
a new cluster. This is a heuristic, not a semantic clustering model: two fan-outs that mean
the same thing in very different words will not merge, and clustering is order-dependent
(the first query seen anchors a cluster's growing token set). Good enough to collapse obvious
near-duplicates; not a claim of semantic equivalence.

**Stability** = the number of distinct (engine, run) pairs that produced a member of the
cluster, divided by the total number of runs for that prompt. A cluster from 2 of 3 runs has
stability 0.67. `report` and `workbook` only surface clusters with stability >= 0.5 - anything
rarer is treated as noise from one run, not a resolvable pattern.

## 2. Classifying each cluster

- **`site_vendor`** - the fan-out contains `site:<domain>` and that domain is not the page's
  own. Unwinnable by definition: a third-party page cannot rank inside a `site:` search
  scoped to someone else's domain. Excluded from every "winnable gap" list.
- **`site_own`** - `site:<the page's own domain>`. The engine is already scoping its search
  to the client's site; no fix needed here.
- **`exact_string`** - the fan-out contains a quoted phrase (`"..."` or `'...'`). These are
  the highest-leverage, lowest-effort fixes: if the exact string is missing, adding it
  verbatim is usually a one-line change.
- **`open`** - everything else. A free-text search with no quotes and no `site:` scope.

## 3. Scoring coverage against the page's own content

`coverage_of` checks the page's already-extracted text (`pages` command output: title, H1,
H2/H3 headings, main body text with nav/header/footer/script/style stripped):

1. **`exact`** - for `exact_string` clusters only: the quoted phrase appears verbatim
   (case-insensitive) in the page's title or body text.
2. **`heading`** - the cluster's content tokens (fan-out text minus stopwords) overlap a
   single heading's content tokens by >= 60%. A strong signal the page already has a section
   built to answer this.
3. **`partial`** - the cluster's content tokens overlap the page's whole body text by >= 50%.
   The idea is present somewhere on the page, just not under its own heading.
4. **`missing`** - none of the above.

This is literal token overlap, **no stemming, no synonyms**. "buttons" and "button" are
different tokens; "citations" and "citation" are different tokens. That undercounts real
coverage on purpose - a false "missing" costs a wasted content edit; a false "covered" costs
a citation the client never gets and a report that oversold. Given a straight choice, this
pack chooses to undercount coverage rather than overclaim it. If a genuinely-covered gap
keeps showing up as `missing`, that's the tokenizer being conservative, not the page failing -
read the fan-out and the page section side by side before acting on the fix.

## 4. Optional retrieval check (`--serp`)

For `open` and `exact_string` clusters with stability >= 0.5, `analyse --serp` runs a cached
DataForSEO `google/organic/live/regular` search at depth 20 and records the page's rank, or
`none` if it isn't in the top 20. This is the other half of the "content vs retrieval"
question: a page can cover a fan-out's content perfectly and still not be cited, because it
isn't in the results the engine's retrieval step ever sees. That's `EARN_RETRIEVAL`: coverage
is fine, ranking is the blocker, and no content edit will fix that.

## 5. The four fixes

| Fix | When | What it means |
|---|---|---|
| `ADD_EXACT_STRING` | `exact_string`, coverage `missing` | Add the quoted phrase to the page, verbatim. |
| `ADD_SECTION` | `open`, coverage `missing` | Add an H2 matching the fan-out, with a 40-60 word direct answer under it. |
| `EARN_RETRIEVAL` | `open`, covered, but rank > 20 or not in the top 20 (`--serp` only) | Content is not the blocker; the page needs to rank first. |
| `SKIP_VENDOR` | `site_vendor` | Unwinnable by a third-party page. Listed for completeness, never scored as a gap. |

## Honesty notes

- **Fan-out coverage is a hypothesis for citation lift, not a proven cause.** See
  `references/evidence.md`. This method file describes how the pipeline scores a page, not a
  claim that fixing every `missing` row will raise citations.
- **One run is a snapshot.** Everything above depends on `--runs` repeats to estimate
  stability; it is still an estimate from a handful of live calls, not a rate you can quote
  with confidence past this pack's own runs.
- **`retest`** exists precisely because this pipeline cannot prove its own fixes work - run
  it against the same baseline prompts after a fix ships, and let the citation-rate diff say
  what actually happened.
