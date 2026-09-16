#!/usr/bin/env python3
"""brand360.py - the data layer for mos-geo-brand-360.

Asks AI engines about a brand ONCE per prompt and saves what they said,
so the skill can judge whether the brand is known, found, cited and
recommended. Standard library only - no pip install needed.

Subcommands
  path        Print where this run's folder belongs (MarketingOS-aware).
  preflight   Check credentials and that every model in config/engines.json
              still exists at its provider.
  run         Send the prompt set to the engines and save raw + normalised
              results.
  summarise   Turn data/results.jsonl into visibility-report.md (+ data/domains.csv),
              the only file the skill reads back (keeps token use down).

Run folder layout
  brand-360-report.md     the finished report (written by the skill)
  visibility-report.md    the engine summary (written by summarise)
  data/                   prompts.json, results.jsonl, run-meta.json,
                          domains.csv, raw/ (per-call API responses)

Providers (primary first; a failed or unconfigured primary falls back):
  models  DataForSEO LLM Responses  ->  OpenRouter
  apps    DataForSEO LLM Scraper / SERP API  ->  Bright Data

Credentials come from the environment, or from --env-file:
  DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD
  OPENROUTER_API_KEY
  BRIGHTDATA_API_KEY, BRIGHTDATA_SERP_ZONE (zone only needed for the
  AI Overviews fallback)

Nothing in this script ever receives the brand's domain before the run.
That is deliberate: the test is whether the engines can find the brand
from its name and industry alone.
"""

from __future__ import annotations

import argparse
import base64
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
ENV_KEYS = ("DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD", "OPENROUTER_API_KEY",
            "BRIGHTDATA_API_KEY", "BRIGHTDATA_SERP_ZONE")
PHASES = ("closed-book", "api-search", "app")
DATA_DIR = "data"
VISIBILITY_REPORT = "visibility-report.md"
NO_AIO = "(Google showed no AI Overview for this query.)"
NO_AIMODE = "(Google AI Mode returned no answer for this query.)"
DFS_PROMPT_LIMIT = 500
# Fallback when the locations endpoint is unreachable.
COUNTRY_CODES = {"AU": 2036, "US": 2840, "GB": 2826, "NZ": 2554, "CA": 2124, "IE": 2372, "SG": 2702}

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
    for key in ENV_KEYS:
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


def has_provider(env: dict, provider: str) -> bool:
    return {
        "dataforseo": bool(env.get("DATAFORSEO_LOGIN") and env.get("DATAFORSEO_PASSWORD")),
        "openrouter": bool(env.get("OPENROUTER_API_KEY")),
        "brightdata": bool(env.get("BRIGHTDATA_API_KEY")),
    }.get(provider, False)


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
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"error": f"{type(e).__name__}: {e}"}


def mask(value: str | None) -> str:
    return f"set (…{value[-4:]})" if value else "MISSING"


def domain_of(url: str) -> str:
    host = urllib.parse.urlparse(url if "//" in url else f"//{url}").hostname or ""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def enabled(items: list[dict]) -> list[dict]:
    return [i for i in items if i.get("enabled", True)]


def citation_list(items) -> list[dict]:
    """Normalise any list of URLs or {url|link|href, title} dicts, deduped."""
    out, seen = [], set()
    for item in items or []:
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def resolve_grounding_url(cite: dict) -> dict:
    """Gemini cites vertexaisearch redirect links. Follow one hop to the real
    URL; if that fails, fall back to the title, which Gemini sets to the
    source domain."""
    url = cite["url"]
    if "vertexaisearch.cloud.google.com" not in url:
        return cite
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA}), timeout=15)
    except urllib.error.HTTPError as e:
        if e.headers.get("Location"):
            return {"url": e.headers["Location"], "title": cite["title"]}
    except Exception:
        pass
    title = (cite.get("title") or "").strip()
    if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", title, re.I):
        return {"url": f"https://{title}/", "title": title}
    return cite


# ------------------------------------------------------------ DataForSEO --

# DataForSEO task codes worth one more try: search-engine side errors and timeouts.
DFS_RETRY_CODES = {40101, 40102, 50000, 50301}


def dfs_request(cfg, env, method, path, body=None, timeout=180, retries=1):
    """Returns (task, result, cost, error). Retries transient failures once."""
    for attempt in range(retries + 1):
        task, result, cost, err, code = _dfs_once(cfg, env, method, path, body, timeout)
        if not err or code not in DFS_RETRY_CODES or attempt == retries:
            return task, result, cost, err
        time.sleep(5)


