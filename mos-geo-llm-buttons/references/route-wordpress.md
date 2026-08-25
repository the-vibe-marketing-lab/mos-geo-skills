# Route: WordPress

Read this when recon confirmed WordPress. The deliverable is a **plugin file**, not a theme
edit, and the reasons are in the constraints below.

## Delivery tooling

### WPVibe MCP (preferred)

WPVibe is Awesome Motive's MCP server for WordPress. The client installs a plugin, slug
`vibe-ai`, and connects it:

```bash
claude mcp add wpvibe https://mcp.wpvibe.ai/mcp
```

Tools it exposes: `rest_api` (arbitrary REST calls with the site's own auth), `write_file`
(theme and plugin files), `run_wp_cli` (WP-CLI over the relay), plus a draft-theme workflow for
staging changes before they go live.

**Two constraints shape the entire design of this route.**

**(a) Theme-file editing is classic-themes only.** WPVibe's file tooling does not support
full-site-editing / block themes. A large share of 2026 WordPress sites are block themes, so a
deliverable built as a `functions.php` edit is undeliverable on half the market. Shipping a
plugin file sidesteps the limitation entirely — a plugin works identically under both theme
types, survives theme switches, and is uninstallable in one click.

**(b) It is a hosted relay holding an encrypted application password on WPVibe's servers.**
Connecting means a third party stores credentials that can write to the client's site. That has
to be disclosed to the client **before** the connection is made, in writing, and it is their
decision, not the member's. A client who finds this out afterwards is entitled to be angry.
If they decline, use a fallback below — the deliverable is identical either way.

### Fallbacks

1. **WordPress/mcp-adapter** — the official adapter. Thin, fewer conveniences, no hosted relay.
   The right answer for a client who says no to (b).
2. **Plain REST API + application password** — the floor. Works everywhere REST is enabled,
   credentials never leave the client's control.

**Do not recommend `Automattic/wordpress-mcp`.** It was archived on 19 January 2026. It still
appears at the top of search results and in older write-ups; it is not maintained.

## What ships

One plugin file: `ai-share-bar/ai-share-bar.php`. It auto-detects the theme type and registers
whichever injection path applies, plus the shortcode, so the client installs one artefact and
nothing else has to be decided at install time.

```php
<?php
/**
 * Plugin Name: AI Share Bar
 * Description: Adds a row of AI-assistant share buttons to the top of single posts.
 * Version:     1.0.0
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
```

The `ABSPATH` guard is not decoration — without it the file is directly executable over HTTP.

## Injection pattern 1 — block themes

Detect with `wp_is_block_theme()`. On a block theme, `the_content` still exists but the post
title is a separate block, so filtering content puts your widget below the intro paragraph
rather than under the title.

Filter the rendered title block instead, which gives precise sub-title placement:

```php
add_filter( 'render_block_core/post-title', 'ai_share_bar_after_title', 10, 2 );

function ai_share_bar_after_title( $block_content, $block ) {
    if ( ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) {
        return $block_content;
    }
    return $block_content . ai_share_bar_render();
}
```

Docs: <https://developer.wordpress.org/reference/hooks/render_block_this-name/> and
<https://developer.wordpress.org/reference/functions/wp_is_block_theme/>

## Injection pattern 2 — classic themes

```php
add_filter( 'the_content', 'ai_share_bar_before_content', 20 );

function ai_share_bar_before_content( $content ) {
    if ( ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) {
        return $content;
    }
    return ai_share_bar_render() . $content;
}
```

**The guard is mandatory**, and the reason is that `the_content` fires far more often than
people assume. It runs for RSS and Atom feeds, for REST API responses (so the widget markup
would end up inside JSON served to a headless front end), for related-post and recent-post
loops in sidebars, for excerpt generation, and for any plugin that renders a post body
somewhere else on the page. Without the three conditions you get the widget four times on one
screen and inside the client's feed.

**Priority 20, not the default 10.** `wpautop` runs at priority 10 and rewrites bare newlines
into `<p>` tags. Injecting before it means your button markup gets paragraph tags interleaved
through it and the flex layout collapses. Running at 20 puts you after `wpautop` has finished
with the post body, so your HTML arrives intact.

Docs: <https://developer.wordpress.org/reference/hooks/the_content/> ·
<https://developer.wordpress.org/reference/functions/in_the_loop/> ·
<https://developer.wordpress.org/reference/functions/is_main_query/>

## Injection pattern 3 — the shortcode escape hatch

Page builders — Elementor, Bricks, Etch — render post content through their own pipeline, and
`the_content` either never fires or fires with the wrong markup. Register a shortcode so an
editor can drop the widget exactly where they want it without a developer:

```php
add_shortcode( 'ai_share_bar', 'ai_share_bar_render' );
```

Usage: `[ai_share_bar]` in a shortcode widget inside the builder's template.

Ship all three patterns in the one file. The block/classic branch is auto-detected; the
shortcode is always registered and costs nothing when unused.

Docs: <https://developer.wordpress.org/reference/functions/add_shortcode/>

## Endpoints as a filterable array

Every provider URL lives in one place, exposed as a filter so a dead provider is a one-line fix
in a child plugin rather than an edit to a file that will be overwritten on update:

```php
function ai_share_bar_endpoints() {
    $urls = array(
        'chatgpt'    => 'https://chatgpt.com/?hints=search&q=',
        'claude'     => 'https://claude.ai/new?q=',
        'perplexity' => 'https://www.perplexity.ai/search/new?q=',
        'grok'       => 'https://grok.com/?q=',
        'googleai'   => 'https://www.google.com/search?udm=50&q=',
    );
    return apply_filters( 'ai_share_bar_endpoints', $urls );
}
```

Populate that array from `../_shared/platform-endpoints.json` at generation time — do not retype
it from this file, which is illustrative and will drift. Gemini is absent because it cannot be
prefilled; if the client wants it, it is a clipboard button, not a URL.

Build hrefs with `esc_url( $base . rawurlencode( $prompt ) )`. `rawurlencode` is the PHP
equivalent of `encodeURIComponent`; `urlencode` encodes spaces as `+`, which some composers
render literally.

## Never serialise URLs into post content

Do not write the assembled `<a href>` markup into `post_content`, and do not offer a "insert the
buttons into every post" bulk-edit script. It looks convenient and it is a trap:

- These endpoints are undocumented and change. Copilot's prefill was removed outright in
  January 2026. Serialised URLs mean a database migration across every post to fix one provider.
- The prompt embeds the URL, so any permalink change silently breaks every button.
- It pollutes the content the client's own exports, feeds, and future migrations carry.

If the client wants the widget as an editable block rather than an automatic injection, register
a **dynamic block with a `render_callback`**. The post stores a block comment; the URLs are
generated fresh on every render.

Docs: <https://developer.wordpress.org/reference/functions/register_block_type/>

## Assets

Enqueue the stylesheet and the icons from the plugin directory, conditionally:

```php
add_action( 'wp_enqueue_scripts', function () {
    if ( ! is_singular( 'post' ) ) { return; }
    wp_enqueue_style( 'ai-share-bar', plugins_url( 'ai-share-bar.css', __FILE__ ), array(), '1.0.0' );
} );
```

Icons live in `ai-share-bar/icons/{platform}.svg`, self-hosted, referenced via
`plugins_url()`. Inline the ChatGPT mark in the PHP render function rather than referencing a
file — it is the most-targeted-for-takedown mark of the five and inlining removes the
broken-image risk entirely.

## QA on WordPress specifically

Beyond the standard checks, verify:

- The widget renders once, not twice, on a post with a related-posts block below the content.
- The widget does **not** appear in `/feed/`. Load it and grep for the wrapper class.
- The widget does **not** appear in `/wp-json/wp/v2/posts/<id>` under `content.rendered`.
- Pages, archives, and the front page are clean — the guard is `is_singular('post')`, so a
  client using a custom post type for articles needs it widened deliberately, not accidentally.
- Deactivating the plugin removes every trace. That is the rollback story, and it is stronger
  than the custom route's.
