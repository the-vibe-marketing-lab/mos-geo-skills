#!/usr/bin/env python3
"""mos-geo-google-preferred-sources: check a site before installing Google's
"Add as preferred source" button, then verify the live install.

Subcommands
  check   <url> [--json]           pre-install recon: eligible unit (domain/subdomain), the
                                   eligibility deeplink to open in a browser, stack, article
                                   candidates from the sitemap, CSP, and any existing install
  verify  <url> [<url> ...] [--expect-absent <url> ...] [--json]
                                   per page: publisher.js / publisher.mjs, button divs,
                                   manual-mode wiring, deeplinks, consistency errors and CSP;
                                   status PASS / WARN / FAIL / NEEDS BROWSER per page.
                                   --expect-absent <url> (repeatable) inverts the check for a page
                                   that must stay clean: PASS when no install, FAIL when one is found

Examples
  python3 preferred_sources.py check https://www.example.com
  python3 preferred_sources.py verify https://www.example.com/ https://www.example.com/blog/post/
  python3 preferred_sources.py verify https://www.example.com/ --json
  python3 preferred_sources.py verify https://www.example.com/blog/post/ --expect-absent https://www.example.com/checkout/

Exit codes
  check:  0 when the homepage was fetched, 2 when it could not be.
  verify: 0 when no page FAILs, 1 when any page FAILs, 2 when every page failed to fetch.

Google's implementation (developers.google.com/search/docs/appearance/preferred-sources):
  standard  <script async src="https://news.google.com/swg/js/v1/publisher.js"></script>
            + <div google-add-preferred-source-btn></div>  (optional data-theme, data-lang)
  manual    the same script with preferred-sources-control="manual", then
            (self.PREFERRED_SOURCE = self.PREFERRED_SOURCE || []).push(function(preferredSource) {
              preferredSource.init({...}); ... preferredSource.addPreferredSource(); })
            or an ES module importing .../publisher.mjs
  deeplink  https://www.google.com/preferences/source?q=example.com
Eligibility is decided by Google (domain- or subdomain-level sites only; a subdirectory is not
eligible) and is confirmed by searching the site at https://www.google.com/preferences/source.
That tool is a JavaScript app: this script prints the link for a human or browser check and
never scrapes it.

Standard library only. Every detector works on a string of HTML, so the tests need no network.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-AU,en;q=0.9", "Accept-Encoding": "gzip"}
TIMEOUT = 20

PUBLISHER_JS = "https://news.google.com/swg/js/v1/publisher.js"
PUBLISHER_MJS = "https://news.google.com/swg/js/v1/publisher.mjs"
PUBLISHER_RE = re.compile(r"news\.google\.com/swg/js/v1/publisher\.(m?js)", re.I)
BUTTON_ATTR = "google-add-preferred-source-btn"
CUSTOM_CLASS = "js-preferred-source"   # our custom button: a deeplink anchor that manual mode upgrades to the popup
MANUAL_ATTR = "preferred-sources-control"
ELIGIBILITY_TOOL = "https://www.google.com/preferences/source"
DEEPLINK_HOSTS = {"google.com", "www.google.com"}
DEEPLINK_PATH = "/preferences/source"

PASS, WARN, FAIL, NEEDS_BROWSER = "PASS", "WARN", "FAIL", "NEEDS BROWSER"
STATUS_RANK = {PASS: 0, NEEDS_BROWSER: 1, WARN: 2, FAIL: 3}

# ----------------------------------------------------------------- fetch --


def fetch(url: str, timeout: int = TIMEOUT) -> tuple:
    """(status, headers, body, final_url, error). Follows redirects, never raises.
    Headers are a dict of lowercase name -> list of values (CSP can repeat)."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if r.headers.get("Content-Encoding", "").lower() == "gzip" or body[:2] == b"\x1f\x8b":
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass
            return r.status, header_lists(r.headers), body, r.geturl(), ""
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:  # noqa: BLE001 - an unreadable error body is simply empty
            pass
        return e.code, header_lists(e.headers) if e.headers else {}, body, url, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - network errors become a status the caller reports
        return 0, {}, b"", url, str(getattr(e, "reason", e))


def header_lists(msg) -> dict:
    out: dict = {}
    for k, v in msg.items():
        out.setdefault(k.lower(), []).append(v)
    return out


def text_of(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")


# ----------------------------------------------------------- eligibility --


def strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def normalise_url(url: str) -> dict:
    """The eligible unit is scheme + host. A path beyond "/" is reported, not used."""
    raw = url.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.I):
        raw = "https://" + raw
    p = urllib.parse.urlsplit(raw)
    host = (p.hostname or "").lower()
    if not host:
        raise ValueError(f"not a URL: {url!r}")
    scheme = p.scheme.lower() if p.scheme.lower() in ("http", "https") else "https"
    netloc = host + (f":{p.port}" if p.port and p.port not in (80, 443) else "")
    unit = f"{scheme}://{netloc}/"
    path = p.path or "/"
    warnings = []
    if path not in ("", "/"):
        warnings.append(f"The URL has a path ({path}). Only a domain or subdomain is eligible "
                        f"as a preferred source, so the button and deeplink must point at {host}, "
                        f"not at {host}{path}.")
    if scheme != "https":
        warnings.append("The URL is not https. Google's examples use https; check the live site redirects to https.")
    return {
        "input": url,
        "url": urllib.parse.urlunsplit((scheme, netloc, path, p.query, "")),
        "scheme": scheme,
        "host": host,
        "eligible_unit": unit,
        "path": path,
        "has_path": path not in ("", "/"),
        "deeplink": deeplink_for(host),
        "eligibility_check": {
            "status": "MANUAL CHECK",
            "tool": ELIGIBILITY_TOOL,
            "how": f"Open {deeplink_for(host)} in a browser (or search {host} at {ELIGIBILITY_TOOL}). "
                   "If the site appears, it is eligible. This script does not scrape the tool.",
        },
        "warnings": warnings,
    }


