---
name: mos-geo-topic-clusters
description: >
  Turn one Ahrefs Organic Keywords or Search Console page+query export into keyword clusters (one cluster = one page) rolled up into topics with a pillar, each mapped to the page ranking today, with a status, an opportunity score, home-page overload and a cannibalisation list. Jev judges pairs; code builds clusters and every number; a human approves each row.
  USE WHEN the user says "topic clusters", "keyword clusters", "keyword clustering", "cluster these keywords", "pillar pages", "which keywords belong on one page", "keyword to page mapping", "cluster my GSC queries", "is the home page ranking for too much", "/mos-geo-topic-clusters", or hands over an Ahrefs or GSC keyword export to group.
  NOT FOR a SEOGets + Screaming Frog cannibalisation audit (pm-seo-kw-cannibalisation-checker), sitemap content gaps (pm-seo-content-gap-analysis), topical maps from seed keywords (pm-seo-topical-map), keyword-to-page cosine mapping against a target list (pm-seo-embedding-inventory), or claiming clusters earn AI citations.
---

# Topic clusters

You are producing a **reviewable content plan**: every keyword the site appears for, grouped into
clusters that one page should target, rolled up into topics, with the page that ranks today, the
status and the next action. A person approves each cluster row before anything is briefed, merged
or redirected.

## Why the rules are strict

1. **Code does counting, Jev does judgement, a human approves.** Parsing, dedupe, walls, candidate
   pairs, clustering, every total, average, share and score are code (`scripts/clusters.py`). Jev
   only answers "should these two searches target the same page?" (same-page / related / different)
   and picks a topic name from the cluster names. It never counts, never enforces transitivity and
   never writes free text.
