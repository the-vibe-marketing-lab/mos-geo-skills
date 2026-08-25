# LLM Share Buttons — Code Reference

**Client:** {{CLIENT_NAME}}
**Prepared by:** {{AGENCY_NAME}}
**Date:** {{DATE}}
**Target stack:** {{DETECTED_STACK}}
**Companion document:** LLM Share Buttons — Implementation Brief

This document holds the full source. It is kept separate from the brief so the brief stays readable for non-developers. Read the brief first for scope, placement and success criteria; use this document to build.

---

## 1. Endpoints and parameters

Generated from the verified endpoint contract, `platform-endpoints.json`, **verified {{ENDPOINTS_VERIFIED_ON}}**.

{{ENDPOINT_TABLE}}

**Reading the table.**

- **Auto-submits** — the assistant sends the prompt the instant the page loads, with no chance for the reader to edit it. Keep prompts short and self-contained; assume the reader never sees the composer.
- **Requires login** — a logged-out reader hits an auth wall instead of an answer. Most article readers are logged out. Weigh this before enabling a login-gated platform on a consumer-facing site; the prompt does survive the sign-in round trip on the platforms tested, but the drop-off does not.
- **Mode** — `prefill` builds a link. `clipboard` means the platform has **no working prefill parameter**: copy the prompt to the clipboard, open the platform in a new tab, and show a "prompt copied — paste it in" toast. Clipboard mode needs a secure context (HTTPS) for `navigator.clipboard`, with a hidden-textarea `execCommand` shim as fallback.

**Do not add parameters that are not in the table.** Several parameters circulating in GEO write-ups do not work: Gemini has no functioning prefill parameter on any of `?q=`, `?text=`, `?prompt=` or `?prompt_text=` (the composer stays blank), and Microsoft Copilot's prefill was removed outright in January 2026 after a one-click data-exfiltration disclosure — its parameter is now stripped on redirect. Neither should appear in the build.

> **Stability warning.** {{STABILITY_WARNING}}

---

## 2. The config block

Everything platform-specific lives here. This is the file to edit when a provider changes or breaks.

```js
// {{CONFIG_FILE_PATH}}
// Endpoint contract verified {{ENDPOINTS_VERIFIED_ON}}. Re-verify before each build.

export const LLM_PLATFORMS = [
{{PLATFORM_CONFIG_JS}}
];

// Order is render order. Set `enabled: false` to drop a platform without a code change.
export const ENABLED_PLATFORMS = LLM_PLATFORMS.filter((p) => p.enabled);
```

---

## 3. The prompt builder

```js
// {{PROMPT_HELPER_PATH}}

export const PROMPT_TEMPLATE =
  '{{PROMPT_TEMPLATE_JS}}';

/**
 * Build the prompt text for one article.
 * @param {string} url   Canonical, absolute article URL.
 * @param {string} topic Topic phrase for the article's section.
 * @returns {string} Plain, un-encoded prompt text.
 */
export function buildPrompt(url, topic) {
  return PROMPT_TEMPLATE.replace(/{URL}/g, url).replace(/{TOPIC}/g, topic);
}

/**
 * Build the destination href for one platform.
 * The prompt is encoded exactly once — never pre-encode the input.
 * @param {object} platform Entry from LLM_PLATFORMS.
 * @param {string} prompt   Output of buildPrompt().
 * @returns {string|null}   Absolute URL, or null for clipboard-mode platforms.
 */
export function buildHref(platform, prompt) {
  if (platform.mode !== 'prefill' || !platform.param) return null;
  const url = new URL(platform.endpoint);
  url.searchParams.set(platform.param, prompt);
  Object.entries(platform.extraParams || {}).forEach(([k, v]) => {
    url.searchParams.set(k, v);
  });
  return url.toString();
}
```

`URL.searchParams.set()` percent-encodes the value for you. If you build the string by hand instead, use `encodeURIComponent(prompt)` — once, never twice. Double-encoding is the most common cause of a prompt arriving as literal `%20`s.

---

## 4. The route-to-topic helper

Derives the topic phrase and page type from the current path, and decides whether the widget renders at all.

```js
// {{TOPIC_HELPER_PATH}}

export const TOPIC_MAP = {
{{TOPIC_MAP_JS}}
};

// Second-segment keywords that mark a hub, listing or tool page.
export const EXCLUDED_SEGMENTS = {{EXCLUDED_SEGMENTS_JS}};

// Path prefixes that are never article pages.
export const EXCLUDED_PREFIXES = {{EXCLUDED_PREFIXES_JS}};

/**
 * @param {string} path Pathname only, e.g. '/health-insurance/dentures/'.
 * @returns {{topic: string, pageType: string}|null} null means: do not render.
 */
export function resolveArticleContext(path) {
  const segments = path.split('/').filter(Boolean);

  // Homepage and single-segment landing pages are out of scope.
  if (segments.length < 2) return null;

  const [section, second] = segments;

  if (EXCLUDED_PREFIXES.includes(section)) return null;
  if (EXCLUDED_SEGMENTS.includes(second)) return null;

  const entry = TOPIC_MAP[section];
  if (!entry) return null;

  return { topic: entry.topic, pageType: entry.pageType };
}
```

