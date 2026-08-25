#!/usr/bin/env bash
# recon.sh — detect a client site's tech stack and extract its brand tokens.
#
# This is the hard prerequisite step for the LLM-buttons skill:
#   * the detected stack decides the implementation route (WordPress plugin/snippet
#     vs. component vs. raw <script> embed), and
#   * the extracted palette decides the styling of the buttons.
#
# Usage:
#   ./recon.sh <url> [--out <dir>] [--json]
#
# Output:
#   Human-readable markdown on stdout (always written to <out>/recon.md).
#   With --json, stdout is JSON instead and <out>/recon.json is also written.
#
# Notes:
#   - Colour/font extraction reuses the approach proven in
#     pm-skills/pm-client-context-generator/scripts/extract-brand-assets.sh
#     (stylesheet discovery, URL resolution, hex frequency counting, font-family
#     harvesting) with CSS custom properties added as the highest-signal path.
#   - No JavaScript is executed. CSS-in-JS and SPA-rendered styles are invisible
#     to curl; the report says so explicitly rather than guessing.
#   - Australian spelling used throughout (colour, normalise, behaviour).
#   - Writes only inside the --out directory. Never touches the repo.
#
# Exit codes: 0 ok, 1 usage error, 2 could not fetch the page.

set -euo pipefail

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# ---------------------------------------------------------------- arguments --
URL=""
OUT=""
EMIT_JSON=0

usage() {
  cat >&2 <<'USAGE'
Usage: recon.sh <url> [--out <dir>] [--json]

  <url>          Site to recon (scheme optional; https:// assumed).
  --out <dir>    Directory for recon.md / recon.json / working files.
                 Default: a fresh temp directory (path is printed).
  --json         Emit JSON on stdout instead of markdown (markdown still saved).
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --out)  [ $# -ge 2 ] || { usage; exit 1; }; OUT="$2"; shift 2 ;;
    --json) EMIT_JSON=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "recon.sh: unknown option '$1'" >&2; usage; exit 1 ;;
    *)  [ -z "$URL" ] || { echo "recon.sh: unexpected argument '$1'" >&2; exit 1; }
        URL="$1"; shift ;;
  esac
done

[ -n "$URL" ] || { usage; exit 1; }
case "$URL" in http://*|https://*) : ;; *) URL="https://$URL" ;; esac

if [ -z "$OUT" ]; then
  OUT="$(mktemp -d 2>/dev/null || mktemp -d -t recon)"
else
  mkdir -p "$OUT"
fi
OUT="$(cd "$OUT" && pwd)"

WORK="$OUT/.work"
mkdir -p "$WORK"

REPORT="$OUT/recon.md"
: > "$REPORT"
say() { printf '%s\n' "$*" >> "$REPORT"; }

# ------------------------------------------------------------ URL plumbing --
SCHEME="${URL%%://*}"
REST="${URL#*://}"
HOSTPORT="${REST%%/*}"
case "$REST" in
  */*) PATHPART="/${REST#*/}" ;;
  *)   PATHPART="/" ;;
esac
PATHPART="${PATHPART%%\?*}"
PATHPART="${PATHPART%%#*}"
ORIGIN="$SCHEME://$HOSTPORT"

# Directory portion of the page path, no trailing slash ("" for root).
case "$PATHPART" in
  */) PAGE_DIR="${PATHPART%/}" ;;
  *)  PAGE_DIR="${PATHPART%/*}" ;;
esac

resolve_url() {
  # Resolve a stylesheet href against the page origin. Handles absolute,
  # protocol-relative (//cdn/x.css), root-relative (/x.css) and relative forms.
  case "$1" in
    http://*|https://*) printf '%s' "$1" ;;
    //*)                printf '%s:%s' "$SCHEME" "$1" ;;
    /*)                 printf '%s%s' "$ORIGIN" "$1" ;;
    *)                  printf '%s%s/%s' "$ORIGIN" "$PAGE_DIR" "$1" ;;
  esac
}

lower() { tr '[:upper:]' '[:lower:]'; }

# ----------------------------------------------------------------- fetching --
HDR="$WORK/headers.txt"
PAGE="$WORK/page.html"
: > "$HDR"

# Response headers via HEAD, exactly as briefed. Some hosts refuse HEAD, so the
# GET below also dumps its headers and the two are merged.
curl -sSIL --max-time 25 -A "$UA" "$URL" >> "$HDR" 2>/dev/null || true

FETCH_OK=1
if ! curl -sSL --max-time 30 -A "$UA" -D "$WORK/headers-get.txt" -o "$PAGE" "$URL" 2>"$WORK/curl.err"; then
  FETCH_OK=0
fi
[ -f "$WORK/headers-get.txt" ] && cat "$WORK/headers-get.txt" >> "$HDR"
[ -f "$PAGE" ] || : > "$PAGE"

if [ "$FETCH_OK" -eq 0 ] && [ ! -s "$PAGE" ]; then
  echo "recon.sh: could not fetch $URL" >&2
  sed -n '1,5p' "$WORK/curl.err" >&2 || true
  exit 2
fi

FINAL_URL="$(curl -sSL --max-time 25 -A "$UA" -o /dev/null -w '%{url_effective}' "$URL" 2>/dev/null || printf '%s' "$URL")"
HTTP_CODE="$(curl -sSL --max-time 25 -A "$UA" -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo "000")"

# Normalise the HTML for attribute scraping: single quotes -> double quotes,
# entity-decoded ampersands, one tag per line where cheaply possible.
tr "'" '"' < "$PAGE" | sed -e 's/&amp;/\&/g' > "$WORK/page.q.html"
PAGEQ="$WORK/page.q.html"

hdr_get() {
  # Last occurrence of a header wins (end of the redirect chain).
  grep -i "^$1:" "$HDR" 2>/dev/null | tail -1 | sed -E 's/^[^:]*:[[:space:]]*//' | tr -d '\r' || true
}

