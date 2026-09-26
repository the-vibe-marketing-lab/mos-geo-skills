# Schema Knowledge Base

Reference for schema type mappings, rich result eligibility and best practice, used by `mos-geo-schema-optimisation`. It is a working reference, not a pitch: any claim about what schema does for rankings or AI citations lives in `_shared/geo-evidence.md` (section "Schema markup") with its source, and nowhere else.

## Table of Contents

1. [Content Type to Schema Mapping](#content-type-to-schema-mapping)
2. [Rich Result Eligibility](#rich-result-eligibility)
3. [Schema and AI search](#schema-and-ai-search)
4. [Schema Best Practices](#schema-best-practices)
5. [Common CMS Patterns and Misapplications](#common-cms-patterns)
6. [JSON-LD Patterns](#json-ld-patterns)
7. [Industry-Specific Schema](#industry-specific-schema)
8. [Retired rich results](#retired-rich-results)
9. [Google's current requirements](#googles-current-requirements)

---

## Content Type to Schema Mapping

Use this table to determine the ideal schema for each page template. The "Primary" column is the main schema type. "Supporting" types should be included alongside the primary type.

| Page Template | Primary Schema | Supporting Schema | Notes |
|---------------|---------------|-------------------|-------|
| Homepage | WebSite + Organization | (use @graph) | Always include both. Add industry-specific type (LocalBusiness, MedicalBusiness, etc.) if applicable |
| Product pages | Product | Brand, Offer (if sold online), AggregateRating (if reviews exist) | Only add Offer if pricing is live on the page. Never fabricate pricing |
| Service pages | Service | Provider (Organization), AreaServed, Offer | Use ServiceType for categorisation |
| Blog posts / Articles | Article | Author (Person or Organization), Publisher | Use BlogPosting for blog-specific content. Include datePublished, dateModified |
| Category / Listing pages | ItemList + CollectionPage | ListItem for each item | Use numberOfItems, itemListElement |
| FAQ pages | FAQPage | Question, Answer | Each Q&A pair as a mainEntity item. Google requires visible Q&A on the page |
| Recipe pages | Recipe | NutritionInformation, HowToStep | Include prepTime, cookTime, recipeIngredient. Nutrition values must match on-page |
| How-to / Guide pages | HowTo | HowToStep, HowToTool, HowToSupply | Step-by-step content. Include estimatedCost, totalTime if available |
| Event pages | Event | Location, Organizer, Offer | Include startDate, endDate, eventAttendanceMode |
| Video pages | VideoObject | (embed in page schema) | Include duration, thumbnailUrl, uploadDate, contentUrl or embedUrl |
| Review pages | Review or AggregateRating | ReviewBody, Rating | Only if genuine reviews. Never fabricate ratings |
| Contact / About pages | Organization or LocalBusiness | ContactPoint, PostalAddress | Include telephone, email, openingHours for local businesses |
| Location / Branch pages | LocalBusiness | PostalAddress, GeoCoordinates, OpeningHoursSpecification | Use specific subtypes: Restaurant, Dentist, Store, etc. |
| Medical content | MedicalWebPage | MedicalCondition, MedicalAudience | Include lastReviewed, reviewedBy, specialty |
| Course / Training | Course | CourseInstance, Offer, Provider | Include hasCourseInstance with dates and delivery method |
| Job listings | JobPosting | Organization, Place | Include datePosted, validThrough, employmentType |
| News articles | NewsArticle | Author, Publisher, DatePublished | Stricter than Article - must be timely, journalistic content |
| Podcast episodes | PodcastEpisode | PodcastSeries, Person (host) | Include duration, datePublished, associatedMedia |
| Software / App pages | SoftwareApplication | Offer, AggregateRating | Include applicationCategory, operatingSystem |

### Breadcrumbs (BreadcrumbList)

BreadcrumbList should be present on virtually every page except the homepage. It's one of the most universally applicable schema types. If the site has visible breadcrumb navigation, the schema should match it exactly.

### Organization (site-wide)

Organization schema should appear on every page, either inline or via @id reference. At minimum include: name, url, logo, sameAs (social profiles). Add parentOrganization, foundingDate, numberOfEmployees or areaServed only when they are true, stable and the site can keep them current.

---

## Rich Result Eligibility

Google's currently supported rich result types and their schema requirements:

| Rich Result | Required Schema | Minimum Properties | Notes |
|-------------|----------------|-------------------|-------|
| Product snippet | Product | name, image, offers OR review OR aggregateRating | Offer requires price + priceCurrency + availability |
| FAQ accordion | FAQPage | mainEntity with Question + acceptedAnswer | Content MUST be visible on the page (not hidden behind tabs/accordions by default) |
| Recipe card | Recipe | name, image, recipeIngredient, recipeInstructions | Google prefers all optional fields too (prepTime, nutrition, etc.) |
| How-to steps | HowTo | name, step (HowToStep with text) | Can include images per step |
| Article snippet | Article | headline, image, datePublished, author | Enhanced article features (top stories, etc.) |
| Breadcrumb trail | BreadcrumbList | itemListElement with ListItem | Position + name required, item (URL) on all except last |
| Sitelinks search | WebSite | potentialAction (SearchAction) | Only for homepage. Google may or may not show it |
| Local pack | LocalBusiness | name, address, telephone | Works with Google Business Profile |
| Event listing | Event | name, startDate, location | Google shows event packs in SERPs |
| Video carousel | VideoObject | name, description, thumbnailUrl, uploadDate | contentUrl or embedUrl required |
| Course listing | Course | name, description, provider | hasCourseInstance for specific offerings |
| Job listing | JobPosting | title, description, datePosted, hiringOrganization | validThrough strongly recommended |
| Review snippet | Review or AggregateRating | reviewRating or ratingValue | Self-serving reviews not eligible (your own products) |
| Software app | SoftwareApplication | name, offers, aggregateRating | For app/software download pages |

### Types with no rich result

These types trigger no visible rich result in Google. They still describe the page accurately, which is reason enough when they fit the content, but do not sell them on a search or AI benefit:

- **MedicalWebPage**, **MedicalBusiness**
- **Organization** beyond the basics
- **Service**
- **CollectionPage**
- **WebPage / WebSite** (apart from the homepage WebSite entity)

---

## Schema and AI search

Short version, with sources in `_shared/geo-evidence.md` → "Schema markup":

- Google says there is no special schema needed to appear in AI Overviews or AI Mode. Normal structured data guidelines apply.
- Microsoft (Bing) has said publicly that schema helps its LLMs understand content.
- The independent studies disagree. One (n=730 citations) found attribute-rich schema cited more often than generic schema, with no-schema pages in between. Another found no link between schema coverage and LLM citation at all.

What that means for a brief: recommend schema for accuracy, rich result eligibility and entity clarity. Do not promise AI citations. Thin, generic markup is the one pattern the evidence argues against, so lean, fully populated blocks beat long, half-empty ones.

### LocalBusiness only for real locations

Only use LocalBusiness on pages for an actual physical office or store. For service area pages that target a suburb where the business has no premises, use Service with `areaServed` instead of inventing a PostalAddress.

### Entity linking with sameAs

Connect the business entity to its authoritative profiles through `sameAs` (and `additionalType` where a Wikidata item exists). This disambiguates which entity the page is about. Only list profiles that exist and that the brand controls or that describe it accurately.

```json
"sameAs": [
  "https://en.wikipedia.org/wiki/Brand_Name",
  "https://www.wikidata.org/wiki/Q12345678",
  "https://www.linkedin.com/company/brand-name",
  "https://www.facebook.com/brandname"
],
"additionalType": "https://www.wikidata.org/wiki/Q12345678"
```

Define entities with stable @id identifiers, then connect them across pages with `about`, `mentions`, `publisher` and `sameAs`.

---

## Schema Best Practices

### The @graph Pattern

For pages that need multiple top-level entities (especially the homepage), use `@graph` to define them as a connected set:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Brand Name",
      "url": "https://example.com/"
    },
    {
      "@type": "WebSite",
      "@id": "https://example.com/#website",
      "url": "https://example.com/",
      "publisher": { "@id": "https://example.com/#organization" }
    }
  ]
}
```

### @id Cross-Referencing

Define entities once with an @id, then reference them from other pages:

```json
// On the homepage - define the Organization
{ "@type": "Organization", "@id": "https://example.com/#organization", ... }

// On any other page - reference it
{ "publisher": { "@id": "https://example.com/#organization" } }
```

This is the single most important pattern for building a connected entity graph. Every schema recommendation should use @id references for Organization, WebSite, and Author entities rather than repeating the full object.

### Don't Nest What You Can Reference

Bad: Duplicating the full Organization object on every page.
Good: Define once, reference via @id everywhere else.

### Keep Schema Accurate to On-Page Content

Every property in the JSON-LD must reflect what's actually visible on the page. Google's guidelines are explicit: structured data must not be misleading. Common violations:
- Product schema with pricing that doesn't match the page
- FAQ schema with Q&A pairs that aren't visible on the page
- Recipe schema with nutrition values that don't match on-page panels
- AggregateRating that doesn't correspond to actual visible reviews

### datePublished and dateModified

Include these on all content pages (Article, BlogPosting, MedicalWebPage, Recipe, etc.). If the CMS tracks modification dates, always include dateModified, and only change it when the content really changes.

### Author and Publisher

Use Person for named authors, Organization for brand-published content. Always include the author.

### sameAs for Entity Disambiguation

Organization and Person entities should include sameAs arrays pointing to authoritative profiles (LinkedIn, Wikipedia, social media, Crunchbase), so the entity is unambiguous.

---

## Common CMS Patterns and Misapplications

These are the problems you'll see most often in Screaming Frog crawls:

### 1. Generic Article Everywhere
**What it looks like**: Every page has Article + Organization + ImageObject + Person, regardless of content type.
**Why it's wrong**: Product pages aren't articles. FAQ pages aren't articles. Category pages aren't articles. The CMS is stamping one schema block across all templates.
**Fix**: Map schema to content type per template. Replace Article with the correct primary type.

### 2. Organization Without sameAs or Rich Properties
**What it looks like**: Organization with just name and url.
**Fix**: Add logo, sameAs (social profiles), parentOrganization if applicable, contactPoint for customer service.

### 3. BreadcrumbList Missing on Some Pages
**What it looks like**: Most pages have BreadcrumbList but a few (often homepage, landing pages, or special pages) don't.
**Fix**: Add BreadcrumbList to all non-homepage pages. Verify the ListItem hierarchy matches the visible breadcrumb trail.

### 4. No Rich Result Eligible Schema
**What it looks like**: The site has schema but earns zero rich results because it only uses generic types (Organization, ImageObject, Person).
**Fix**: Add rich-result-eligible types: Product, FAQPage, Recipe, HowTo, VideoObject, etc.

### 5. Duplicate Schema Blocks
**What it looks like**: Multiple identical JSON-LD blocks on the same page (CMS injecting schema in both header and body, or via plugin + theme).
**Fix**: Consolidate to a single JSON-LD block per page. Use @graph if multiple entities needed.

### 6. Missing datePublished / dateModified on Content
**What it looks like**: Article or BlogPosting schema without dates.
**Fix**: Add both dates. If the CMS tracks them, make them dynamic.

---

## JSON-LD Patterns

### Homepage Pattern
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Brand",
      "url": "https://example.com/",
      "logo": { "@type": "ImageObject", "url": "https://example.com/logo.png" },
      "sameAs": ["https://facebook.com/brand", "https://linkedin.com/company/brand"],
      "contactPoint": { "@type": "ContactPoint", "telephone": "+61...", "contactType": "customer service" }
    },
    {
      "@type": "WebSite",
      "@id": "https://example.com/#website",
      "url": "https://example.com/",
      "name": "Brand",
      "publisher": { "@id": "https://example.com/#organization" },
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://example.com/search?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    }
  ]
}
```

### Product Page Pattern
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Product Name",
  "description": "Product description...",
  "image": "https://example.com/product.jpg",
  "url": "https://example.com/products/product-name/",
  "brand": { "@type": "Brand", "name": "Brand" },
  "category": "Product Category",
  "sku": "SKU123",
  "offers": {
    "@type": "Offer",
    "price": "99.95",
    "priceCurrency": "AUD",
    "availability": "https://schema.org/InStock",
    "url": "https://example.com/products/product-name/"
  }
}
```

### Service Page Pattern
```json
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "Service Name",
  "description": "What the service involves...",
  "provider": { "@id": "https://example.com/#organization" },
  "areaServed": { "@type": "Country", "name": "Australia" },
  "serviceType": "Category of service"
}
```

### FAQPage Pattern
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Question text?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Answer text..."
      }
    }
  ]
}
```

### Article Pattern (enriched)
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Article Title",
  "description": "Brief description...",
  "image": "https://example.com/article-hero.jpg",
  "datePublished": "2024-01-15",
  "dateModified": "2024-06-01",
  "author": { "@id": "https://example.com/#organization" },
  "publisher": { "@id": "https://example.com/#organization" },
  "mainEntityOfPage": { "@type": "WebPage", "@id": "https://example.com/blog/article-slug/" },
  "about": { "@type": "Thing", "name": "Topic" }
}
```

### LocalBusiness Pattern
```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Business Name",
  "url": "https://example.com/",
  "telephone": "+61...",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "Sydney",
    "addressRegion": "NSW",
    "postalCode": "2000",
    "addressCountry": "AU"
  },
  "geo": { "@type": "GeoCoordinates", "latitude": -33.8688, "longitude": 151.2093 },
  "openingHoursSpecification": [
    { "@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "09:00", "closes": "17:00" }
  ],
  "sameAs": [],
  "image": "https://example.com/storefront.jpg"
}
```

### MedicalWebPage Pattern
```json
{
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  "name": "Page Title",
  "headline": "H1 Heading",
  "description": "Page meta description...",
  "url": "https://example.com/health-topic/",
  "datePublished": "2024-01-15",
  "dateModified": "2024-06-01",
  "publisher": { "@id": "https://example.com/#organization" },
  "medicalAudience": { "@type": "MedicalAudience", "audienceType": "Patient" },
  "about": { "@type": "MedicalCondition", "name": "Condition Name" },
  "lastReviewed": "2024-06-01",
  "reviewedBy": { "@type": "Organization", "name": "Medical Team" },
  "specialty": "https://schema.org/Oncology"
}
```

### Recipe Pattern
```json
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Recipe Name",
  "description": "Short description...",
  "image": "https://example.com/recipe.jpg",
  "author": { "@id": "https://example.com/#organization" },
  "datePublished": "2024-01-15",
  "prepTime": "PT15M",
  "cookTime": "PT30M",
  "totalTime": "PT45M",
  "recipeYield": "4 servings",
  "recipeCategory": "Category",
  "nutrition": {
    "@type": "NutritionInformation",
    "calories": "350 calories",
    "proteinContent": "18g"
  },
  "recipeIngredient": ["Ingredient 1", "Ingredient 2"],
  "recipeInstructions": [
    { "@type": "HowToStep", "text": "Step 1 instructions..." },
    { "@type": "HowToStep", "text": "Step 2 instructions..." }
  ]
}
```

---

## Industry-Specific Schema

### Healthcare / Medical Nutrition
- Use `MedicalWebPage` for health content (not Article)
- Use `MedicalAudience` with `audienceType: "Patient"` on product and content pages
- Include `lastReviewed` and `reviewedBy` for trust signals
- Use `specialty` property for medical specialisation (Oncology, Gastroenterology, etc.)
- Reference `MedicalCondition`, `MedicalSignOrSymptom`, `MedicalTherapy` for entity connections
- Use `MedicalBusiness` on homepage for medical entity signals
- **Regulated health claims** (in Australia, the TGA): no therapeutic claims in description fields. Use factual nutritional statements. Don't include Offer or pricing for products that are not sold directly online.

### E-commerce / Retail
- Product schema must include `Offer` with accurate `price`, `priceCurrency`, `availability`
- Use `AggregateRating` only if genuine reviews exist on the page
- `Brand` entity enriches product recognition
- Category pages use `ItemList` + `CollectionPage`
- Use `additionalProperty` (PropertyValue) for product specifications

### Professional Services (Legal, Accounting, Consulting)
- Use `ProfessionalService` or specific subtype (LegalService, FinancialService)
- `Service` schema for individual service offerings
- `Review` only from genuine client testimonials visible on page
- Include `areaServed`, `hasOfferCatalog` for service catalogues

### Trades / Home Services (Plumbing, Electrical, Pest Control)
- Use `HomeAndConstructionBusiness` or specific subtype
- `Service` with `areaServed` for each service area
- `FAQPage` where the page really is Q&A (trades queries are often question-shaped)
- `HowTo` for educational content (common in this vertical)
- Include `priceRange` on LocalBusiness if pricing is publicly available

### Food & Beverage / Hospitality
- `Recipe` must match on-page content exactly (ingredients, steps, nutrition)
- `Restaurant` or `FoodEstablishment` for venue pages
- `Menu` and `MenuItem` for menu pages
- `NutritionInformation` values must match on-pack/on-page panels - never estimate

### Education / Training
- `Course` with `CourseInstance` for specific offerings
- Include `educationalCredentialAwarded`, `timeRequired`
- `EducationalOrganization` for the institution
- `hasCourseInstance` with `courseMode` (online, onsite, blended)

### Real Estate
- `RealEstateListing` for property listings
- Include `floorSize`, `numberOfRooms`, `address`
- `RealEstateAgent` for agent/agency pages

---

## Speakable markup

`speakable` (SpeakableSpecification) marks the passages of a page best suited to text-to-speech. Google documents it as a beta feature that lets Google Assistant read news content aloud (US, English only; developers.google.com/search/docs/appearance/structured-data/speakable). There is no published evidence that it changes how AI engines choose what to cite, so only recommend it on news content, and never as a GEO lever.

```json
{
  "@type": "Article",
  "speakable": {
    "@type": "SpeakableSpecification",
    "cssSelector": [".article-summary", ".key-findings"]
  }
}
```

---

## Retired rich results

Google has retired several structured data features. If a crawl shows any of these, flag them for removal to keep the schema lean. Google says the June 2025 change does not affect ranking (source in `_shared/geo-evidence.md`).

- Phased out from June 2025: Book Actions, Course Info, Claim Review, Estimated Salary, Learning Video, Special Announcement, Vehicle Listing.
- Announced November 2025, removed from Search Console from January 2026: further lesser-used features, including Practice Problem structured data. Check Google's documentation changelog (developers.google.com/search/updates) for the current list before flagging anything else.

### Schema must match primary page content

In August 2023 Google limited FAQ rich results to well-known, authoritative government and health sites, and How-To rich results to desktop. Check the current documentation before promising either. Schema must match the primary content of the page.

**What this means for audits:**
- FAQ schema on a page that isn't primarily FAQ content → flag for removal or reassessment
- HowTo schema on a page that isn't primarily instructional → flag for removal
- Review/AggregateRating on pages without genuine visible reviews → flag for removal

---

## Google's current requirements

### General guidelines
1. **Schema must reflect on-page content** - structured data that describes content not on the page is spam
2. **Don't mark up content that's not visible** - hidden tabs, accordions loaded via JS that aren't in initial HTML may not count
3. **One primary entity per page** - use @graph for multiple entities, but each page should have one main purpose
4. **Self-serving reviews are not eligible** - you can't use Review/AggregateRating for your own products on your own site
5. **Offer properties must be accurate** - price, availability, currency must match the live page
6. **FAQPage content must be visible**. Google's 2023 update limited FAQ rich results to authoritative government and health sites
7. **Manual actions** - a structured data manual action removes a page's rich result eligibility (developers.google.com/search/docs/appearance/structured-data/sd-policies)

### Recent changes

- **FAQ and How-To rich results reduced (August 2023)**: FAQ rich results limited to well-known government and health sites, How-To to desktop. Google said this is not a ranking change. FAQPage markup that matches visible Q&A does no harm, but do not promise a rich result for it.
- **Product structured data**: Google keeps investing in product and merchant listing experiences, so Product markup with accurate Offer data is usually the highest-value addition on ecommerce sites.
- **AI Overviews and AI Mode**: Google says no special markup is needed; follow the normal structured data guidelines and make sure the markup matches the visible content.

### What Google Explicitly Does Not Support
- Schema types that have no associated rich result feature still provide semantic value, but Google won't show any visual enhancement for them
- `MedicalWebPage` - no rich result, but entity value
- `Service` - no rich result, but entity value
- `SoftwareSourceCode` - no rich result
- Arbitrary custom schema types - only schema.org types