def _dfs_once(cfg, env, method, path, body, timeout):
    token = base64.b64encode(
        f"{env['DATAFORSEO_LOGIN']}:{env['DATAFORSEO_PASSWORD']}".encode()).decode()
    status, resp = http_json(method, cfg["providers"]["dataforseo"]["base_url"] + path,
                             {"Authorization": f"Basic {token}"}, body, timeout)
    resp = resp or {}
    task = (resp.get("tasks") or [{}])[0] or {}
    if status != 200 or resp.get("status_code") != 20000:
        code = 50000 if status in (0, 500, 502, 503, 504) else resp.get("status_code")
        return task, None, 0.0, f"HTTP {status} / {resp.get('status_code')}: {resp.get('status_message') or resp.get('error')}", code
    cost = float(task.get("cost") or 0)
    if task.get("status_code") != 20000:
        return task, None, cost, f"task {task.get('status_code')}: {task.get('status_message')}", task.get("status_code")
    return task, (task.get("result") or [None])[0], cost, None, 20000


_LOCATION_CACHE: dict = {}


def dfs_location_code(cfg, env, country: str) -> int:
    country = (country or "AU").upper()
    if not _LOCATION_CACHE:
        task, _, _, err = dfs_request(cfg, env, "GET", cfg["providers"]["dataforseo"]["locations_path"], timeout=60)
        for loc in (task.get("result") or []) if not err else []:
            if loc.get("location_type") == "Country" and loc.get("country_iso_code"):
                _LOCATION_CACHE[loc["country_iso_code"]] = loc["location_code"]
        _LOCATION_CACHE.setdefault("_loaded", True)
    code = _LOCATION_CACHE.get(country) or COUNTRY_CODES.get(country)
    if not code:
        sys.exit(f"Unknown --country {country} for DataForSEO")
    return code


def dfs_model_call(cfg, env, model, prompt, with_search, country):
    spec = model["dataforseo"]
    pcfg = cfg["providers"]["dataforseo"]
    body = {"user_prompt": prompt["text"][:DFS_PROMPT_LIMIT],
            "model_name": spec["model"],
            "max_output_tokens": pcfg.get("max_output_tokens", 1200)}
    if not spec.get("always_searches"):
        body["web_search"] = bool(with_search)
    if with_search and spec.get("country_field") and country:
        body["web_search_country_iso_code"] = country.upper()
    task, result, cost, err = dfs_request(
        cfg, env, "POST", pcfg["llm_responses_path"].format(se=spec["se"]), [body], timeout=240)
    if err:
        return task, "", [], [], cost, err
    text, cites = [], []
    for item in result.get("items") or []:
        if item.get("type") != "message":
            continue
        for sec in item.get("sections") or []:
            if sec.get("type") == "text" and sec.get("text"):
                text.append(sec["text"])
            cites += sec.get("annotations") or []
    cites = [resolve_grounding_url(c) for c in citation_list(cites)]
    return task, "".join(text).strip(), cites, result.get("fan_out_queries") or [], cost, None


def dfs_app_call(cfg, env, app, prompt, country):
    spec = app["dataforseo"]
    body = {"keyword": prompt["text"],
            "location_code": dfs_location_code(cfg, env, country),
            "language_code": cfg["providers"]["dataforseo"]["language_code"]}
    body.update(spec.get("extra", {}))
    task, result, cost, err = dfs_request(cfg, env, "POST", spec["path"], [body], timeout=240)
    if err:
        return task, "", [], [], cost, err
    if spec["kind"] == "llm_scraper":
        cites = list(result.get("sources") or [])
        for item in result.get("items") or []:
            cites += item.get("sources") or []
        answer = result.get("markdown") or "\n\n".join(
            i.get("markdown") or "" for i in result.get("items") or []).strip()
        return task, answer, citation_list(cites), result.get("fan_out_queries") or [], cost, None
    overview = next((i for i in result.get("items") or [] if i.get("type") == "ai_overview"), None)
    if not overview:
        return task, NO_AIO if app["id"] == "google-aio" else NO_AIMODE, [], [], cost, None
    cites = list(overview.get("references") or [])
    for el in overview.get("items") or []:
        cites += el.get("references") or []
    return task, overview.get("markdown") or "", citation_list(cites), [], cost, None


# ------------------------------------------------------------ OpenRouter --