2. **Embeddings propose, they never decide.** They only find candidate pairs for Jev. Short queries
   sit close in embedding space across intents ("keto recipes" vs "keto meal plan" vs "keto meal
   delivery"), which is exactly the mistake the old TF-IDF + k-means tool made.
3. **Walls never merge.** Own-brand searches are pulled out and reported on their own. Third-party
   brand searches, informational vs commercial searches, and local searches never share a cluster
   with the other side. The local wall is the place itself: "sydney" and "melbourne" searches are
   separate walls, "near me" with no place is its own wall, an Ahrefs Local flag with no place
   another. `mixed` intent can join either intent side.
4. **No chaining.** Clusters form by average linkage over judged pairs. A merge needs the average
   P(same-page) to reach `merge_min`, enough judged pairs between the two groups (`min_coverage`),
   and no pair Jev called "different" (`cannot_link_min_different`). The verify pass then re-judges
   every member against its cluster head, and `cluster` **evicts** any member the head judged below
   `merge_min` or "different": it moves to a cluster whose head judged it same-page, or to
   Unclustered with the reason. So a bridge keyword can't hold two topics together.
5. **Don't sell this as a GEO lever.** Clusters are the coverage map for the sub-questions AI search
   fans out to, and the right unit to group tracked AI prompts by. Topic coverage correlates with AI
   citation in vendor studies; nothing shows clustering causes it. The README says so.

## Pipeline

| # | Stage | Gate before moving on |
|---|---|---|
| 0 | TypeSafe skill + `preflight` | TypeSafe skill installed; export detected (Ahrefs or GSC); `TYPESAFE_API_KEY` set (or dry-run agreed); embeddings provider shown |
| 1 | `ingest` | Row count, duplicates merged, own-brand count and (GSC) multi-page queries look right. Own-brand list checked with the user |
| 2 | `recall` | Candidate pairs counted; recall proxy well above the random baseline; embeddings provider as expected |
| 3 | `judge --dry-run`, then `judge --limit 5` | Cost estimate shown; the 5-request answers read and sensible |
| 4 | `judge` (pairs) | Zero errors; spend logged |
| 5 | `cluster`, then `judge --pass verify` + `cluster` until verify sends 0 requests | Usually 2-3 rounds, cents each |
| 6 | `serp` (optional, off by default) | Dry run first; suspect SERPs reported; re-run `cluster` after |
| 7 | `judge --pass labels`, `build` | xlsx + README + two step folders; headline shown to the user |

Set `SKILL=<this skill's folder>` and run from the user's project so the run folder lands in their brain:

```bash
RUN=$(python3 "$SKILL/scripts/clusters.py" path --brand "<brand>")
mkdir -p "$RUN"
```

Same rules as the other mos-geo skills: `campaigns/geo/YYYY-MM/mos-geo-topic-clusters/` in a
one-brand brain, a brand folder in an agency brain, `outputs/geo/YYYY-MM/<brand>/mos-geo-topic-clusters/`
with no brain, and `-2`, `-3` for repeat runs in a month.

```
<run folder>/
  deliverables/
    keywords-by-cluster.csv           START HERE: every keyword once (Topic, Cluster, Keyword, demand, Position, URL),
                                      topic > cluster order, then Unclustered, then Branded; UTF-8 with BOM for Excel
    README.md                         this run's numbers, the steps, the GEO caveat
    topic-clusters.xlsx               README, Clusters, Topics, Keywords, Cannibalisation, Pages, Unclustered, Branded
    01-review-clusters/               clusters.md (prompt), clusters.csv (approved / review_status / note)
    02-fix-cannibalisation/           cannibalisation.md (prompt), cannibalisation.csv (approved / status / note)
  data/   config.json (the run's effective config), keywords.json, candidates.json, judgements.json, clusters.json, labels.json, serp.json,
          jev_requests.jsonl (+ .index.jsonl), embed_cache.jsonl, jev_cache.jsonl, serp_cache.jsonl,
          usage.json, output_digest.txt
```

Never commit a run folder into this pack: it holds client data.

---

## Stage 0: Setup and inputs

### 0a. Install the TypeSafe skill if it is missing: do this before asking for anything

Jev is TypeSafe's model and the TypeSafe skill carries its current docs. Check, and install
without asking when it is missing:

```bash
claude plugin list 2>/dev/null | grep -qi typesafe && echo installed || echo missing
```

Missing, in Claude Code: run both, then tell the user it loads after a session restart:

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

In another agent, use one method only: `npx skills add typesafe-ai/skills --skill typesafe-ai`.
Load it whenever a Jev primitive, limit, threshold or API shape is in play.

### 0b. Keys

Keys live in a `.env` **outside this repo** (see `.env.example`) and are passed with `--env-file`.
The scripts say "is set" or "is missing" and never print a value.

| Key | Needed for | Without it |
|---|---|---|
| `TYPESAFE_API_KEY` | `judge` (Jev). Required for a real run | Everything up to `judge` runs; `judge` only with `--dry-run` |
| `OPENAI_API_KEY` | Embeddings, **first choice** (`text-embedding-3-small`, 256 dims) | Falls back to Voyage |
| `VOYAGE_API_KEY` | Embeddings, second choice (`voyage-3.5-lite`, 256 dims) | Falls back to none |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | Optional `serp` stage | `serp` is skipped |

**Embeddings fallback: OpenAI, then Voyage, then none.** `--embeddings openai|voyage|none`
overrides. With none, recall uses shared words and the shared ranking URL only, and the README
warns that synonyms with no word in common ("cheap flights" / "budget airfare") can land in
separate clusters. Embeddings cost next to nothing (about $0.0001 for 1,000 keywords) and are
cached by (provider, model, dimensions, text), so reruns are free. An exhausted OpenAI balance
fails fast (HTTP 429 `insufficient_quota`). When `recall` exits on that: if `VOYAGE_API_KEY` is set,
rerun `recall` with `--embeddings voyage`; otherwise rerun with `--embeddings none` and tell the user
that without embeddings, synonyms with no word in common may be missed (the README says so too).
Suggest topping up OpenAI and rerunning from `recall` later: Jev answers are cached, so only new
pairs cost anything.

### 0c. Ask for the file and the brand terms, in one message

- **The export**, either:
  - **Ahrefs** Site Explorer > Organic keywords > Export (CSV, UTF-16, all columns). An
    all-countries export lists each keyword once per country, each with its own volume, position
    and URL. By default only the file's most common Country is used (ingest prints it and how many
    other-country rows it dropped), so demand, position and URL all describe one market.
    `--country XX` picks another; `--country all` sums every country (mixes markets: avoid).
  - **Google Search Console** page + query (the SEOGets export, or any CSV with `page`, `query`,
    `Clicks`, `Impressions`, `Position`). The Search Console UI caps at 1,000 rows: use the API,
    SEOGets or BigQuery for the full set.