Render the component only when `resolveArticleContext()` returns non-null. Return nothing at all on the negative cases — not an empty wrapper, which still costs layout and shows up in the accessibility tree.

---

## 5. Component source

Target framework: **{{FRAMEWORK}}**. Component name: `{{COMPONENT_NAME}}`.

```{{COMPONENT_LANG}}
{{COMPONENT_SOURCE}}
```

**Injection.** {{INJECTION_POINT}}

```{{TEMPLATE_LANG}}
{{INJECTION_SNIPPET}}
```

Removing that single line removes the widget entirely.

---

## 6. Stylesheet

All colours are CSS custom properties scoped to the wrapper, seeded from {{CLIENT_SHORT_NAME}}'s extracted palette. Override any token from the wrapper class without touching the component.

Buttons use the **client's** brand palette. Platform identity is carried by the wordmark, not by reproducing each provider's brand colour — see §6 of the brief for the compliance reasoning.

```css
/* {{STYLESHEET_PATH}} */

.llm-share {
  /* Palette — {{CLIENT_SHORT_NAME}} */
  --llm-primary: {{BRAND_PRIMARY_HEX}};
  --llm-primary-hover: {{BRAND_PRIMARY_HOVER_HEX}};
  --llm-on-primary: {{BRAND_ON_PRIMARY_HEX}};
  --llm-surface: {{BRAND_SURFACE_HEX}};
  --llm-border: {{BRAND_BORDER_HEX}};
  --llm-text: {{BRAND_TEXT_HEX}};
  --llm-text-muted: {{BRAND_MUTED_HEX}};
  --llm-focus: {{BRAND_FOCUS_HEX}};

  /* Shape and type */
  --llm-radius: {{BRAND_RADIUS}};
  --llm-font: {{BRAND_FONT_STACK}};
  --llm-gap: 0.5rem;
  --llm-btn-min-height: 44px; /* accessibility floor — do not lower */

  font-family: var(--llm-font);
  margin: 1.25rem 0 1.75rem;
}

.llm-share__heading {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--llm-text-muted);
  margin: 0 0 var(--llm-gap);
}

.llm-share__list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--llm-gap);
  margin: 0;
  padding: 0;
  list-style: none;
}

.llm-share__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: var(--llm-btn-min-height);
  padding: 0.5rem 0.875rem;
  border: 1px solid var(--llm-border);
  border-radius: var(--llm-radius);
  background: var(--llm-surface);
  color: var(--llm-text);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.2;
  text-decoration: none;
  cursor: pointer;
  transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
}

.llm-share__btn:hover {
  background: var(--llm-primary);
  border-color: var(--llm-primary);
  color: var(--llm-on-primary);
}

.llm-share__btn:focus-visible {
  outline: 3px solid var(--llm-focus);
  outline-offset: 2px;
}

.llm-share__icon {
  width: 18px;
  height: 18px;
  flex: none;
  color: currentColor; /* glyphs use fill/stroke: currentColor */
}

@media (prefers-reduced-motion: reduce) {
  .llm-share__btn { transition: none; }
}

@media (max-width: 420px) {
  .llm-share__btn { flex: 1 1 auto; justify-content: center; }
}
```

---

## 7. Tracking snippet

Fires once per click, **before** the tab opens. Do not `preventDefault()` — the anchor's native new-tab behaviour is what keeps the popup blocker satisfied.

```js
// {{TRACKING_HELPER_PATH}}

export function trackLlmShareClick({ platformId, pageUrl, pageType, pageTopic }) {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    event: 'llm_share_click',
    llm_platform: platformId,
    page_url: pageUrl,
    page_type: pageType,
    page_topic: pageTopic,
  });
}
```

Bind it to the anchor's `click` handler. The `dataLayer.push` is synchronous, so it completes before the browser opens the new tab.

---

## 8. Tag manager and GA4 configuration

1. **Create the trigger.** {{ANALYTICS_CONTAINER}} → Triggers → New → Custom Event. Event name: `llm_share_click`. Fires on: All Custom Events.
2. **Create four data layer variables**, one each for `llm_platform`, `page_url`, `page_type`, `page_topic`. Data Layer Variable Name must match the key exactly.
3. **Create the GA4 event tag.** Tag type: Google Analytics: GA4 Event. Configuration tag: the existing {{CLIENT_SHORT_NAME}} GA4 config. Event Name: `llm_share_click`. Event Parameters: map the four variables to parameter names `llm_platform`, `page_url`, `page_type`, `page_topic`. Trigger: the custom event trigger from step 1.
4. **Register the custom dimensions in GA4.** Admin → Custom definitions → Create custom dimension, scope Event, for `llm_platform`, `page_type` and `page_topic`. GA4 only collects a parameter into reports once it is registered, and registration is **not** retroactive — do this before launch or the first weeks of data are unreportable.
5. **Verify in Preview mode.** Load a representative article, click each button, and confirm one event per click with all four parameters populated. Use Chrome DevTools with "Preserve log" enabled so the new tab does not clear the console.
6. **Publish the container.**