def or_model_call(cfg, env, model, prompt, with_search, country):
    spec = model["openrouter"]
    pcfg = cfg["providers"]["openrouter"]
    body = {
        "model": spec["model"],
        # No system prompt, ever. The answer must come from the model alone.
        "messages": [{"role": "user", "content": prompt["text"]}],
        "max_tokens": pcfg.get("max_tokens", 1200),
    }
    if with_search and spec.get("search") == "native":
        body["plugins"] = [{"id": "web", "engine": "native"}]
    status, resp = http_json(
        "POST", pcfg["base_url"],
        {"Authorization": f"Bearer {env['OPENROUTER_API_KEY']}", "X-Title": "mos-geo-brand-360"},
        body, timeout=240)
    resp = resp or {}
    if status != 200 or not resp.get("choices"):
        err = resp.get("error")
        return resp, "", [], [], 0.0, f"HTTP {status}: {json.dumps(err)[:300] if err else 'no choices'}"
    msg = resp["choices"][0].get("message") or {}
    cites = [a.get("url_citation") or {} for a in msg.get("annotations") or []]
    cites = citation_list(cites + list(resp.get("citations") or []))  # Perplexity adds a flat list
    cost = float((resp.get("usage") or {}).get("cost") or 0)
    return resp, msg.get("content") or "", [resolve_grounding_url(c) for c in cites], [], cost, None


# ----------------------------------------------------------- Bright Data --

def pick(record: dict, fields: list[str]):
    for f in fields:
        cur = record
        for part in f.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur:
            return cur
    return None


