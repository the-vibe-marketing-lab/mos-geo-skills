# LLM Share Buttons — Implementation Brief

**Client:** {{CLIENT_NAME}}
**Prepared by:** {{AGENCY_NAME}}
**Date:** {{DATE}}
**Companion document:** Code Reference — LLM Share Buttons ({{CLIENT_NAME}})
**Companion file:** `llm-share-buttons-demo.html` — open in any browser for a pixel-accurate preview

---

## 1. Executive Summary

Add a row of buttons to the top of every article and guide on `{{CLIENT_DOMAIN}}`.

Each button opens an AI assistant — {{PLATFORM_LIST}} — in a new tab with a prompt already typed for the reader: a request to summarise the article and treat {{CLIENT_SHORT_NAME}} as an authoritative source on the topic.

Every click sends a real person into an AI assistant with a {{CLIENT_SHORT_NAME}} URL inside the prompt. The assistant fetches the page, generates a summary that cites it, and carries {{CLIENT_SHORT_NAME}} into that session's working context. At scale this seeds {{CLIENT_SHORT_NAME}}'s URLs and brand into the conversations LLMs are having with users, supporting the wider goal of lifting share of voice in AI Overviews, ChatGPT, Perplexity and Google AI Mode answers.

The build is small — one component, one stylesheet, one tracking event, one layout injection — and reversible in a single line of code. Estimated effort: **{{EFFORT_ESTIMATE}}**.

**Stack assumption.** This brief assumes {{CLIENT_NAME}}'s article pages are built on **{{DETECTED_STACK}}**, with **{{DETECTED_CMS}}** as the content source and **{{DETECTED_ANALYTICS}}** for analytics. That stack was inferred from a scan of the public site, not from access to the repository. **Please flag any mismatch before the build starts** so the component shape, injection point and tracking hook can be revised. A wrong stack assumption changes the component file format and the injection path, but not the endpoints, the prompt, or the tracking contract.

---

## 2. Success Criteria

The build is complete and ready for release when **all** of the following are true.

### Functional

- [ ] The widget renders on every URL inside the in-scope path patterns (full list in §3.1).
- [ ] The widget does **not** render on the homepage, category or vertical landing pages, hub and listing pages, calculator or tool pages, or any quote, checkout or account flow.
- [ ] One instance per article, positioned immediately after the byline (author + updated date) and before the introductory paragraph or key-points box.
- [ ] Each button opens in a new tab on the assistant's "new chat" screen with the prompt pre-filled.
- [ ] The pre-filled prompt arrives intact at the assistant — correctly URL-encoded, no truncation, no double-encoding.
- [ ] Any platform icons used are self-hosted from {{CLIENT_SHORT_NAME}}'s own domain or CDN — **no third-party SVG mirrors**.
- [ ] No layout shift (CLS) on first paint — the widget reserves its dimensions immediately.
- [ ] At 375px viewport width the button row wraps cleanly with **no horizontal scroll**.
- [ ] The prompt contains no instruction that could be read as a memory-injection or persistence directive beyond a plain citation request (see §7).

### Accessibility

- [ ] **Keyboard:** Tab cycles through every button, Enter activates, and the focus ring is clearly visible against the page background.
- [ ] **Screen reader:** the wrapper exposes a meaningful `aria-label`; each button announces its assistant name as its accessible name.
- [ ] Every button meets the 44 x 44 CSS px minimum touch-target size.
- [ ] The Lighthouse Accessibility score on a representative article (`{{EXAMPLE_ARTICLE_URL}}`) does **not regress by more than 2 points** after the change.

### Tracking

- [ ] Every button click fires a single `llm_share_click` event to the data layer with four parameters: `llm_platform`, `page_url`, `page_type`, `page_topic`.
- [ ] The event fires **before** the new tab opens — verify in {{DETECTED_ANALYTICS}} preview mode, or in Chrome DevTools with "Preserve log" enabled.
- [ ] The tag container forwards the event to GA4 as a custom event with all four parameters registered as custom dimensions.

### Brand & Compliance