- **Brand terms**: the brand name, misspellings and product names (`--brand-terms "a,b,c"`).
  The site's host name is matched automatically (`widgetco.com.au` catches "widgetco").
- **Anything local** the default place list misses (suburbs, regions): put them in a per-run
  `--config` file inside the run folder, e.g. `{"local": {"places": ["bondi", "parramatta"]}}`.

```bash
python3 "$SKILL/scripts/clusters.py" preflight --input <csv> --env-file <.env>
```

Anything that isn't one of the two shapes fails loudly with the columns found. Nothing is guessed.

## Stage 1-2: Ingest and recall

```bash
python3 "$SKILL/scripts/clusters.py" ingest --input <csv> --out "$RUN" --brand-terms "<a,b,c>"
python3 "$SKILL/scripts/clusters.py" recall --run-dir "$RUN" --env-file <.env>
```

- Every keyword keeps a stable id (a hash of its normalised text) and the list of source rows it
  came from (`r2`, `r3` = file line numbers), so nothing shifts when a row is blank or merged.
- Normalising lowercases, turns punctuation into spaces and `tyson's` into `tysons`. Only exact
  normalised duplicates merge at ingest; plurals and word-order variants (identical stemmed words)
  become same-page edges in code without a Jev call.
- **Search-operator queries** (`allintitle:`, `site:` ...) and keywords that normalise to nothing are
  dropped, with counts. URLs are normalised (scheme, host case, trailing slash) so `/a` and `/a/`
  are one page; a blank page is never a ranking URL.
- **GSC rows add up in order:** rows for the same raw URL sum (spelling variants that normalise to
  one keyword, like `tyson's` / `tysons`); jump links (`/page/#section`) are the same page, so across
  them the best fragment counts (one SERP impression can list the page and its jump links; clicks
  still add up); across different pages a query's demand is its **largest** page's impressions and its
  position the **best** page's (one search can show several of your pages). Per-page numbers stay
  for shares and cannibalisation. Ingest prints the multi-page query count before and after.
- **Blank position** stays blank: averages use only rows with a position, and a cluster with no
  position is never Owned. A GSC export without a Position column is refused.
- **Ahrefs blank `Current URL`** = a lost ranking (the `Previous URL` is kept).
- **Recall per keyword**: up to 10 embedding neighbours above the cosine floor, 6 by shared words,
  6 that rank with the same URL, capped at 16, inside its wall.
