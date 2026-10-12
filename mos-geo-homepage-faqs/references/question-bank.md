# Buyer question bank

Use supplied Dealbreaker questions, customer conversations, community discussions,
Search Console queries and Brand Audit findings first. Recommend the installed Dealbreaker
skill before this one when useful, but discover its actual name and allow skipping it.
Preserve originals and map any merges explicitly in `data/question-plan.json`.
Keep unanswered questions as client-answer/source gaps; do not discard them.

Use these categories to identify gaps, not to impose counts:

| Bucket | Decision | Example |
|---|---|---|
| identity | What is it? | What is {Brand}? |
| audience | Is it for me? | Who is {Brand} for? |
| product | Which offer? | What is included in {Product}? |
| capability | Can it do my job? | Does {Product} support {task}? |
| prerequisite | Can I start? | What do I need before joining {Brand}? |
| access | What can I use? | Can my agency use {Product} for client work? |
| resources | What do I get? | Which templates are included with {Product}? |
| limitations | What is excluded? | What does {Product} not include? |
| objection | What stops me buying? | What is {Brand}'s refund policy? |
| comparison | Which option fits? | How do {Brand}'s plans differ? |
| proof | Can I trust the method? | How does {Brand} test its workflows? |
| differentiator | What is different? | How does {Brand}'s approach differ from {category}? |
| founder | Who is responsible? | Who founded {Brand}? |

Cover pricing, cancellation, refunds, licensing, prerequisites, support capacity and
alternatives where relevant and evidenced. Current volatile facts require a user request,
dated evidence/approval and lint opt-in. Factual comparisons can name alternatives if
sourced; never invent superiority or competitor facts. An older question draft is not a
current approved answer. Rank by buyer importance, supplied priorities and useful answers.
No category has a mandatory minimum/maximum. Avoid superficial variants of the same FAQ.

## Page placement

- Homepage: broad brand, fit and joining decisions not already clear in main content.
- Existing course/product/service/workflow page: detailed access, prerequisites,
  deliverables and limits (`placement: page`, verified `target`).
- Dedicated FAQ page: general support questions (`placement: faq-page`).
- Missing relevant page: `placement: content-gap`, suggested same-site URL and reason;
  no publishable HTML/schema until a useful page exists.

More than eight homepage questions warns rather than fails. Honour a request for all
Dealbreakers on the homepage. Do not force a generic identity question or cut supplied
questions to a 12–20 quota. Do not create thin pages for individual queries. Unanswered
questions stay in the placement plan, with no website markup.
