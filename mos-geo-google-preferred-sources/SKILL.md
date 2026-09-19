---
name: mos-geo-google-preferred-sources
description: >
  Add Google's "Add as a preferred source" button to a website, end to end: check the site is
  eligible, detect its stack and brand, build a button styled to match the site using Google's
  official code, place it where readers actually click it (after the best paragraph of an
  article, not buried in the footer), then verify the live install with a script. Installs it
  directly when the site's code or WordPress is reachable, or writes a paste-ready developer
  handover and preview for a client site. Readers who pick a site as a preferred source see it
  more in Top Stories and get a "preferred" badge on it in AI Overviews and AI Mode. USE WHEN the
  user says "Google Preferred Sources", "preferred source button", "add as a preferred source",
  "make me preferred on Google", "preferred sources badge", "google.com/preferences/source",
  "get my readers to pick my site in Google", "the Top Stories preferred badge", "preferred
  badge in AI Overviews", "/mos-geo-google-preferred-sources", or asks to add the Preferred
  Sources step to a GEO brand audit. NOT FOR getting a site into Google News or Discover
  generally, schema markup, LLM share buttons that open ChatGPT or Claude (use
  mos-geo-llm-buttons), or testing what AI engines say about a brand (use mos-geo-brand-360).
---

# Google Preferred Sources button

A reader clicks one button on the site. Google saves the site as one of that reader's preferred
sources and drops them straight back on the page. From then on, for that reader, Google says the
site "is more likely to appear in Top Stories" with a "preferred" badge, and in AI Mode and AI
Overviews its content "can be highlighted with a 'preferred' badge".

That is the whole promise, and the skill never inflates it. SEO news sites call this a "global
ranking signal". Google's own documentation makes no ranking claim at all, and doesn't mention
Discover. The evidence and exact wording live in `references/google-spec.md`. Read it before
writing any copy for the user or their client.

The deliverable is a **working button on the real site**, or, when the site isn't reachable from
here, a handover a developer can paste in ten minutes. Never hand over "go read Google's docs
and add the button". Writing that code is the job.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | Preflight: URL, mode, brand | A reachable URL and a chosen mode |
| 1 | Check: eligibility, stack, CSP, existing install | `check` has run and the eligibility link has been opened |
| 2 | Brand: palette and type from an article page | User confirmed the style |
| 3 | Build: button code for the detected stack | Uses Google's code from `references/google-spec.md`, nothing else |
| 4 | Place: article positions plus one sitewide spot | Placement map written down |
| 5 | Ship: install, or write the handover | Files written or code committed |
| 6 | Verify: `verify` on the live pages | No FAIL; NEEDS BROWSER pages checked by hand |

Set `SKILL` to this skill's folder (the folder this SKILL.md sits in) before running scripts.

---

## Stage 0: Preflight

Ask in one message, skipping anything the user already said:

1. **Site URL.** Required. The button is useless without the site's real host and styling.
2. **Whose site, and can we touch the code?** This picks the mode:
   - **Install**: the site's code is in this working directory (or a folder the user names), or a
     WordPress MCP (WPVibe, mcp-adapter) is connected. You make the change.
   - **Handover**: a client site you can't edit. You write the handover and preview.
3. **Brand/agency name**, only for Handover (the handover is white-labelled to the member's
   agency, never to us).

## Stage 1: Check

```bash
python3 "$SKILL/scripts/preferred_sources.py" check <url>
```

It reports the eligible unit (domain or subdomain; a subdirectory like `/blog` is never
eligible, so the button always points at the host), the stack, up to three article URLs from the
sitemap, the Content-Security-Policy position on `news.google.com`, and any existing install.