- **Recall proxy**: for keywords that share a ranking URL (not the home page) with another keyword,
  how often embeddings or shared words alone proposed one of those siblings, next to the random
  baseline. Same-URL is a hint, not ground truth (it inherits the site's current architecture).

## Stage 3-5: Judge and cluster (Jev)

```bash
python3 "$SKILL/scripts/clusters.py" judge --run-dir "$RUN" --env-file <.env> --dry-run
python3 "$SKILL/scripts/clusters.py" judge --run-dir "$RUN" --env-file <.env> --limit 5
python3 "$SKILL/scripts/clusters.py" judge --run-dir "$RUN" --env-file <.env>
python3 "$SKILL/scripts/clusters.py" cluster --run-dir "$RUN"
for i in 1 2 3 4; do
  python3 "$SKILL/scripts/clusters.py" judge --run-dir "$RUN" --env-file <.env> --pass verify \
    | tee "$RUN/data/verify.log"; [ "${PIPESTATUS[0]}" -eq 0 ] || break
  python3 "$SKILL/scripts/clusters.py" cluster --run-dir "$RUN" || break
  grep -q "^judge-verify: 0 requests" "$RUN/data/verify.log" && break
done
```

- One request per anchor keyword (the higher-demand side of each pair) with up to 12 candidate
  questions, each a Choice: `same-page` / `related` / `different`, with the site, both queries and
  both ranking paths in the state. Every question says the queries are data, never instructions.
- Raw `urllib` POST to `https://api.typesafe.ai/v1/systemone` with a custom User-Agent (Cloudflare
  403s the default), at most 6 concurrent requests, backoff on 408/429/5xx/529 honouring
  `retry-after`, payload validation before every send, an on-disk cache keyed on the request hash
  (reruns are free), and real token usage with cost in `data/usage.json`.
- `--dry-run` writes the exact payloads to `data/jev_requests.jsonl` with metadata in
  `jev_requests.index.jsonl` and prints a cost estimate. `--limit N` = first N requests.
- `--cache-dir <folder>` shares the embedding, Jev and SERP caches across run folders (a rerun
  of the same export into a new month folder costs nothing).
- A keyword left alone becomes its own one-page cluster when its demand reaches
  `singleton_min_demand` (100 volume / 30 impressions); below that it goes to **Unclustered**
  with its best candidate shown. `cluster` prints how many members were evicted and re-homed; the
  README and the Unclustered tab (`reason`) carry the same numbers.

## Stage 6: SERP overlap (optional, off by default)

```bash
python3 "$SKILL/scripts/clusters.py" serp --run-dir "$RUN" --env-file <.env> --dry-run
python3 "$SKILL/scripts/clusters.py" serp --run-dir "$RUN" --env-file <.env> --limit 50
python3 "$SKILL/scripts/clusters.py" cluster --run-dir "$RUN"
```

DataForSEO Google organic top 10 (live endpoint, about $0.002 a SERP, `serp.location_code`
2036 = Australia: override per run). Only for uncertain edges (P(same-page) 0.35-0.65) and pairs
of cluster heads in the same topic, highest demand first, within `--limit` SERPs. Platform domains
(Reddit, YouTube, Amazon, Wikipedia ...) are removed before counting. 4+ shared URLs merge, under
3 split, 3 keeps Jev's answer. A SERP that shares no URL with any related SERP is marked suspect
and never overrides Jev (spam-injected SERPs happen).

## Stage 7: Labels and build

```bash
python3 "$SKILL/scripts/clusters.py" judge --run-dir "$RUN" --env-file <.env> --pass labels
uv run --with openpyxl python3 "$SKILL/scripts/clusters.py" build --run-dir "$RUN"
uv run --with openpyxl python "$SKILL/../_shared/brand-audit/tick_checklist.py" \
    --skill mos-geo-topic-clusters --run-dir "$RUN" --note "topic-clusters.xlsx + README in deliverables/"
```

(`_shared/` sits next to this skill in the mos-geo-skills repo; resolve `$SKILL` to the repo copy,
not the `~/.claude/skills` link, if the relative path doesn't resolve.)

- **Cluster name** = its highest-demand keyword (selected, never generated). **Topic name** = Jev's
  pick among the topic's cluster names; the pillar is the cluster with the best mix of demand and
  connections inside the topic (`scoring.pillar_weights`).
- **Per cluster, all in code:** demand (Ahrefs volume or GSC impressions), clicks (GSC clicks or
  Ahrefs traffic estimate), demand-weighted position, the ranking URL and its share, the number of
  ranking URLs, status, opportunity score = demand x (CTR at position 3 − current CTR). GSC uses the
  real CTR; Ahrefs uses the config CTR curve (an assumption, marked PLACEHOLDER).
- **Status:** Owned (top 3), Striking (4-20), Underperforming (below 20), Cannibalised (a second
  URL holds 15%+ of demand within 5 positions), Lost (Ahrefs: used to rank, blank now), Gap-in-list.
- **Home page overload:** the Pages tab counts clusters per URL. The home page's largest cluster
  gets "keep on the home page"; every other cluster it carries gets "create a dedicated page".
- **Cannibalisation tab:** every GSC query with 2+ distinct pages (High: second page 30%+ of
  impressions within 3 positions; Medium: 15%+ AND within 5; else Low; suggested keeper = most
  clicks; brand searches marked) plus every Cannibalised cluster.
- `data/output_digest.txt` hashes every cell except the README spend line: the same export with a
  warm cache gives the same digest.

Show the user the README headline: clusters, topics, statuses, home page load, cannibalisation
count, spend, and the top 10 clusters by opportunity.

## Handing it over

The person running this is usually a marketer, not an SEO. Point them at
`deliverables/keywords-by-cluster.csv` first (Ahrefs columns `Topic,Cluster,Keyword,Volume,KD,Position,URL`;
GSC `Topic,Cluster,Keyword,Impressions,Clicks,Position,URL`), then `deliverables/README.md`.
It lists the steps (review clusters, fix cannibalisation, brief the approved "Create" rows) with this
run's numbers and the GEO caveat. Each step's `.md` opens with "What this is", "What to do" and a
**Prompt for your AI** to paste into Claude Code. The prompts are review-only: the AI walks the
rows highest-opportunity first, records the user's answers in `approved` and `note`, never merges or
splits a cluster itself, and never redirects or deletes a page without an explicit yes for that page.

## Thresholds (all PLACEHOLDER until tuned on labelled pairs)

| Setting | Value | How it was set |
|---|---|---|
| `merge_min` | 0.5 | Average P(same-page) to merge: Jev's own "more likely than not" point. Read on two real exports (an Ahrefs meal-delivery site, a GSC boxing site) |
| `cannot_link_min_different` | 0.5 | Stops chains an average alone lets through (0.95 + 0.05 averages exactly 0.5) |
| `min_coverage` | 0.5 | Judged pairs needed between two groups, as a share of the smaller group |
| `topic_min` / `topic_min_coverage` / `topic_same_weight` | 0.8 / 0.5 / 1.0 | Topic link = P(related) + P(same-page) of judged pairs across two clusters (i.e. 1 − P(different)); 0.8 = average P(different) at most 0.2. Swept on two real runs: that score sits near 0.99 for most recall pairs, so **coverage does most of the discriminating**; P(related) alone (weight 0) either chained keto with high-protein and meal-prep clusters (28-40 clusters) or broke the keto topic into 2-7, so it was rejected |
| `recall.cos_floor` | 0.5 | Generic for 256-dimension `text-embedding-3-small` short queries; not yet measured on real vectors |
| `singleton_min_demand` | 100 / 30 | Keeps real one-keyword pages as clusters, sends long-tail noise to Unclustered |

Tune with about 100 labelled keyword pairs from the user ("same page?" yes/no) before calling any
cluster final. Because raw probabilities are stored, re-thresholding never re-calls Jev.
`ingest` saves the run's effective config to `data/config.json` (defaults + `--config` +
`--brand-terms`/`--country`) and every later stage reads it. To re-threshold, write a partial JSON
(e.g. `{"thresholds": {"merge_min": 0.6}}`) and pass it once:

```bash
python3 "$SKILL/scripts/clusters.py" cluster --run-dir "$RUN" --config over.json   # merged into data/config.json
uv run --with openpyxl python3 "$SKILL/scripts/clusters.py" build --run-dir "$RUN"   # uses the saved config
```

## Reference map

| File | Read it when |
|---|---|
| `config/defaults.json` | Changing walls, recall, thresholds, SERP settings or scoring (override with `--config`) |
| `scripts/clusters.py` | The docstring lists every subcommand; `average_linkage`, `score_cluster`, `compatible` hold the rules |
| `scripts/test_clusters.py` | Before changing a rule: `python3 -m unittest scripts/test_clusters.py` (offline; add `uv run --with openpyxl` to test the xlsx too) |
| `.env.example` | Setting up keys, outside the repo |

## Things that will bite you

**The home page ranks for everything.** On small sites the home page often holds the core service
cluster plus a dozen others. The first is fine; the rest are the "create a dedicated page" rows.

**Ahrefs "Branded" includes competitors.** Those rows form their own walled partition (useful for
"X alternative" pages) and are listed as third-party on the Branded tab. Only `--brand-terms` and
the host name decide own-brand.

**GSC position is impression-weighted and GSC has no volume.** Demand on a GSC run is impressions,
which under-count searches you rank badly for. Anonymised queries are missing entirely. Say so when
you present totals.

**A keyword export only shows where the site already appears.** Gap-in-list is rare by design;
real gaps need seed or competitor research on top.

**Rate limit, not cost, is the constraint.** Jev costs about $0.10-0.20 per ~1,500 keywords (run
`judge --dry-run` for the exact estimate) and takes a couple of minutes at 6 concurrent. Pin the Jev model
(the response `model` field) once thresholds are tuned; `jev-latest` moves.

**Nothing client-specific belongs in this skill.** Brand terms, suburbs, country filters and
location codes go on the command line or in a per-run `--config` file in the run folder.