# =============================================================== A. STACK ====
SERVER="$(hdr_get 'server')"
XPB="$(hdr_get 'x-powered-by')"
XVERCEL="$(hdr_get 'x-vercel-id')"
CFRAY="$(hdr_get 'cf-ray')"
XGEN="$(hdr_get 'x-generator')"

NEXT_HDRS="$(grep -iE '^x-nextjs-[a-z-]*:' "$HDR" 2>/dev/null | tr -d '\r' | sort -u | tr '\n' '; ' || true)"
DRUPAL_HDRS="$(grep -iE '^x-drupal-[a-z-]*:' "$HDR" 2>/dev/null | tr -d '\r' | sort -u | tr '\n' '; ' || true)"
SHOPIFY_HDRS="$(grep -iE '^x-shopify-[a-z-]*:|^x-shopid:|^x-shardid:' "$HDR" 2>/dev/null | tr -d '\r' | sort -u | tr '\n' '; ' || true)"

META_GEN="$(grep -oiE '<meta[^>]*name="generator"[^>]*>' "$PAGEQ" 2>/dev/null \
  | grep -oiE 'content="[^"]*"' | head -1 | sed -E 's/^[Cc]ontent="//; s/"$//' || true)"

# Asset-path fingerprints in the HTML.
: > "$WORK/fingerprints.txt"
# NOTE: the Git Bash grep on Windows aborts (SIGABRT) when -i and -F are combined,
# so every case-insensitive search below uses plain -i with a regex-safe needle.
fp() { # fp <needle> <label>  — case-sensitive literal match
  if grep -qF "$1" "$PAGEQ" 2>/dev/null; then printf '%s (matched "%s")\n' "$2" "$1" >> "$WORK/fingerprints.txt"; fi
}
fp '/_next/'              'Next.js'
fp '/_astro/'             'Astro'
fp '/wp-content/'         'WordPress'
fp '/wp-includes/'        'WordPress'
fp 'cdn.shopify.com'      'Shopify'
fp 'assets.squarespace.com' 'Squarespace'
fp 'static1.squarespace.com' 'Squarespace'
fp '/media/jui/'          'Joomla'
fp '/sites/default/files/' 'Drupal'
fp 'drupal-settings-json' 'Drupal'
fp 'Drupal.settings'      'Drupal'
if grep -qi 'webflow' "$PAGEQ" 2>/dev/null; then echo 'Webflow (matched "webflow")' >> "$WORK/fingerprints.txt"; fi
if grep -qi '_nuxt'   "$PAGEQ" 2>/dev/null; then echo 'Nuxt (matched "_nuxt")'      >> "$WORK/fingerprints.txt"; fi
if grep -qi 'gatsby'  "$PAGEQ" 2>/dev/null; then echo 'Gatsby (matched "gatsby")'   >> "$WORK/fingerprints.txt"; fi
sort -u "$WORK/fingerprints.txt" -o "$WORK/fingerprints.txt"

# --- WordPress probes (this is the routing switch) -------------------------
WPJSON_CODE="$(curl -sSL --max-time 15 -A "$UA" -o "$WORK/wpjson.txt" -w '%{http_code}' "$ORIGIN/wp-json/" 2>/dev/null || echo "000")"
WPJSON_IS_JSON="no"
if [ -s "$WORK/wpjson.txt" ] && head -c 400 "$WORK/wpjson.txt" | grep -qE '^[[:space:]]*\{' \
   && head -c 4000 "$WORK/wpjson.txt" | grep -qiE '"(name|namespaces|routes|description|gmt_offset)"'; then
  WPJSON_IS_JSON="yes"
fi
WPLOGIN_CODE="$(curl -sSL --max-time 15 -A "$UA" -o "$WORK/wplogin.html" -w '%{http_code}' "$ORIGIN/wp-login.php" 2>/dev/null || echo "000")"
WPLOGIN_REAL="no"
if [ "$WPLOGIN_CODE" = "200" ] && grep -qiE 'name="log"|id="loginform"|wp-submit' "$WORK/wplogin.html" 2>/dev/null; then
  WPLOGIN_REAL="yes"
fi

IS_WORDPRESS="false"
if [ "$WPJSON_IS_JSON" = "yes" ] || [ "$WPLOGIN_REAL" = "yes" ] \
   || grep -q 'WordPress' <<<"$META_GEN" 2>/dev/null \
   || grep -qE 'WordPress' "$WORK/fingerprints.txt" 2>/dev/null; then
  IS_WORDPRESS="true"
fi

# --- verdict ---------------------------------------------------------------
has_fp() { grep -qi "^$1" "$WORK/fingerprints.txt" 2>/dev/null; }
gen_is()  { printf '%s' "$META_GEN" | grep -qi "$1"; }

DETECTED="Unknown / bespoke"
if [ "$IS_WORDPRESS" = "true" ]; then DETECTED="WordPress"
elif has_fp 'Shopify'      || [ -n "$SHOPIFY_HDRS" ]; then DETECTED="Shopify"
elif has_fp 'Squarespace'  || gen_is 'squarespace';   then DETECTED="Squarespace"
elif has_fp 'Webflow'      || gen_is 'webflow';       then DETECTED="Webflow"
elif gen_is 'astro'        || has_fp 'Astro';         then DETECTED="Astro"
elif has_fp 'Next.js'      || [ -n "$NEXT_HDRS" ];    then DETECTED="Next.js"
elif has_fp 'Nuxt';                                   then DETECTED="Nuxt"
elif has_fp 'Gatsby';                                 then DETECTED="Gatsby"
elif has_fp 'Joomla'       || gen_is 'joomla';        then DETECTED="Joomla"
elif has_fp 'Drupal'       || [ -n "$DRUPAL_HDRS" ] || gen_is 'drupal'; then DETECTED="Drupal"
elif gen_is 'wix';                                    then DETECTED="Wix"
fi

HOSTING=""
if [ -n "$XVERCEL" ] || printf '%s' "$SERVER" | grep -qi 'vercel'; then HOSTING="Vercel"
elif printf '%s' "$SERVER" | grep -qi 'netlify'; then HOSTING="Netlify"
elif printf '%s' "$SERVER" | grep -qi 'cloudflare'; then HOSTING="Cloudflare"
elif printf '%s' "$SERVER" | grep -qi 'github.com'; then HOSTING="GitHub Pages"
elif [ -n "$CFRAY" ]; then HOSTING="behind Cloudflare"
elif [ -n "$SERVER" ]; then HOSTING="$SERVER"
fi

# Confidence = how many independent signal families agree.
SIGNALS=0
[ -n "$META_GEN" ] && SIGNALS=$((SIGNALS + 1))
[ -s "$WORK/fingerprints.txt" ] && SIGNALS=$((SIGNALS + 1))
{ [ -n "$SERVER" ] || [ -n "$XPB" ] || [ -n "$XGEN" ] || [ -n "$NEXT_HDRS" ] || [ -n "$SHOPIFY_HDRS" ] || [ -n "$DRUPAL_HDRS" ]; } && SIGNALS=$((SIGNALS + 1))
[ "$WPJSON_IS_JSON" = "yes" ] && SIGNALS=$((SIGNALS + 1))

if [ "$DETECTED" = "Unknown / bespoke" ]; then CONFIDENCE="low"
elif [ "$SIGNALS" -ge 2 ]; then CONFIDENCE="high"
else CONFIDENCE="medium"; fi

# =========================================================== B. ANALYTICS ====
grep -oE 'GTM-[A-Z0-9]{4,}'  "$PAGEQ" 2>/dev/null | sort -u > "$WORK/gtm.txt"  || true
grep -oE 'G-[A-Z0-9]{6,}'    "$PAGEQ" 2>/dev/null | sort -u > "$WORK/ga4.txt"  || true
grep -oE 'UA-[0-9]{4,}-[0-9]+' "$PAGEQ" 2>/dev/null | sort -u >> "$WORK/ga4.txt" || true
sort -u "$WORK/ga4.txt" -o "$WORK/ga4.txt" 2>/dev/null || true

: > "$WORK/analytics_other.txt"
an() { if grep -qi "$1" "$PAGEQ" 2>/dev/null; then printf '%s\n' "$2" >> "$WORK/analytics_other.txt"; fi; }
an 'cdn.segment.com'        'Segment (analytics.js)'
an 'analytics.track('       'Segment (analytics.track call)'
an 'cdn.mxpnl.com'          'Mixpanel'
an 'mixpanel.init'          'Mixpanel'
an 'amplitude'              'Amplitude'
an 'posthog'                'PostHog'
an 'plausible.io'           'Plausible'
an 'static.hotjar.com'      'Hotjar'
an 'connect.facebook.net'   'Meta Pixel'
an 'clarity.ms'             'Microsoft Clarity'
an 'gtag('                  'gtag.js present (GA4 or Google Ads)'
an 'dataLayer'              'dataLayer present (GTM data layer)'
sort -u "$WORK/analytics_other.txt" -o "$WORK/analytics_other.txt" 2>/dev/null || true

# ================================================================= C. CSP ====
CSP_HDR="$(hdr_get 'content-security-policy')"
CSPRO_HDR="$(hdr_get 'content-security-policy-report-only')"
CSP_META="$(grep -oiE '<meta[^>]*http-equiv="content-security-policy"[^>]*>' "$PAGEQ" 2>/dev/null \
  | grep -oiE 'content="[^"]*"' | head -1 | sed -E 's/^[Cc]ontent="//; s/"$//' || true)"

CSP_ALL="$CSP_HDR"
[ -n "$CSP_META" ] && CSP_ALL="$CSP_ALL ; $CSP_META"

csp_directive() {
  printf '%s' "$CSP_ALL" | tr ';' '\n' | grep -iE "^[[:space:]]*$1[[:space:]]" | head -1 \
    | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' || true
}
CSP_SCRIPT="$(csp_directive 'script-src')"
CSP_CONNECT="$(csp_directive 'connect-src')"
CSP_DEFAULT="$(csp_directive 'default-src')"

CSP_INLINE_RISK="no CSP detected — inline script is fine"
if [ -n "$CSP_HDR" ] || [ -n "$CSP_META" ]; then
  EFFECTIVE_SCRIPT="$CSP_SCRIPT"
  [ -z "$EFFECTIVE_SCRIPT" ] && EFFECTIVE_SCRIPT="$CSP_DEFAULT"
  if [ -z "$EFFECTIVE_SCRIPT" ]; then
    CSP_INLINE_RISK="CSP present but no script-src/default-src — inline script probably allowed [VERIFY]"
  elif printf '%s' "$EFFECTIVE_SCRIPT" | grep -qi "unsafe-inline"; then
    CSP_INLINE_RISK="'unsafe-inline' allowed — inline script OK"
  elif printf '%s' "$EFFECTIVE_SCRIPT" | grep -qiE "nonce-|sha256-|sha384-|sha512-"; then
    CSP_INLINE_RISK="BLOCKING: nonce/hash-based CSP — inline script needs a matching nonce or hash, or must ship as an external file"
  else
    CSP_INLINE_RISK="BLOCKING: inline script will be refused — ship the widget as an external file from an allowed origin"
  fi
fi

# ======================================================== D. BRAND TOKENS ====
grep -oE 'href="[^"]*\.css[^"]*"' "$PAGEQ" 2>/dev/null \
  | sed -E 's/^href="//; s/"$//' \
  | grep -vE '^(data:|javascript:)' \
  | awk '!seen[$0]++' | head -10 > "$WORK/css_urls.txt" || true

CSS_COUNT=0
STYLES="$WORK/all_styles.txt"
cat "$PAGE" > "$STYLES"          # inline <style> blocks and style="" attributes
: > "$WORK/css_resolved.txt"
while IFS= read -r css_path; do
  [ -z "$css_path" ] && continue
  full_url="$(resolve_url "$css_path")"
  printf '%s\n' "$full_url" >> "$WORK/css_resolved.txt"
  if curl -sSL --max-time 15 -A "$UA" "$full_url" >> "$STYLES" 2>/dev/null; then
    CSS_COUNT=$((CSS_COUNT + 1))
  fi
  printf '\n' >> "$STYLES"
done < "$WORK/css_urls.txt"

# --- CSS custom properties: the highest-signal path ------------------------
# Matches both pretty-printed and minified CSS: --name: value;
grep -oE '\-\-[A-Za-z0-9][A-Za-z0-9_-]*[[:space:]]*:[[:space:]]*[^;{}]{1,140}' "$STYLES" 2>/dev/null \
  | sed -E 's/[[:space:]]*:[[:space:]]*/\t/; s/[[:space:]]+$//' \
  | grep -vE '^\S+\t$' \
  | awk -F'\t' 'NF==2 && !seen[$0]++' > "$WORK/customprops.tsv" || true

# Colour-valued custom properties (hex / rgb / hsl / oklch / color-mix).
awk -F'\t' '$2 ~ /^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|oklch\(|oklab\(|lab\(|lch\(|color\(|color-mix\()/' \
  "$WORK/customprops.tsv" > "$WORK/colour_tokens.tsv" 2>/dev/null || true

# Semantic-looking names get promoted to the top of the palette.
SEMANTIC_RE='colou?r|bg|background|surface|text|accent|brand|primary|secondary|tertiary|fg|foreground|ink|paper|border|muted|link|success|warn|error|danger|info|shade|tint|theme'
awk -F'\t' -v re="$SEMANTIC_RE" 'tolower($1) ~ re' "$WORK/colour_tokens.tsv" > "$WORK/colour_semantic.tsv" 2>/dev/null || true
awk -F'\t' -v re="$SEMANTIC_RE" 'tolower($1) !~ re' "$WORK/colour_tokens.tsv" > "$WORK/colour_other.tsv" 2>/dev/null || true

N_COLOUR_TOKENS="$(wc -l < "$WORK/colour_tokens.tsv" 2>/dev/null | tr -d ' ' || echo 0)"
[ -z "$N_COLOUR_TOKENS" ] && N_COLOUR_TOKENS=0

# --- hex frequency fallback (the extract-brand-assets.sh approach) ----------
grep -oE '#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}[^0-9a-fA-F]' "$STYLES" 2>/dev/null \
  | sed -E 's/#([0-9a-fA-F]{6}).*/#\1/; s/#([0-9a-fA-F]{3})[^0-9a-fA-F]/#\1/' \
  | lower | sort | uniq -c | sort -rn | head -20 > "$WORK/hexcounts.txt" || true
N_HEX="$(wc -l < "$WORK/hexcounts.txt" 2>/dev/null | tr -d ' ' || echo 0)"
[ -z "$N_HEX" ] && N_HEX=0

if [ "$N_COLOUR_TOKENS" -ge 3 ]; then
  PALETTE_METHOD="CSS custom properties (design tokens read straight from the stylesheet — highest confidence)"
elif [ "$N_HEX" -ge 3 ]; then
  PALETTE_METHOD="raw hex frequency counting (no usable custom properties found — treat ranking as a hint, not a token map)"
else
  PALETTE_METHOD="INSUFFICIENT DATA — [VERIFY — could not auto-extract]"
fi

# --- fonts -----------------------------------------------------------------
grep -ioE 'font-family[[:space:]]*:[[:space:]]*[^;{}"]{1,160}' "$STYLES" 2>/dev/null \
  | sed -E 's/^[Ff][Oo][Nn][Tt]-[Ff][Aa][Mm][Ii][Ll][Yy][[:space:]]*:[[:space:]]*//; s/[[:space:]]+$//' \
  | grep -vE '^(inherit|initial|unset|revert)$' \
  | grep -v '^$' | sort | uniq -c | sort -rn | head -20 > "$WORK/fonts_counted.txt" || true
sed -E 's/^[[:space:]]*[0-9]+[[:space:]]+//' "$WORK/fonts_counted.txt" > "$WORK/fonts.txt" 2>/dev/null || true

# Font-ish custom properties (e.g. --font-display: "Bricolage Grotesque").
# Deliberately excludes the size/weight/leading/tracking scale — we want the
# FAMILY tokens, which are what the buttons actually have to match.
awk -F'\t' '
  tolower($1) ~ /size|weight|leading|tracking|height|spacing|style|width|scale|step/ { next }
  tolower($1) ~ /font|typeface|family/ { print; next }
  $2 ~ /(serif|sans-serif|monospace|cursive|system-ui|ui-monospace)/ { print }
' "$WORK/customprops.tsv" > "$WORK/font_tokens.tsv" 2>/dev/null || true

grep -oE 'fonts\.googleapis\.com[^"'"'"' )>]*' "$STYLES" 2>/dev/null | sed 's/&amp;/\&/g' | sort -u | head -8 > "$WORK/gfonts.txt" || true

# Family names named in Google Fonts URLs / @font-face — useful cross-check.
{
  grep -oE 'family=[^"&'"'"' )>]+' "$WORK/gfonts.txt" 2>/dev/null | sed -E 's/^family=//; s/:.*$//; s/\+/ /g'
  grep -oE '@font-face[^}]*font-family[[:space:]]*:[[:space:]]*[^;}]+' "$STYLES" 2>/dev/null \
    | sed -E 's/.*font-family[[:space:]]*:[[:space:]]*//; s/[[:space:]]*$//' | tr -d '"'
} 2>/dev/null | grep -v '^$' | sort -u | head -12 > "$WORK/font_families.txt" || true

# --- SPA / CSS-in-JS escalation check --------------------------------------
SPA_NOTE=""
if [ "$CSS_COUNT" -eq 0 ] || [ "$N_HEX" -lt 5 ]; then
  SPA_NOTE="This site looks JS-rendered (SPA) or uses CSS-in-JS: ${CSS_COUNT} stylesheet(s) fetched, ${N_HEX} distinct hex value(s) found. CSS-in-JS rules are injected at runtime and NEVER exist as text in the served HTML or in any .css file, so curl cannot see them. ESCALATE: load the page in a real browser and serialise the computed styles — e.g. getComputedStyle(document.body), and iterate document.styleSheets[].cssRules to dump the injected rules. Do not guess the palette from what is above."
fi

# =========================================================== E. SITEMAPS =====
: > "$WORK/sitemaps.txt"
probe_sitemap() {
  local u="$1" code n
  code="$(curl -sSL --max-time 15 -A "$UA" -o "$WORK/sm.tmp" -w '%{http_code}' "$u" 2>/dev/null || echo "000")"
  if [ "$code" = "200" ] && grep -qiE '<(urlset|sitemapindex)' "$WORK/sm.tmp" 2>/dev/null; then
    n="$(grep -oE '<loc>' "$WORK/sm.tmp" 2>/dev/null | wc -l | tr -d ' ')"
    if grep -qi '<sitemapindex' "$WORK/sm.tmp" 2>/dev/null; then
      printf '%s | HTTP %s | sitemap INDEX | %s child sitemap(s)\n' "$u" "$code" "$n" >> "$WORK/sitemaps.txt"
    else
      printf '%s | HTTP %s | urlset | %s URL(s)\n' "$u" "$code" "$n" >> "$WORK/sitemaps.txt"
    fi
  else
    printf '%s | HTTP %s | not a sitemap\n' "$u" "$code" >> "$WORK/sitemaps.txt"
  fi
}
probe_sitemap "$ORIGIN/sitemap.xml"
probe_sitemap "$ORIGIN/sitemap_index.xml"

ROBOTS_CODE="$(curl -sSL --max-time 15 -A "$UA" -o "$WORK/robots.txt" -w '%{http_code}' "$ORIGIN/robots.txt" 2>/dev/null || echo "000")"
: > "$WORK/robots_sitemaps.txt"
if [ "$ROBOTS_CODE" = "200" ]; then
  grep -iE '^[[:space:]]*sitemap[[:space:]]*:' "$WORK/robots.txt" 2>/dev/null \
    | sed -E 's/^[[:space:]]*[Ss]itemap[[:space:]]*:[[:space:]]*//' | tr -d '\r' | sort -u > "$WORK/robots_sitemaps.txt" || true
  # Follow whatever robots.txt declares — plenty of sites use a non-standard name
  # (e.g. /sitemap-index.xml) and the two conventional probes above both 404.
  while IFS= read -r sm; do
    [ -z "$sm" ] && continue
    grep -qF "$sm |" "$WORK/sitemaps.txt" 2>/dev/null && continue
    probe_sitemap "$sm"
  done < "$WORK/robots_sitemaps.txt"
fi

# ============================================================== REPORT =======
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

say "# Recon — $URL"
say ""
say "- Generated: \`$NOW\`"
say "- Final URL after redirects: \`$FINAL_URL\` (HTTP $HTTP_CODE)"
say "- Origin: \`$ORIGIN\`"
say "- Working files: \`$OUT\`"
say ""
say "## A. Tech stack"
say ""
say "**detected_stack: $DETECTED**${HOSTING:+ (hosted on / fronted by $HOSTING)}"
say ""
say "- **is_wordpress: $IS_WORDPRESS**  <- routing switch for this skill"
say "- confidence: **$CONFIDENCE** ($SIGNALS independent signal famil$([ "$SIGNALS" = "1" ] && echo y || echo ies) agreed)"
say ""
say "### Response headers"
say ""
if [ -n "$SERVER" ];       then say "- \`server:\` $SERVER";             else say "- \`server:\` (absent)"; fi
if [ -n "$XPB" ];          then say "- \`x-powered-by:\` $XPB";          else say "- \`x-powered-by:\` (absent)"; fi
if [ -n "$XVERCEL" ];      then say "- \`x-vercel-id:\` $XVERCEL";       else say "- \`x-vercel-id:\` (absent)"; fi
if [ -n "$CFRAY" ];        then say "- \`cf-ray:\` $CFRAY";              else say "- \`cf-ray:\` (absent)"; fi
if [ -n "$XGEN" ];         then say "- \`x-generator:\` $XGEN";          else say "- \`x-generator:\` (absent)"; fi
if [ -n "$NEXT_HDRS" ];    then say "- \`x-nextjs-*:\` $NEXT_HDRS";      else say "- \`x-nextjs-*:\` (absent)"; fi
if [ -n "$DRUPAL_HDRS" ];  then say "- \`x-drupal-*:\` $DRUPAL_HDRS";    else say "- \`x-drupal-*:\` (absent)"; fi
if [ -n "$SHOPIFY_HDRS" ]; then say "- \`x-shopify-*:\` $SHOPIFY_HDRS";  else say "- \`x-shopify-*:\` (absent)"; fi
say ""
say "### meta generator"
say ""
if [ -n "$META_GEN" ]; then say "- \`<meta name=\"generator\">\` = **$META_GEN**"; else say "- none present"; fi
say ""
say "### Asset-path fingerprints"
say ""
if [ -s "$WORK/fingerprints.txt" ]; then
  while IFS= read -r l; do say "- $l"; done < "$WORK/fingerprints.txt"
else
  say "- none of the known fingerprints matched"
fi
say ""
say "### WordPress probes"
say ""
say "- \`$ORIGIN/wp-json/\` -> HTTP $WPJSON_CODE, JSON REST payload: **$WPJSON_IS_JSON**"
if [ "$WPJSON_IS_JSON" = "yes" ]; then
  say "  - REST API is **reachable** — the WordPress route (plugin / mu-plugin / REST-driven injection) is available."
else
  say "  - REST API not confirmed. If this site *is* WordPress, the REST API may be disabled or firewalled — fall back to a theme/snippet route."
fi
say "- \`$ORIGIN/wp-login.php\` -> HTTP $WPLOGIN_CODE, real login form: **$WPLOGIN_REAL**"
say ""
say "## B. Analytics"
say ""
if [ -s "$WORK/gtm.txt" ]; then
  while IFS= read -r l; do say "- GTM container: \`$l\`"; done < "$WORK/gtm.txt"
else
  say "- GTM container: none found"
fi
if [ -s "$WORK/ga4.txt" ]; then
  while IFS= read -r l; do say "- Google measurement ID: \`$l\`"; done < "$WORK/ga4.txt"
else
  say "- Google measurement ID (G-… / UA-…): none found"
fi
if [ -s "$WORK/analytics_other.txt" ]; then
  while IFS= read -r l; do say "- $l"; done < "$WORK/analytics_other.txt"
fi
say ""
if [ -s "$WORK/gtm.txt" ]; then
  say "**Tracking route:** push the button-click event to \`dataLayer\` and let GTM fan it out."
elif [ -s "$WORK/ga4.txt" ]; then
  say "**Tracking route:** call \`gtag('event', ...)\` directly against the measurement ID above."
else
  say "**Tracking route:** [VERIFY — could not auto-extract] no analytics endpoint found in the served HTML. The widget's click event has nowhere to land; either the analytics loads via a tag manager injected client-side, or the client has none. Confirm with the client before shipping tracking code."
fi
say ""
say "## C. Content Security Policy"
say ""
if [ -n "$CSP_HDR" ]; then say "- \`content-security-policy\` header: \`$CSP_HDR\`"; else say "- \`content-security-policy\` header: (absent)"; fi
if [ -n "$CSPRO_HDR" ]; then say "- \`content-security-policy-report-only\` header: \`$CSPRO_HDR\`"; fi
if [ -n "$CSP_META" ]; then say "- \`<meta http-equiv=\"Content-Security-Policy\">\`: \`$CSP_META\`"; else say "- \`<meta http-equiv=\"Content-Security-Policy\">\`: (absent)"; fi
say ""
if [ -n "$CSP_SCRIPT" ];  then say "- **script-src:** \`$CSP_SCRIPT\`"; else say "- **script-src:** not specified"; fi
if [ -n "$CSP_CONNECT" ]; then say "- **connect-src:** \`$CSP_CONNECT\`"; else say "- **connect-src:** not specified"; fi
if [ -n "$CSP_DEFAULT" ]; then say "- default-src: \`$CSP_DEFAULT\`"; fi
say ""
say "- **Shipping impact:** $CSP_INLINE_RISK"
say ""
say "## D. Brand tokens"
say ""
say "- Stylesheets discovered in HTML: $(wc -l < "$WORK/css_urls.txt" 2>/dev/null | tr -d ' ') (fetched OK: $CSS_COUNT)"
if [ -s "$WORK/css_resolved.txt" ]; then
  while IFS= read -r l; do say "  - \`$l\`"; done < "$WORK/css_resolved.txt"
fi
say "- Custom properties found: $(wc -l < "$WORK/customprops.tsv" 2>/dev/null | tr -d ' ') (colour-valued: $N_COLOUR_TOKENS)"
say "- **Palette method: $PALETTE_METHOD**"
say ""
say "### Palette — CSS custom properties"
say ""
if [ "$N_COLOUR_TOKENS" -gt 0 ]; then
  if [ -s "$WORK/colour_semantic.tsv" ]; then
    say "Semantic-looking token names first:"
    say ""
    while IFS="$(printf '\t')" read -r k v; do [ -n "$k" ] && say "- \`$k: $v\`"; done < "$WORK/colour_semantic.tsv"
    say ""
  fi
  if [ -s "$WORK/colour_other.tsv" ]; then
    say "Other colour-valued tokens (bespoke names — often the actual brand palette):"
    say ""
    while IFS="$(printf '\t')" read -r k v; do [ -n "$k" ] && say "- \`$k: $v\`"; done < "$WORK/colour_other.tsv"
    say ""
  fi
else
  say "- none found — **[VERIFY — could not auto-extract]**"
  say ""
fi
say "### Palette — hex frequency (fallback / cross-check)"
say ""
if [ -s "$WORK/hexcounts.txt" ]; then
  awk 'NF==2 {printf "- `%s` — %s use(s)\n", $2, $1}' "$WORK/hexcounts.txt" >> "$REPORT"
else
  say "- no hex values found — **[VERIFY — could not auto-extract]**"
fi
say ""
say "### Fonts"
say ""
if [ -s "$WORK/font_families.txt" ]; then
  say "Family names (from Google Fonts URLs and \`@font-face\`):"
  say ""
  while IFS= read -r l; do say "- **$l**"; done < "$WORK/font_families.txt"
  say ""
fi
if [ -s "$WORK/font_tokens.tsv" ]; then
  say "Font custom properties:"
  say ""
  while IFS="$(printf '\t')" read -r k v; do [ -n "$k" ] && say "- \`$k: $v\`"; done < "$WORK/font_tokens.tsv"
  say ""
fi
if [ -s "$WORK/fonts.txt" ]; then
  say "\`font-family\` declarations (most used first):"
  say ""
  while IFS= read -r l; do say "- \`$l\`"; done < "$WORK/fonts.txt"
  say ""
else
  say "- no \`font-family\` declarations found — **[VERIFY — could not auto-extract]**"
  say ""
fi
if [ -s "$WORK/gfonts.txt" ]; then
  say "Google Fonts URLs:"
  say ""
  while IFS= read -r l; do say "- \`$l\`"; done < "$WORK/gfonts.txt"
  say ""
fi
if [ -n "$SPA_NOTE" ]; then
  say "> **ESCALATE TO A BROWSER.** $SPA_NOTE"
  say ""
fi
say "## E. Sitemap discovery"
say ""
while IFS= read -r l; do say "- $l"; done < "$WORK/sitemaps.txt"
say "- \`$ORIGIN/robots.txt\` -> HTTP $ROBOTS_CODE"
if [ -s "$WORK/robots_sitemaps.txt" ]; then
  while IFS= read -r l; do say "  - \`Sitemap:\` $l"; done < "$WORK/robots_sitemaps.txt"
else
  say "  - no \`Sitemap:\` line in robots.txt"
fi
say ""
say "Use the sitemap to build the URL-pattern -> topic-phrase scope map for the buttons."
say ""
say "---"
say ""
say "_Anything marked \`[VERIFY — could not auto-extract]\` is a genuine gap. Ask the client rather than inventing a value — a wrong brand colour is worse than an admitted unknown._"

# ================================================================= JSON ======
json_str() {
  printf '"%s"' "$(printf '%s' "${1-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\r//g' -e 's/\t/ /g')"
}
json_arr_file() {
  local first=1 l
  printf '['
  if [ -f "$1" ]; then
    while IFS= read -r l; do
      [ -z "$l" ] && continue
      [ $first -eq 1 ] || printf ','
      first=0
      json_str "$l"
    done < "$1"
  fi
  printf ']'
}
json_obj_tsv() {
  local first=1 k v
  printf '{'
  if [ -f "$1" ]; then
    while IFS="$(printf '\t')" read -r k v; do
      [ -z "$k" ] && continue
      [ $first -eq 1 ] || printf ','
      first=0
      json_str "$k"; printf ':'; json_str "$v"
    done < "$1"
  fi
  printf '}'
}

if [ "$EMIT_JSON" -eq 1 ]; then
  {
    printf '{\n'
    printf '  "url": %s,\n'         "$(json_str "$URL")"
    printf '  "final_url": %s,\n'   "$(json_str "$FINAL_URL")"
    printf '  "http_code": %s,\n'   "$(json_str "$HTTP_CODE")"
    printf '  "generated_at": %s,\n' "$(json_str "$NOW")"
    printf '  "detected_stack": %s,\n' "$(json_str "$DETECTED")"
    printf '  "is_wordpress": %s,\n' "$IS_WORDPRESS"
    printf '  "confidence": %s,\n'  "$(json_str "$CONFIDENCE")"
    printf '  "hosting": %s,\n'     "$(json_str "$HOSTING")"
    printf '  "headers": {"server": %s, "x_powered_by": %s, "x_vercel_id": %s, "cf_ray": %s, "x_generator": %s, "x_nextjs": %s, "x_drupal": %s, "x_shopify": %s},\n' \
      "$(json_str "$SERVER")" "$(json_str "$XPB")" "$(json_str "$XVERCEL")" "$(json_str "$CFRAY")" \
      "$(json_str "$XGEN")" "$(json_str "$NEXT_HDRS")" "$(json_str "$DRUPAL_HDRS")" "$(json_str "$SHOPIFY_HDRS")"
    printf '  "meta_generator": %s,\n' "$(json_str "$META_GEN")"
    printf '  "fingerprints": %s,\n'  "$(json_arr_file "$WORK/fingerprints.txt")"
    printf '  "wordpress": {"wp_json_status": %s, "wp_json_is_rest": %s, "wp_login_status": %s, "wp_login_form": %s},\n' \
      "$(json_str "$WPJSON_CODE")" "$(json_str "$WPJSON_IS_JSON")" "$(json_str "$WPLOGIN_CODE")" "$(json_str "$WPLOGIN_REAL")"
    printf '  "analytics": {"gtm": %s, "google_measurement_ids": %s, "other": %s},\n' \
      "$(json_arr_file "$WORK/gtm.txt")" "$(json_arr_file "$WORK/ga4.txt")" "$(json_arr_file "$WORK/analytics_other.txt")"
    printf '  "csp": {"header": %s, "report_only": %s, "meta": %s, "script_src": %s, "connect_src": %s, "default_src": %s, "shipping_impact": %s},\n' \
      "$(json_str "$CSP_HDR")" "$(json_str "$CSPRO_HDR")" "$(json_str "$CSP_META")" \
      "$(json_str "$CSP_SCRIPT")" "$(json_str "$CSP_CONNECT")" "$(json_str "$CSP_DEFAULT")" "$(json_str "$CSP_INLINE_RISK")"
    printf '  "brand": {\n'
    printf '    "palette_method": %s,\n' "$(json_str "$PALETTE_METHOD")"
    printf '    "stylesheets": %s,\n'    "$(json_arr_file "$WORK/css_resolved.txt")"
    printf '    "colour_tokens": %s,\n'  "$(json_obj_tsv "$WORK/colour_tokens.tsv")"
    printf '    "font_tokens": %s,\n'    "$(json_obj_tsv "$WORK/font_tokens.tsv")"
    printf '    "font_families": %s,\n'  "$(json_arr_file "$WORK/font_families.txt")"
    printf '    "font_family_declarations": %s,\n' "$(json_arr_file "$WORK/fonts.txt")"
    printf '    "google_fonts_urls": %s,\n' "$(json_arr_file "$WORK/gfonts.txt")"
    printf '    "hex_frequency": ['
    awk 'NF==2 {gsub(/"/,"",$2); printf "%s{\"hex\":\"%s\",\"count\":%s}", (NR>1?",":""), $2, $1}' "$WORK/hexcounts.txt" 2>/dev/null || true
    printf '],\n'
    printf '    "spa_escalation_note": %s\n' "$(json_str "$SPA_NOTE")"
    printf '  },\n'
    printf '  "sitemaps": {"probes": %s, "robots_status": %s, "robots_sitemap_lines": %s},\n' \
      "$(json_arr_file "$WORK/sitemaps.txt")" "$(json_str "$ROBOTS_CODE")" "$(json_arr_file "$WORK/robots_sitemaps.txt")"
    printf '  "report_markdown": %s\n' "$(json_str "$REPORT")"
    printf '}\n'
  } > "$OUT/recon.json"
  cat "$OUT/recon.json"
  printf '\n' >&2
  printf 'Markdown report: %s\n' "$REPORT" >&2
else
  cat "$REPORT"
  printf '\nSaved to: %s\n' "$REPORT" >&2
fi