Reporting suggestion: build one GA4 exploration with `llm_platform` and `page_topic` as dimensions and event count as the metric. That answers both "which assistant do readers pick" and "which sections drive shares" from one report.

---

## 9. Maintenance

**These endpoints are undocumented surfaces, and the 2026 trend is removal, not addition.**

- Microsoft Copilot's prefill parameter was **killed in January 2026** after a one-click data-exfiltration attack was disclosed. It is now stripped on redirect.
- Anthropic patched a prompt-injection vector through its own parameter.
- Microsoft has published security research treating this entire pattern as an attack class.
- Providers that never supported prefill are widely documented as if they do — Gemini's `?prompt_text=` is the best-known example, and it does not work.

Practical consequences for this build:

1. **Never hardcode these URLs into post content, a CMS field, or a database.** Render them at runtime from the single config block in §2. A provider going dark then costs one line, not a content migration.
2. **Re-verify before every build and on a quarterly cadence after launch.** Verification means live navigation in a real browser session — `curl` is not sufficient, because every one of these apps is a client-rendered SPA that returns HTTP 200 for any query string, whether or not the parameter is consumed.
3. **Fail soft.** If a platform's endpoint 404s or strips the parameter, set `enabled: false` rather than leaving a button that lands readers on an error page.
4. **Watch the login walls.** A platform that was open to logged-out visitors can gate later. That converts a working button into a dead end without any code changing.
5. **Keep the prompt a plain summarise-and-cite request.** Persistence or "remember this permanently" phrasing is what triggered the security response across this pattern in the first place.

---

## Placeholder key

| Token | Meaning |
| --- | --- |
| `{{AGENCY_NAME}}` | Member's agency name |
| `{{CLIENT_NAME}}` | Client's full name |
| `{{CLIENT_SHORT_NAME}}` | Short form used in prose |
| `{{DATE}}` | Document date, ISO format |
| `{{DETECTED_STACK}}` | Framework detected by the site scan |
| `{{FRAMEWORK}}` | Framework the component is emitted for |
| `{{COMPONENT_NAME}}` | Component name |
| `{{COMPONENT_LANG}}` | Fence language for the component block (`vue`, `jsx`, `php`, `html`) |
| `{{COMPONENT_SOURCE}}` | Full component source for the detected framework |
| `{{TEMPLATE_LANG}}` | Fence language for the injection snippet |
| `{{INJECTION_SNIPPET}}` | The exact line(s) to add to the article template |
| `{{INJECTION_POINT}}` | Prose description of where the component mounts |
| `{{CONFIG_FILE_PATH}}` | Path for the platform config block |
| `{{PROMPT_HELPER_PATH}}` | Path for the prompt builder |
| `{{TOPIC_HELPER_PATH}}` | Path for the route-to-topic helper |
| `{{TRACKING_HELPER_PATH}}` | Path for the tracking helper |
| `{{STYLESHEET_PATH}}` | Path for the stylesheet |
| `{{ENDPOINT_TABLE}}` | Markdown table generated from `platform-endpoints.json` — platform, endpoint, param, extra params, mode, auto-submits, requires login |
| `{{ENDPOINTS_VERIFIED_ON}}` | `verified_on` date from `platform-endpoints.json` |
| `{{STABILITY_WARNING}}` | `stability_warning` string from `platform-endpoints.json`, quoted verbatim |
| `{{PLATFORM_CONFIG_JS}}` | JS array literal entries for the enabled platforms |
| `{{PROMPT_TEMPLATE_JS}}` | Canonical prompt as a single-quoted JS string with `{URL}` / `{TOPIC}` slots |
| `{{TOPIC_MAP_JS}}` | JS object entries mapping route section to `{ topic, pageType }` |
| `{{EXCLUDED_SEGMENTS_JS}}` | JS array of excluded second-segment keywords |
| `{{EXCLUDED_PREFIXES_JS}}` | JS array of excluded path prefixes |
| `{{ANALYTICS_CONTAINER}}` | Tag manager product name, e.g. "Google Tag Manager" |
| `{{BRAND_PRIMARY_HEX}}` | Extracted brand primary |
| `{{BRAND_PRIMARY_HOVER_HEX}}` | Hover / darker primary |
| `{{BRAND_ON_PRIMARY_HEX}}` | Foreground colour on primary |
| `{{BRAND_SURFACE_HEX}}` | Button surface / page background |
| `{{BRAND_BORDER_HEX}}` | Border colour |
| `{{BRAND_TEXT_HEX}}` | Body text colour |
| `{{BRAND_MUTED_HEX}}` | Muted / secondary text |
| `{{BRAND_FOCUS_HEX}}` | Focus ring colour |
| `{{BRAND_RADIUS}}` | Border radius, e.g. `8px` |
| `{{BRAND_FONT_STACK}}` | Client font stack with system fallbacks |
