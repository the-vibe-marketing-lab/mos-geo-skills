# Anatomy of Steve Toth's homepage FAQ GPT

A dissection of what the "LLM-Friendly Homepage FAQ Generator" custom GPT writes (the raw
sample is `source-sample-steve-toth-gpt.md`). The skill keeps the GPT's answer shape exactly
and changes what feeds it: every fact comes from the brand's own site, the month's audit
files, the interview and cited third-party sources, and a script proves it.

Credit, for anyone who asks: the GPT is Steve Toth's (SEO Notebook / Notebook Agency). This
skill is modelled on its output.

## The three-part envelope

The GPT wraps its FAQs in two notes. They are its audit trail, so the skill keeps both, as
files rather than chat.

| Part | What the GPT does | Where the skill puts it |
|---|---|---|
| Research preamble | Says how thin the independent evidence is, names the same-name entity it avoided, lists the source types it trusted and the themes it found | The public `## Summary` of `data/research.md`, rendered at the top of `research-note.md` (the rest of research.md stays private) |
| FAQ set | 20 questions and answers | `faqs.md` |
| Closing note | Explains why outcome claims were framed as method, not result | The bottom of `research-note.md` |

Write the preamble honestly. If third-party evidence is sparse, say so in one sentence. Never
pad it with invented testimonial themes.

## The answer formula

Every one of the sample's 20 answers follows these rules. `lint` checks the ones marked (L).

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

The GPT's hidden selection logic. Counts are from the 20-FAQ sample.

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

**Deliberately absent:** price, member count, competitors and location. They are volatile or
unverifiable. The skill keeps that exclusion, and never names a same-name entity either:
disambiguate through the identity answer's own specifics (founder, city, domain). It adds a founder question only when the
founder is a verifiable public entity and the interview says yes.

## Worked example (shape only)

Question: `Does {Brand} teach GEO and AI SEO?`

Answer: `{Brand} teaches generative engine optimisation, or GEO, alongside traditional SEO,
covering brand visibility, technical website structure, content planning and practical
methods for improving how brands appear in AI search.`

One sentence, entity first, key terms restated, acronym expanded once, capability verb, a
noun list and a purpose clause, 29 words.

## Where the GPT goes wrong (what the skill fixes)

| GPT weakness | Evidence in the sample | Fix |
|---|---|---|
| No sources shown | Themes are asserted in the preamble, never tied to pages | Every FAQ cites its source URL(s) in its comment; that list is the evidence ledger, and `evidence` says first-party, third-party or mixed |
| Guessable facts | Tool names and "enterprise and small-business environments" with no visible source | Provenance lint fails any number or capitalised name not in the input bundle |
| Wrong locale | US spelling for an Australian brand | Brand locale, checked by `lint` |
| Repetition | Three answers make nearly the same point | Near-duplicate question check (fail) and answer overlap warning |
| No homepage fit | 20 FAQs is long for a homepage | Ranked set: top 8 on the homepage, the rest for an FAQ page |
| Dead-end answers | No links | One verified internal link per answer where a page backs it up |
| One register for every brand | Same voice for any brand | Interview captures tone and never-say terms |

## Things that are not true, so never say them

- FAQ markup earns no rich result for any site. Google limited FAQ rich results to
  government and health sites in August 2023 and removed them from Search on 7 May 2026.
- Nothing shows AI engines weight FAQ blocks specially. The text is ordinary retrievable
  page text; self-contained answers are simply easy to lift.
- Internal links help people and crawlers find the page that backs up an answer. They are
  not a proven way to earn AI citations.
