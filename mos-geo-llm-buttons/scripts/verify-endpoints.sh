#!/usr/bin/env bash
# verify-endpoints.sh — re-test the AI-assistant deep links in
# _shared/platform-endpoints.json and print a pass/fail table.
#
# Usage:
#   ./verify-endpoints.sh [--platform <id>] [--quiet]
#
# WHAT THIS CAN PROVE
#   * The endpoint is still reachable over HTTPS from this machine.
#   * Where the redirect chain ends up.
#   * Whether the prefill parameter SURVIVES that redirect chain — which is
#     exactly how the known Copilot failure manifests (the param is stripped).
#
# WHAT THIS CANNOT PROVE
#   Every target is a client-rendered SPA that returns HTTP 200 for ANY query
#   string. A 200 therefore says nothing about whether the parameter is read by
#   the app and rendered into the composer. That is why no platform is ever
#   classified "working" here — only REACHABLE, PARAM-STRIPPED or UNREACHABLE.
#   Confirming actual prefill requires a logged-in browser. See the footer.
#
# Exit codes:
#   0  every default_enabled platform came back REACHABLE
#   1  usage / data error
#   2  at least one default_enabled platform is UNREACHABLE or PARAM-STRIPPED
#
# Australian spelling used throughout. Reads only; writes nothing outside $TMPDIR.

set -euo pipefail

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# A distinctive, URL-safe token. Alphanumeric on purpose: no percent-encoding,
# so we can grep for it verbatim in curl's %{url_effective}.
PROBE="MOSGEOPROBE7391"

STALE_DAYS=90

# ---------------------------------------------------------------- arguments --
FILTER=""
QUIET=0

usage() {
  cat >&2 <<'USAGE'
Usage: verify-endpoints.sh [--platform <id>] [--quiet]

  --platform <id>  Test only this platform id (e.g. claude, chatgpt).
  --quiet          Table only; suppress the per-row explanatory notes.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --platform) [ $# -ge 2 ] || { usage; exit 1; }; FILTER="$2"; shift 2 ;;
    --quiet)    QUIET=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) echo "verify-endpoints.sh: unknown argument '$1'" >&2; usage; exit 1 ;;
  esac
done

# ------------------------------------------------------- locate the dataset --
# Resolved relative to the script's own path, so this works from any directory.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JSON="$SCRIPT_DIR/../../_shared/platform-endpoints.json"

if [ ! -f "$JSON" ]; then
  echo "verify-endpoints.sh: cannot find platform-endpoints.json at $JSON" >&2
  exit 1
fi
JSON="$(cd "$(dirname "$JSON")" && pwd)/$(basename "$JSON")"

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t verifyep)"
trap 'rm -rf "$TMP"' EXIT

# ------------------------------------------------------------- JSON parsing --
# Three tiers, because neither jq nor a working python3 can be assumed:
#   1. jq         — if installed
#   2. any python — python3 / python / py -3, each validated before use
#                   (on Windows `python3` is often a Store stub that always fails)
#   3. awk        — last-resort line parser for this file's known shape
# All three emit identical delimited rows, so nothing downstream cares which ran.
#
# Columns: id, label, endpoint, param, extra(k=v&k=v), default_enabled, verified, mode
#
# The delimiter is US (0x1f), NOT tab. bash `read` treats tab as IFS whitespace
# and COLLAPSES runs of it, so a single empty field (e.g. extra_params = {})
# would silently shift every later column. 0x1f is non-whitespace, so empty
# fields survive intact.
SEP="$(printf '\037')"
ROWS="$TMP/platforms.dsv"

find_python() {
  local c
  for c in python3 python py; do
    command -v "$c" >/dev/null 2>&1 || continue
    if [ "$c" = "py" ]; then
      if py -3 -c "import json" >/dev/null 2>&1; then printf 'py -3'; return 0; fi
    else
      if "$c" -c "import json" >/dev/null 2>&1; then printf '%s' "$c"; return 0; fi
    fi
  done
  return 1
}

PARSER=""
VERIFIED_ON=""

