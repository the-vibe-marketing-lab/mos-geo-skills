# Recon — detecting the stack

`scripts/recon.sh <url>` runs this ladder automatically. Read this file when it comes back
ambiguous, when the site is a client-rendered SPA, or when you need to work a tier by hand.

The ladder is ordered by cost. Stop at the first tier that gives an unambiguous answer — a
`meta generator` tag naming WordPress ends the investigation, and firing up a browser to
confirm it is wasted time.

## Tier 0 — Response headers

```bash
curl -sIL --max-time 15 -A "Mozilla/5.0" https://client.com/
```

Read these, in this order:

| Header | Tells you |
| --- | --- |
| `server` | `nginx`, `Apache`, `cloudflare`, `Vercel`, `Netlify`, `AmazonS3` |
| `x-powered-by` | `PHP/8.x` (likely WordPress), `Next.js`, `Express`, `Shopify` |
| `x-vercel-id` / `x-vercel-cache` | Vercel — pairs with Next.js or Astro |
| `x-nextjs-cache` / `x-nextjs-prerender` | Next.js, definitively |
| `cf-ray` | Cloudflare in front — tells you nothing about the origin, do not stop here |
| `x-litespeed-cache` / `x-cache-enabled` | LiteSpeed, near-always WordPress hosting |
| `link` | A `rel="https://api.w.org/"` value is a WordPress REST discovery link |

Follow redirects (`-L`). A surprising number of sites answer the apex differently from `www`,
and the stack fingerprints live on whichever one actually serves content.

## Tier 1 — Generator meta

```bash
curl -sL --max-time 20 -A "Mozilla/5.0" https://client.com/ | grep -i '<meta name="generator"'
```

The single highest-signal line in the document when it exists. `WordPress 6.x`, `Astro v7.1.3`,
`Hugo 0.x`, `Drupal 10`, `Wix.com Website Builder`. Many WordPress sites strip it for security
theatre, so absence proves nothing.

## Tier 2 — Asset-path fingerprints

Grep the raw HTML for path markers. These survive minification and are hard to remove:

| Marker | Stack |
| --- | --- |
| `/_next/static/` | Next.js |
| `/_astro/` | Astro |
| `/_nuxt/` | Nuxt |
| `/wp-content/` · `/wp-includes/` | WordPress |
| `/wp-json/` | WordPress with REST enabled |
| `cdn.shopify.com` · `shopify-features` | Shopify |
| `assets.website-files.com` · `wf-` classes | Webflow |
| `static1.squarespace.com` · `Static.SQUARESPACE_CONTEXT` | Squarespace |
| `static.parastorage.com` · `wix-` | Wix |
| `/sites/default/files/` | Drupal |

Two markers agreeing is a confirmed stack. One marker plus a matching header is confirmed. One
marker alone on an otherwise silent page is a hypothesis — carry it forward as `[VERIFY]`.

## Tier 3 — The WordPress probe

If anything at all points at WordPress, confirm it and learn what you can write to:

```bash
curl -s --max-time 15 https://client.com/wp-json/ | head -c 400
```

A JSON body with a `namespaces` array containing `wp/v2` is proof. It also tells you:

- **The REST API is reachable**, which is the fallback delivery route if WPVibe is unavailable.
- **Which plugins expose namespaces** — `elementor/`, `bricks/`, `yoast/`, `wpvibe/`. An
  Elementor or Bricks namespace is a strong hint that content is built outside `the_content`,
  which pushes you toward the shortcode escape hatch in `route-wordpress.md`.

A 401 or 403 means REST is locked down; that is a real constraint to record, not a detection
failure. WordPress is still confirmed.

## Tier 4 — Analytics detection

The tracking spec has to land in whatever the client already runs, so find it before you write
the code:

| Pattern in the HTML | Stack |
| --- | --- |
| `GTM-` followed by 6–8 alphanumerics | Google Tag Manager container |
| `G-` followed by 10 alphanumerics | GA4 measurement ID |
| `gtag(` with no GTM container | GA4 direct, no tag manager |
| `cdn.segment.com` · `analytics.load(` | Segment |
| `cdn.mxpnl.com` · `mixpanel.init(` | Mixpanel |
| `plausible.io/js` · `cdn.usefathom.com` | Privacy-first analytics — no dataLayer, needs a custom event call |