Then do the one check the script can't: **open the eligibility link it prints**
(`https://www.google.com/preferences/source?q=<host>`) and confirm the site appears in the
search. The tool only works for a **signed-in Google account**. A headless or logged-out browser
lands on Google's sign-in page and proves nothing, so ask the user to open it in their own
signed-in browser (or use a browser session that's already signed in). Put this question in the
same AskUserQuestion as the Stage 2 style choice, so it costs one round trip. If the site doesn't appear, stop and say so. Don't install a button that
leads to "no results". Google doesn't say what gets a site listed, so don't guess for the user.

Also tell the user about the Search Console prerequisite. To be "eligible for display as a
preferred source" in AI Mode and AI Overviews, Google says the site must be included in Search
generative AI features in Search Console. Link it (see `references/google-spec.md`) and mark it
as a manual check.

If the site sends a CSP at all, the fix goes into the install or the handover:
`references/implementation.md` rule 3 covers the script host, the inline wiring and the popup.
Otherwise the button silently behaves as a plain link.

## Stage 2: Brand

Style the button from a **real article page**, never the homepage. Sites often scope a bolder
palette to the homepage only, and the button lives on articles. Pull rendered values: the
primary/action colour, text colour, surface, border radius and font stack, taken from the site's
existing primary button when there is one. Anything you can't extract is written as
`[VERIFY — could not auto-extract]`. Never invent a brand colour.

Confirm with AskUserQuestion before building, showing the extracted values. Offer three options:
**custom button in the site's style (Recommended)**, **Google's standard button** (`light`/`dark`
theme only, zero styling work), and **"I'll give you the brand kit"**.

Why custom is the default: Google's standard button looks the same on every site, while a button
in the site's own style, with copy that fits the page, reads as part of the article. Google's docs
explicitly support a custom button through manual mode, so this isn't a hack.

## Stage 3: Build

Read **`references/google-spec.md`** (the only source for code) and
**`references/implementation.md`** (one section per stack).

**First decide popup or link, and ask the user** (add it to the Stage 2 AskUserQuestion):

| Mode | What Google receives | Reader experience |
|---|---|---|
| **Deeplink** (Recommended when the owner wants the domain pinned) | `?q=<host>`: exactly the domain you set | Google's preferences page opens in a new tab, and the article stays open |
| **Popup** (manual or standard mode) | `source=<the current page URL>`, sent by `publisher.js`, which you can't override (observed 2026-09-19) | Google's popup opens over the article |

Owners often object when the popup shows the article URL instead of their homepage. Google's
docs don't say the popup adds anything other than the site, but the documented way to name the
domain explicitly is the deeplink.

- **Custom button, deeplink mode** = a styled `<a href="https://www.google.com/preferences/source?q=<host>" target="_blank" rel="noopener noreferrer">`
  with "(opens in a new tab)" in its accessible name. No `publisher.js`. Mark it with
  `data-preferred-source` (not the `js-preferred-source` class, which `verify` reads as "popup
  wiring expected"). The script block shrinks to tracking only.
- **Custom button, popup mode** = manual mode: the script with `preferred-sources-control="manual"` plus a
  styled `<a class="js-preferred-source">` whose `href` is the same deeplink.
  JavaScript opens Google's popup (the reader stays on the page). With JS blocked or slow, the
  plain link still works. Start from `assets/button.html`.
- **Standard button** = the two lines from Google, with `data-theme`.
- Load `publisher.js` **once per page**, only on pages that show the button.
- Fire a `preferred_source_click` event (with `placement` and `page_url`) on click, so the user
  can see which position earns clicks. Send it to **whatever analytics the site already runs**: in
  Install mode, look for an existing click-tracking pattern first (a sibling component, a
  `dataLayer` push, DataFast/Plausible/Fathom/PostHog calls) and copy it. Only push to
  `window.dataLayer` if it already exists as an array. Creating one on a site without Google Tag
  Manager just swallows events.
- Copy for the button: **"Add us as a preferred source on Google"** by default. It's short, first
  person and true, and keeps Google's phrase "preferred source" so readers recognise the feature.
  Use the same label on every placement.
- **Google "G" on the button (default: on the main in-article button only).** Google's official
  pack (`google_preferred_source_badge_all_languages.zip`, linked in the spec) only contains
  full badges with Google's own fixed wording, not a standalone G. So offer the owner two options:
  - **Official badge** as the clickable image: Google's asset, used as intended, but the wording
    is Google's ("Add as a preferred source on Google") and the colours are Google's.
  - **Site-styled button + G**: the G from Google's own host (see `references/google-spec.md`
    §4), self-hosted, in a white circular chip so the multicoloured G never sits on a coloured
    fill. Don't recolour, crop or distort it, and never draw your own G. Say plainly that using
    Google's logo outside the official badge is the owner's trademark call, and let them make it.

## Stage 4: Place

Read **`references/placement.md`**. The short version:

- **In the article, right after the strongest paragraph or section**: the moment the reader
  already rates the content. This is the main placement.
- **End of the article**, as a quieter second spot.
- **One sitewide spot** (footer or author box), low-key.
- **Not** in the header nav, not in a popup, not above the first paragraph, and not more than
  two in-article spots on one page. Too many calls to action and readers take none.

Write the placement as a table (page type → position → variant) before touching code.

## Stage 5: Ship

**Install mode.** Make the change in the site's code following `references/implementation.md`:
a plugin file on WordPress (works on classic and block themes, one-click rollback), a component
on Next/React/Astro/Nuxt, a snippet plus a custom-code embed on Webflow/Shopify/Squarespace.
Keep it on a branch or draft, show the user the diff, and deploy only on their go-ahead.

**Handover mode.** Write two files into the GEO campaign folder:
`campaigns/geo/YYYY-MM/preferred-sources/` (agency HQ brain:
`campaigns/geo/YYYY-MM/<client-slug>/preferred-sources/`; outside a brain:
`outputs/geo/YYYY-MM/<client-slug>/preferred-sources/`). Never overwrite a delivered build. A
second one in the same month goes in `preferred-sources-2/`.

| File | Built from | What it is |
|---|---|---|
| `<client>-preferred-sources-handover.md` | `assets/handover-template.md` | Eligibility result, placement map, every line of code, QA list, rollback |
| `<client>-preferred-sources-preview.html` | `assets/button.html` | Standalone preview of the styled button on a sample article, to approve before shipping |

Replace every `{{PLACEHOLDER}}`, keep every `[VERIFY]` flag, and read it once as the client
would: no internal paths, no other client's name, no ranking promise.

## Stage 6: Verify

After deploy (or in Handover mode, after the client ships), run:

```bash
python3 "$SKILL/scripts/preferred_sources.py" verify <article-url> <another-article-url> \
  --expect-absent <homepage> --expect-absent <checkout-or-account-url>
```

Pass every page that should carry the button as a normal argument, and every page that must stay
clean (the homepage unless you chose the sitewide footer spot, checkout, account) with
`--expect-absent`. It checks each page for exactly one `publisher.js`, a button or wired custom
button, a deeplink pointing at the right host, and CSP. For `--expect-absent` pages, finding an
install is the failure. **NEEDS BROWSER** means the button is rendered by
JavaScript (common on React sites): open the page in a real browser, click the button, and
confirm Google's popup opens and closes back onto the page. Report what you actually saw.

The script reads the server HTML and inline scripts only. If the click handler lives in a bundled
JS file (a React/Vue component), `verify` can FAIL a manual-mode page with "no
`addPreferredSource()` call" even though it works. Confirm in a browser before believing either
result, and say which one you trusted. Exit codes: 0 no FAIL, 1 any FAIL, 2 nothing fetched.

Then, inside a MarketingOS brain, tick the skill's row in the month's audit workbook:

```bash
uv run --with openpyxl python "$SKILL/../_shared/brand-audit/tick_checklist.py" \
  --skill mos-geo-google-preferred-sources --run-dir <the preferred-sources folder> \
  --note "button live on <n> page types, verify PASS"
```

## Report

Lead with what's now true: "The Preferred Sources button is live on <site> in <positions>" (or
"The handover is ready"). Then: eligibility result, stack, style choice, placement map, verify
result per page, and the manual checks left (the Search Console AI-features setting, the browser
click-test). End with one next action.

