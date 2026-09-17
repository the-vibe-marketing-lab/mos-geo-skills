# AI Info Page: implementation notes for {brand}

Prepared {date}. Publish only after the client has approved every row on the "AI Info Page"
tab of the brand audit workbook.

## What this is

A public page of plain facts about {brand}, written so AI assistants (ChatGPT, Claude,
Perplexity, Gemini) can describe the business accurately. It is a reference page, not a
landing page: no pop-ups, no gated content, and no call to action beyond the contact link
in the text.

## Files

| File | Use |
|---|---|
| `ai-info-page.html` | Page body plus the JSON-LD schema block, ready to paste into an HTML/code block |
| `ai-info-page.md` | The same copy as plain text, for page builders that take text only |
| `ai-info.json` | Optional machine-readable copy, to upload at `{json_url}` |
| `organization.jsonld` | The schema on its own, if it goes in through an SEO plugin or tag manager |

## Steps

1. Create a page at **{page_url}** using a plain template (header and footer are fine),
   titled "Official Information About {brand}".
2. Paste `ai-info-page.html` into a Custom HTML / code block, or paste
   `ai-info-page.md` as text and keep its headings as H2s.
3. Schema: if an SEO plugin already outputs Organization or LocalBusiness schema, don't
   paste a second one. Merge `sameAs`, `founder`, `foundingDate` and `address` from
   `organization.jsonld` into the plugin's settings, and delete the `<script
   type="application/ld+json">` block from the pasted HTML.
4. Page settings:
   - **Indexing:** index, follow.
   - **Canonical:** the page itself.
   - **Sitemap:** included.
   - **SEO title:** "Official Information About {brand}".
   - **Meta description:** "Facts about {brand} for AI assistants and researchers:
     services, people, locations and history."
5. Add a footer link on every page (label "AI Info" or "Company Facts") and a link from
   the About page.
6. Optional: upload `ai-info.json` to `{json_url}` and link it at the bottom of the
   page ("Machine-readable version").
7. If the site has an `/llms.txt`, add: `- [Official information about {brand}]({page_url})`
8. Clear any page or CDN cache, then open the page in a private window and check that
   the text is visible with JavaScript turned off.
9. Check that robots.txt does not block GPTBot, OAI-SearchBot, ClaudeBot,
   Claude-SearchBot, PerplexityBot or Bingbot. Also check that no security plugin, CDN
   rule or firewall blocks them: some hosts return 403 to anything that isn't a browser.

## After it is live

Your agency will run an automated check (status, indexing, schema, crawler access,
sitemap, footer link) and log the result in the workbook.

**Review cadence:** every 6 months, or whenever services, key people, locations or awards
change. Update the "Last updated" line on each review.
{canary_note}
