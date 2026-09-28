# `data/findings.json`: the contract

You write this file. `dealbreakers.py build` renders every output from it and refuses to
render when a rule below fails. Read this when writing or fixing `findings.json`.

## Shape

```json
{
  "brand": "Trading name",
  "website": "https://example.com",
  "date": "YYYY-MM-DD",
  "mode": "own",
  "offer_summary": "What is sold today, to whom, at what price points, in 2 to 4 sentences.",
  "offer_sources": [{"url": "https://example.com/pricing", "quote": "verbatim text"}],
  "positioning_drift": {
    "summary": "Older copy sold X to Y; the current offer is Z.",
    "sources": [{"url": "https://web.archive.org/web/2025.../https://example.com/", "quote": "verbatim"}]
  },
  "personas": [
    {"id": "agency-owner", "label": "Agency owner", "needs": "One line: what must be true before they buy.",
     "source": "https://example.com/about"}
  ],
  "dealbreakers": [
    {
      "id": "proof-01",
      "category": "Proof & Results",
      "claim": "There isn't yet public proof that the core system produces more LLM citations.",
      "detail": "Optional second sentence of context.",
      "buyer_question": "Show me actual citation gains, not SEO traffic gains.",
      "severity": "critical",
      "evidence": "stated",
      "sources": [{"url": "https://example.com/", "quote": "we don't have a wall of citation screenshots yet"}],
      "checked": [],
      "reason": "",
      "personas": ["agency-owner"],
      "fix": {
        "type": "proof-asset",
        "action": "Publish one dated before/after citation case study with the prompt set and engines named.",
        "answer": "",
        "answer_sources": []
      }
    }
  ],
  "handled": [
    {"objection": "Is this another expensive AI course?", "how": "Entry is free with no card.",
     "sources": [{"url": "https://example.com/", "quote": "Free to join"}]}
  ],
  "priorities": ["proof-01"],
  "not_prioritised": "Generic 'expensive course' objections: entry is free, so they cost little conversion."
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `brand`, `website`, `date` | yes | `date` is the day of the crawl |
| `mode` | yes | `own` (the brand is the client or the user's own) or `competitor`. Competitor mode writes no Initiatives rows. |
| `offer_summary` + `offer_sources` | yes | At least one source; quotes verified |
| `positioning_drift` | no | Include only with sources (a Wayback page counts once saved) |
| `personas` | yes | 2 to 4. `id` is lowercase-hyphenated |
| `dealbreakers[].id` | yes | Unique, lowercase-hyphenated, e.g. `pricing-03` |
| `dealbreakers[].category` | yes | A name from the menu in `method.md`, or a new one (warned, not failed) |
| `dealbreakers[].claim` | yes | One sentence, the objection itself |
| `dealbreakers[].buyer_question` | yes | The buyer's own words, as a question or demand |
| `dealbreakers[].severity` | yes | `critical`, `major`, `minor` |
| `dealbreakers[].evidence` | yes | `stated`, `contradicted`, `absent`, `inferred` |
| `dealbreakers[].sources` | by evidence | See rules |
| `dealbreakers[].checked` | for `absent` | Saved page URLs, or strings starting `search: ` for a query you ran |
| `dealbreakers[].reason` | for `inferred` | Why a reasonable buyer would worry |
| `dealbreakers[].personas` | yes | At least one persona id from `personas` |
| `dealbreakers[].fix.type` | yes | `faq`, `pricing-page`, `proof-asset`, `policy-doc`, `positioning`, `product`, `none` |
| `dealbreakers[].fix.action` | yes unless type is `none` | What the brand should do |
| `dealbreakers[].fix.answer` | no | A draft FAQ answer; only with `answer_sources` |
| `handled` | yes | At least one, each with a verified source |
| `priorities` | yes | 3 to 7 ids, each `critical` or `major`, in order |
| `not_prioritised` | yes | One or two sentences |

## Build rules (each failure prints `[FAIL]`)

1. Required fields present and of the right type; ids unique; enums valid.
2. **Quote check.** Every `quote` in `offer_sources`, `positioning_drift.sources`,
   `dealbreakers[].sources`, `handled[].sources` and `fix.answer_sources` must appear in the
   saved text of that URL in `data/pages/` (case, whitespace, smart quotes and punctuation
   are normalised; it's a substring match). A URL that was never saved fails with a hint to
   run `add`.
3. `stated` needs 1+ source; `contradicted` needs 2+ sources with different URLs.
4. `absent` needs 2+ entries in `checked`; every non-`search:` entry must be a saved page.
5. `inferred` needs `reason` and can't be `critical`.
6. Every persona id used exists; every persona is used by at least one finding.
7. `fix.answer` without `answer_sources` fails.
8. `priorities`: 3 to 7 ids, all exist, none `minor`.

Warnings (`[WARN]`, don't block): a new category name, more than 25% critical, fewer than
6 or more than 10 categories, fewer than 12 findings, a category with only one finding.
