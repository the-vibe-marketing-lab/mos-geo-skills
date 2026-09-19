# Where the button goes

The button asks a reader to vouch for the site. People vouch when they've just got value, so
placement follows the reader's peak moment, not the page template's empty slots.

## The map

| Placement | Where exactly | Variant | Status |
|---|---|---|---|
| **In-article** | Straight after the article's strongest paragraph or section: the stat, the fix, the example the reader came for | `ps-cta` (card with a one-line note) | Main. Every article |
| **End of article** | After the last paragraph, before comments/related posts | `ps-cta--quiet` (text link) | Second. Every article |
| **Sitewide** | Footer or author box | `ps-cta--quiet` | Optional, low-key |

Write this table for the site (page type → position → variant) before building. Only articles,
guides, news and blog posts get in-article buttons. They're the pages that feed Top Stories and
AI answers.

## Choosing "the strongest paragraph"

It's an editorial call, so make it one:

- **Install mode, few articles (under ~20):** read each post and place the in-article button
  after its strongest section yourself (shortcode, MDX component or partial). List where you put
  each one in the report.
- **Many articles:** use the automatic mid-article default (about 40% down, never before the 3rd
  paragraph) and tell the user editors can move it with the shortcode/component on their best posts.
- **Handover mode:** name the rule in the handover and give two examples from the client's own
  articles ("on <article>, after the section '<heading>'").

## Don't

- **No header or nav button.** It competes with the site's own call to action. Too many calls to
  action and readers take none.
- **No popups, sticky bars or interstitials.** It's a trust request. Interrupting the reader
  before they've read anything spends trust you haven't earned yet.
- **Not above the first paragraph.** The reader hasn't got any value yet.
- **Max two in-article buttons per page** (in-article + end). A third looks like begging.
- **Not on out-of-scope pages:** checkout, account, login-gated content, calculators, thin
  landing pages.

## Copy

- The label keeps Google's phrase "preferred source" so readers recognise the feature. Default:
  "Add us as a preferred source on Google", the same on every placement.
- The Google G (if the owner chose it) goes on the main in-article button only. The quiet
  end-of-article link stays text only.
- The note above the in-article button is one short, true line in the site's voice, e.g.
  "Want more of this when you search on Google?" Never promise rankings, and never promise
  anything for the reader beyond seeing more from the site.