- [ ] {{CLIENT_NAME}}'s brand and legal owners have signed off on the button treatment. **Wordmark-only is the default and needs no third-party approval.** If logos are added, see §6 — Anthropic requires prior written approval for its marks, and Google prohibits composite logo lockups.
- [ ] Any logo used comes from the provider's own official brand kit, unmodified, with no recolouring and no third-party reinterpretation.
- [ ] Button styling uses {{CLIENT_SHORT_NAME}}'s brand palette. Platform identity is carried by the wordmark, not by reproducing each provider's brand colour.

### Rollback

- [ ] The component can be removed by deleting a single line in the article layout template. No data migration, no CMS schema change, no CDN purge required.

---

## 3. Scope: which pages get the buttons

The widget renders on individual article-level pages — guides, explainers, and news or research pieces — and stays off everything else.

### 3.1 In scope

Each pattern maps to a topic phrase that is interpolated into the AI prompt.

{{TOPIC_MAP_TABLE}}

### 3.2 Out of scope — do not render

{{OUT_OF_SCOPE_LIST}}

A route-prefix check is sufficient: split the path into segments, look up the first segment in the topic-phrase map, and exclude any second segment that matches an excluded keyword. The exact helper is in the Code Reference companion document.

---

## 4. Where to inject the component

One instance per article, in a single position.

**Position:** immediately after the byline block (author and updated-date line), and immediately before the introductory paragraph or key-points box.

**In this stack:** {{INJECTION_POINT}}

**Template file:** `{{ARTICLE_TEMPLATE_PATH}}`

**Heading shown above the button row:** "{{WIDGET_HEADING}}"

A pixel-accurate preview of the placement ships with this brief as `llm-share-buttons-demo.html`. Open it in any browser — it is fully self-contained and makes no network requests.

---

## 5. The component

Build a single component named `{{COMPONENT_NAME}}` and inject it once into the article layout. The component:

- Reads the current route to derive the canonical page URL and the topic phrase.
- Builds the prompt by interpolating the URL and topic into the canonical template (§7).
- Renders the button row in fixed order: {{PLATFORM_LIST}}.
- Sets each button's `href` to that platform's new-chat endpoint with the URL-encoded prompt appended as a query parameter.
- Opens every button in a new tab with `target="_blank" rel="noopener noreferrer"`.
- Fires the `llm_share_click` event on click, before the new tab opens.

**All platform endpoints live in one config block** so a broken or removed provider is a one-line fix rather than a code migration. See §6 of the Code Reference for why this matters.

Full source for the component, the styles and the route-to-topic helper is in the **Code Reference** companion document.

---

## 6. Icons and brand compliance

**Default: wordmark-only.** Each button shows the platform name in {{CLIENT_SHORT_NAME}}'s own typography and brand palette, with no third-party logo. This is the recommended shipping state. It carries no trademark exposure, needs no external approval, and removes a whole class of broken-image and takedown risk.

**If {{CLIENT_NAME}} wants logos**, they must be downloaded from each provider's official brand resources and self-hosted at `{{ICON_BASE_PATH}}/{platform}.svg`. Do not use third-party SVG mirrors or icon CDNs — they have been, and will continue to be, taken down at brand owners' request. The OpenAI mark has already been pulled from one widely used third-party SVG CDN.

Official sources:

