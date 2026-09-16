# Report template: the two parts you write

`brand-360-report.md` is built by `brand360.py assemble`, never by hand. The script owns the
frontmatter, the title, the snapshot note, sections 1 to 17 (from the research agent), the
reference list and the prompt-set appendix. You write exactly two files in `$RUN/data/`:

1. `header.md`: the bullet block under the title.
2. `section-18.md`: the AI Visibility Scorecard.

Copy the shapes below. Replace everything in `{braces}`. Keep every bold label, heading,
table column and the order. Australian English, no em dashes, no rates ("2 of 5", never
"40%").

The reference output is the first TVML run:
`campaigns/geo/2026-09/the-vibe-marketing-lab/brand-360-report.md` in the TVML brain.

---

## `data/header.md`

```markdown
- **Brand:** {brand name} ({short name or acronym, omit the brackets if none})
- **Industry (input):** {industry exactly as given}
- **Research date:** {D Month YYYY} | **Market:** {country name} ({ISO code})
- **Method:** `/mos-geo-brand-360`. The only inputs were the brand name and the industry. No domain, founder or product name was given to any engine.
- **Entity found:** {site} and {main platform presence}, run by {operator} in {city} ({confidence} confidence). Name collisions: {comma list of every collision}. Details are under *Entity found*.
- **What the engines found:** {x} of {n} AI surfaces landed on this entity, {y} blended it with others, and {z} ({which}) described a different "{name}". See Section 18.
- **Headline:** {the one finding that matters, with the key number in bold}.
- **Cost of the engine run:** ${cost from visibility-report.md} ({providers}, {calls} calls, {failed} failed).
- **Researcher context:** {"the research agent had no prior knowledge of the brand" OR "the research agent's workspace already held {brand} files. It was told to use only live web evidence (see 18.5)"}.
```

Take the cost, call count and provider from the header and coverage matrix of
`visibility-report.md` (calls = rows in the matrix times prompts; failures = the Errors
column).

---

## `data/section-18.md`

```markdown
## 18. AI Visibility Scorecard

Source: `visibility-report.md` in this folder ({answers} engine answers, {provider note}, run {D Month YYYY}, market {ISO code}). Each prompt was asked once. The 13 prompts are listed in the appendix.

### 18.1 Engine by engine

| Engine | Surface | Known (closed-book) | Found ("What is {short name}?") | Resolved to | Mixed up with | Branded answers citing a source | Recommended (unbranded) |
|---|---|---|---|---|---|---|---|
| ChatGPT | API | **{Yes/Partly/No}** | **{Yes/Partly/No/Wrong brand}** | {domains} | {collisions or blank} | {x}/5 | **{x}/5** |
| Claude | API | ... |
| Gemini | API | ... |
| Perplexity | API | n/a | ... |
| ChatGPT | App | n/a | ... |
| Gemini | App | n/a | ... |
| Google AI Mode | App | n/a | ... |
| Google AI Overviews | App | n/a | ... |

**How to read "Found".** Every branded answer repeats the brand name, because the prompt contains it. So "Found" is judged from what the answer said the brand *is*, not from a name match.

### 18.2 The funnel

- **Known:** {x} of {n} models know {short name} without search. {one sentence on how they said it}
- **Found:** {x} of {n} surfaces clearly identified the right brand ({which}). {y} were partial ({which}). {z} described a different entity ({which}).
- **Cited:** {x} of {n} surfaces cited {own domain} at least once ({count} citations in total{, rank note}). {which surfaces never cited it, and what they used instead}
- **Recommended:** **{x} of {n}** unbranded buyer answers named {short name}, across all {n} surfaces.

**Headline: the brand drops out {completely} at {stage}.** {two sentences on what that means for a buyer}

### 18.3 Who gets recommended instead

These are the names and sources the engines put in front of buyers for the five unbranded prompts:

- **Courses:** {names}
- **Communities:** {names}
- **For "{the problem-aware prompt}":** {what came up}

{One or two sentences comparing these with the competitors in Section 3.}

### 18.4 Sources the engines trust

| Class | Domains (citations across the run) | What it means |
|---|---|---|
| Own | {domain (count, engines)} | {meaning} |
| Collision | {domains} | {meaning} |
| Platform | {domains} | {meaning} |
| Third-party (category) | {domains} | {meaning} |

{Dead links from the Dead links column, or "No cited URL was dead."} Full list: `data/domains.csv` ({n} domains).

**What the engines searched for.**
- **{pattern}:** {queries from section 6 of visibility-report.md}
- **{pattern}:** {queries}

### 18.5 What this does not tell you

- **One snapshot:** every prompt ran once. AI answers change between runs, so a single miss or hit is not a pattern. Re-run the same `data/prompts.json` to measure change.
- **Accuracy is yours to judge:** this section shows what the engines said. It does not score whether each statement is true.
- **Logged-out users only:** the app answers (ChatGPT, Gemini, AI Mode, AI Overviews) reflect a logged-out user in {country}. Signed-in users with history may see different answers.
- **{One provider / Fallbacks used}:** {"every answer came from DataForSEO. No fallback provider was needed." OR name the surfaces a fallback served, from the Via column}.
- **Researcher context:** {same fact as the header, one or two sentences}.
```

Drop a table row for a surface that was switched off, and add one for an extra that was
switched on (Grok, Perplexity app, Copilot). Adjust the `/5` counts if the prompt set was
changed.

---

## The assemble call

```bash
python3 "$SKILL/scripts/brand360.py" assemble --run-dir "$RUN" \
  --description "{First|Latest} /mos-geo-brand-360 audit of {short name}. 17-section brand research plus an AI Visibility Scorecard across {surfaces}. Headline - {headline}."
```

The script refuses to build (and says why) if the research draft is missing a section or its
reference list, or if either of your files has the wrong opening line.
