# {{CLIENT}}: Google Preferred Sources button

Prepared by {{AGENCY}} · {{DATE}}

## What this is

A button on {{CLIENT}}'s articles that lets readers add {{HOST}} as a preferred source in Google.
Google's documentation says that for readers who do, {{CLIENT}} "is more likely to appear in
Top Stories" with a "preferred" badge, and its content "can be highlighted with a 'preferred'
badge" in AI Overviews and AI Mode. The reader clicks, confirms in a Google popup and lands back
on the article.

What it isn't: Google makes no ranking claim for this feature, and it only affects the readers
who choose {{CLIENT}}. Source: <https://developers.google.com/search/docs/appearance/preferred-sources>

## Eligibility

| Check | Result |
|---|---|
| Eligible unit (domain/subdomain only) | {{HOST}} |
| Listed in Google's source preferences tool | {{ELIGIBILITY_RESULT}} |
| Included in Search generative AI features (Search Console, needed for the AI badge) | {{AI_FEATURES_RESULT}} |
| Content-Security-Policy allows `news.google.com` | {{CSP_RESULT}} |

## Placement

{{PLACEMENT_TABLE}}

Examples on your own articles:

{{PLACEMENT_EXAMPLES}}

## Look

{{STYLE_SUMMARY}}

Preview: open `{{PREVIEW_FILE}}` in a browser.

## Code

Platform: **{{STACK}}**

{{CODE_BLOCKS}}

{{CSP_FIX}}

## Tracking

Each click pushes `preferred_source_click` to `window.dataLayer` with `placement` and `page_url`.
In Google Tag Manager, a Custom Event trigger on `preferred_source_click` sends it to GA4, so
you can see which placement earns clicks.

## QA before sign-off

- [ ] `publisher.js` appears once per article page (View Source, search `publisher.js`)
- [ ] The in-article button sits between two paragraphs, not inside a list, quote or table
- [ ] Clicking it opens Google's popup and closing it returns to the same article
- [ ] With JavaScript disabled, the button still opens google.com/preferences/source for {{HOST}}
- [ ] The button doesn't appear on the homepage, checkout, account or feed
- [ ] Keyboard: Tab reaches the button, the focus ring is visible, Enter activates it
- [ ] A `preferred_source_click` event shows in GTM preview

## Rollback

{{ROLLBACK}}

The automatic placements live in code only, so removing the code removes them. If editors placed
the button by hand (a WordPress shortcode or a CMS component), remove those first, or they'll be
left behind as literal text or an empty component.
