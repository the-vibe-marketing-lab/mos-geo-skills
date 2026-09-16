# Building the prompt set

The prompt set is the whole experiment. Write it once, show it to the user, then run it
once. Every prompt is built from **`{brand_name}` and `{industry}` only**.

## The rule that matters most

**Never put a domain, URL, founder name, location or product name in a prompt.** Not even
if you know them, and not even if the user's own files mention them. The test is whether an
engine can find the brand from its name and category alone. A prompt that carries a clue
measures your clue, not the brand's visibility.

The same goes for you: if this session already knows the brand (from project files or
memory), do not "help" the prompts with that knowledge.

## Shape

Write `data/prompts.json` inside the run folder (the run also copies whatever `--prompts`
file it is given there, so the folder always keeps the exact prompts it asked):

```json
{
  "closed_book": [
    {"id": "cb01", "text": "What is {brand_name}? Tell me what you know about it: what it does, who runs it, where it is based and who it is for. If you are not sure, say so."},
    {"id": "cb02", "text": "Who are the best-known brands in {industry}? List the ones you would recommend and say why."},
    {"id": "cb03", "text": "Have you heard of {brand_name} in {industry}? How does it compare with the alternatives?"}
  ],
  "branded": [ ... 5 prompts ... ],
  "unbranded": [ ... 5 prompts ... ]
}
```

Substitute the real values; the placeholders above are for illustration. Keep the three
closed-book prompts close to the wording shown, so results compare across brands.

### Branded (5)

What a buyer types once they have heard the name. Cover, in this order:

1. **Identity:** "What is {brand_name}?"
2. **Reputation:** "Is {brand_name} any good? What do people say about it?"
3. **Offer and price:** "What does {brand_name} offer and how much does it cost?"
4. **Alternatives:** "What are the best alternatives to {brand_name}?"
5. **Decision-stage question:** one late-stage question a buyer in `{industry}` would ask
   before paying (for software: integrations or security certification; for a service:
   contract terms, guarantees or who delivers the work; for a community or course: what
   you actually get and whether it is worth it).

### Unbranded (5)

What a buyer types before they know the brand exists. **The brand name must not appear.**
Spread them across the buying journey:

1. **Problem-aware:** a question about the problem `{industry}` solves.
2. **Solution-aware:** "What is the best way to …" for that problem.
3. **Category shortlist:** "Best {industry} for {a typical buyer}".
4. **Comparison:** "What should I look for when choosing {industry}?"
5. **Local or niche:** the same shortlist narrowed to the most likely buyer segment or
   market for this category.

Write them the way a real person types into ChatGPT: plain words, one question, no
keyword stuffing.

## Size and cost

3 closed-book + 10 search prompts is the default. With the default surfaces that is
3 x 3 closed-book calls, 4 x 10 API search calls and 4 x 10 app calls: 89 calls, about $2.11
per brand on DataForSEO (measured, see `providers.md`). Every prompt runs **once**. Do
not add repeats. If the user wants a cheaper run, cut unbranded prompts before cutting
surfaces.

Keep every prompt under 500 characters. DataForSEO rejects longer ones, and the script
checks before spending anything.

## Confirm before spending

Show the 13 prompts to the user in one message and ask for a yes before running. Changing
a prompt after the run means paying for the run again.
