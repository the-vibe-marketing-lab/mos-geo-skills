# AI Info Page: implementation notes for {brand}

Prepared {date}. Publish only after the client has approved every row on the "AI Info Page"
tab of the brand audit workbook.

## What this is

A public page of plain facts about {brand}, written so AI assistants (ChatGPT, Claude,
Perplexity, Gemini) can describe the business accurately. It is a reference page, not a
landing page: no pop-ups, no gated content, and no call to action beyond the contact link
in the text.

## Files

Paths are relative to the AI info folder.

| File | Use |
|---|---|
| `implementation/ai-info-page.html` | The page body, ready to paste into an HTML/code block |
| `ai-info-page.md` | The same copy as plain text, for page builders that take text only |
| `schema/ai-info-schema.json` | The page's structured data (JSON-LD): this page, and the business it describes |
| `preview/ai-info-preview.html` | Open in a browser to see the approved page before building it |

## Steps

1. Create a page at **{page_url}** using a plain template (header and footer are fine),
   titled "Official Information About {brand}".
2. Paste `implementation/ai-info-page.html` into a Custom HTML / code block, or paste
   `ai-info-page.md` as text and keep its headings as H2s.
3. Schema: add `schema/ai-info-schema.json` to this page only, inside
   `<script type="application/ld+json"> … </script>` (a code block at the bottom of the page,
   or the SEO plugin's custom schema field). If the SEO plugin already outputs Organization
   or LocalBusiness schema site-wide, keep one business entity: copy `sameAs`, `founder`,
   `foundingDate` and `address` from the file into the plugin's settings, and use only the
   `WebPage` part of the file on this page.
4. Page settings:
   - **Indexing:** index, follow.
   - **Canonical:** the page itself.
   - **Sitemap:** included.
   - **SEO title:** "Official Information About {brand}".
   - **Meta description:** "Facts about {brand} for AI assistants and researchers:
     services, people, locations and history."
5. Add a footer link on every page (label "AI Info" or "Company Facts") and a link from
   the About page.
6. If the site has an `/llms.txt`, add: `- [Official information about {brand}]({page_url})`
7. Clear any page or CDN cache, then open the page in a private window and check that
   the text is visible with JavaScript turned off.
8. Check that robots.txt does not block GPTBot, OAI-SearchBot, ClaudeBot,
   Claude-SearchBot, PerplexityBot or Bingbot. Also check that no security plugin, CDN
   rule or firewall blocks them: some hosts return 403 to anything that isn't a browser.

## After it is live

Your agency will run an automated check (status, indexing, schema, crawler access,
sitemap, footer link) and log the result in the workbook.

**Review cadence:** every 6 months, or whenever services, key people, locations or awards
change. Update the "Last updated" line on each review.
{canary_note}
