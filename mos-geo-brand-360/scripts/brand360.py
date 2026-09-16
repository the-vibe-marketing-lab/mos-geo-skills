#!/usr/bin/env python3
"""brand360.py - the data layer for mos-geo-brand-360.

Asks AI engines about a brand ONCE per prompt and saves what they said,
so the skill can judge whether the brand is known, found, cited and
recommended. Standard library only - no pip install needed.

Subcommands
  preflight   Check API keys and that every model slug in config/engines.json
              still exists on OpenRouter.
  run         Send the prompt set to the engines and save raw + normalised
              results.
  summarise   Turn results.jsonl into visibility.md + domains.csv - the only
              files the skill reads back (keeps token use down).

Keys come from the environment, or from --env-file:
  OPENROUTER_API_KEY   closed-book pass + API answers with native web search
  BRIGHTDATA_API_KEY   the answers real users see in the consumer apps
  BRIGHTDATA_SERP_ZONE optional: a SERP API zone name, for Google AI Overviews

Nothing in this script ever receives the brand's domain before the run.
That is deliberate: the test is whether the engines can find the brand
from its name and industry alone.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_DIR / "config" / "engines.json"
UA = "mos-geo-brand-360/1.0"

# Platforms that host many brands. Citing them says little about which
# entity an engine resolved the brand to, so they are listed separately.
PLATFORM_DOMAINS = {
    "linkedin.com", "youtube.com", "reddit.com", "wikipedia.org", "x.com",
    "twitter.com", "facebook.com", "instagram.com", "tiktok.com",
    "github.com", "medium.com", "skool.com", "crunchbase.com", "g2.com",
    "capterra.com", "trustpilot.com", "glassdoor.com", "indeed.com",
    "pypi.org", "substack.com", "quora.com", "google.com", "apple.com",
}


# --------------------------------------------------------------- helpers --

def load_env(env_file: str | None) -> dict:
    env = {}
    if env_file:
        path = Path(env_file).expanduser()
        if not path.is_file():
            sys.exit(f"--env-file not found: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip().removeprefix("export ").strip()] = val.strip().strip("'\"")
    for key in ("OPENROUTER_API_KEY", "BRIGHTDATA_API_KEY", "BRIGHTDATA_SERP_ZONE"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


def load_config(path: str | None) -> dict:
    return json.loads(Path(path or DEFAULT_CONFIG).read_text(encoding="utf-8"))


def http_json(method: str, url: str, headers: dict | None = None,
              body=None, timeout: int = 180):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", UA)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": raw[:500]}


def mask(key: str | None) -> str:
    return f"set (…{key[-4:]})" if key else "MISSING"


def domain_of(url: str) -> str:
    host = urllib.parse.urlparse(url if "//" in url else f"//{url}").hostname or ""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def enabled_or_engines(cfg: dict) -> list[dict]:
    return [e for e in cfg["openrouter"]["engines"] if e.get("enabled", True)]


def enabled_bd_scrapers(cfg: dict) -> list[dict]:
    return [s for s in cfg["brightdata"].get("scrapers", []) if s.get("enabled", True)]


# ------------------------------------------------------------- preflight --

def cmd_preflight(args) -> int:
    env = load_env(args.env_file)
    cfg = load_config(args.config)
    problems = 0

    print("mos-geo-brand-360 preflight")
    print("===========================")
    print(f"OPENROUTER_API_KEY  {mask(env.get('OPENROUTER_API_KEY'))}")
    print(f"BRIGHTDATA_API_KEY  {mask(env.get('BRIGHTDATA_API_KEY'))}")
    zone = env.get("BRIGHTDATA_SERP_ZONE")
    print(f"BRIGHTDATA_SERP_ZONE {zone or 'not set (AI Overviews will be skipped)'}")
    if not env.get("OPENROUTER_API_KEY"):
        problems += 1
    if not env.get("BRIGHTDATA_API_KEY"):
        print("  (no Bright Data key: the consumer-app phase will be skipped)")

    status, body = http_json("GET", cfg["openrouter"]["models_url"], timeout=60)
    live = {m["id"] for m in (body or {}).get("data", [])} if status == 200 else set()
    print("\nOpenRouter models")
    if not live:
        print(f"  [WARN] could not load the model list (HTTP {status})")
        problems += 1
    for eng in enabled_or_engines(cfg):
        ok = eng["model"] in live
        problems += 0 if ok else 1
        print(f"  [{'ok' if ok else 'GONE'}] {eng['id']:<11} {eng['model']}")

    if env.get("OPENROUTER_API_KEY"):
        status, body = http_json(
            "GET", "https://openrouter.ai/api/v1/key",
            {"Authorization": f"Bearer {env['OPENROUTER_API_KEY']}"}, timeout=30)
        if status == 200:
            data = (body or {}).get("data", {})
            print(f"  [ok] key accepted (limit remaining: {data.get('limit_remaining', 'n/a')})")
        else:
            print(f"  [FAIL] key rejected (HTTP {status})")
            problems += 1

    print("\nBright Data scrapers")
    scrapers = enabled_bd_scrapers(cfg)
    if not scrapers:
        print("  [WARN] none configured in config/engines.json")
    for s in scrapers:
        print(f"  [cfg] {s['id']:<15} dataset {s['dataset_id']}")
    for s in cfg["brightdata"].get("scrapers", []):
        if not s.get("enabled", True):
            print(f"  [off] {s['id']:<15} {s.get('_note', 'disabled')}")

    print(f"\n{'Ready.' if problems == 0 else f'{problems} problem(s) - fix before running.'}")
    return 0 if problems == 0 else 2


# ------------------------------------------------------------------- run --

def load_prompts(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for group in ("closed_book", "branded", "unbranded"):
        items = data.get(group)
        if not isinstance(items, list) or not items:
            sys.exit(f"prompts file needs a non-empty '{group}' list")
        for i, item in enumerate(items):
            if not item.get("text"):
                sys.exit(f"{group}[{i}] has no 'text'")
            item.setdefault("id", f"{group[:2]}{i + 1:02d}")
    return data


def extract_or_citations(msg: dict, body: dict) -> list[dict]:
    out, seen = [], set()
    for ann in msg.get("annotations") or []:
        uc = ann.get("url_citation") or {}
        if uc.get("url") and uc["url"] not in seen:
            seen.add(uc["url"])
            out.append({"url": uc["url"], "title": uc.get("title", "")})
    # Perplexity also returns a flat top-level list.
    for url in body.get("citations") or []:
        if isinstance(url, str) and url not in seen:
            seen.add(url)
            out.append({"url": url, "title": ""})
    return out


def openrouter_call(cfg, key, eng, prompt, with_search):
    body = {
        "model": eng["model"],
        # No system prompt, ever. The answer must come from the model alone.
        "messages": [{"role": "user", "content": prompt["text"]}],
        "max_tokens": cfg["openrouter"].get("max_tokens", 1200),
    }
    if with_search and eng.get("search") == "native":
        body["plugins"] = [{"id": "web", "engine": "native"}]
    status, resp = http_json(
        "POST", cfg["openrouter"]["base_url"],
        {"Authorization": f"Bearer {key}", "X-Title": "mos-geo-brand-360"},
        body, timeout=240)
    resp = resp or {}
    if status != 200 or not resp.get("choices"):
        err = resp.get("error")
        return resp, "", [], f"HTTP {status}: {json.dumps(err)[:300] if err else 'no choices'}"
    msg = resp["choices"][0].get("message") or {}
    return resp, msg.get("content") or "", extract_or_citations(msg, resp), None


def pick(record: dict, fields: list[str]):
    for f in fields:
        cur = record
        for part in f.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur:
            return cur
    return None


def normalise_bd_citations(value) -> list[dict]:
    out, seen = [], set()
    for item in value or []:
        if isinstance(item, str):
            url, title = item, ""
        elif isinstance(item, dict):
            url = item.get("url") or item.get("link") or item.get("href") or ""
            title = item.get("title") or item.get("name") or ""
        else:
            continue
        if url and url not in seen:
            seen.add(url)
            out.append({"url": url, "title": title})
    return out


def brightdata_scraper(cfg, key, scraper, prompts, raw_dir, country):
    """One batch per scraper: every prompt goes in a single trigger call."""
    bd = cfg["brightdata"]
    inputs = []
    for p in prompts:
        if scraper.get("url_template"):
            url = scraper["url_template"].replace("{q}", urllib.parse.quote_plus(p["text"]))
        else:
            url = scraper["url"]
        row = {"url": url, "prompt": p["text"]}
        if scraper.get("set_country") and country:
            row["country"] = country
        row.update(scraper.get("input_extra", {}))
        inputs.append(row)
    qs = urllib.parse.urlencode({
        "dataset_id": scraper["dataset_id"], "format": "json",
        "include_errors": "true"})
    headers = {"Authorization": f"Bearer {key}"}
    status, resp = http_json("POST", f"{bd['trigger_url']}?{qs}", headers, inputs, timeout=120)
    snap = (resp or {}).get("snapshot_id")
    if status != 200 or not snap:
        err = f"trigger failed HTTP {status}: {json.dumps(resp)[:300]}"
        return {p["id"]: (None, "", [], err) for p in prompts}

    deadline = time.time() + bd.get("timeout_seconds", 900)
    state = "running"
    while time.time() < deadline:
        time.sleep(bd.get("poll_seconds", 15))
        _, prog = http_json("GET", bd["progress_url"].format(snapshot_id=snap), headers, timeout=60)
        state = (prog or {}).get("status", "unknown")
        if state in ("ready", "failed", "canceled"):
            break
    if state != "ready":
        err = f"snapshot {snap} ended as '{state}'"
        return {p["id"]: (None, "", [], err) for p in prompts}

    # The snapshot can still say "building" for a few seconds after "ready".
    records = None
    for _ in range(20):
        _, records = http_json("GET", bd["snapshot_url"].format(snapshot_id=snap), headers, timeout=300)
        if isinstance(records, list):
            break
        time.sleep(10)
    if not isinstance(records, list):
        err = f"snapshot {snap} never became downloadable: {json.dumps(records)[:200]}"
        return {p["id"]: (None, "", [], err) for p in prompts}
    (raw_dir / f"{scraper['id']}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    by_prompt = {}
    for rec in records:
        text = pick(rec, ["prompt", "input.prompt"])
        if text:
            by_prompt.setdefault(text.strip(), rec)
    results = {}
    for i, p in enumerate(prompts):
        rec = by_prompt.get(p["text"].strip())
        if rec is None and len(records) == len(prompts):
            rec = records[i]  # fall back to input order
        if rec is None:
            results[p["id"]] = (None, "", [], "no record returned for this prompt")
            continue
        err = rec.get("error") or rec.get("error_code")
        answer = pick(rec, scraper.get("answer_fields", ["answer_text"])) or ""
        cites = normalise_bd_citations(pick(rec, scraper.get("citation_fields", ["citations"])))
        results[p["id"]] = (rec, answer if isinstance(answer, str) else json.dumps(answer),
                            cites, str(err) if err and not answer else None)
    return results


def ai_overview_call(cfg, key, zone, prompt, country):
    """Google AI Overviews via the SERP API. An empty answer means Google
    showed no overview for that query, which is a result, not an error."""
    aio = cfg["brightdata"]["ai_overviews"]
    search = aio["search_url"].replace("{q}", urllib.parse.quote_plus(prompt["text"])) \
                              .replace("{country}", (country or "us").lower())
    status, resp = http_json(
        "POST", aio["request_url"], {"Authorization": f"Bearer {key}"},
        {"zone": zone, "url": search, "format": "raw"}, timeout=120)
    if status != 200 or not isinstance(resp, dict):
        return resp, "", [], f"HTTP {status}: {json.dumps(resp)[:300]}"
    overview = resp.get("ai_overview") or {}
    parts = []
    for block in overview.get("texts") or []:
        if block.get("snippet"):
            parts.append(block["snippet"])
        for item in block.get("list") or []:
            if isinstance(item, dict) and item.get("snippet"):
                parts.append("- " + item["snippet"])
    cites = normalise_bd_citations(
        [{"url": r.get("href") or r.get("url"), "title": r.get("title", "")}
         for r in overview.get("references") or []])
    return resp, "\n".join(parts) or NO_AIO, cites, None


NO_AIO = "(Google showed no AI Overview for this query.)"


def cmd_run(args) -> int:
    env = load_env(args.env_file)
    cfg = load_config(args.config)
    prompts = load_prompts(args.prompts)
    phases = {p.strip() for p in args.phases.split(",")}
    out = Path(args.out)
    search_prompts = [dict(p, type="branded") for p in prompts["branded"]] + \
                     [dict(p, type="unbranded") for p in prompts["unbranded"]]
    closed = [dict(p, type="closed_book") for p in prompts["closed_book"]]

    or_engines = enabled_or_engines(cfg)
    bd_scrapers = enabled_bd_scrapers(cfg)

    jobs = []  # (phase, engine, prompt)
    if "closed-book" in phases:
        jobs += [("closed-book", e, p) for e in or_engines if e.get("closed_book") for p in closed]
    if "api-search" in phases:
        jobs += [("api-search", e, p) for e in or_engines for p in search_prompts]
    app_calls = len(bd_scrapers) * len(search_prompts) if "app" in phases else 0
    aio_on = "aio" in phases and cfg["brightdata"].get("ai_overviews", {}).get("enabled")
    aio_calls = len(search_prompts) if aio_on else 0

    print(f"Plan: {len(jobs)} OpenRouter calls + {app_calls} Bright Data app records "
          f"({len(bd_scrapers)} scrapers x {len(search_prompts)} prompts) + {aio_calls} AI Overview "
          f"searches. Country {args.country}. One run each, no repeats.")
    if args.dry_run:
        for phase, eng, p in jobs[:5]:
            print(f"  e.g. {phase:<12} {eng['id']:<11} {p['id']}: {p['text'][:70]}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    results_path = out / "results.jsonl"
    records = []

    if jobs:
        key = env.get("OPENROUTER_API_KEY")
        if not key:
            sys.exit("OPENROUTER_API_KEY missing - run preflight.")

        def work(job):
            phase, eng, p = job
            raw, answer, cites, err = openrouter_call(cfg, key, eng, p, phase == "api-search")
            raw_dir = out / "raw" / phase / eng["id"]
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"{p['id']}.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
            return {"phase": phase, "surface": "api", "engine": eng["id"],
                    "label": eng["label"], "model": eng["model"],
                    "prompt_id": p["id"], "prompt_type": p["type"], "prompt": p["text"],
                    "answer": answer, "citations": cites, "error": err}

        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i, rec in enumerate(pool.map(work, jobs), 1):
                records.append(rec)
                flag = "ERR" if rec["error"] else "ok "
                print(f"  [{flag}] {i}/{len(jobs)} {rec['phase']:<12} {rec['engine']:<11} {rec['prompt_id']}")

    if app_calls:
        key = env.get("BRIGHTDATA_API_KEY")
        if not key:
            print("BRIGHTDATA_API_KEY missing - skipping the consumer-app phase.")
        else:
            raw_dir = out / "raw" / "app"
            raw_dir.mkdir(parents=True, exist_ok=True)

            def bd_work(scraper):
                return scraper, brightdata_scraper(cfg, key, scraper, search_prompts, raw_dir, args.country)

            with cf.ThreadPoolExecutor(max_workers=max(1, len(bd_scrapers))) as pool:
                for scraper, res in pool.map(bd_work, bd_scrapers):
                    for p in search_prompts:
                        _, answer, cites, err = res[p["id"]]
                        records.append({
                            "phase": "app", "surface": "app", "engine": scraper["id"],
                            "label": scraper["label"], "model": "consumer app",
                            "prompt_id": p["id"], "prompt_type": p["type"], "prompt": p["text"],
                            "answer": answer, "citations": cites, "error": err})
                    bad = sum(1 for p in search_prompts if res[p["id"]][3])
                    print(f"  [app] {scraper['id']:<11} {len(search_prompts) - bad} ok, {bad} errors")

    if aio_calls:
        key, zone = env.get("BRIGHTDATA_API_KEY"), env.get("BRIGHTDATA_SERP_ZONE")
        if not (key and zone):
            print("BRIGHTDATA_API_KEY or BRIGHTDATA_SERP_ZONE missing - skipping AI Overviews.")
        else:
            raw_dir = out / "raw" / "aio"
            raw_dir.mkdir(parents=True, exist_ok=True)

            def aio_work(p):
                raw, answer, cites, err = ai_overview_call(cfg, key, zone, p, args.country)
                (raw_dir / f"{p['id']}.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
                return p, answer, cites, err

            with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
                shown = 0
                for p, answer, cites, err in pool.map(aio_work, search_prompts):
                    shown += int(answer not in ("", NO_AIO))
                    records.append({
                        "phase": "app", "surface": "app", "engine": "google-aio",
                        "label": "Google AI Overviews", "model": "SERP",
                        "prompt_id": p["id"], "prompt_type": p["type"], "prompt": p["text"],
                        "answer": answer, "citations": cites, "error": err})
            print(f"  [aio] overview shown for {shown}/{len(search_prompts)} queries")

    with results_path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    meta_path = out / "run-meta.json"
    old = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta = {"brand": args.brand, "industry": args.industry,
            "country": args.country, "run_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "phases": sorted(phases | set(old.get("phases", [])))}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    errors = sum(1 for r in records if r["error"])
    print(f"\nSaved {len(records)} results to {results_path} ({errors} errors).")
    return 0 if records else 2


# ------------------------------------------------------------- summarise --

def brand_patterns(brand: str, aliases: list[str]) -> list[re.Pattern]:
    names = {brand.strip()}
    if brand.lower().startswith("the "):
        names.add(brand.strip()[4:])
    names.update(a.strip() for a in aliases if a.strip())
    return [re.compile(r"(?<!\w)" + re.escape(n).replace(r"\ ", r"[\s\-]+") + r"(?!\w)", re.I)
            for n in names]


def mentions(text: str, pats) -> bool:
    return any(p.search(text or "") for p in pats)


def mention_snippet(text: str, pats, width: int = 160) -> str:
    for p in pats:
        m = p.search(text or "")
        if m:
            start = max(0, m.start() - width)
            return " ".join(text[start:m.end() + width].split())
    return ""


DOMAIN_IN_TEXT = re.compile(r"\b((?:[a-z0-9-]+\.)+(?:com|net|org|io|ai|co|au|uk|app|dev|lab))\b", re.I)


def check_link(url: str) -> str:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return str(resp.status)
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405):
                continue
            return str(e.code)
        except Exception as e:  # network errors, TLS, timeouts
            return f"error: {type(e).__name__}"
    return "unknown"


def cmd_summarise(args) -> int:
    run_dir = Path(args.run_dir)
    # A phase can be re-run into the same folder; the latest answer wins.
    latest = {}
    for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            latest[(r["phase"], r["engine"], r["prompt_id"])] = r
    rows = list(latest.values())
    meta = json.loads((run_dir / "run-meta.json").read_text(encoding="utf-8")) if (run_dir / "run-meta.json").exists() else {}
    brand = args.brand or meta.get("brand")
    if not brand:
        sys.exit("--brand is required (no run-meta.json found)")
    pats = brand_patterns(brand, args.alias or [])
    own = {domain_of(d) for d in (args.own_domain or [])}
    comps = {domain_of(d) for d in (args.competitor or [])}

    def classify(dom: str) -> str:
        if own and (dom in own or any(dom.endswith("." + o) for o in own)):
            return "own"
        # Platform first: a competitor that lives on Skool or YouTube must not
        # turn the whole platform into a competitor.
        if dom in PLATFORM_DOMAINS or any(dom.endswith("." + p) for p in PLATFORM_DOMAINS):
            return "platform"
        if dom in comps or any(dom.endswith("." + c) for c in comps):
            return "competitor"
        return "third-party" if own else "unlabelled"

    surfaces = sorted({(r["surface"], r["engine"], r["label"]) for r in rows})
    L = [f"# Visibility data: {brand}", ""]
    L.append(f"Industry: {meta.get('industry', 'n/a')} | Run: {meta.get('run_at', 'n/a')} | "
             "Every prompt was asked **once**, so treat each cell as a snapshot, not a rate.")
    L.append("")

    # 1. Coverage matrix
    L += ["## 1. Coverage matrix", "",
          "| Engine | Surface | Closed-book mentions brand | Branded: mentions | Branded: cites ≥1 source | Unbranded: mentions | Errors |",
          "|---|---|---|---|---|---|---|"]
    for surface, eng, label in surfaces:
        mine = [r for r in rows if r["engine"] == eng and r["surface"] == surface]
        def frac(sel, fn):
            sel = [r for r in sel if not r["error"]]
            return f"{sum(1 for r in sel if fn(r))}/{len(sel)}" if sel else "-"
        cb = [r for r in mine if r["phase"] == "closed-book"]
        br = [r for r in mine if r["prompt_type"] == "branded" and r["phase"] != "closed-book"]
        ub = [r for r in mine if r["prompt_type"] == "unbranded"]
        L.append(f"| {label} | {surface} | {frac(cb, lambda r: mentions(r['answer'], pats))} | "
                 f"{frac(br, lambda r: mentions(r['answer'], pats))} | "
                 f"{frac(br, lambda r: bool(r['citations']))} | "
                 f"{frac(ub, lambda r: mentions(r['answer'], pats))} | "
                 f"{sum(1 for r in mine if r['error'])} |")
    L.append("")
    L.append("\"Mentions\" is a literal name match. A closed-book answer can repeat the name while "
             "saying \"I don't know this brand\", so read section 2 before scoring *Known*.")
    L.append("")

    # 2. Closed-book answers
    L += ["## 2. Closed-book answers (no search)", ""]
    for r in [r for r in rows if r["phase"] == "closed-book"]:
        body = " ".join((r["answer"] or r["error"] or "").split())
        L.append(f"- **{r['label']}** / {r['prompt_id']} ({r['prompt'][:60]}…): {body[:args.excerpt]}")
    L.append("")

    # 3. Entity resolution
    L += ["## 3. Entity resolution (branded prompts)", "",
          "Which websites each engine tied the brand to. Platform domains are listed apart "
          "because they host many brands.", "",
          "| Engine | Surface | Top cited domains | Platforms cited | Domains named in the answer text |",
          "|---|---|---|---|---|"]
    for surface, eng, label in surfaces:
        br = [r for r in rows if r["engine"] == eng and r["surface"] == surface
              and r["prompt_type"] == "branded" and r["phase"] != "closed-book" and not r["error"]]
        if not br:
            continue
        cited = Counter(domain_of(c["url"]) for r in br for c in r["citations"])
        brand_doms = [(d, n) for d, n in cited.most_common() if classify(d) != "platform"][:4]
        plat = [(d, n) for d, n in cited.most_common() if classify(d) == "platform"][:4]
        named = Counter(m.lower().removeprefix("www.") for r in br for m in DOMAIN_IN_TEXT.findall(r["answer"] or ""))
        fmt = lambda pairs: ", ".join(f"{d} ({n})" for d, n in pairs) or "-"
        L.append(f"| {label} | {surface} | {fmt(brand_doms)} | {fmt(plat)} | {fmt(named.most_common(4))} |")
    L.append("")

    # 4. Unbranded prompts
    L += ["## 4. Unbranded buyer prompts", ""]
    for pid in sorted({r["prompt_id"] for r in rows if r["prompt_type"] == "unbranded"}):
        sel = [r for r in rows if r["prompt_id"] == pid and not r["error"]]
        if not sel:
            continue
        hit = [r for r in sel if mentions(r["answer"], pats)]
        L.append(f"### {pid}: {sel[0]['prompt']}")
        L.append(f"Brand mentioned by {len(hit)}/{len(sel)} engines: "
                 f"{', '.join(r['label'] for r in hit) or 'none'}.")
        top = Counter(domain_of(c["url"]) for r in sel for c in r["citations"]).most_common(8)
        L.append(f"Most-cited domains: {', '.join(f'{d} ({n})' for d, n in top) or 'none'}")
        for r in hit:
            L.append(f"- {r['label']}: \"…{mention_snippet(r['answer'], pats)}…\"")
        if not args.no_excerpts:
            for r in sel:
                if r not in hit:
                    L.append(f"- {r['label']} (no mention): {' '.join(r['answer'].split())[:args.excerpt]}")
        L.append("")

    # 5. Cited domains
    dom_rows = defaultdict(lambda: {"count": 0, "engines": set(), "urls": set()})
    for r in rows:
        for c in r["citations"]:
            d = domain_of(c["url"])
            dom_rows[d]["count"] += 1
            dom_rows[d]["engines"].add(r["label"])
            dom_rows[d]["urls"].add(c["url"])
    link_status = {}
    if args.check_links:
        urls = sorted({u for v in dom_rows.values() for u in v["urls"]})
        print(f"Checking {len(urls)} cited URLs…")
        with cf.ThreadPoolExecutor(max_workers=12) as pool:
            link_status = dict(zip(urls, pool.map(check_link, urls)))

    def dead(d):
        return sum(1 for u in dom_rows[d]["urls"]
                   if link_status.get(u, "").startswith(("404", "410", "error")))

    ranked = sorted(dom_rows, key=lambda d: -dom_rows[d]["count"])
    L += ["## 5. Cited domains", "",
          f"Class: own / competitor / platform / third-party"
          f"{'' if own else ' (own domain not supplied yet, so non-platform domains show as unlabelled)'}.", "",
          "| Domain | Class | Citations | Engines | Dead links |", "|---|---|---|---|---|"]
    for d in ranked[:args.top_domains]:
        v = dom_rows[d]
        L.append(f"| {d} | {classify(d)} | {v['count']} | {len(v['engines'])} | "
                 f"{dead(d) if args.check_links else 'not checked'} |")
    L.append("")
    L.append(f"Full list: `domains.csv` ({len(ranked)} domains).")

    (run_dir / "visibility.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    with (run_dir / "domains.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "class", "citations", "engines", "url", "http_status"])
        for d in ranked:
            for u in sorted(dom_rows[d]["urls"]):
                w.writerow([d, classify(d), dom_rows[d]["count"],
                            "; ".join(sorted(dom_rows[d]["engines"])), u, link_status.get(u, "")])
    print(f"Wrote {run_dir / 'visibility.md'} and domains.csv")
    return 0


# ------------------------------------------------------------------ main --

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--config", help="engines config (default: config/engines.json)")
        p.add_argument("--env-file", help="a .env file holding the API keys")

    p = sub.add_parser("preflight", help="check keys and model slugs")
    common(p)
    p.set_defaults(fn=cmd_preflight)

    p = sub.add_parser("run", help="query the engines once per prompt")
    common(p)
    p.add_argument("--brand", required=True)
    p.add_argument("--industry", required=True)
    p.add_argument("--prompts", required=True, help="prompts JSON (see references/prompt-set.md)")
    p.add_argument("--out", required=True, help="run folder")
    p.add_argument("--phases", default="closed-book,api-search,app,aio",
                   help="comma list of closed-book, api-search, app, aio")
    p.add_argument("--country", default="AU",
                   help="2-letter market for the consumer apps and Google (default AU)")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("summarise", help="build visibility.md + domains.csv")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--brand", help="defaults to the brand in run-meta.json")
    p.add_argument("--alias", action="append", help="another name the brand goes by (repeatable)")
    p.add_argument("--own-domain", action="append",
                   help="the brand's real domain, supplied AFTER the run, for labelling only")
    p.add_argument("--competitor", action="append",
                   help="a competitor's own domain (repeatable); platform domains stay 'platform'")
    p.add_argument("--check-links", action="store_true", help="HTTP-check every cited URL")
    p.add_argument("--excerpt", type=int, default=400, help="characters kept per answer excerpt")
    p.add_argument("--no-excerpts", action="store_true", help="drop non-mention excerpts to save tokens")
    p.add_argument("--top-domains", type=int, default=30)
    p.set_defaults(fn=cmd_summarise)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
