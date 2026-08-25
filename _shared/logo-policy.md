# Logo and trademark policy — AI assistant buttons

**Last reviewed:** 2026-08-23
**Applies to:** any skill in `mos-geo-skills` that renders a button, badge or link referencing an AI provider.

Short version: **use wordmarks, not logos.** The name of a platform, set in your own typeface, as the label on a link that genuinely goes there. Logos are opt-in, off by default, and every provider below has terms that a five-logo button row sits awkwardly against.

This is a working summary of published brand guidelines, not legal advice. When a client's brand or legal team asks, send them the source URLs.

---

## Contents

1. [Anthropic (Claude) — the most restrictive](#1-anthropic-claude--the-most-restrictive)
2. [OpenAI (ChatGPT)](#2-openai-chatgpt)
3. [Google (AI Mode, Gemini)](#3-google-ai-mode-gemini)
4. [xAI (Grok)](#4-xai-grok)
5. [Perplexity](#5-perplexity)
6. [The recommendation](#6-the-recommendation)
7. [Paragraph to paste into a client brief](#7-paragraph-to-paste-into-a-client-brief)

---

## 1. Anthropic (Claude) — the most restrictive

**Source:** <https://www.anthropic.com/legal/trademark-guidelines>

This reverses the common assumption in the industry that OpenAI is the strictest of the group. It is not. Anthropic is.

The guidelines require **prior written approval**. The operative wording is that you may only use their trademarks as specifically permitted by them, and only in materials they approve beforehand. That is an approval gate, not a set of conditions you can satisfy on your own and proceed.

Also required:

- **No alterations.** No recolouring, no redrawing, no cropping, no fitting the mark into your own shape.
- **No implication of endorsement, sponsorship or partnership.**
- **Permission is requested via marketing@anthropic.com.**

And the part people assume exists but does not: **there is no public self-serve "works with Claude" badge programme.** You cannot go and download an approved badge and be compliant by using it correctly. There is nothing to download.

**Practical position:** do not ship the Claude logo on a client button without written approval on file. The wordmark "Claude" as a text label describing where the link goes is the defensible option.

---

## 2. OpenAI (ChatGPT)

**Sources:** <https://openai.com/brand/> and <https://openai.com/policies/developer-apps-terms/>

- The **"Powered by OpenAI" badge is for active API customers.** A share button is a hyperlink with a query string — it is not API usage, so the badge programme does not apply to it. Using the badge on a page that makes no API calls misrepresents the relationship.
- Preferred phrasing where a relationship genuinely exists: **"powered by"** or **"built on"**.
- **Explicitly avoid: "built with", "developed with", "partnered with".** These imply a collaboration that does not exist.
- **Must not imply endorsement** of the client, their product, or their content.
- Permission is **revocable at any time**, so anything you ship should be easy to swap out.

**Practical position:** the wordmark "ChatGPT" as a link label is nominative use. The OpenAI logo, the OpenAI name in a badge lockup, and any "powered by" claim are all out of scope for a share button.

---

## 3. Google (AI Mode, Gemini)

**Sources:** <https://about.google/brand-resource-center/brand-terms/> and <https://www.google.com/permissions/trademark/rules/>

Google runs a **permission-request model** — you ask, they decide.

Hard prohibitions on the marks themselves:

- **No recolouring.**
- **No drop shadows or other effects.**
- **No transparency changes.**
- **No stretching or distortion.**

The one that matters most here: Google **forbids combining their marks with other logos into a composite lockup.** A tight row of five AI provider logos rendered as a single unit is arguably exactly that. It is not a settled question, but it is a real risk and the client's legal team will spot it.

Google also **requires an attribution notice** stating that the marks are trademarks of Google LLC wherever they appear.

**Practical position:** "Google AI Mode" as a text label. If a logo is genuinely required, request permission and carry the attribution notice.

---

## 4. xAI (Grok)

**Source:** <https://x.ai/legal/brand-guidelines>

- **Prohibits use of the marks in product names, app names and domain names.**
- Prohibits **"adding anything in close proximity to the Marks in a way that creates an impression of a new mark."**

That second clause is the one a button row runs into. A tight horizontal strip of provider logos, styled as one component, plausibly reads as a new composite mark. Same exposure as the Google composite-lockup rule, arriving from a different direction.

Contact for permission: **legal@x.ai**

**Note from the endpoint research:** Grok is the weakest button of the set anyway — logged-out visitors hit a sign-in wall instead of an answer (see `platform-endpoints.json`). Trademark risk plus poor user outcome is a good reason to leave it off consumer-facing builds entirely.

---

## 5. Perplexity

**Source:** brand system at <https://live.standards.site/perplexity>

- **Editorial use is generally fine** — referring to Perplexity in an article, a comparison, or a description.
- **Commercial use requires prior written consent.** A button on a client's commercial site is commercial use.
- **No recolouring and no effects** applied to the mark.

**Practical position:** the least aggressive of the five, but a client button is still commercial. Wordmark by default.

---

## 6. The recommendation

**Default to wordmark-only buttons.** The platform name rendered as text, in the site's own typeface, as the label on a link that genuinely opens that platform.

Why this is the right default:

- **Nominative use is far more defensible.** Using a word mark to accurately describe where a link goes is a well-established use. Reproducing five protected logos in a composite row is not, and it collides with at least two of the guidelines above (Google's composite-lockup rule, xAI's proximity rule) before anyone has even asked about approvals.
- **No approval gate.** Anthropic's prior-written-approval requirement alone makes a logo row unshippable without paperwork, and no self-serve badge exists to fall back on.
- **Nothing is lost.** A reader recognises "ChatGPT" as text just as fast as the logo. The button's job is to be clicked, and the word does that job.

Rules for any skill in this pack:

- **Logos are off by default.** They are an explicit opt-in flag, never the fallback.
- **When the opt-in is used, surface the per-provider warning** from the sections above so the member knows what they are taking on.
- **Never add "Official", "Partner", "Certified", or a checkmark** to any of these buttons, in any form, wordmark or logo. Every provider above prohibits implying endorsement, and a tick next to a brand name is the fastest way to imply it.
- **Never alter a mark** if one is used — no recolouring to match the site palette, no shadows, no distortion. Every provider above prohibits it.
- **Keep the provider list configurable**, so removing one is a config change rather than a rebuild.

---

## 7. Paragraph to paste into a client brief

Copy this into a brief or an email to get brand/legal sign-off:

> This page includes a row of links that open AI assistants (ChatGPT, Claude, Perplexity, Google AI Mode) with a prompt asking for a summary of this page. By default the links are labelled with the platform name as plain text in our own typeface, with no logos, no badges, and no endorsement language. This is nominative use — the name is used only to describe where the link goes. We are not claiming a partnership, integration, or approval from any of these companies, and no logo or brand asset belonging to them is reproduced.
>
> If you would prefer the buttons to carry the official logos, that needs brand approval from each provider before we build it. Anthropic in particular requires prior written approval for any use of the Claude marks (marketing@anthropic.com) and does not run a self-serve badge programme. Google requires a permission request plus a trademark attribution notice, and prohibits combining their marks with other logos in a single lockup — which a five-logo row would be. Our recommendation is text labels.

---

## Sources

- Anthropic trademark guidelines — <https://www.anthropic.com/legal/trademark-guidelines>
- OpenAI brand guidelines — <https://openai.com/brand/>
- OpenAI developer apps terms — <https://openai.com/policies/developer-apps-terms/>
- Google brand terms — <https://about.google/brand-resource-center/brand-terms/>
- Google trademark rules — <https://www.google.com/permissions/trademark/rules/>
- xAI brand guidelines — <https://x.ai/legal/brand-guidelines>
- Perplexity brand system — <https://live.standards.site/perplexity>