# Each tier is ATTEMPTED and then checked for output. A tool that merely exists
# is not trusted — a broken jq on PATH would otherwise abort the whole script
# under `set -e` before printing anything.
if command -v jq >/dev/null 2>&1 && jq --version >/dev/null 2>&1; then
  # $sep is passed in rather than escaped inline, so the separator is defined in
  # exactly one place (SEP above) for all three parser tiers.
  if jq -r --arg sep "$SEP" '.platforms[] | [
      .id, .label, .endpoint, (.param // ""),
      ((.extra_params // {}) | to_entries | map("\(.key)=\(.value)") | join("&")),
      (.default_enabled | tostring), (.verified // ""), (.mode // "")
    ] | join($sep)' "$JSON" > "$ROWS" 2>/dev/null && [ -s "$ROWS" ]; then
    PARSER="jq"
    VERIFIED_ON="$(jq -r '.verified_on // ""' "$JSON" 2>/dev/null || true)"
  fi
fi

if [ -z "$PARSER" ] && PY="$(find_python)"; then
  PARSER="python ($PY)"
  $PY - "$JSON" > "$ROWS" <<'PYEOF'
import io, json, sys
US = chr(31)
d = json.load(io.open(sys.argv[1], encoding="utf-8"))
for p in d.get("platforms", []):
    extra = "&".join("%s=%s" % (k, v) for k, v in (p.get("extra_params") or {}).items())
    row = [p.get("id") or "", p.get("label") or "", p.get("endpoint") or "",
           p.get("param") or "", extra,
           "true" if p.get("default_enabled") else "false",
           p.get("verified") or "", p.get("mode") or ""]
    sys.stdout.write(US.join(str(x) for x in row) + "\n")
PYEOF
  VERIFIED_ON="$($PY -c "import io,json,sys;print(json.load(io.open(sys.argv[1],encoding='utf-8')).get('verified_on',''))" "$JSON" 2>/dev/null || true)"
  [ -s "$ROWS" ] || PARSER=""
fi

if [ -z "$PARSER" ]; then
  PARSER="awk (no jq and no working python found)"
  awk '
    BEGIN { US = sprintf("%c", 31) }
    function val(line) {
      sub(/^[^:]*:[[:space:]]*/, "", line)
      sub(/,[[:space:]]*$/, "", line)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
      gsub(/^"|"$/, "", line)
      if (line == "null") line = ""
      return line
    }
    /"platforms"[[:space:]]*:/ { inp = 1; next }
    /"excluded"[[:space:]]*:/  { inp = 0 }
    inp && /^[[:space:]]*\{[[:space:]]*$/ { id=lab=ep=pm=ex=de=vf=md=""; next }
    inp && /^[[:space:]]*\}/ {
      if (id != "") print id US lab US ep US pm US ex US de US vf US md
      id = ""; next
    }
    inp && /"extra_params"[[:space:]]*:/ {
      s = $0; sub(/^[^:]*:[[:space:]]*/, "", s); ex = ""
      while (match(s, /"[^"]+"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        pair = substr(s, RSTART, RLENGTH); s = substr(s, RSTART + RLENGTH)
        k = pair; sub(/"[[:space:]]*:.*$/, "", k); sub(/^"/, "", k)
        v = pair; sub(/^"[^"]+"[[:space:]]*:[[:space:]]*"/, "", v); sub(/"$/, "", v)
        ex = ex (ex == "" ? "" : "&") k "=" v
      }
      next
    }
    inp && /"id"[[:space:]]*:/              { id  = val($0); next }
    inp && /"label"[[:space:]]*:/           { lab = val($0); next }
    inp && /"endpoint"[[:space:]]*:/        { ep  = val($0); next }
    inp && /"param"[[:space:]]*:/           { pm  = val($0); next }
    inp && /"default_enabled"[[:space:]]*:/ { de  = val($0); next }
    inp && /"verified"[[:space:]]*:/        { vf  = val($0); next }
    inp && /"mode"[[:space:]]*:/            { md  = val($0); next }
  ' "$JSON" > "$ROWS"
  VERIFIED_ON="$(grep -m1 '"verified_on"' "$JSON" | sed -E 's/.*"verified_on"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/' || true)"
fi

if [ ! -s "$ROWS" ]; then
  echo "verify-endpoints.sh: parsed zero platforms from $JSON (parser: $PARSER)" >&2
  exit 1
fi

# ----------------------------------------------------------------- helpers --
build_url() { # build_url <endpoint> <param> <extra>
  local ep="$1" param="$2" extra="$3" qs=""
  [ -n "$param" ] && qs="$param=$PROBE"
  if [ -n "$extra" ]; then
    if [ -n "$qs" ]; then qs="$qs&$extra"; else qs="$extra"; fi
  fi
  if [ -z "$qs" ]; then printf '%s' "$ep"; return; fi
  case "$ep" in
    *\?*) printf '%s&%s' "$ep" "$qs" ;;
    *)    printf '%s?%s' "$ep" "$qs" ;;
  esac
}

days_since() { # days_since YYYY-MM-DD -> integer, or nothing if date can't parse
  local d="$1" epoch now
  epoch="$(date -d "$d" +%s 2>/dev/null || true)"
  if [ -z "$epoch" ]; then
    epoch="$(date -j -f "%Y-%m-%d" "$d" +%s 2>/dev/null || true)"
  fi
  [ -z "$epoch" ] && return 0
  now="$(date +%s)"
  printf '%s' "$(( (now - epoch) / 86400 ))"
}

# ------------------------------------------------------------------ header --
echo
echo "AI-assistant deep-link verification"
echo "==================================="
echo "Dataset : $JSON"
echo "Parser  : $PARSER"
echo "Probe   : ?<param>=$PROBE"
echo "Run at  : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

# ------------------------------------------------------- staleness warning --
if [ -n "$VERIFIED_ON" ]; then
  AGE="$(days_since "$VERIFIED_ON")"
  if [ -n "$AGE" ] && [ "$AGE" -gt "$STALE_DAYS" ] 2>/dev/null; then
    echo "!! STALE DATA WARNING"
    echo "!! verified_on = $VERIFIED_ON — that is $AGE days ago (threshold: $STALE_DAYS)."
    echo "!! These are undocumented surfaces and the 2026 trend is REMOVAL, not addition."
    echo "!! Re-verify in a logged-in browser and update verified_on before shipping."
    echo
  else
    echo "verified_on: $VERIFIED_ON${AGE:+ ($AGE day(s) ago — inside the $STALE_DAYS-day freshness window)}"
    echo
  fi
else
  echo "!! verified_on is missing from the dataset — freshness cannot be assessed."
  echo
fi

# ------------------------------------------------------------------- table --
printf '%-11s %-14s %-6s %-7s %s\n' "PLATFORM" "STATUS" "HTTP" "REDIRS" "DETAIL"
printf '%-11s %-14s %-6s %-7s %s\n' "-----------" "--------------" "------" "-------" "----------------------------------------"

EXIT_CODE=0
MATCHED=0
: > "$TMP/direct.txt"
: > "$TMP/indirect.txt"
: > "$TMP/notes.txt"

while IFS="$SEP" read -r ID LABEL ENDPOINT PARAM EXTRA DEFEN VERIF MODE; do
  [ -z "${ID:-}" ] && continue
  if [ -n "$FILTER" ] && [ "$FILTER" != "$ID" ]; then continue; fi
  MATCHED=$((MATCHED + 1))

  case "${VERIF:-}" in
    direct)   printf '%s (%s)\n' "$LABEL" "$ID" >> "$TMP/direct.txt" ;;
    indirect) printf '%s (%s)\n' "$LABEL" "$ID" >> "$TMP/indirect.txt" ;;
  esac

  URL="$(build_url "$ENDPOINT" "$PARAM" "$EXTRA")"

  RC=0
  OUT="$(curl -sS -L --max-time 20 -A "$UA" -o /dev/null \
          -w '%{http_code}|%{url_effective}|%{num_redirects}' "$URL" 2>"$TMP/err.txt")" || RC=$?

  if [ "$RC" -ne 0 ] || [ -z "$OUT" ]; then
    CODE="000"; EFFECTIVE=""; REDIRS="-"
  else
    CODE="${OUT%%|*}"
    REST="${OUT#*|}"
    EFFECTIVE="${REST%|*}"
    REDIRS="${REST##*|}"
  fi

  STATUS=""
  DETAIL=""

  if [ "$RC" -ne 0 ] || [ "$CODE" = "000" ]; then
    STATUS="UNREACHABLE"
    ERRLINE="$(head -1 "$TMP/err.txt" 2>/dev/null | cut -c1-90 || true)"
    DETAIL="curl failed${ERRLINE:+: $ERRLINE}"
  elif [ "$CODE" -ge 400 ] 2>/dev/null; then
    STATUS="UNREACHABLE"
    DETAIL="HTTP $CODE from $EFFECTIVE"
  elif [ -z "$PARAM" ]; then
    STATUS="REACHABLE"
    DETAIL="no prefill param in the dataset (mode=${MODE:-unknown}) — reachability only"
  elif printf '%s' "$EFFECTIVE" | grep -q "$PROBE"; then
    STATUS="REACHABLE"
    DETAIL="?$PARAM= survived the redirect chain -> $EFFECTIVE"
    if [ -n "$EXTRA" ]; then
      MISSING=""
      OLDIFS="$IFS"; IFS='&'
      for kv in $EXTRA; do
        printf '%s' "$EFFECTIVE" | grep -q "$kv" || MISSING="$MISSING $kv"
      done
      IFS="$OLDIFS"
      [ -n "$MISSING" ] && DETAIL="$DETAIL [extra param(s) LOST:$MISSING]"
    fi
  else
    STATUS="PARAM-STRIPPED"
    DETAIL="?$PARAM= is GONE after $REDIRS redirect(s) -> $EFFECTIVE  <-- the Copilot failure signature"
  fi

  printf '%-11s %-14s %-6s %-7s %s\n' "$ID" "$STATUS" "$CODE" "$REDIRS" "$(printf '%s' "$DETAIL" | cut -c1-160)"

  if [ "$STATUS" != "REACHABLE" ] && [ "$DEFEN" = "true" ]; then
    EXIT_CODE=2
    printf '  !! %s (%s) is default_enabled and came back %s — do NOT ship it until this is resolved.\n' \
      "$LABEL" "$ID" "$STATUS" >> "$TMP/notes.txt"
  fi
  if [ "$STATUS" = "REACHABLE" ] && [ "${VERIF:-}" != "direct" ] && [ -n "$PARAM" ]; then
    printf '  -  %s (%s): REACHABLE only, verified=%s. Nobody has watched this param land in a composer — confirm in a browser before shipping.\n' \
      "$LABEL" "$ID" "${VERIF:-unset}" >> "$TMP/notes.txt"
  fi