def deeplink_for(host: str) -> str:
    return f"{ELIGIBILITY_TOOL}?q={urllib.parse.quote(host, safe='.-')}"


# ------------------------------------------------------------ html parse --


class PageScan(HTMLParser):
    """One pass over a page: scripts, button elements, anchors, metas and visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.seen_head = False
        self.seen_body = False
        self.scripts: list = []        # {"src", "attrs", "in_head", "text", "type"}
        self.buttons: list = []        # {"tag", "attrs", "in_head"}
        self.anchors: list = []        # href strings
        self.anchor_attrs: list = []   # attr dicts of those anchors (class, etc.)
        self.link_hrefs: list = []     # <link href> (preload / modulepreload)
        self.metas: list = []          # attr dicts
        self.ids: list = []
        self.words = 0
        self._script = None
        self._skip = 0                 # depth inside style/noscript/template/script

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        if tag == "head":
            self.in_head, self.seen_head = True, True
        elif tag == "body":
            self.in_head, self.seen_body = False, True
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "script":
            self._script = {"src": a.get("src", ""), "attrs": a, "in_head": self.in_head,
                            "type": a.get("type", "").lower(), "text": ""}
            self.scripts.append(self._script)
            return
        if tag in ("style", "noscript", "template"):
            self._skip += 1
        if BUTTON_ATTR in a:
            self.buttons.append({"tag": tag, "attrs": a, "in_head": self.in_head})
        if tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
            self.anchor_attrs.append(a)
        if tag == "link" and a.get("href"):
            self.link_hrefs.append(a["href"])
        if tag == "meta":
            self.metas.append(a)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "script":
            self._script = None

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        elif tag == "script":
            self._script = None
        elif tag in ("style", "noscript", "template") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._script is not None:
            self._script["text"] += data
            return
        if self._skip or self.in_head:
            return
        self.words += len(data.split())

    def meta_content(self, name: str) -> list:
        return [m.get("content", "") for m in self.metas if m.get("name", "").lower() == name]

    def csp_metas(self) -> list:
        return [m.get("content", "") for m in self.metas
                if m.get("http-equiv", "").lower() == "content-security-policy"]


def scan(html: str) -> PageScan:
    p = PageScan()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001 - html.parser is forgiving; a broken page still yields what it read
        pass
    return p


# ------------------------------------------------------------------- CSP --

TARGET = "https://news.google.com/swg/js/v1/publisher.js"


def parse_csp(policy: str) -> dict:
    """{directive: [sources]} for one policy. The first occurrence of a directive wins."""
    out: dict = {}
    for part in policy.split(";"):
        tokens = part.strip().split()
        if not tokens:
            continue
        name = tokens[0].lower()
        if name not in out:
            out[name] = [t for t in tokens[1:]]
    return out


def split_policies(values: list) -> list:
    """A header may repeat or be comma-joined; each comma-separated chunk is a policy."""
    out = []
    for v in values or []:
        for chunk in v.split(","):
            if chunk.strip():
                out.append(chunk.strip())
    return out


def source_matches(src: str, url: str) -> bool:
    """Does one CSP source expression match url? Keywords are handled by the caller."""
    u = urllib.parse.urlsplit(url)
    s = src.strip()
    if s == "*":
        return u.scheme in ("http", "https")
    if re.fullmatch(r"[a-z][a-z0-9+.-]*:", s, re.I):
        return s[:-1].lower() == u.scheme
    m = re.fullmatch(r"(?:([a-z][a-z0-9+.-]*)://)?(\*|\*\.[^/:]+|[^/:*]+)(?::(\d+|\*))?(/.*)?", s, re.I)
    if not m:
        return False
    scheme, host, _port, path = m.groups()
    if scheme and scheme.lower() != u.scheme and not (scheme.lower() == "http" and u.scheme == "https"):
        return False
    host = host.lower()
    target = (u.hostname or "").lower()
    if host == "*":
        pass
    elif host.startswith("*."):
        if not target.endswith(host[1:]):
            return False
    elif host != target:
        return False
    if path:
        path = urllib.parse.unquote(path)
        if path.endswith("/"):
            return u.path.startswith(path)
        return u.path == path
    return True


def directive_verdict(policy: dict, chain: list, url: str) -> tuple:
    """(verdict, directive_used, reason) for the first directive in chain the policy sets."""
    for name in chain:
        if name in policy:
            srcs = policy[name]
            lowered = [s.lower() for s in srcs]
            if "'strict-dynamic'" in lowered and name.startswith("script"):
                listed = any(not s.startswith("'") and source_matches(s, url) for s in srcs)
                return "unclear", name, ("'strict-dynamic' is set, so host allowlists are ignored"
                                         + (" (the news.google.com allowance alone is not sufficient)" if listed else "")
                                         + "; the publisher.js tag needs the page's nonce/hash or a trusted "
                                           "loader to run")
            if not srcs or lowered == ["'none'"]:
                return "BLOCKS", name, f"{name} is 'none'"
            for s in srcs:
                if s.startswith("'"):
                    continue
                if source_matches(s, url):
                    return "allows", name, f"{name} includes {s}"
            return "BLOCKS", name, f"{name} has no source matching {urllib.parse.urlsplit(url).hostname}"
    return "allows", "", "no directive restricts it"


def inline_verdict(policy: dict) -> tuple:
    """("allows" | "may block", reason) for inline <script> blocks under one policy."""
    for name in ("script-src-elem", "script-src", "default-src"):
        if name in policy:
            lowered = [x.lower() for x in policy[name]]
            ignorers = [x for x in lowered if x == "'strict-dynamic'" or x.startswith("'nonce-")
                        or re.match(r"'sha(256|384|512)-", x)]
            if "'unsafe-inline'" in lowered and not ignorers:
                return "allows", f"{name} has 'unsafe-inline'"
            if "'unsafe-inline'" in lowered:
                return "may block", f"{name} has 'unsafe-inline' but it is ignored because of {ignorers[0]}"
            return "may block", f"{name} has no 'unsafe-inline'"
    return "allows", "no directive restricts inline scripts"


def csp_check(header_values: list = None, meta_values: list = None, report_only: list = None) -> dict:
    """Would a CSP let publisher.js load (script) and let it reach news.google.com (frame, connect)?
    script verdict: "no CSP" / "allows" / "BLOCKS" / "unclear"."""
    policies = [("header", p) for p in split_policies(header_values)]
    policies += [("meta", p) for p in split_policies(meta_values)]
    result = {"script": "no CSP", "frame": "no CSP", "connect": "no CSP", "inline": "no CSP",
              "policies": len(policies),
              "details": [], "report_only": bool(split_policies(report_only))}
    if result["report_only"]:
        result["details"].append("Content-Security-Policy-Report-Only is set: it reports but never blocks.")
    if not policies:
        return result
    chains = {
        "script": ["script-src-elem", "script-src", "default-src"],
        "frame": ["frame-src", "child-src", "default-src"],
        "connect": ["connect-src", "default-src"],
    }
    urls = {"script": TARGET, "frame": "https://news.google.com/", "connect": "https://news.google.com/"}
    rank = {"allows": 0, "unclear": 1, "BLOCKS": 2}
    for kind, chain in chains.items():
        worst = "allows"
        for origin, text in policies:
            verdict, used, reason = directive_verdict(parse_csp(text), chain, urls[kind])
            if used:
                result["details"].append(f"{kind} ({origin} CSP): {verdict} - {reason}")
            if rank[verdict] > rank[worst]:
                worst = verdict
        result[kind] = worst
    result["inline"] = "allows"
    for origin, text in policies:
        verdict, reason = inline_verdict(parse_csp(text))
        if verdict != "allows":
            result["inline"] = verdict
            result["details"].append(f"inline ({origin} CSP): {verdict} - {reason}")
    return result


# ----------------------------------------------------------------- stack --

STACK_ORDER = ["WordPress", "Shopify", "Squarespace", "Wix", "Webflow", "Ghost", "Astro", "Next.js", "Nuxt",
               "Framer", "Hugo", "Jekyll"]


def detect_stack(html: str, headers: dict = None) -> dict:
    """{"stack": str, "signals": [str]}. Elementor is reported as a WordPress builder."""
    h = html or ""
    low = h.lower()
    headers = {k.lower(): (v if isinstance(v, list) else [v]) for k, v in (headers or {}).items()}
    page = scan(h)
    generators = [g for g in page.meta_content("generator") if g]
    signals: list = []

    def sig(stack, evidence):
        signals.append((stack, evidence))

    for g in generators:
        gl = g.lower()
        for name, key in (("WordPress", "wordpress"), ("Elementor", "elementor"), ("Ghost", "ghost"),
                          ("Hugo", "hugo"), ("Jekyll", "jekyll"), ("Astro", "astro"), ("Webflow", "webflow"),
                          ("Wix", "wix"), ("Squarespace", "squarespace"), ("Framer", "framer"),
                          ("Nuxt", "nuxt"), ("Next.js", "next.js")):
            if key in gl:
                sig(name, f'<meta name="generator" content="{g}">')
    literal = [
        ("WordPress", "/wp-content/"), ("WordPress", "/wp-includes/"), ("WordPress", "api.w.org"),
        ("Elementor", "elementor-"), ("Elementor", "/plugins/elementor"),
        ("Next.js", "/_next/"), ("Next.js", "__next_data__"), ("Next.js", "self.__next_f"),
        ("Nuxt", "/_nuxt/"), ("Nuxt", "__nuxt__"),
        ("Astro", "/_astro/"), ("Astro", "<astro-island"), ("Astro", "data-astro-cid"),
        ("Shopify", "cdn.shopify.com"), ("Shopify", "shopify.theme"),
        ("Webflow", "webflow.js"), ("Webflow", "data-wf-page"), ("Webflow", "data-wf-site"),
        ("Squarespace", "static1.squarespace.com"), ("Squarespace", "assets.squarespace.com"),
        ("Squarespace", "squarespace_context"),
        ("Wix", "static.wixstatic.com"), ("Wix", "static.parastorage.com"),
        ("Ghost", "/ghost/api/"), ("Ghost", "ghost-portal"),
        ("Framer", "framerusercontent.com"),
    ]
    for stack, needle in literal:
        if needle in low:
            sig(stack, f'"{needle}" in HTML')
    for name, values in headers.items():
        joined = " ".join(values)
        if name.startswith("x-nextjs") or (name == "x-powered-by" and "next.js" in joined.lower()):
            sig("Next.js", f"header {name}: {joined}")
        elif name.startswith("x-shopify") or name in ("x-shopid", "x-shardid"):
            sig("Shopify", f"header {name}")
        elif name == "x-wix-request-id":
            sig("Wix", f"header {name}")
        elif name == "link" and "api.w.org" in joined:
            sig("WordPress", "header link: rel=https://api.w.org/")
        elif name == "x-powered-by" and "wp engine" in joined.lower():
            sig("WordPress", f"header x-powered-by: {joined}")
        elif name == "x-ghost-cache-status":
            sig("Ghost", f"header {name}")
    found = {s for s, _ in signals}
    stack = next((s for s in STACK_ORDER if s in found), "")
    if "Elementor" in found:
        stack = "WordPress (Elementor)" if stack in ("", "WordPress") else f"{stack} + Elementor"
    seen, uniq = set(), []
    for s, e in signals:
        if (s, e) not in seen:
            seen.add((s, e))
            uniq.append(f"{s}: {e}")
    return {"stack": stack or "unknown [VERIFY]", "signals": uniq}


# ------------------------------------------------------------- sitemaps --

EXCLUDE_RE = re.compile(
    r"/(tag|tags|category|categories|author|authors|page|feed|wp-json|search|topics?|archive|archives|"
    r"cart|checkout|account|login|my-account)(/|$)|/page/\d+|[?&](page|p)=|/feed/?$", re.I)
NON_ARTICLE_RE = re.compile(r"^/(about|about-us|contact|contact-us|privacy|privacy-policy|terms|terms-of-service|"
                            r"cookie-policy|cookies|legal|disclaimer|sitemap|faq|careers|jobs|pricing|shop|store)/?$",
                            re.I)
ASSET_RE = re.compile(r"\.(jpe?g|png|gif|webp|svg|pdf|xml|gz|zip|mp4|mp3|css|js)$", re.I)
PREFERRED_RE = re.compile(r"/(blog|news|posts?|articles?|guides?|insights|resources|stories|journal|learn)/", re.I)
DATED_RE = re.compile(r"/(19|20)\d{2}/\d{1,2}/|/(19|20)\d{2}-\d{2}(-\d{2})?[-/]|(19|20)\d{2}-\d{2}-\d{2}")


def robots_sitemaps(robots: str) -> list:
    return [m.group(1).strip() for m in re.finditer(r"(?im)^\s*sitemap\s*:\s*(\S+)", robots or "")]


def parse_sitemap(xml: str) -> tuple:
    """("index" | "urlset" | "", [loc, ...])."""
    x = xml or ""
    locs = [html_unescape(m.group(1).strip()) for m in re.finditer(r"<(?:\w+:)?loc>\s*(.*?)\s*</(?:\w+:)?loc>", x, re.S)]
    if re.search(r"<(?:\w+:)?sitemapindex[\s>]", x):
        return "index", locs
    if re.search(r"<(?:\w+:)?urlset[\s>]", x):
        return "urlset", locs
    return "", locs


def html_unescape(s: str) -> str:
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


def article_score(url: str, host: str) -> int:
    """-1 when the URL cannot be an article, else a preference score (higher is better)."""
    p = urllib.parse.urlsplit(url)
    if strip_www((p.hostname or "").lower()) != strip_www(host.lower()):
        return -1
    path = p.path or "/"
    segments = [s for s in path.split("/") if s]
    if not segments or EXCLUDE_RE.search(path + ("?" + p.query if p.query else "")) or ASSET_RE.search(path):
        return -1
    if NON_ARTICLE_RE.match(path):
        return -1
    score = 0
    if PREFERRED_RE.search(path if path.endswith("/") else path + "/"):
        score += 10
    if DATED_RE.search(path):
        score += 6
    slug = segments[-1]
    if slug.count("-") >= 2:
        score += 3
    if len(segments) >= 2:
        score += 1
    return score


def pick_articles(urls: list, host: str, n: int = 3) -> list:
    scored = []
    seen = set()
    for i, u in enumerate(urls):
        key = u.split("#")[0].rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        s = article_score(u, host)
        if s >= 0:
            scored.append((-s, i, u))
    scored.sort()
    return [u for _, _, u in scored[:n]]


def child_sitemap_priority(url: str) -> int:
    low = url.lower()
    if re.search(r"post|blog|article|news|guide|insight|resource", low):
        return 0
    if re.search(r"page|product|categor|tag|author|image|video|collection", low):
        return 2
    return 1


def find_articles(root: str, host: str, robots: str, n: int = 3, fetcher=None) -> dict:
    fetcher = fetcher or fetch
    tried, candidates = [], robots_sitemaps(robots)
    source = "robots.txt" if candidates else "fallback paths"
    if not candidates:
        candidates = [urllib.parse.urljoin(root, p) for p in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml")]
    urls: list = []
    for sm in candidates:
        st, _, body, _, _ = fetcher(sm)
        tried.append(f"{sm} ({st})")
        if st != 200 or not body:
            continue
        kind, locs = parse_sitemap(text_of(body))
        if kind == "index":
            for child in sorted(locs, key=child_sitemap_priority)[:3]:
                cst, _, cb, _, _ = fetcher(child)
                tried.append(f"{child} ({cst})")
                if cst == 200 and cb:
                    urls.extend(parse_sitemap(text_of(cb))[1])
                if len(pick_articles(urls, host, n)) >= n:
                    break
        else:
            urls.extend(locs)
        if len(pick_articles(urls, host, n)) >= n:
            break
    return {"source": source, "sitemaps_tried": tried, "urls_seen": len(urls), "articles": pick_articles(urls, host, n)}


# -------------------------------------------------------------- detector --

SPA_MARKERS = ("__NEXT_DATA__", "self.__next_f", "__NUXT__", "data-reactroot", "ng-version", "data-server-rendered",
               "<astro-island")
SPA_IDS = {"root", "app", "__next", "__nuxt", "svelte", "gatsby-focus-wrapper"}


def looks_client_rendered(html: str, page: PageScan = None) -> bool:
    page = page or scan(html)
    marker = any(m in html for m in SPA_MARKERS) or bool(SPA_IDS & set(page.ids))
    return page.words < 150 and (marker or len(page.scripts) >= 5)


def parse_deeplink(href: str) -> dict:
    """None when href is not a preferences/source link, else {"href", "q", ...}."""
    try:
        p = urllib.parse.urlsplit(href.strip())
    except ValueError:
        return None
    if (p.hostname or "").lower() not in DEEPLINK_HOSTS or p.path.rstrip("/") != DEEPLINK_PATH:
        return None
    q = urllib.parse.parse_qs(p.query).get("q", [""])[0].strip()
    return {"href": href, "q": q}


def check_deeplink(link: dict, page_host: str) -> tuple:
    """(errors, notes) for one deeplink against the page host."""
    errors, notes = [], []
    q = link["q"]
    if not q:
        return [f"deeplink has no q value: {link['href']}"], notes
    qurl = q if re.match(r"^[a-z]+://", q, re.I) else "https://" + q
    qp = urllib.parse.urlsplit(qurl)
    qhost = (qp.hostname or "").lower()
    if qp.path not in ("", "/") or qp.query:
        errors.append(f"deeplink q={q!r} includes a path; only a domain or subdomain is eligible (use q={qhost})")
    if page_host and qhost != page_host.lower():
        if strip_www(qhost) == strip_www(page_host.lower()):
            notes.append(f"deeplink q={qhost} differs from the page host {page_host} only by www. (fine)")
        else:
            errors.append(f"deeplink q={qhost} does not match the page host {page_host}")
    return errors, notes


def detect_install(html: str, page_url: str = "", headers: dict = None) -> dict:
    """Everything verify reports about one page, from its HTML (and headers for CSP)."""
    html = html or ""
    page = scan(html)
    host = (urllib.parse.urlsplit(page_url).hostname or "").lower() if page_url else ""
    errors, warnings, notes = [], [], []

    # publisher.js / .mjs as <script src>, plus module imports inside inline scripts
    tags = []
    for s in page.scripts:
        m = PUBLISHER_RE.search(s["src"] or "")
        if m:
            tags.append({"variant": "publisher." + m.group(1).lower(), "async": "async" in s["attrs"],
                         "defer": "defer" in s["attrs"], "in_head": s["in_head"],
                         "manual": s["attrs"].get(MANUAL_ATTR, "").lower() == "manual",
                         "type": s["type"]})
    inline = "\n".join(s["text"] for s in page.scripts if not s["src"])
    module_imports = len(re.findall(r"import\b[^;]*?['\"]https://news\.google\.com/swg/js/v1/publisher\.mjs['\"]", inline))
    module_imports += len(re.findall(r"import\(\s*['\"]https://news\.google\.com/swg/js/v1/publisher\.mjs['\"]", inline))
    # Mentions a browser could act on: inline loaders, framework payloads (next/script), preloads.
    # Text in <pre>/<code> samples is deliberately not counted.
    raw_mentions = max(0, len(PUBLISHER_RE.findall(inline + " " + " ".join(page.link_hrefs))) - module_imports)
    script_count = len(tags) + module_imports
    queue = bool(re.search(r"\bPREFERRED_SOURCE\b", inline))
    add_call = bool(re.search(r"\baddPreferredSource\s*\(", inline))
    init_call = bool(re.search(r"\.init\s*\(", inline)) and queue
    manual_attr = any(t["manual"] for t in tags)
    manual = manual_attr or module_imports > 0 or queue or add_call

    buttons = [{"tag": b["tag"], "data_theme": b["attrs"].get("data-theme", ""),
                "data_lang": b["attrs"].get("data-lang", ""), "in_head": b["in_head"]} for b in page.buttons]
    deeplinks, tool_links, seen = [], [], set()
    for attrs in page.anchor_attrs:
        d = parse_deeplink(attrs.get("href", ""))
        if not d:
            continue
        d["custom"] = CUSTOM_CLASS in attrs.get("class", "").split()
        if d["href"] in seen:
            if d["custom"]:
                for other in deeplinks + tool_links:
                    if other["href"] == d["href"]:
                        other["custom"] = True
            continue
        seen.add(d["href"])
        (deeplinks if d["q"] else tool_links).append(d)
    if tool_links:
        notes.append(f"{len(tool_links)} link(s) to {ELIGIBILITY_TOOL} without q=; that opens the search tool, "
                     "not this site's preferred-source page")
    for d in deeplinks:
        e, n = check_deeplink(d, host)
        d["errors"], d["notes"] = e, n
        errors += e
        notes += n

    csp = csp_check((headers or {}).get("content-security-policy"), page.csp_metas(),
                    (headers or {}).get("content-security-policy-report-only"))

    # script checks
    if script_count > 1:
        warnings.append(f"publisher script loaded {script_count} times (duplicate); keep one")
    for t in tags:
        if not t["async"] and not t["defer"] and t["type"] != "module":
            warnings.append(f"{t['variant']} has no async attribute (Google's snippet uses async)")
        if not t["in_head"]:
            notes.append(f"{t['variant']} is in <body>; Google prefers <head> (works either way)")
    for b in buttons:
        if b["data_theme"] and b["data_theme"].lower() not in ("light", "dark"):
            warnings.append(f"button data-theme={b['data_theme']!r} is not light or dark")
        if b["in_head"]:
            errors.append("a google-add-preferred-source-btn element sits inside <head>; it must be in <body>")

    installed_script = script_count > 0
    if installed_script:
        if not buttons and not deeplinks and not add_call and not queue:
            errors.append("publisher script is loaded but there is no button div, no deeplink and no "
                          "addPreferredSource call, so nothing renders")
        elif not buttons and not add_call and not queue and deeplinks:
            warnings.append("publisher script is loaded but only a deeplink is used; the script is unnecessary")
    if buttons and not installed_script:
        if raw_mentions:
            notes.append("publisher.js is named in the page source but not as a <script> tag "
                         "(framework loader?); confirm it loads in a browser")
        else:
            errors.append("google-add-preferred-source-btn div found but publisher.js is not loaded")
    if manual_attr and not add_call:
        errors.append(f'{MANUAL_ATTR}="manual" is set but no addPreferredSource() call was found inline '
                      "(if it lives in an external bundle, confirm in a browser)")
    if (queue or add_call) and not installed_script and not raw_mentions:
        errors.append("manual-mode code (PREFERRED_SOURCE / addPreferredSource) found but publisher.js is not loaded")
    if manual_attr and buttons:
        notes.append("manual mode is set and a standard button div is present; check both do not render")
    if any(d.get("custom") for d in deeplinks) and not (installed_script and (queue or add_call)):
        warnings.append(f"custom button present (.{CUSTOM_CLASS}) but publisher.js/queue missing - popup won't "
                        "open, readers leave the page via the deeplink")
    if installed_script and csp["script"] == "BLOCKS":
        errors.append("the page's Content-Security-Policy blocks https://news.google.com scripts")
    elif installed_script and csp["script"] == "unclear":
        why = next((d.split(" - ", 1)[1] for d in csp["details"] if d.startswith("script") and "unclear" in d), "")
        warnings.append("CSP may block publisher.js (unclear" + (f": {why}" if why else "")
                        + "); confirm in a browser console")
    if (queue or add_call) and csp["inline"] == "may block":
        warnings.append("CSP may block the inline wiring script - needs a nonce/hash or 'unsafe-inline'; "
                        "check in a browser")
    if installed_script and (csp["frame"] == "BLOCKS" or csp["connect"] == "BLOCKS"):
        warnings.append("CSP frame-src/connect-src does not list news.google.com; the button flow may break "
                        "[VERIFY in a browser]")

    found = installed_script or bool(buttons) or bool(deeplinks) or queue or add_call
    spa = looks_client_rendered(html, page)
    if errors:
        status = FAIL
    elif not found:
        if spa:
            status = NEEDS_BROWSER
            notes.append("page looks client-rendered (little server HTML); the button may be injected "
                         "by JavaScript, so check it in a real browser")
        elif raw_mentions:
            status = NEEDS_BROWSER
        else:
            status = FAIL
            errors.append("no publisher script, button div or preferences/source deeplink found")
    elif buttons and not installed_script and raw_mentions:
        status = NEEDS_BROWSER
    elif warnings:
        status = WARN
    else:
        status = PASS

    return {
        "url": page_url,
        "status": status,
        "script": {"count": script_count, "tags": tags, "module_imports": module_imports,
                   "raw_mentions": raw_mentions, "manual_attr": manual_attr},
        "buttons": buttons,
        "manual": {"mode": manual, "queue": queue, "init": init_call, "add_call": add_call},
        "deeplinks": deeplinks,
        "tool_links": [d["href"] for d in tool_links],
        "csp": csp,
        "client_rendered": spa,
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
    }


def install_summary(r: dict) -> str:
    parts = []
    if r["script"]["count"]:
        parts.append(f"script x{r['script']['count']}")
    if r["buttons"]:
        parts.append(f"button x{len(r['buttons'])}")
    if r["manual"]["add_call"]:
        parts.append("manual addPreferredSource")
    if r["deeplinks"]:
        parts.append(f"deeplink x{len(r['deeplinks'])}")
    return ", ".join(parts) or "none found"


# -------------------------------------------------------------- commands --


def verify_url(url: str) -> dict:
    st, headers, body, final, err = fetch(url)
    if st != 200 or not body:
        return {"url": url, "final_url": final, "http_status": st, "status": FAIL, "fetch_error": err or f"HTTP {st}",
                "errors": [f"could not fetch the page ({err or st})"], "warnings": [], "notes": []}
    r = detect_install(text_of(body), final, headers)
    r["url"], r["final_url"], r["http_status"] = url, final, st
    return r


def expect_absent(r: dict) -> dict:
    """Re-grade a detect_install result for a page that must have NO install
    (homepage, checkout): PASS when clean, FAIL when anything is found."""
    if "fetch_error" in r:
        return dict(r, expect_absent=True)
    found = install_summary(r)
    r = dict(r, expect_absent=True, errors=[], warnings=[], notes=[])
    if found != "none found":
        r["status"] = FAIL
        r["errors"] = [f"expected no preferred-source install, found: {found}"]
    elif r["script"]["raw_mentions"]:
        r["status"] = NEEDS_BROWSER
        r["notes"] = ["publisher.js is named in inline script/preload; confirm it does not load in a browser"]
    elif r["client_rendered"]:
        r["status"] = NEEDS_BROWSER
        r["notes"] = ["page looks client-rendered; confirm in a browser that no button is injected"]
    else:
        r["status"] = PASS
        r["notes"] = ["no install found, as expected"]
    return r


def print_page(r: dict) -> None:
    print(f"\n[{r['status']}] {r['url']}" + ("  (expect absent)" if r.get("expect_absent") else ""))
    if r.get("final_url") and r["final_url"] != r["url"]:
        print(f"  final URL: {r['final_url']}")
    if "fetch_error" in r:
        print(f"  ERROR: {r['fetch_error']}")
        return
    s = r["script"]
    if s["count"]:
        for t in s["tags"]:
            print(f"  script: {t['variant']}  async={'yes' if t['async'] else 'no'}  "
                  f"in_head={'yes' if t['in_head'] else 'no'}  manual={'yes' if t['manual'] else 'no'}")
        if s["module_imports"]:
            print(f"  script: publisher.mjs imported by {s['module_imports']} inline module(s)")
    else:
        print("  script: not found" + (f" (named {s['raw_mentions']}x in page source)" if s["raw_mentions"] else ""))
    if r["buttons"]:
        for b in r["buttons"]:
            print(f"  button: <{b['tag']} {BUTTON_ATTR}>  data-theme={b['data_theme'] or '-'}  "
                  f"data-lang={b['data_lang'] or '-'}")
    else:
        print("  button: none")
    m = r["manual"]
    if m["mode"]:
        print(f"  manual: PREFERRED_SOURCE queue={'yes' if m['queue'] else 'no'}  "
              f"addPreferredSource()={'yes' if m['add_call'] else 'no'}")
    for d in r["deeplinks"]:
        print(f"  deeplink: q={d['q'] or '(empty)'}  {d['href']}")
    c = r["csp"]
    print(f"  CSP: script={c['script']}  frame={c['frame']}  connect={c['connect']}")
    for e in r["errors"]:
        print(f"  FAIL: {e}")
    for w in r["warnings"]:
        print(f"  WARN: {w}")
    for n in r["notes"]:
        print(f"  note: {n}")


def cmd_verify(args) -> int:
    if not args.urls and not args.expect_absent:
        print("error: give at least one url or --expect-absent url", file=sys.stderr)
        return 2
    results = [verify_url(u) for u in args.urls] + [expect_absent(verify_url(u)) for u in args.expect_absent or []]
    fetched = [r for r in results if "fetch_error" not in r]
    worst = max((r["status"] for r in results), key=lambda s: STATUS_RANK[s]) if results else FAIL
    counts = {s: sum(1 for r in results if r["status"] == s) for s in (PASS, WARN, FAIL, NEEDS_BROWSER)}
    summary = (f"OVERALL {worst}: {len(results)} page(s) - {counts[PASS]} PASS, {counts[WARN]} WARN, "
               f"{counts[FAIL]} FAIL, {counts[NEEDS_BROWSER]} NEEDS BROWSER")
    code = 2 if not fetched else (1 if counts[FAIL] else 0)
    if args.json:
        print(json.dumps({"overall": worst, "counts": counts, "exit_code": code, "pages": results}, indent=2))
    else:
        print("Google preferred sources: verify")
        for r in results:
            print_page(r)
        print("\n" + summary)
    return code


def cmd_check(args) -> int:
    try:
        info = normalise_url(args.url)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    root = info["eligible_unit"]
    st, headers, body, final, err = fetch(root)
    report: dict = {"eligibility": info, "homepage": {"url": root, "final_url": final, "http_status": st,
                                                      "error": err}}
    if st != 200 or not body:
        report["homepage"]["ok"] = False
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            _print_eligibility(info)
            print(f"\nHomepage: {root} -> {st or 'no response'} {err}")
            print("\nCHECK INCOMPLETE: the homepage could not be fetched")
        return 2
    report["homepage"]["ok"] = True
    home_html = text_of(body)
    final_host = (urllib.parse.urlsplit(final).hostname or "").lower()
    if final_host and final_host != info["host"]:
        info["warnings"].append(f"{info['host']} redirects to {final_host}; install on and point the deeplink "
                                f"at the host the site actually serves ({final_host})")
    stack = detect_stack(home_html, headers)
    home_scan = scan(home_html)
    csp = csp_check(headers.get("content-security-policy"), home_scan.csp_metas(),
                    headers.get("content-security-policy-report-only"))
    _, _, rb, _, _ = fetch(urllib.parse.urljoin(final, "/robots.txt"))
    articles = find_articles(final, final_host or info["host"], text_of(rb))
    existing = [dict(detect_install(home_html, final, headers), url=final)]
    for a in articles["articles"]:
        existing.append(verify_url(a))
    installed = [r for r in existing if "fetch_error" not in r and install_summary(r) != "none found"]
    report.update({"stack": stack, "csp": csp, "articles": articles,
                   "existing_install": [{"url": r["url"], "status": r["status"],
                                         "found": install_summary(r) if "fetch_error" not in r else "fetch failed",
                                         "errors": r["errors"], "warnings": r["warnings"]} for r in existing]})
    ready = csp["script"] != "BLOCKS"
    report["summary"] = (f"CHECK {info['host']}: eligibility MANUAL CHECK, stack {stack['stack']}, "
                         f"CSP {csp['script']}, {len(articles['articles'])} article(s), "
                         f"existing install on {len(installed)}/{len(existing)} page(s)"
                         + ("" if ready else " - CSP BLOCKS publisher.js, fix before installing"))
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    _print_eligibility(info)
    print(f"\nHomepage: {root} -> {st} {final}")
    print(f"\nStack: {stack['stack']}")
    for s in stack["signals"] or ["(no signals)"]:
        print(f"  - {s}")
    print(f"\nCSP for https://news.google.com: script={csp['script']}  frame={csp['frame']}  connect={csp['connect']}")
    for d in csp["details"]:
        print(f"  - {d}")
    print(f"\nArticle candidates (sitemaps from {articles['source']}; {articles['urls_seen']} URLs seen):")
    for a in articles["articles"] or ["(none found; pick an article URL by hand)"]:
        print(f"  - {a}")
    if not articles["articles"]:
        for t in articles["sitemaps_tried"]:
            print(f"    tried {t}")
    print("\nExisting install:")
    for r in report["existing_install"]:
        print(f"  [{r['status'] if r['found'] != 'none found' else '-'}] {r['url']}: {r['found']}")
    print("\n" + report["summary"])
    return 0


def _print_eligibility(info: dict) -> None:
    print(f"Google preferred sources: check {info['input']}")
    print(f"\nEligible unit: {info['eligible_unit']}  (host {info['host']})")
    for w in info["warnings"]:
        print(f"  WARN: {w}")
    print(f"Eligibility: MANUAL CHECK - open {info['deeplink']} in a browser")
    print(f"  (or search {info['host']} at {ELIGIBILITY_TOOL}; if it appears, the site is eligible)")
    print(f"Deeplink to use on the site: {info['deeplink']}")


def main(argv: list = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    p = sub.add_parser("check", help="pre-install recon: eligibility link, stack, articles, CSP, existing install")
    p.add_argument("url", help="the site (a homepage; a path is reported and ignored)")
    p.add_argument("--json", action="store_true", help="print JSON instead of the text report")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("verify", help="verify a live install on one or more pages")
    p.add_argument("urls", nargs="*", metavar="url", help="pages that should carry the install")
    p.add_argument("--expect-absent", action="append", metavar="url", default=[],
                   help="a page that must NOT carry the install (homepage, checkout): PASS when clean, "
                        "FAIL when found (repeatable)")
    p.add_argument("--json", action="store_true", help="print JSON instead of the text report")
    p.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    if args.cmd == "verify" and not args.urls and not args.expect_absent:
        ap.error("verify needs at least one url or --expect-absent url")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
