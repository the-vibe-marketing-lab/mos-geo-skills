# The AI summary block

The optional companion to the buttons — and, on the only controlled evidence that exists, the
part that actually moves the numbers.

Read this before recommending buttons on their own, and before answering a client who asks
whether the tactic works.

## The evidence

One controlled A/B test has been published on this tactic. Search Engine Land, 13 April 2026,
run on Leite's Culinaria:

<https://searchengineland.com/ai-buttons-474137>

| Variant | Result |
| --- | --- |
| AI share buttons alone | **-17% clicks** |
| AI share buttons **+** an on-page AI summary block | **+36% clicks, +116% impressions** |

The honest reading: buttons alone cost the site traffic. Buttons paired with a summary block
gained it substantially. The most plausible explanation is that the summary block is doing the
work — it gives the page an extractable, quotable synopsis that AI surfaces can lift, which is a
mechanism that operates on every crawl rather than only when a reader clicks something.

## How honest to be about it

Completely. Say the following, in the brief, in these terms:

- This is **one study, on one site, in one niche.** It is not a body of evidence.
- The -17% figure is real and it is the finding for buttons alone. Do not bury it.
- The mechanism for the pairing result is inferred, not proven. Nobody isolated the summary
  block as a third variant.
- The reason to ship anyway is cost, not certainty: the build is small and reversible in one
  line, so the expected value holds even on thin evidence.

A client who later finds the -17% number themselves — and they will, it is the headline of the
article — will discount everything else in the deliverable. Getting caught overselling costs
more than the tactic is worth.

## What the block actually is

A short, scannable synopsis of the article, rendered on the page, above or beside the button
row. Not a meta description, not a teaser, not the intro paragraph rewritten.

Shape that works:

- **Three to five bullets**, each a complete standalone claim. A bullet that only makes sense
  after reading the one above it is useless to an extractive system.
- **60 to 120 words total.** Long enough to carry the article's actual conclusions, short enough
  that a reader scans it instead of skipping it.
- **Specifics survive extraction, generalities do not.** "Extras cover typically pays 60% of a
  dental bill up to an annual limit" is quotable; "dental cover varies" is not.
- **A visible heading** — "Key points" or "In short". It labels the block for a human and gives
  a machine an unambiguous boundary.
- **No links inside it.** The block is a summary, not a navigation surface.

The block must be *true to the article*. If it says something the body does not support, you
have built a machine for propagating a wrong claim into AI answers with the client's name on it.

## Generating it

Generate from the article's own text, not from its title or its metadata. Draft the bullets by
pulling the conclusions the piece actually reaches, then verify each one appears in the body.

Two rules that matter more than they sound:

- **The client reviews and owns the copy.** These are on-page factual claims on their domain,
  frequently in regulated verticals — finance, health, insurance. An AI-drafted summary that
  ships unreviewed is a compliance problem, not a content problem. Hand over drafts, marked as
  drafts.
- **It needs to be regenerable.** An article gets updated and the summary silently goes stale.
  Whatever the client builds, it should be a field on the content model that an editor can
  refresh, not hardcoded markup nobody remembers exists.

## Marking it up so it is extractable

Plain semantic HTML does most of the work. Do not overthink it.

```html
<aside class="ai-summary" aria-labelledby="ai-summary-heading">
  <h2 id="ai-summary-heading">Key points</h2>
  <ul>
    <li>…</li>
  </ul>
</aside>
```

A real heading and a real list, high in the DOM, immediately after the H1 and byline. Extractive
systems read document order; a summary buried below the fold is a summary that arrives after the
extractor has decided what the page is about.

Do not hide it behind a toggle or an accordion for "cleanliness". Content that requires
interaction to reveal is content that gets missed, by readers and by machines.

If the client already has structured data on the article, `speakable` on the summary's selector
is a reasonable addition. It is limited in support and it is not the point — do not present
schema as the mechanism here. The mechanism is a clear, quotable synopsis in the HTML.

## Placement with the buttons

Two arrangements work:

- **Stacked** — summary block first, button row directly beneath it, both above the article
  body. Reads as one editorial module. This is the default.
- **Side by side** on wide viewports — summary left, buttons right — collapsing to stacked below
  about 768px. Only if the client's layout has the horizontal room; it usually does not.

Either way it is **one instance per article**, near the top, after the byline. A second copy at
the foot of the article doubles the visual footprint for a marginal gain, and it is not what was
tested.

Avoid sticky or floating treatments. They compete with cookie banners, chat widgets, and mobile
share sheets, and they make an editorial feature read as a growth hack.

## Presenting the tradeoff to a client

Give them the choice explicitly rather than deciding for them:

**Buttons only.** Half a dev day, one component, reversible in one line, no content work. The
one controlled test measured a click decline for this variant. Defensible as a small bet; do not
sell it as an improvement.

**Buttons plus summary block.** The variant that measured well. Costs real content work — a
summary per article, drafted and reviewed — plus a field on the content model. Scales badly by
hand across a large library, which is the honest objection and worth naming before they raise
it. Suggest they start with the top 20 pages by traffic and measure before committing the
library.

**Summary block only.** Not tested, and therefore not something to recommend on evidence. Worth
naming as an option so the client sees the full space, with the caveat attached.

The recommendation, absent a reason to differ: **buttons plus summary block on the top pages
first.** It matches the one variant that measured well, and it keeps the content cost bounded
until there is a read on the client's own numbers.
