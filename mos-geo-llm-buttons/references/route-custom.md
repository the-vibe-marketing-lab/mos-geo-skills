# Route: custom (non-WordPress)

Read this when recon returned anything other than WordPress. The deliverable is a **single
component** injected once into the article layout, plus a stylesheet, self-hosted icons, and one
tracking call.

Whatever the framework, the component does the same six things:

1. Read the current route to derive the page URL and the topic phrase.
2. Decide whether this route is in scope; render nothing if not.
3. Build the prompt from the canonical template (`prompt-policy.md`).
4. Render five buttons in fixed order: ChatGPT, Claude, Perplexity, Grok, AI Mode.
5. Set each `href` to the platform endpoint with the encoded prompt appended.
6. Fire the analytics event on click, **before** the tab opens.

## Deriving URL and topic from the route

The page URL must be the **canonical absolute URL**, not `window.location.href`. Query strings
and UTM parameters would otherwise end up inside the prompt, and the assistant would fetch a
tracking-decorated URL. Read the canonical link tag or the framework's route path joined to the
site origin.

The topic comes from a route-prefix lookup, not from page content:

```js
const TOPIC_MAP = {
  'health-insurance': 'Australian health insurance',
  'energy':           'Australian energy plans and bills',
  // ...one entry per in-scope first path segment
};

const EXCLUDED_SECOND = new Set(['guides', 'companies', 'calculators']);

export function resolveTopic(pathname) {
  const seg = pathname.split('/').filter(Boolean);
  if (seg.length < 2) return null;                    // landing page, not an article
  if (EXCLUDED_SECOND.has(seg[1])) return null;       // hub or listing page
  return TOPIC_MAP[seg[0]] ?? null;                   // unknown vertical, stay off
}
```

Returning `null` renders nothing. **Default to off** — an unmapped section is more likely to be
a new landing page than a new article vertical, and a widget on a checkout flow is a worse
failure than a missing widget on a guide.

## Nuxt 3 / Vue 3

A single SFC, `components/LlmShareButtons.vue`, injected once into the article layout
immediately after the byline block.

```vue
<script setup>
import { computed } from 'vue';
import { useRoute, useRuntimeConfig } from '#imports';
import { resolveTopic } from '~/utils/llm-share';

const props = defineProps({ brand: { type: String, required: true } });
const route = useRoute();
const config = useRuntimeConfig();

const topic = computed(() => resolveTopic(route.path));
const pageUrl = computed(() => new URL(route.path, config.public.siteUrl).href);
const prompt = computed(() => buildPrompt(props.brand, pageUrl.value));
const platforms = computed(() => PLATFORMS.map(p => ({ ...p, href: p.base + encodeURIComponent(prompt.value) })));
</script>
```

Guard the template with `v-if="topic"` so an out-of-scope route renders nothing at all rather
than an empty wrapper that still occupies vertical space.

## React / Next.js

Identical prop shape. It must be a client component — the click handler needs the browser:

```jsx
'use client';
import { usePathname } from 'next/navigation';
```

In the app router, place it in the article page component after the header. In the pages router,
`useRouter().asPath` replaces `usePathname()`. Do not reach for `next/script`; there is no
third-party script to load.

## Astro

Astro's default is zero JavaScript, and this widget almost qualifies. The hrefs are fully
computable at build time from the page's frontmatter — so render the anchors as static HTML in
a `.astro` component and ship no client bundle for the buttons themselves.

The tracking call is the only part that needs the client. Use a single narrow island, or a
delegated listener in the site's existing analytics bundle keyed on the wrapper class. Do not
hydrate the whole component for one event handler.

```astro
---
const { brand, pageUrl, topic } = Astro.props;
const prompt = buildPrompt(brand, pageUrl);
const platforms = PLATFORMS.map(p => ({ ...p, href: p.base + encodeURIComponent(prompt) }));
---
```

Hugo, Jekyll, and Eleventy follow the same shape: build the hrefs in the template from
front-matter, ship static anchors.

## Framework-free vanilla JS — the universal floor

For Shopify, Webflow, Squarespace, a bespoke PHP site, or a stack you could not identify. One
self-contained `<script>` plus one stylesheet, pasteable into a template or a tag manager.

```html
<div class="ai-share" aria-label="Read this article with an AI assistant"></div>
<script>
(function () {
  var el = document.querySelector('.ai-share');
  var topic = resolveTopic(location.pathname);
  if (!el || !topic) return;
  var url = (document.querySelector('link[rel=canonical]') || {}).href || location.origin + location.pathname;
  var prompt = buildPrompt(BRAND, url);
  el.innerHTML = PLATFORMS.map(function (p) {
    return '<a class="ai-share__btn" data-platform="' + p.id + '" target="_blank" rel="noopener noreferrer" href="' +
           p.base + encodeURIComponent(prompt) + '">' + p.mark + '<span>' + p.label + '</span></a>';
  }).join('');
})();
</script>
```