def bd_batch(cfg, env, scraper_id, prompts, raw_dir, country):
    """One trigger per scraper with every prompt; returns {prompt_id: (answer, cites, err)}."""
    bd = cfg["providers"]["brightdata"]
    scraper = bd["scrapers"][scraper_id]
    inputs = []
    for p in prompts:
        url = scraper["url_template"].replace("{q}", urllib.parse.quote_plus(p["text"])) \
            if scraper.get("url_template") else scraper["url"]
        row = {"url": url, "prompt": p["text"]}
        if scraper.get("set_country") and country:
            row["country"] = country.upper()
        row.update(scraper.get("input_extra", {}))
        inputs.append(row)
    fail = lambda msg: {p["id"]: ("", [], msg) for p in prompts}
    headers = {"Authorization": f"Bearer {env['BRIGHTDATA_API_KEY']}"}
    qs = urllib.parse.urlencode({"dataset_id": scraper["dataset_id"], "format": "json",
                                 "include_errors": "true"})
    status, resp = http_json("POST", f"{bd['trigger_url']}?{qs}", headers, inputs, timeout=120)
    snap = (resp or {}).get("snapshot_id")
    if status != 200 or not snap:
        return fail(f"Bright Data trigger failed HTTP {status}: {json.dumps(resp)[:300]}")

    deadline, state = time.time() + bd.get("timeout_seconds", 900), "running"
    while time.time() < deadline:
        time.sleep(bd.get("poll_seconds", 15))
        _, prog = http_json("GET", bd["progress_url"].format(snapshot_id=snap), headers, timeout=60)
        state = (prog or {}).get("status", "unknown")
        if state in ("ready", "failed", "canceled"):
            break
    if state != "ready":
        return fail(f"Bright Data snapshot {snap} ended as '{state}'")
    records = None
    for _ in range(20):  # the snapshot can say "building" briefly after "ready"
        _, records = http_json("GET", bd["snapshot_url"].format(snapshot_id=snap), headers, timeout=300)
        if isinstance(records, list):
            break
        time.sleep(10)
    if not isinstance(records, list):
        return fail(f"Bright Data snapshot {snap} never became downloadable")
    (raw_dir / f"brightdata-{scraper_id}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    by_prompt = {}
    for rec in records:
        text = pick(rec, ["prompt", "input.prompt"])
        if text:
            by_prompt.setdefault(text.strip(), rec)
    out = {}
    for i, p in enumerate(prompts):
        rec = by_prompt.get(p["text"].strip())
        if rec is None and len(records) == len(prompts):
            rec = records[i]  # fall back to input order
        if rec is None:
            out[p["id"]] = ("", [], "Bright Data returned no record for this prompt")
            continue
        answer = pick(rec, bd["answer_fields"]) or ""
        answer = answer if isinstance(answer, str) else json.dumps(answer)
        cites = citation_list(pick(rec, bd["citation_fields"]))
        err = rec.get("error") or rec.get("error_code")
        out[p["id"]] = (answer, cites, str(err) if err and not answer else None)
    return out


def bd_ai_overview(cfg, env, prompt, country):
    serp = cfg["providers"]["brightdata"]["serp"]
    search = serp["search_url"].replace("{q}", urllib.parse.quote_plus(prompt["text"])) \
                               .replace("{country}", (country or "us").lower())
    status, resp = http_json(
        "POST", serp["request_url"], {"Authorization": f"Bearer {env['BRIGHTDATA_API_KEY']}"},
        {"zone": env["BRIGHTDATA_SERP_ZONE"], "url": search, "format": "raw"}, timeout=120)
    if status != 200 or not isinstance(resp, dict):
        return "", [], f"Bright Data SERP HTTP {status}: {json.dumps(resp)[:300]}"
    overview = resp.get("ai_overview") or {}
    parts = []
    for block in overview.get("texts") or []:
        if block.get("snippet"):
            parts.append(block["snippet"])
        parts += ["- " + i["snippet"] for i in block.get("list") or []
                  if isinstance(i, dict) and i.get("snippet")]
    cites = citation_list(overview.get("references"))
    return "\n".join(parts) or NO_AIO, cites, None


# ------------------------------------------------------------------ path --

def find_brain(start: Path) -> Path | None:
    """The MarketingOS brain root at or above `start`, without crossing a git
    repository boundary. A linked git worktree has no .mos/ of its own
    (.mos/ is gitignored), so it borrows its main checkout's config but the
    worktree itself is returned as the root."""
    for d in [start, *start.parents]:
        if (d / ".mos" / "config.yaml").is_file():
            return d
        git = d / ".git"
        if git.is_file():  # linked worktree: "gitdir: <main>/.git/worktrees/<name>"
            m = re.match(r"gitdir:\s*(.+)", git.read_text(encoding="utf-8").strip())
            main = Path(m.group(1)).parents[2] if m else None
            if main and not main.exists() and re.match(r"^[A-Za-z]:[\\/]", m.group(1)):
                drive, rest = m.group(1)[0].lower(), m.group(1)[2:].replace("\\", "/")
                main = Path(f"/mnt/{drive}{rest}").parents[2]  # Windows path seen from WSL
            return d if main and (main / ".mos" / "config.yaml").is_file() else None
        if git.is_dir():
            return None
    return None


def plain(text: str) -> str:
    """Markdown answer -> one clean line for a table cell."""
    text = re.sub(r"\[\[\d+\]\]\([^)]*\)", "", text or "")      # [[1]](url)
    text = re.sub(r"\(\[([^\]]*)\]\([^)]*\)\)", "", text)         # ([site](url))
    text = re.sub(r"\[([^\]]*)\]\(https?://[^)]*\)", r"\1", text)  # [text](url) -> text
    text = re.sub(r"\[\d+(?:\]\[\d+)*\]", "", text)               # [1][5]
    text = re.sub(r"(^|\s)#{1,6}\s+", r"\1", text)                 # headings
    text = re.sub(r"[*_`]{1,3}", "", text)                         # emphasis, code
    return " ".join(text.split()).replace("|", "\\|")


def run_dir_for(brand: str, day: str, start: Path) -> Path:
    """Campaign layout is campaigns/{platform}/{YYYY-MM}/{brand-slug}/, with
    `geo` as the platform. Outside a MarketingOS brain the same shape goes
    under outputs/brand-360/. A second run for the same brand in the same
    month gets a -2, -3 ... suffix so nothing is overwritten."""
    slug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        sys.exit(f"--date must be YYYY-MM-DD, got {day}")
    brain = find_brain(start.resolve())
    base = (brain / "campaigns" / "geo") if brain else (start.resolve() / "outputs" / "brand-360")
    target = base / day[:7] / slug
    n = 2
    while target.exists() and any(target.iterdir()):
        target = base / day[:7] / f"{slug}-{n}"
        n += 1
    return target


def cmd_path(args) -> int:
    day = args.date or time.strftime("%Y-%m-%d")
    target = run_dir_for(args.brand, day, Path(args.start or "."))
    print(target)
    return 0


# ------------------------------------------------------------- preflight --

def cmd_preflight(args) -> int:
    env = load_env(args.env_file)
    cfg = load_config(args.config)
    models, apps = enabled(cfg["models"]), enabled(cfg["apps"])
    problems = 0

    print("mos-geo-brand-360 preflight")
    print("===========================")
    for key in ENV_KEYS:
        shown = env.get(key) if key == "BRIGHTDATA_SERP_ZONE" else mask(env.get(key))
        print(f"{key:<21} {shown or 'MISSING'}")

    if has_provider(env, "dataforseo"):
        print("\nDataForSEO models")
        for m in models:
            spec = m.get("dataforseo")
            if not spec:
                continue
            path = cfg["providers"]["dataforseo"]["models_path"].format(se=spec["se"])
            task, _, _, err = dfs_request(cfg, env, "GET", path, timeout=60)
            if err:
                print(f"  [FAIL] {m['id']:<11} {err}")
                problems += 1
                continue
            live = {x["model_name"]: x for x in task.get("result") or []}
            info = live.get(spec["model"])
            ok = bool(info) and (info.get("web_search_supported") or not m.get("api_search"))
            problems += 0 if ok else 1
            print(f"  [{'ok' if ok else 'GONE'}] {m['id']:<11} {spec['model']}"
                  + ("" if ok else f"  (available: {', '.join(list(live)[:8])} …)"))
        code = dfs_location_code(cfg, env, args.country)
        print(f"  [ok] country {args.country.upper()} -> location_code {code}")

    if has_provider(env, "openrouter"):
        status, body = http_json("GET", cfg["providers"]["openrouter"]["models_url"], timeout=60)
        live = {m["id"] for m in (body or {}).get("data", [])} if status == 200 else set()
        print("\nOpenRouter models (fallback)")
        for m in models:
            if m.get("openrouter"):
                ok = m["openrouter"]["model"] in live
                problems += 0 if ok else 1
                print(f"  [{'ok' if ok else 'GONE'}] {m['id']:<11} {m['openrouter']['model']}")

    print("\nCoverage")
    for m in models:
        chain = [p for p in cfg["provider_order"]["models"] if p in m and has_provider(env, p)]
        problems += 0 if chain else 1
        print(f"  {m['label']:<24} {' -> '.join(chain) or 'NO PROVIDER'}")
    for a in apps:
        chain = [p for p in cfg["provider_order"]["apps"] if p in a and has_provider(env, p)]
        if a["id"] == "google-aio" and "brightdata" in chain and not env.get("BRIGHTDATA_SERP_ZONE"):
            chain.remove("brightdata")
        problems += 0 if chain else 1
        print(f"  {a['label']:<24} {' -> '.join(chain) or 'NO PROVIDER'}")
    off = [i["label"] for i in cfg["models"] + cfg["apps"] if not i.get("enabled", True)]
    if off:
        print(f"  (switched off: {', '.join(off)})")

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
            if len(item["text"]) > DFS_PROMPT_LIMIT:
                sys.exit(f"{group}[{i}] is over {DFS_PROMPT_LIMIT} characters (DataForSEO limit)")
            item.setdefault("id", f"{group[:2]}{i + 1:02d}")
    return data


def save_raw(out: Path, phase: str, engine: str, prompt_id: str, provider: str, raw) -> None:
    d = out / DATA_DIR / "raw" / phase / engine
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{prompt_id}.{provider}.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")


def record(phase, surface, item, provider, p, answer, cites, fan_out, cost, err, tried):
    return {"phase": phase, "surface": surface, "engine": item["id"], "label": item["label"],
            "provider": provider, "prompt_id": p["id"], "prompt_type": p["type"],
            "prompt": p["text"], "answer": answer, "citations": cites, "fan_out": fan_out,
            "cost": round(cost, 6), "error": err, "fallback_from": tried}


def cmd_run(args) -> int:
    env = load_env(args.env_file)
    cfg = load_config(args.config)
    prompts = load_prompts(args.prompts)
    phases = {p.strip() for p in args.phases.split(",")}
    if phases - set(PHASES):
        sys.exit(f"unknown phase(s): {', '.join(phases - set(PHASES))}")
    out = Path(args.out)
    search_prompts = [dict(p, type="branded") for p in prompts["branded"]] + \
                     [dict(p, type="unbranded") for p in prompts["unbranded"]]
    closed = [dict(p, type="closed_book") for p in prompts["closed_book"]]
    models, apps = enabled(cfg["models"]), enabled(cfg["apps"])
    if args.only:
        only = {x.strip() for x in args.only.split(",")}
        unknown = only - {i["id"] for i in models + apps}
        if unknown:
            sys.exit(f"--only: unknown or disabled id(s): {', '.join(sorted(unknown))}")
        models = [m for m in models if m["id"] in only]
        apps = [a for a in apps if a["id"] in only]

    model_jobs = []
    if "closed-book" in phases:
        model_jobs += [("closed-book", m, p) for m in models if m.get("closed_book") for p in closed]
    if "api-search" in phases:
        model_jobs += [("api-search", m, p) for m in models if m.get("api_search") for p in search_prompts]
    app_jobs = [(a, p) for a in apps for p in search_prompts] if "app" in phases else []

    def chain(item, kind):
        c = [pr for pr in cfg["provider_order"][kind] if pr in item and has_provider(env, pr)]
        if item["id"] == "google-aio" and not env.get("BRIGHTDATA_SERP_ZONE") and "brightdata" in c:
            c.remove("brightdata")
        return c

    print(f"Plan: {len(model_jobs)} model calls + {len(app_jobs)} app calls, country "
          f"{args.country.upper()}. One run each, no repeats.")
    for m in models:
        print(f"  {m['label']:<24} {' -> '.join(chain(m, 'models')) or 'NO PROVIDER (skipped)'}")
    for a in apps:
        print(f"  {a['label']:<24} {' -> '.join(chain(a, 'apps')) or 'NO PROVIDER (skipped)'}")
    if args.dry_run:
        return 0

    if has_provider(env, "dataforseo"):
        dfs_location_code(cfg, env, args.country)  # fail fast on a bad country
    data = out / DATA_DIR
    data.mkdir(parents=True, exist_ok=True)
    kept = data / "prompts.json"  # the run folder keeps the exact prompts it asked
    if Path(args.prompts).resolve() != kept.resolve():
        kept.write_text(Path(args.prompts).read_text(encoding="utf-8"), encoding="utf-8")
    records = []

    def model_work(job):
        phase, m, p = job
        tried = []
        for provider in chain(m, "models"):
            fn = dfs_model_call if provider == "dataforseo" else or_model_call
            raw, answer, cites, fan_out, cost, err = fn(cfg, env, m, p, phase == "api-search", args.country)
            save_raw(out, phase, m["id"], p["id"], provider, raw)
            if not err:
                return record(phase, "api", m, provider, p, answer, cites, fan_out, cost, None, tried)
            tried.append(f"{provider}: {err}")
        return record(phase, "api", m, None, p, "", [], [], 0.0,
                      "; ".join(tried) or "no provider configured", tried)

    def app_work(job):
        a, p = job
        c = chain(a, "apps")
        if c[:1] != ["dataforseo"]:
            return a, p, None, [], c
        raw, answer, cites, fan_out, cost, err = dfs_app_call(cfg, env, a, p, args.country)
        save_raw(out, "app", a["id"], p["id"], "dataforseo", raw)
        if not err:
            return a, p, record("app", "app", a, "dataforseo", p, answer, cites, fan_out, cost, None, []), [], c
        return a, p, None, [f"dataforseo: {err}"], c

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, rec in enumerate(pool.map(model_work, model_jobs), 1):
            records.append(rec)
            via = rec["provider"] or "FAILED"
            print(f"  [{via:<10}] {i}/{len(model_jobs)} {rec['phase']:<12} {rec['engine']:<11} {rec['prompt_id']}")

        pending = defaultdict(list)  # (app id) -> [(app, prompt, tried)]
        for a, p, rec, tried, c in pool.map(app_work, app_jobs):
            if rec:
                records.append(rec)
                print(f"  [dataforseo] app {a['id']:<15} {p['id']}")
            elif "brightdata" in c:
                pending[a["id"]].append((a, p, tried))
            else:
                records.append(record("app", "app", a, None, p, "", [], [], 0.0,
                                      "; ".join(tried) or "no provider configured", tried))
                print(f"  [FAILED    ] app {a['id']:<15} {p['id']}")

    if pending:
        raw_dir = out / DATA_DIR / "raw" / "app"
        raw_dir.mkdir(parents=True, exist_ok=True)

        def bd_work(item):
            app_id, rows = item
            a = rows[0][0]
            if app_id == "google-aio":
                return rows, {p["id"]: bd_ai_overview(cfg, env, p, args.country) for _, p, _ in rows}
            return rows, bd_batch(cfg, env, a["brightdata"], [p for _, p, _ in rows], raw_dir, args.country)

        with cf.ThreadPoolExecutor(max_workers=len(pending)) as pool:
            for rows, res in pool.map(bd_work, pending.items()):
                for a, p, tried in rows:
                    answer, cites, err = res[p["id"]]
                    if err:
                        tried = tried + [f"brightdata: {err}"]
                    records.append(record("app", "app", a, None if err else "brightdata", p, answer,
                                          cites, [], 0.0, "; ".join(tried) if err else None, tried))
                bad = sum(1 for _, p, _ in rows if res[p["id"]][2])
                print(f"  [brightdata] app {rows[0][0]['id']:<15} {len(rows) - bad} ok, {bad} failed")

    with (data / "results.jsonl").open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    meta_path = data / "run-meta.json"
    old = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta = {"brand": args.brand, "industry": args.industry, "country": args.country.upper(),
            "run_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "phases": sorted(phases | set(old.get("phases", [])))}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    errors = sum(1 for r in records if r["error"])
    fallbacks = sum(1 for r in records if r["fallback_from"] and not r["error"])
    cost = sum(r["cost"] for r in records)
    print(f"\nSaved {len(records)} results to {data / 'results.jsonl'}: {errors} failed, "
          f"{fallbacks} served by a fallback provider. DataForSEO/OpenRouter cost ${cost:.3f} "
          "(Bright Data is billed separately).")
    return 0 if records and errors < len(records) else 2


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


# Query strings carry noise like utm_source=chatgpt.com; drop them before scanning.
QUERY_STRING = re.compile(r"\?[^\s)\]]*")
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
    data = run_dir / DATA_DIR
    for line in (data / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            latest[(r["phase"], r["engine"], r["prompt_id"])] = r
    rows = list(latest.values())
    meta_path = data / "run-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    brand = args.brand or meta.get("brand")
    if not brand:
        sys.exit("--brand is required (no data/run-meta.json found)")
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
    total = sum(r.get("cost") or 0 for r in rows)
    L.append(f"Industry: {meta.get('industry', 'n/a')} | Country: {meta.get('country', 'n/a')} | "
             f"Run: {meta.get('run_at', 'n/a')} | API cost: ${total:.3f} (Bright Data billed separately)")
    L.append("")
    L.append("Every prompt was asked **once**, so treat each cell as a snapshot, not a rate.")
    L.append("")

    # 1. Coverage matrix
    L += ["## 1. Coverage matrix", "",
          "| Engine | Surface | Via | Closed-book mentions brand | Branded: mentions | Branded: cites ≥1 source | Unbranded: mentions | Errors |",
          "|---|---|---|---|---|---|---|---|"]
    for surface, eng, label in surfaces:
        mine = [r for r in rows if r["engine"] == eng and r["surface"] == surface]
        def frac(sel, fn):
            sel = [r for r in sel if not r["error"]]
            return f"{sum(1 for r in sel if fn(r))}/{len(sel)}" if sel else "-"
        cb = [r for r in mine if r["phase"] == "closed-book"]
        br = [r for r in mine if r["prompt_type"] == "branded" and r["phase"] != "closed-book"]
        ub = [r for r in mine if r["prompt_type"] == "unbranded"]
        via = ", ".join(sorted({r.get("provider") or "failed" for r in mine}))
        L.append(f"| {label} | {surface} | {via} | {frac(cb, lambda r: mentions(r['answer'], pats))} | "
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
        named = Counter(m.lower().removeprefix("www.") for r in br
                        for m in DOMAIN_IN_TEXT.findall(QUERY_STRING.sub("", r["answer"] or "")))
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
        L += [f"### {pid}: {sel[0]['prompt']}", "",
              f"Brand mentioned by **{len(hit)}/{len(sel)}** engines.", ""]
        top = Counter(domain_of(c["url"]) for r in sel for c in r["citations"]).most_common(8)
        if top:
            L += ["| Most-cited domain | Citations |", "|---|---|"]
            L += [f"| {d} | {n} |" for d, n in top]
            L.append("")
        L += ["| Engine | Mentions brand | Top cited domains | What it said |", "|---|---|---|---|"]
        for r in sel:
            mine = Counter(domain_of(c["url"]) for c in r["citations"]).most_common(3)
            if r in hit:
                said = f"…{mention_snippet(plain(r['answer']), pats)}…"
            elif args.no_excerpts:
                said = ""
            else:
                said = plain(r["answer"])[:args.excerpt]
            L.append(f"| {r['label']} | {'**Yes**' if r in hit else 'No'} | "
                     f"{', '.join(d for d, _ in mine) or '-'} | {said} |")
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
    L.append(f"Full list: `data/domains.csv` ({len(ranked)} domains).")
    L.append("")

    # 6. What the engines searched for
    L += ["## 6. Search queries the engines ran (fan-out)", "",
          "What each engine actually typed into its search tool, and which prompt triggered it. "
          "Queries that add a location or a different category show how the engine interpreted "
          f"the brand. Up to {args.fan_out} queries per engine.", ""]
    fan_rows = []
    for surface, eng, label in surfaces:
        seen = set()
        for r in sorted((r for r in rows if r["engine"] == eng and r["surface"] == surface),
                        key=lambda r: r["prompt_id"]):
            for q in r.get("fan_out") or []:
                if q not in seen and len(seen) < args.fan_out:
                    seen.add(q)
                    fan_rows.append(f"| {label} | {r['prompt_id']} | {plain(r['prompt'])} | {plain(q)} |")
    if fan_rows:
        L += ["| Engine | ID | Prompt | Search query |", "|---|---|---|---|"] + fan_rows
    else:
        L.append("No engine reported its search queries in this run.")
    failed = [r for r in rows if r["error"]]
    if failed:
        L += ["", "## 7. Failed calls", ""]
        L += [f"- {r['label']} / {r['prompt_id']}: {r['error'][:200]}" for r in failed]

    # Frontmatter satisfies the MarketingOS contract (mos validate) and is
    # harmless anywhere else.
    brain = find_brain(run_dir.resolve())
    rel = run_dir.resolve().relative_to(brain).as_posix() if brain else run_dir.name
    front = ["---",
             f"title: {brand} - AI visibility data ({meta.get('run_at', '')[:10]})",
             "type: campaign",
             "description: Engine-by-engine summary of the AI answers behind the brand-360 "
             "AI Visibility Scorecard. Generated by brand360.py summarise.",
             f"date: {meta.get('run_at', time.strftime('%Y-%m-%d'))[:10]}",
             "status: active",
             "sources:",
             f"  - {rel}/{DATA_DIR}/prompts.json",
             f"  - {rel}/{DATA_DIR}/results.jsonl",
             "---", ""]
    (run_dir / VISIBILITY_REPORT).write_text("\n".join(front + L) + "\n", encoding="utf-8")
    with (data / "domains.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "class", "citations", "engines", "url", "http_status"])
        for d in ranked:
            for u in sorted(dom_rows[d]["urls"]):
                w.writerow([d, classify(d), dom_rows[d]["count"],
                            "; ".join(sorted(dom_rows[d]["engines"])), u, link_status.get(u, "")])
    print(f"Wrote {run_dir / VISIBILITY_REPORT} and {data / 'domains.csv'}")
    return 0



# ------------------------------------------------------------------ main --

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--config", help="engines config (default: config/engines.json)")
        p.add_argument("--env-file", help="a .env file holding the API keys")

    p = sub.add_parser("path", help="print the run folder for this brand (MarketingOS-aware)")
    p.add_argument("--brand", required=True)
    p.add_argument("--date", help="YYYY-MM-DD (default today)")
    p.add_argument("--start", help="folder to resolve from (default: current folder)")
    p.set_defaults(fn=cmd_path)

    p = sub.add_parser("preflight", help="check credentials and model names")
    common(p)
    p.add_argument("--country", default="AU", help="2-letter market to check (default AU)")
    p.set_defaults(fn=cmd_preflight)

    p = sub.add_parser("run", help="query the engines once per prompt")
    common(p)
    p.add_argument("--brand", required=True)
    p.add_argument("--industry", required=True)
    p.add_argument("--prompts", required=True, help="prompts JSON (see references/prompt-set.md)")
    p.add_argument("--out", required=True, help="run folder")
    p.add_argument("--phases", default=",".join(PHASES),
                   help="comma list of closed-book, api-search, app")
    p.add_argument("--country", default="AU",
                   help="2-letter market for the consumer apps and Google (default AU)")
    p.add_argument("--only", help="comma list of engine ids to run (e.g. google-aio) - for retries")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("summarise", help="build visibility-report.md + data/domains.csv")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--brand", help="defaults to the brand in data/run-meta.json")
    p.add_argument("--alias", action="append", help="another name the brand goes by (repeatable)")
    p.add_argument("--own-domain", action="append",
                   help="the brand's real domain, supplied AFTER the run, for labelling only")
    p.add_argument("--competitor", action="append",
                   help="a competitor's own domain (repeatable); platform domains stay 'platform'")
    p.add_argument("--check-links", action="store_true", help="HTTP-check every cited URL")
    p.add_argument("--excerpt", type=int, default=400, help="characters kept per answer excerpt")
    p.add_argument("--no-excerpts", action="store_true", help="drop non-mention excerpts to save tokens")
    p.add_argument("--top-domains", type=int, default=30)
    p.add_argument("--fan-out", type=int, default=12, help="search queries listed per engine")
    p.set_defaults(fn=cmd_summarise)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
