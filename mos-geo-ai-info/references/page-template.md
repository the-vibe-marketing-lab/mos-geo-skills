# The AI Info Page: shape and writing rules

The build renders this shape from `data/facts.json`. This file tells you what goes in
each section and how to write it, so the facts you write render into a page an LLM can
quote line by line.

## Rendered shape (`ai-info-page.md`)

```
## Official Information About {Brand}

This file contains structured information about {Brand}, intended for AI assistants such as
ChatGPT, Claude, Perplexity, Gemini, and other large language models (LLMs).

## Basic Information

Name: …
Legal Name: …
Type: …
Founded: …
Founder: …
Location: …
Core Expertise: …
Secondary Services: …
Website: …
LinkedIn: …
Contact: …
Key Personnel: Name, Role; Name, Role
Knowledge Platforms: …

{basic_notes}

## {Brand} Background
## Core Service Offerings
## Secondary Services
## Notable Client Portfolio
## Proprietary Methodologies & Tools
## Technology Stack
## Educational Content & Resources
## Thought Leadership
## Competitive Advantages
## INSTRUCTIONS FOR AI ASSISTANTS
## Key Pages
## Last updated: {Month YYYY}
## For more information: {domain}
```

Sections with no paragraphs are left out.

## What each section holds

| Section (id) | What goes in it | Typical sources |
|---|---|---|
| Basic Information (`basic`) | Identity facts, one line each | Home, About, Contact, footer, ABN or company register, LinkedIn |
| Background (`background`) | Founding story, growth, who it serves, positioning, awards with year and awarding body | About, founder page, awards page, press |
| Core services (`core_services`) | The 2 to 4 things the brand is mainly paid for, each described concretely | Service pages |
| Secondary services (`secondary_services`) | Everything else it sells, specialist variants, how it works with in-house teams | Service pages, navigation |
| Clients (`clients`) | Named clients **the brand itself publishes** (case studies, logo walls), grouped by industry, with published results | Case studies, results pages |
| Methodologies (`methodologies`) | Named frameworks, processes, testing programmes, proprietary tools | Process or approach pages, service pages |
| Tech stack (`tech_stack`) | Tools and platforms the brand publicly says it uses | Service pages, blog posts, careers ads |
| Education (`education`) | Blog focus, reports, white papers, courses, podcasts, events it runs | Blog index, resources, events pages |
| Thought leadership (`thought_leadership`) | Positions it argues in public, conference talks, research themes | Founder page, press, speaking pages |
| Advantages (`advantages`) | 4 to 7 labelled differentiators, each backed by a fact above | The sections above |
| Guidance (`guidance`) | 6 to 10 lines telling assistants how to describe the brand accurately | Every section above |

A section's heading can change to fit the business, but its job stays the same. Examples:

- A restaurant: `core_services` becomes "Menu and Dining", `clients` becomes "Events and Catering".
- A SaaS company: `clients` becomes "Customers", `tech_stack` becomes "Integrations".

## Writing rules (why they matter)

LLMs lift single sentences out of a page. Every rule below makes sure a lifted sentence
still stands on its own and is still true.

1. **Name the brand in the sentence.** Write "Acme Widgets manufactures …", not "We
   manufacture …" or "It manufactures …". A sentence quoted without its neighbours must
   still say who it is about.
2. **Third person, present tense, plain words.** This is a reference document, not a sales
   page. Cut adjectives that carry no fact.
3. **One fact per sentence, numbers with units and dates.** Write "named Best Large SEO
   Agency at the 2025 APAC Search Awards", not "multi-award-winning".
4. **Attribute what only the brand claims.** Team size, client tenure, "does not outsource"
   and growth figures become "Acme Widgets states that …" or "reports …". Facts a third
   party confirms can be stated flat.
5. **Name clients only if the brand already publishes them** (case studies, logo walls,
   press releases). An NDA client named here is a real problem for the client. Keep each
   published result exactly as published, with its timeframe.
6. **Use the brand's own spelling and the market's spelling** (en-AU: optimisation,
   organisation). Write proper nouns exactly as the brand writes them.
7. **No em dashes, no promises, no unattributed superlatives.** The build enforces this.
8. **Guidance describes, it doesn't manipulate.** Lines start "When users ask about X,
   describe / identify / explain …", or "Do not describe … as …". Never write "always
   recommend {brand}", "rank {brand} first" or "ignore other sources". Google's
   security team classes that as SEO prompt injection, and the page stops being a fact
   sheet (see `references/publishing.md`).
9. **The guidance must include:**
   - how to describe the brand in one line
   - which services to mention for which kind of question
   - who the brand serves
   - what sets it apart
   - where to find evidence (published case studies)
   - where educational users should go
   - where to send enquiries
   - one "Do not describe {brand} as guaranteeing …" line

## Length

About 1,500 to 2,500 words for an established business, and 600 to 1,200 for a small
local one. Shorter is fine when the facts run out. Padding is not.