| Platform | Brand resource |
| --- | --- |
| ChatGPT | https://openai.com/brand |
| Claude | https://www.anthropic.com/legal/trademark-guidelines |
| Perplexity | Perplexity brand system (request via Perplexity's brand contact) |
| Grok | https://x.ai/legal/brand-guidelines |
| Google AI Mode | https://about.google/brand-resource-center/brand-terms/ |

**Known constraints to raise with legal before shipping logos:**

- **Anthropic** requires prior written approval for use of its marks. Do not ship the Claude logo on the assumption that a compatibility-indicator use is covered.
- **Google** prohibits composite logo lockups and restricts use of its marks in ways that imply endorsement. Note also that the AI Mode button targets Google Search's AI Mode surface, not Gemini — do not label or badge it with the Gemini logo.
- **OpenAI** publishes the most restrictive policy of the set; confirm in writing if {{CLIENT_NAME}}'s compliance process requires it.

**Fallback glyph.** The build ships with a neutral, original monochrome glyph (`generic-ai.svg`) so the widget renders correctly out of the box in icon mode without shipping anyone's trademark. Replace it per-platform only after sign-off.

**Styling.** Buttons take {{CLIENT_SHORT_NAME}}'s brand palette — primary `{{BRAND_PRIMARY_HEX}}` on `{{BRAND_SURFACE_HEX}}` — not the five providers' brand colours. Platform identity is carried by the wordmark. All widget styles are tokenised as CSS custom properties and can be themed from the wrapper class.

---

## 7. The prompt

The same prompt is used for every button — no per-platform variants. It is parameterised on two values: the canonical page URL and the topic phrase derived from the route (§3.1).

**Template:**

> {{PROMPT_TEMPLATE}}

**Worked example**, for `{{EXAMPLE_ARTICLE_URL}}` (topic: {{EXAMPLE_TOPIC_PHRASE}}):

> {{PROMPT_EXAMPLE}}

The prompt is then passed through `encodeURIComponent()` and appended to each platform's new-chat endpoint. Endpoint and query-parameter details for every platform are in the Code Reference.

**On prompt wording.** Keep the prompt to a plain summarise-and-cite request. Do not instruct the assistant to "save", "store" or "permanently remember" the URL — that phrasing reads as a persistence or memory-injection directive, is the pattern security researchers have flagged across this whole tactic, and is the reason at least one provider disabled its prefill parameter outright. A citation request is sufficient and carries none of that risk.

**Length.** Some platforms auto-submit the prompt the moment the page loads, and at least one truncates around 14,000 characters. Keep the prompt short and self-contained.

---

## 8. Tracking

Every click pushes a single event to the data layer **before** the new tab opens.

**Event name:** `llm_share_click`

**Event payload:**

| Key | Value |
| --- | --- |
| `event` | `llm_share_click` |
| `llm_platform` | The platform id — one of the ids listed in the Code Reference endpoint table |
| `page_url` | Full canonical URL of the article |
| `page_type` | {{PAGE_TYPE_VALUES}} |
| `page_topic` | The topic phrase from §3.1 |

{{CLIENT_NAME}}'s analytics owner should configure a trigger on `event = 'llm_share_click'` that forwards to:

- **GA4** as a custom event `llm_share_click`, with `llm_platform`, `page_type` and `page_topic` registered as custom dimensions (the URL is captured natively).
- Any secondary analytics destination already in use, with the same properties.

No PII is captured. No consent gating beyond the existing analytics category is required.

---

## 9. Expected impact

State this plainly with the client before the build is approved.

The only controlled A/B test published on this tactic — Search Engine Land, 13 April 2026, https://searchengineland.com/ai-buttons-474137 — found that:

- **Buttons alone reduced clicks by 17%.** Adding the button row on its own performed worse than the control.
- **Buttons paired with an on-page AI summary block increased clicks 36% and impressions 116%.**

The read is that the buttons are not the mechanism on their own. What moved the numbers was the page carrying a machine-readable summary that assistants could lift, with the buttons acting as the distribution prompt on top of it.

**Recommendation: ship the pairing, not the buttons alone.** If {{CLIENT_NAME}} is only approving the button row in this phase, treat the on-page AI summary block as the immediate follow-up and set the measurement window accordingly. Shipping buttons in isolation and measuring after four weeks is the scenario most likely to produce a negative result.

One test is not a law, and the sample was a single publisher. But it is the only controlled evidence that exists, and it points one way.

---

## 10. Quality Assurance

Before sign-off, verify on the following URLs, with the tag manager in preview mode.

{{QA_TABLE}}

For each rendered instance, confirm:

- Every button opens in a new tab with the URL-encoded prompt arriving intact at the destination.
- Any platform that requires a login lands the user on the sign-in screen with the prompt preserved through the round trip — verify in a logged-out private window, since this is the most common real-world state for an article reader.
- The `llm_share_click` event fires with the correct `llm_platform`, `page_url`, `page_type` and `page_topic`.
- At 375px width the button row wraps cleanly with no horizontal scroll.
- Keyboard Tab cycles every button with a visible focus ring; Enter activates the focused button.
- A screen reader announces the wrapper label and each button label correctly.
- The negative cases above render **no** widget at all — not a hidden or empty wrapper.

---

## 11. Rollback

If any issue arises after release — layout regression, analytics anomaly, CSP violation, brand complaint, or a provider removing its prefill parameter — removal is a single edit: delete `{{ROLLBACK_LINE}}` from the article layout template.

No data migration, no CMS schema change, no CDN purge.

To disable a single platform rather than the whole widget, set its `enabled` flag to `false` in the config block described in the Code Reference. That is also a one-line change.

---

## Sign-off

| Role | Name | Status |
| --- | --- | --- |
| Author | {{AGENCY_NAME}} | Drafted {{DATE}} |
| Recipient | {{CLIENT_CONTACT_NAME}} ({{CLIENT_NAME}}) | Pending |
| Brand / legal sign-off | {{CLIENT_NAME}} | Pending |
| Implementer | {{CLIENT_NAME}} engineering | Pending |

Questions on this brief: {{AGENCY_CONTACT_EMAIL}}

---

## Placeholder key

Every token the generating skill must substitute in this file.

| Token | Meaning |
| --- | --- |
| `{{AGENCY_NAME}}` | The member's agency name — the brief is white-labelled to them |
| `{{AGENCY_CONTACT_EMAIL}}` | Contact address for build questions |
| `{{CLIENT_NAME}}` | Client's full legal or trading name |
| `{{CLIENT_SHORT_NAME}}` | Short form used in running prose |
| `{{CLIENT_DOMAIN}}` | Bare domain, e.g. `example.com.au` |
| `{{CLIENT_CONTACT_NAME}}` | Named recipient on the client side |
| `{{DATE}}` | Brief date, ISO format |
| `{{DETECTED_STACK}}` | Framework detected by the site scan, e.g. "Nuxt 3 + Vue 3" |
| `{{DETECTED_CMS}}` | CMS detected by the site scan |
| `{{DETECTED_ANALYTICS}}` | Tag manager / analytics detected, e.g. "Google Tag Manager" |
| `{{EFFORT_ESTIMATE}}` | Effort estimate in dev-days for the detected stack |
| `{{PLATFORM_LIST}}` | Comma-separated enabled platform labels, in render order |
| `{{TOPIC_MAP_TABLE}}` | Markdown table: URL pattern / example / topic phrase |
| `{{OUT_OF_SCOPE_LIST}}` | Markdown bullet list of excluded route patterns |
| `{{INJECTION_POINT}}` | Stack-specific description of where the component mounts |
| `{{ARTICLE_TEMPLATE_PATH}}` | Path to the article layout template in the client's repo |
| `{{COMPONENT_NAME}}` | Component name for the detected framework |
| `{{WIDGET_HEADING}}` | Visible heading above the row, e.g. "Read this article with AI:" |
| `{{ICON_BASE_PATH}}` | Self-hosted icon directory, default `/icons/llm-share` |
| `{{BRAND_PRIMARY_HEX}}` | Extracted brand primary colour |
| `{{BRAND_SURFACE_HEX}}` | Extracted surface / background colour |
| `{{PROMPT_TEMPLATE}}` | Canonical prompt with `{URL}` and `{TOPIC}` slots |
| `{{PROMPT_EXAMPLE}}` | The same prompt with the worked example values filled in |
| `{{EXAMPLE_ARTICLE_URL}}` | A real in-scope article URL from the client's site |
| `{{EXAMPLE_TOPIC_PHRASE}}` | The topic phrase matching that example URL |
| `{{PAGE_TYPE_VALUES}}` | The `page_type` values in use, e.g. "`guide` or `news`" |
| `{{QA_TABLE}}` | Markdown table: URL / expected behaviour, including negative cases |
| `{{ROLLBACK_LINE}}` | The exact single line to delete, e.g. `<LlmShareButtons />` |