GTM present means the `dataLayer.push()` spec works as written. No GTM and no GA4 means the
tracking section of the brief becomes a request to the client rather than a code snippet — say
so plainly instead of shipping a push into an undefined `dataLayer`.

## Tier 5 — CSP capture

```bash
curl -sI --max-time 15 https://client.com/ | grep -i 'content-security-policy'
```

A restrictive `script-src` changes what the widget can be:

- `script-src` without `'unsafe-inline'` — no inline `onclick`, no inline `<script>`. The
  tracking call has to live in a bundled file with an event listener attached.
- `img-src 'self'` — confirms the self-hosted-icons decision. External SVG would be blocked.
- `connect-src` restrictions do not matter here; the widget makes no fetches.
- No CSP header at all — check for a `<meta http-equiv="Content-Security-Policy">` before
  concluding there is none.

Record the finding either way. "No CSP present" in the brief saves a dev fifteen minutes.

## Tier 6 — Sitemap discovery

Feeds the Stage 4 scope map:

```bash
curl -s https://client.com/robots.txt | grep -i sitemap
curl -sI https://client.com/sitemap.xml https://client.com/sitemap_index.xml
```

Treat an advertised sitemap as a hint, not a fact — robots.txt frequently points at a sitemap
that 404s. Fall through to `/sitemap_index.xml`, `/sitemap-index.xml`, `/wp-sitemap.xml`
(WordPress core), `/sitemap.xml.gz`, and `/page-sitemap.xml` (Yoast) before giving up and
crawling the nav.

What you want out of it is the **shape of the URL space**, not every URL: which first path
segments exist, how many pages sit under each, and which segments are listing pages rather than
articles. Twenty sample URLs per segment is plenty.

## The browser tier — when curl is not enough

Escalate when the HTML body is a near-empty shell (a `<div id="root">` and a script tag), when
class names look like `css-1x2y3z4` or `sc-abc123` (CSS-in-JS), or when the palette has to come
out of computed styles rather than a stylesheet.

**Interceptor is not installed on this Windows machine.** The browser tier here is the
`mcp__Claude_Browser__*` tools. Navigate to a representative article page, then use
`javascript_tool` for the two things the DOM alone cannot give you:

**Computed styles** — the actual rendered values on real elements:

```js
const el = document.querySelector('h1');
const s = getComputedStyle(el);
JSON.stringify({ color: s.color, font: s.fontFamily, size: s.fontSize, weight: s.fontWeight });
```

Sample at least an `h1`, a body `p`, the primary button or CTA link, and `document.body` for
the surface colour.

**Stylesheet serialisation** — CSS-in-JS rules are injected at runtime and **never exist as
text anywhere in the DOM**, so scraping `<style>` tags misses them entirely:

```js
[...document.styleSheets]
  .flatMap(sheet => { try { return [...sheet.cssRules] } catch { return [] } })
  .map(r => r.cssText)
  .filter(t => /--|#[0-9a-f]{3,8}/i.test(t))
  .slice(0, 200)
```

The `try/catch` matters — cross-origin stylesheets throw on `cssRules` access and one throw
kills the whole expression.

Also read `:root` custom properties directly, which is where a well-built site keeps its
palette:

```js
[...document.querySelectorAll('*')].length; // sanity check the page actually rendered
getComputedStyle(document.documentElement).cssText
```

## Worked example — thevibemarketinglab.com

Tiers 0 and 1 alone settle it. The response headers carry `x-vercel-id`, so the host is Vercel;
the generator meta reads `Astro v7.1.3`, so the framework is Astro. No `/wp-content/`, no
`/_next/`, no REST namespace. Route: **custom**, Astro section of `route-custom.md`. Total cost:
two curl calls, no browser.

The palette comes straight out of CSS custom properties, which is the best case — these are the
site's own token names, so the generated widget inherits future rebrands for free:

```
--ember: #c96442    primary / action
--ink:   #0d0b0a    text
--paper: #faf7f2    surface
--sun:   #f4c24b    accent
```

Type: **Bricolage Grotesque** for headings, **Figtree** for body.

Because the tokens exist, the generated CSS references `var(--ember)` with a hex fallback
rather than hardcoding `#c96442`. On a site with no custom properties you hardcode the extracted
values and say so in the brief, so the client's dev knows to swap them for their own tokens.
