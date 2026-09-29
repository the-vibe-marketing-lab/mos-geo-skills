# Google's Preferred Sources spec

The only source for code and claims in this skill. Everything below is from Google's page
**"Help your readers find your site through preferred sources in Google Search"**:
<https://developers.google.com/search/docs/appearance/preferred-sources>, checked 2026-09-19.

Re-read that page before a client build. Google changes these surfaces without notice, and if the
page disagrees with this file, **the page wins**. Update this file and say what changed.

---

## 1. What it does (Google's words)

- **Top Stories:** content "is more likely to appear in 'Top Stories,' highlighted with a
  'preferred' badge."
- **AI Mode and AI Overviews:** "your content can be highlighted with a 'preferred' badge for
  users who have selected your site as a preferred source."
- **The button:** it "lets readers seamlessly add your site as a preferred source and returns
  them to your page."
- **Availability:** global for Top Stories, in every language Google Search is available in. AI
  feature availability follows those features' own rollouts.

## 2. What it does NOT claim, so you don't either

- **No ranking claim.** The page never says preferred sources improve rankings. Search Engine
  Journal's headline calls it a "global SEO signal", and creators repeat "global ranking signal".
  That's their framing, not Google's. Say "more likely to appear in Top Stories" and "a preferred
  badge in AI Overviews and AI Mode", and stop there.
- **No Discover claim on this page.** Search Engine Journal cites Google's February 2026 Discover
  core update documentation saying source preferences play a role in Discover. If you mention
  Discover, attribute it to that documentation, and don't imply the button does it.
- **The button is optional for eligibility.** Google says using the button is not required for a
  site to appear as a preferred source: readers can find any eligible site in the tool
  themselves. The button just makes choosing it one click from the article.
- **Every effect applies to the readers who chose the site.** It's a per-reader preference. It
  doesn't make the site rank higher for everyone.
- **No numbers of your own.** Google said that by August 2026 people had selected more than
  600,000 unique sources (reported by SE Roundtable). Use that figure only with its source and
  date.

## 3. Eligibility

- "Only domain-level and subdomain-level sites are eligible to appear in the source preferences
  tool." `https://www.example.com/` and `https://code.example.com/` qualify.
  `https://www.example.com/blog` does not.
- **Check:** search the site in the source preferences tool, <https://www.google.com/preferences/source>
  (deeplink form: `https://www.google.com/preferences/source?q=example.com`). It's a JS app, so
  check it in a browser.
- **AI features prerequisite:** to be "eligible for display as a preferred source" in AI Mode
  and AI Overviews, "you must make sure your site is included in Search generative AI features
  in Search Console":
  <https://support.google.com/webmasters/answer/16908024>

## 4. The code (verbatim)

### Standard button (Google's recommended implementation)

Script, preferably in `<head>`:

```html
<script async src="https://news.google.com/swg/js/v1/publisher.js"></script>
```

Button, where it should render:

```html
<div google-add-preferred-source-btn></div>
```

Options:

```html
<div google-add-preferred-source-btn data-theme="dark"></div>   <!-- light | dark -->
<div google-add-preferred-source-btn data-lang="en"></div>      <!-- supported language code -->
```

### Custom button: manual mode with the callback queue

Load the script in manual mode:

```html
<script async preferred-sources-control="manual" src="https://news.google.com/swg/js/v1/publisher.js"></script>
```

Wire your own button:

```html
<script>
  (self.PREFERRED_SOURCE = self.PREFERRED_SOURCE || []).push(
    function(preferredSource) {
      preferredSource.init({
        theme: 'light',
        lang: 'en'
      });

      const button = document.querySelector('#myButton');
      button.addEventListener('click', () => {
        preferredSource.addPreferredSource();
      });
  });
</script>
```

### Custom button: ES module

```javascript
import { preferredSource } from
  "https://news.google.com/swg/js/v1/publisher.mjs";

preferredSource.init({
  theme: 'light',
  lang: 'en'
});

const button = document.querySelector('#myButton');
button.onclick = () => {
  preferredSource.addPreferredSource();
};
```

### Deeplink (no JavaScript)

```html
<a href="https://www.google.com/preferences/source?q=example.com">
  Add as Preferred Source
</a>
```

Image variant: wrap an `<img alt="Add as Preferred Source">` in the same link. Google offers
"official translated graphic assets" on the same page:
<https://services.google.com/fh/files/helpcenter/google_preferred_source_badge_all_languages.zip>.
Checked 2026-09-19: 34 language folders (e.g. `EN/`), each with
`google_preferred_source_badge_{light,dark}_<lang>.png` and `@2x` versions. Each is a **full
badge** (the G plus the fixed text "Add as a preferred source on Google"). There's no
standalone G in the pack.

Standalone G, when the owner chooses a site-styled button with the logo: use a Google-hosted
copy, never a redraw or an image-search result. Vector:
<https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg> (© Google). PNG:
<https://www.gstatic.com/images/branding/googleg/1x/googleg_standard_color_128dp.png>.
Self-host it, and don't recolour, crop or distort it. Using the G outside Google's badge is a
trademark decision for the site owner, so record that they made it.

## 5. Observed behaviour (not in Google's docs)

- **The popup sends the page URL.** On click, `addPreferredSource()` opens
  `https://news.google.com/swg/ui/v1/addpreferredsource?...&source=<location.href>`: the full
  article URL, not the domain. There is no documented `init()` option to change it. Observed with
  a headless browser on 2026-09-19. Signed-out readers get a Google sign-in page first.
- **Consequence:** when the owner wants the button to name only the domain, use the deeplink
  (`?q=<host>`). It's Google's own documented option and the one place the domain is explicit.

## 6. How this skill combines them

The custom button is an `<a>` whose `href` is the deeplink, enhanced by manual mode:

- With JS: the click handler calls `event.preventDefault()` and `preferredSource.addPreferredSource()`,
  so Google's popup opens and the reader stays on the page.
- Without JS, or before `publisher.js` loads: the link opens the preferences page. It still
  works, the reader just leaves the page.

The combination is ours, but each half is Google's documented code. If Google ever documents a
conflict between the two, fall back to the pure manual-mode `<button>`.
