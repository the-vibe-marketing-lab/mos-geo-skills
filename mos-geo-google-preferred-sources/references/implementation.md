# Implementation by stack

Read the section for the stack `check` reported, plus **The custom button** (every stack uses it
unless the user picked Google's standard button). The markup, CSS and script all come from
`assets/button.html`, between its `SNIPPET START` / `SNIPPET END` markers. Don't retype them from
memory.

Three rules hold on every stack:

1. `publisher.js` loads **once per page**, and only on pages that show the button.
2. The button's `href` is the deeplink for the **host**, never a path:
   `https://www.google.com/preferences/source?q=<host>`.
3. If the site sends a Content-Security-Policy, the same change must:
   - add `https://news.google.com` to `script-src` (or `script-src-elem`);
   - allow the inline wiring block: a nonce or hash the site already uses, or `'unsafe-inline'`.
     If the policy has `'strict-dynamic'`, a host allowance alone does nothing and the
     `publisher.js` tag needs the nonce too;
   - leave `frame-src` / `connect-src` permissive enough for Google's popup. Google doesn't
     document what the popup needs, so click-test it in a browser with DevTools open and add
     whatever the console reports as blocked.
   Without these the popup never opens and the button silently behaves as a plain link.

---

## The custom button

- CSS: the `SNIPPET: CSS` block, with the site's tokens filled in. Prefer the site's own CSS
  custom properties (`var(--color-primary)`) over pasted hexes when the article pages define them.
- Head: the manual-mode `publisher.js` tag.
- Markup: one `<aside class="ps-cta">` per placement, each with its own `data-placement`
  (`in-article`, `end-of-article`, `footer`).
- Script: the `SNIPPET: SCRIPT` block, once per page, after the markup.

**Standard button instead?** Head: the plain `publisher.js` tag (no `preferred-sources-control`).
Markup: `<div google-add-preferred-source-btn data-theme="light"></div>` at each placement. No
script block. Tracking isn't possible on Google's rendered button, so say so.

---

## WordPress

Ship **one plugin file**, `preferred-source-button/preferred-source-button.php`, not a theme
edit: it works on classic and block themes, survives theme switches, and rolls back in one click.
Install via the WordPress MCP when connected (WPVibe or mcp-adapter; disclose to the owner that
WPVibe is a hosted relay holding an application password before connecting), otherwise hand over
the file for Plugins → Add New → Upload.

What the plugin does:

- `wp_head`: prints the manual-mode `publisher.js` tag and the CSS, **only when `is_singular('post')`**
  (widen deliberately if articles use a custom post type).
- Shortcode `[preferred_source placement="in-article"]`: the editor drops it after the post's best
  paragraph. **The editor's choice always wins.**
- `the_content` filter at priority **20** (after `wpautop` and shortcodes), guarded with
  `is_singular('post') && in_the_loop() && is_main_query()`:
  - if the post's **raw** content contains the shortcode, add nothing mid-article. Check
    `get_post()->post_content`, not `$content`: by priority 20 shortcodes (priority 11) have
    already been expanded, so `has_shortcode( $content, ... )` is always false;
  - otherwise insert the in-article button after the paragraph at roughly 40% of the post (never
    before the 3rd paragraph; skip posts under 5 paragraphs);
  - append the quiet end-of-article button.
- `wp_footer`: prints the script block, same conditional.

Skeleton (fill from `assets/button.html`; keep the guards exactly):

```php
<?php
/**
 * Plugin Name: Preferred Source Button
 * Description: Adds Google's "Add as a preferred source" button to single posts.
 * Version:     1.0.0
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

const PSB_HOST = '{{HOST}}'; // eligible host only, no path

function psb_is_target() {
    return is_singular( 'post' );
}

function psb_button( $placement = 'in-article' ) {
    $href  = 'https://www.google.com/preferences/source?q=' . rawurlencode( PSB_HOST );
    $quiet = ( 'in-article' === $placement ) ? '' : ' ps-cta--quiet';
    $note  = ( 'in-article' === $placement ) ? '<p class="ps-cta__note">' . esc_html( '{{NOTE}}' ) . '</p>' : '';
    return sprintf(
        '<aside class="ps-cta%1$s" data-placement="%2$s">%3$s<a class="ps-cta__btn js-preferred-source" data-placement="%2$s" href="%4$s" rel="noopener">%5$s</a></aside>',
        $quiet, esc_attr( $placement ), $note, esc_url( $href ), esc_html( '{{LABEL}}' )
    );
}

add_shortcode( 'preferred_source', function ( $atts ) {
    $atts = shortcode_atts( array( 'placement' => 'in-article' ), $atts );
    return psb_button( $atts['placement'] );
} );

add_action( 'wp_head', function () {
    if ( ! psb_is_target() ) { return; }
    echo '<script async preferred-sources-control="manual" src="https://news.google.com/swg/js/v1/publisher.js"></script>' . "\n";
    echo '<style>/* SNIPPET: CSS from assets/button.html */</style>' . "\n";
} );

add_filter( 'the_content', function ( $content ) {
    if ( ! psb_is_target() || ! in_the_loop() || ! is_main_query() ) {
        return $content;
    }
    $post = get_post();
    if ( ! $post || ! has_shortcode( $post->post_content, 'preferred_source' ) ) {
        $parts = explode( '</p>', $content );
        $count = count( $parts ) - 1; // number of closed paragraphs
        if ( $count >= 5 ) {
            $after = max( 3, (int) round( $count * 0.4 ) );
            $out   = '';
            foreach ( $parts as $i => $part ) {
                $out .= $part;
                if ( $i < $count ) {
                    $out .= '</p>';
                    if ( $i + 1 === $after ) {
                        $out .= psb_button( 'in-article' );
                    }
                }
            }
            $content = $out;
        }
    }
    return $content . psb_button( 'end-of-article' );
}, 20 );

add_action( 'wp_footer', function () {
    if ( ! psb_is_target() ) { return; }
    echo "<script>/* SNIPPET: SCRIPT from assets/button.html */</script>\n";
} );
```

Before you ship, check that string surgery on your theme's markup: on a test post, the button must
land between two paragraphs, never inside a list, quote or table. If the theme's content isn't
plain `<p>` runs, drop the automatic insert and rely on the shortcode.

Page builders (Elementor, Bricks, Divi): `the_content` may not fire in builder templates. Use the
shortcode in a Shortcode widget in the single-post template, and add the footer spot the same way.
Elementor users who'd rather not install a plugin can put the head tag and script in Elementor →
Custom Code, and the button in an HTML widget.

**WordPress QA:** one `publisher.js` per post (the theme or an SEO plugin may already add one), no
button in `/feed/`, none in `/wp-json/wp/v2/posts/<id>` `content.rendered`, none on pages,
archives or the front page. On block themes, check the automatic insert actually appears:
`in_the_loop()` returns false inside the post-content block before WordPress 6.4, so on older
installs rely on the shortcode.

**Rollback:** deactivating the plugin removes the head tag, the automatic buttons and the script.
Any `[preferred_source]` shortcodes editors added stay in those posts as literal text. Before
deactivating, either remove them (find them with
`wp post list --s='[preferred_source' --fields=ID,post_title`) or leave behind a one-line
mu-plugin that keeps the shortcode registered as a no-op:
`add_shortcode( 'preferred_source', '__return_empty_string' );`

---

## Next.js (App Router or Pages)

- Put the script in the **article layout or article page only**, with `next/script`:
  `<Script src="https://news.google.com/swg/js/v1/publisher.js" strategy="afterInteractive" preferred-sources-control="manual" />`.
  `next/script` passes unknown props through as attributes. Confirm that in the rendered HTML with `verify`.
- A component `PreferredSourceButton({ placement })` renders only the `<aside>` markup. It can
  be a server component: it has no state and no handlers.
- The wiring is the `SNIPPET: SCRIPT` block, loaded **once** in the article layout (a
  `next/script` with `id="preferred-source-wiring"` and `strategy="afterInteractive"`, with the
  block as its children). It already uses one delegated document listener behind a
  `window.__preferredSourceInit` guard, so it catches buttons that render later, and React
  StrictMode or a second mount can't double-bind it. Don't attach per-button handlers in
  `useEffect`.
- Place `<PreferredSourceButton placement="in-article" />` after the strongest section in MDX
  or CMS-rendered content (an MDX component editors can move is best), and `end-of-article` after
  the body.
- CSS goes in the site's existing styling system (CSS module, Tailwind classes mapped to the
  site's tokens, or global CSS).

Because the button renders client-side on some setups, `verify` may say NEEDS BROWSER. Click-test it.

## Astro, Nuxt, SvelteKit, Hugo, Eleventy, Jekyll, plain HTML

Same shape as Next: head tag in the article layout only, one component or partial for the
`<aside>`, the script block once in the article layout.

**Astro:** Astro processes (bundles and hoists) plain `<script>` tags by default. Add
`is:inline` explicitly so both tags ship exactly as written. Put the head tag in the article layout's `<head>` as
`<script is:inline async preferred-sources-control="manual" src="https://news.google.com/swg/js/v1/publisher.js"></script>`,
and mark the script block `is:inline` too. The page then ships exactly Google's markup, and
`verify` can read it from the server HTML. On static generators, a partial/include
per placement is enough, and editors add the in-article include after the best section.

## Webflow, Shopify, Squarespace, Wix, Ghost

- **Head tag:** page-level custom code on the blog/article template (Webflow: CMS template page
  settings; Shopify: `article.liquid` / the article section; Ghost: post-template code injection;
  Squarespace: blog post code injection). Avoid the sitewide head so it only loads on articles.
- **Button + CSS:** an embed/custom-code block (Webflow Embed, Shopify custom liquid block,
  Squarespace code block) in the article template, plus one in the footer if wanted.
- **Script block:** the same template's footer code.
- Wix limits template-level code. Use the deeplink-only version (the `<a>` without the script)
  if the head injection isn't available. It still works; the reader just leaves the page.

## Footer (sitewide, optional)

The `ps-cta--quiet` variant, `data-placement="footer"`. If the footer shows on every page, the
head tag must load sitewide too, or the footer link just falls back to the deeplink on
non-article pages. That's acceptable: it still works. Don't load `publisher.js` twice to cover
both.