## Reference map

| File | Read it when |
|---|---|
| `references/google-spec.md` | Stage 3 every time, and before writing any claim about what the feature does |
| `references/implementation.md` | Stage 3 and 5: one section per stack, plus the custom button |
| `references/placement.md` | Stage 4 |
| `assets/button.html` | Building the custom button or the preview |
| `assets/handover-template.md` | Handover mode |

## Things that will bite you

- **The eligibility tool can't be curled.** It's a JavaScript app, so check it in a browser.
- **A subdirectory is never eligible.** If the blog lives at `/blog`, the button still points at
  the domain, and the whole domain gets the preference.
- **Two `publisher.js` tags on one page** (a theme snippet plus a plugin) cause double-init. The
  verify script flags it.
- **Homepage colours lie** (see Stage 2).
- **Article prose restyles your button.** The in-article card lives inside the article body,
  where rules like `.article-prose img { width: 100%; border… }` and `.prose a { … }` hit the G
  and the link. Scope the button's rules at least two classes deep (`.ps-cta .ps-cta__g img`),
  reset width, border, margin and radius explicitly, and screenshot the card in the dev server
  **and** the production build. Stylesheet order differs between them.
- **`the_content` fires everywhere on WordPress**: feeds, REST, related-post loops. The guard in
  `references/implementation.md` is not optional.
- **Nothing site-specific belongs in this skill.** Every host, colour and name is read at run
  time. If you find yourself typing a real domain into a file under this folder, that's the bug.