done < "$ROWS"

echo

if [ "$MATCHED" -eq 0 ]; then
  echo "verify-endpoints.sh: no platform matched --platform '$FILTER'" >&2
  echo "Available ids: $(cut -d"$SEP" -f1 "$ROWS" | tr '\n' ' ')" >&2
  exit 1
fi

if [ "$QUIET" -eq 0 ] && [ -s "$TMP/notes.txt" ]; then
  echo "Per-row notes"
  echo "-------------"
  cat "$TMP/notes.txt"
  echo
fi

# ------------------------------------------------------------------ footer --
cat <<'FOOTER'
================================================================================
  WHAT THIS RUN DID *NOT* PROVE
================================================================================
  REACHABLE does NOT mean "the button works".

  Every platform in this dataset is a client-rendered single-page app. It
  returns HTTP 200 for ANY query string, including nonsense ones. An HTTP check
  can therefore never confirm that a prefill parameter is actually READ by the
  app and rendered into the composer.

  The only way to confirm real prefill:
    1. Open the URL in a browser, LOGGED IN to that platform.
    2. Look at the composer/input box.
    3. Confirm the prompt text is present, and note whether it auto-submits.
    4. Repeat LOGGED OUT — several of these hit an auth wall instead.

  This script can only detect the loud failure mode: a parameter being STRIPPED
  from the effective URL during the redirect chain. That is how Microsoft's
  January 2026 removal of Copilot prefill manifests, and it is worth catching
  automatically — but it is the floor, not the ceiling.
================================================================================
FOOTER

echo
echo "  BROWSER-CONFIRMED (verified: \"direct\") — someone has actually watched the"
echo "  prompt land in the composer:"
if [ -s "$TMP/direct.txt" ]; then
  sort -u "$TMP/direct.txt" | sed 's/^/    * /'
else
  echo "    (none in this run)"
fi
echo
echo "  NOT BROWSER-CONFIRMED (verified: \"indirect\") — inferred from redirect"
echo "  behaviour, docs or third-party reports. MANUAL CONFIRMATION REQUIRED"
echo "  before these ship to a client:"
if [ -s "$TMP/indirect.txt" ]; then
  sort -u "$TMP/indirect.txt" | sed 's/^/    * /'
else
  echo "    (none in this run)"
fi
echo
echo "================================================================================"

if [ "$EXIT_CODE" -ne 0 ]; then
  echo "RESULT: FAIL — at least one default_enabled platform is UNREACHABLE or PARAM-STRIPPED."
else
  echo "RESULT: PASS — every default_enabled platform is REACHABLE (which is not the"
  echo "        same as working; see above)."
fi
echo

exit "$EXIT_CODE"
