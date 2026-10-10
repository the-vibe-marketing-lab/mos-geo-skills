# Anatomy of Steve Toth's homepage FAQ GPT

An analysis of two observed TVML runs of the LLM-Friendly Homepage FAQ Generator.
The October 1 historical sample is in `source-sample-steve-toth-gpt.md`. A fresh October 10
live run produced different structure. These observations inform an independent skill;
they are not recovered private instructions. Treat the single-sentence formula below as
our editorial design, not an invariant of the GPT.

| Observable behaviour | October 1 saved sample | October 10 live run |
|---|---|---|
| FAQ count | 20 | 15 |
| Answer length | One sentence each | Two sentences each, 38 to 51 whitespace-delimited words |
| Opening entity | Brand or MarketingOS | Full brand name in all 15 |
| Question mix | Identity, product, capabilities, fit, proof | Mostly Can/Does benefit questions, plus beginner fit and free joining |
| Sources | Described generally, no page links per FAQ | Three general website/Skool links, no page evidence per FAQ |
| Supporting notes | Research preamble and claims closing note | Research preamble, theme/evidence table, claims closing note |
| Homepage selection | No ranked subset | Eight recommended question numbers |
| Price | Excluded | A free-to-join question with premium access qualified |

The live run confirms entity-first answers and cautious outcome framing, but disproves a
fixed sentence count, question count, source-free format or permanent price exclusion.
The GPT says it reviewed public discussions; we cannot verify its research process from
that assertion alone. Its theme table is a summary, not claim-level evidence.

This skill adds passage-level evidence review, consistent spelling, appropriate internal
links, explicit release/access qualifications and a checked export. It chooses 12 to 20
questions, a top-eight homepage subset and single-sentence answers as its own defaults.
It has not demonstrated a causal increase in AI citations.

Credit, for anyone who asks: the GPT is Steve Toth's (SEO Notebook / Notebook Agency). This
skill is modelled on its output.

## The three-part envelope

Both observed runs include research and claims notes. The skill records these as research
notes and a handover; actual source passages form the evidence trail.

| Part | What the GPT does | Where the skill puts it |
|---|---|---|
| Research preamble | Says how thin the independent evidence is, names the same-name entity it avoided, lists the source types it trusted and the themes it found | The public `## Summary` of `data/research.md`, rendered at the top of `research-note.md` (the rest of research.md stays private) |
| FAQ set | A researched set; count varies between runs | `faqs.md` |
| Closing note | Explains why outcome claims were framed as method, not result | The bottom of `research-note.md` |

Write the preamble honestly. If third-party evidence is sparse, say so in one sentence. Never
pad it with invented testimonial themes.

## The answer formula

The historical sample suggests this editorial formula; the live run uses two sentences. All ranges and lint rules below are our design choices. `lint` checks the ones marked (L).

1. **Exactly one sentence.** (L) No second sentence, no semicolon chains.
2. **Opens with the full entity name as the subject.** (L) The brand name, or a product name
   followed by "is {Brand}'s ...". Never `It`, `We`, `Our`, `You`, `Yes` or `No`.
3. **No Yes/No opener, even on a yes/no question.** "Does {Brand} help brands get cited?" is
   answered "{Brand} teaches strategies for ...".
4. **Restate the question's key terms** in the answer, so the pair matches as a unit.
5. **Expand an acronym once:** "generative engine optimisation, or GEO".
6. **About 25 to 45 words,** built as subject + verb + a list of 3 to 6 concrete nouns +
   a purpose clause. (L: 20 to 55 words is the hard range.)
7. **Third person, present tense.**
8. **Name real platforms and tools** the brand actually uses or serves (entity anchoring).
   (L: every capitalised name must appear in the input bundle.)
9. **Capability verbs, not outcome verbs.** Use teaches, helps, shows, is designed to, focuses
   on, includes, gives. Never gets you cited, will rank, guarantees, doubles. (L)
10. **No volatile facts.** No numbers, prices, member counts or dates. (L, unless
    `--allow-volatile`)
11. **No superlatives, no guarantees, no em dashes.** (L)

Why the formula works for an LLM: any one answer can be lifted on its own and still says who
it is about, what it does and for whom. That is the whole point of the format.

### Voice inside the formula

The structure is fixed. The brand's voice changes word choice, examples and warmth, never the
sentence shape. A plain-spoken brand says "shows you how to"; a formal one says "provides
guidance on". Never-say terms fail `lint`; spelling follows the brand's locale.

### Links inside the formula

An answer may carry one internal link. The anchor is 2 to 6 words copied verbatim from the
answer and the answer is never reworded to fit a link. See SKILL.md stage 6b.

## Coverage buckets

Observed coverage in one 20-FAQ sample. These counts inform our design, not a claim about hidden GPT instructions.

| Bucket | Sample count | Job for an LLM |
|---|---|---|
| Identity / definition | 1 | The canonical one-liner |
| Flagship product | 2 | Ties each product entity to the brand entity |
| Core capabilities | 7 | "Does X do Y" retrieval matches |
| Proof / methodology | 4 | Why trust it: how the work is done |
| Audience fit | 4 | Who it is for, including prerequisites |
| Resources | 1 | What you actually get |
| Differentiator | 1 | What makes it different, stated as fact |

Question patterns and slot templates for each bucket are in `question-bank.md`.

**Default exclusions in this skill:** price, member counts and competitor comparisons. The
live GPT includes free joining, so these are our defaults rather than inferred GPT rules, and never names a same-name entity either:
disambiguate through the identity answer's own specifics (founder, city, domain). It adds a founder question only when the
founder is a verifiable public entity and the interview says yes.

## Worked example (shape only)

Question: `Does {Brand} teach GEO and AI SEO?`

Answer: `{Brand} teaches generative engine optimisation, or GEO, alongside traditional SEO,
covering brand visibility, technical website structure, content planning and practical
methods for improving how brands appear in AI search.`

One sentence, entity first, key terms restated, acronym expanded once, capability verb, a
noun list and a purpose clause, 29 words.

## Limits observed in the samples and our improvements

| GPT weakness | Evidence in the sample | Fix |
|---|---|---|
| Weak source mapping | The live run links three general sources, but no FAQ to a supporting passage | Every FAQ indexes its source URLs; passage review records supporting evidence, with first-party/third-party labels |
| Guessable facts | Tool names and "enterprise and small-business environments" with no visible source | Provenance lint fails any number or capitalised name not in the input bundle |
| Locale mismatch | US spelling for an Australian brand in this sample | Brand locale, checked by `lint` |
| Repetition | Three answers make nearly the same point | Near-duplicate question check (fail) and answer overlap warning |
| Variable homepage fit | The historical sample has no subset; the live run recommends eight | Ranked set: top 8 on the homepage, the rest for an FAQ page |
| Dead-end answers | No links | One verified internal link per answer where a page backs it up |
| Voice untested | Two runs of the same brand cannot establish behaviour for other brands | Interview captures tone and never-say terms |

## Things that are not true, so never say them

- FAQ markup earns no rich result for any site. Google limited FAQ rich results to
  government and health sites in August 2023 and removed them from Search on 7 May 2026.
- Nothing shows AI engines weight FAQ blocks specially. The text is ordinary retrievable
  page text; self-contained answers are simply easy to lift.
- Internal links help people and crawlers find the page that backs up an answer. They are
  not a proven way to earn AI citations.