Note the wrapper exists in the HTML before the script runs. That is the no-layout-shift
requirement below.

## Link behaviour

Every button is an `<a>` with `target="_blank" rel="noopener noreferrer"`. Not a `<button>`
calling `window.open()`:

- An anchor is middle-clickable, right-clickable, and copyable. Readers expect that.
- `window.open()` from a handler gets popup-blocked in some configurations.
- Screen readers announce a link as a link.

`noopener` prevents the opened tab reaching back through `window.opener`; `noreferrer` is
belt-and-braces for referrer leakage. Keep both.

## Tracking

Fire before the tab opens, on the same click:

```js
function track(platform, pageUrl, pageType, pageTopic) {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    event: 'llm_share_click',
    llm_platform: platform,   // chatgpt | claude | perplexity | grok | googleai
    page_url: pageUrl,
    page_type: pageType,      // guide | media | article
    page_topic: pageTopic
  });
}
```

**Order matters.** The new tab takes focus immediately, and a push queued after the navigation
call can be lost — particularly on mobile Safari. Push first, then let the anchor's default
behaviour open the tab. Do not `preventDefault()` and re-open manually to "guarantee" ordering;
that reintroduces the popup-blocker problem.

The `dataLayer` guard (`|| []`) is not optional. On a page where GTM has not loaded yet, an
unguarded push throws and the button click surfaces a console error to the reader.

If recon found no GTM and no GA4, do not ship a `dataLayer` push into the void — but do not stop
there either. Deferring to "the client's analytics owner" only works when you are handing over a
brief; on an in-house install you *are* the analytics owner, and that advice is a dead end.

**Write an adapter, not an assumption.** Fire the same four-parameter event into whatever the
site actually runs, guarding each sink so a missing one is a no-op rather than a thrown error:

- `window.dataLayer` — push only if `Array.isArray(window.dataLayer)`. Never create it yourself:
  a decoy `dataLayer` makes a later GTM install believe it already has history.
- The site's own analytics client, whatever it is. Read its loaded script to find the real call
  signature rather than trusting the vendor docs — these get renamed. On thevibemarketinglab.com
  the DataFast client exposes `window.datafast(goalName, properties)`, which is only discoverable
  by reading the minified source.
- `navigator.sendBeacon` to a first-party endpoint, where one exists.

Wrap the whole block in `try/catch` and fire it before the tab opens. Tracking that throws must
never cost the reader their click — the event is the least important thing happening.

## No layout shift

The widget must occupy its final dimensions on first paint. Two rules:

- The wrapper exists in the server-rendered HTML with an explicit `min-height` matching one
  button row (icon 16px + padding + border ≈ 40px), so a client-side render does not push the
  article body down.
- Icons are inline SVG or self-hosted SVG with explicit `width` and `height` attributes. An
  `<img>` without dimensions reflows the row when it loads.

Measure it: the article's CLS on a representative page should not move.

## Mobile

At 375px the five buttons wrap to two lines with **no horizontal scroll**. `flex-wrap: wrap` on
the row plus a gap, and no fixed widths on the buttons. Test at 375px specifically — it is the
narrowest viewport worth supporting and it is where a five-item row breaks.

If the row still overflows, drop the labels to icon-only below 380px rather than shrinking the
tap targets. Minimum tap target stays 44×44px.

## Accessibility

- **Wrapper** carries `aria-label="Read this article with an AI assistant"` on a `<nav>` or a
  `<div role="group">`. A bare div of links announces as noise.
- **Each button** carries its own accessible name: "Summarise this article with ChatGPT", not
  "ChatGPT". The visible label can stay short; use `aria-label` for the full phrase.
- **Keyboard:** Tab reaches all five in DOM order, Enter activates, and the focus ring is
  visible against the client's background. Do not `outline: none` without a replacement —
  `:focus-visible` with a 2px offset ring is the minimum.
- **Icons** are decorative when a text label is present: `aria-hidden="true"` on the SVG so the
  name is not announced twice.
- Lighthouse Accessibility on a representative article should not regress by more than 2 points.

## Icons — self-host, always

Every SVG is served from the client's own domain or CDN, at a stable path like
`/icons/llm-share/{platform}.svg`.

Third-party SVG mirrors get taken down at the brand owner's request. This is not hypothetical:
the OpenAI mark has already been pulled from one widely-used mirror, and any site referencing it
now renders a broken image next to four working ones.

**Inline the ChatGPT mark directly in the component.** It is the most frequently targeted of the
five and inlining removes the failure mode entirely.

In the default styling the marks are monochrome and inherit the client's text colour via
`fill: currentColor`, which is what makes one CSS token swap restyle the whole row. See the
styling section of `../SKILL.md` for why platform brand colours are opt-in rather than default.

## Rollback

Deleting the single `<LlmShareButtons />` line from the article layout removes the widget
completely. No data migration, no CMS schema change, no CDN purge. Say this explicitly in the
brief — it is what gets a cautious engineering lead to approve the change.
