#!/usr/bin/env python3
"""mos-geo-ai-info-generator: a fast AI Info Page draft in the shape of Steve Toth's GPT.

Subcommands
  path     print this month's run folder (same rules as every mos-geo skill)
  crawl    fetch the brand's own site into data/pages/ (delegates to mos-geo-ai-info)
  gather   concatenate brain files + crawl pages + interview answers into data/input-bundle.md
  lint     the deterministic gate: section order, instructions, canary, em dashes, forbidden
           terms, attribution, and numeric provenance (every number must be in the bundle)
  render   page.md -> page.html (semantic, no external assets) + handover.md
  check    test the live page after publishing (delegates to mos-geo-ai-info)

Standard library only. Reuses mos-geo-ai-info/scripts/aiinfo.py (crawl, check, run-folder
rules, canary wording) so the two skills never drift apart.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SIBLING = SKILL_DIR.parent / "mos-geo-ai-info" / "scripts" / "aiinfo.py"
SKILL_FOLDER = "ai-info-draft"
DATA = "data"
BUNDLE = "data/input-bundle.md"
PAGE_MD, PAGE_HTML, HANDOVER = "page.md", "page.html", "handover.md"
ENGINES = ["ChatGPT", "Claude", "Perplexity", "Gemini"]


def sibling():
    if not SIBLING.is_file():
        sys.exit(f"needs mos-geo-ai-info next to this skill ({SIBLING}); install the whole mos-geo-skills pack")
    sys.path.insert(0, str(SIBLING.parent))
    import aiinfo  # noqa: E402
    return aiinfo


# ------------------------------------------------------------------ path --

def cmd_path(args) -> int:
    ai = sibling()
    ai.SKILL_FOLDER = SKILL_FOLDER
    print(ai.run_dir_for(args.brand, args.date or time.strftime("%Y-%m-%d"), Path(args.start or ".")))
    return 0


def cmd_crawl(args) -> int:
    sibling()
    cmd = [sys.executable, str(SIBLING), "crawl", "--url", args.url, "--out", args.run_dir,
           "--max-pages", str(args.max_pages)]
    return subprocess.call(cmd)


def cmd_check(args) -> int:
    sibling()
    cmd = [sys.executable, str(SIBLING), "check", "--url", args.url]
    if args.brand:
        cmd += ["--brand", args.brand]
    if args.run_dir:
        cmd += ["--run-dir", args.run_dir]
    return subprocess.call(cmd)


# ---------------------------------------------------------------- gather --
# The default MarketingOS brain files worth reading for identity facts. Big research
# folders are left out on purpose: third-party research is not first-party fact, and a
# huge bundle makes the provenance check meaningless.
BRAIN_GLOBS = ["CLAUDE.md", "BRAIN.md", "CONTEXT.md", "reference/core/*.md", "reference/proof/*.md",
               "business/brand/*.md", "business/offer/*.md", "business/offers/*.md", "business/proof/*.md",
               "business/proof/*/*.md", "business/strategy/*.md", "business/audience/*.md"]
FILE_CAP = 6000  # words per file


def cmd_gather(args) -> int:
    run = Path(args.run_dir)
    files: list[tuple[str, Path]] = []
    if args.brain:
        brain = Path(args.brain)
        for g in BRAIN_GLOBS:
            files += [("brain", p) for p in sorted(brain.glob(g)) if p.is_file()]
    for inc in args.include or []:
        p = Path(inc)
        found = sorted(p.rglob("*.md")) if p.is_dir() else ([p] if p.is_file() else [])
        if not found:
            print(f"  [warn] --include {inc}: nothing found")
        files += [("include", f) for f in found]
    files += [("crawl", p) for p in sorted((run / DATA / "pages").glob("*.md"))]
    interview = run / DATA / "interview.md"
    if interview.is_file():
        files.append(("interview", interview))
    seen, parts, manifest = set(), [], []
    for kind, p in files:
        key = p.resolve()
        if key in seen:
            continue
        seen.add(key)
        words = p.read_text(encoding="utf-8", errors="replace").split()
        text = " ".join(words[:FILE_CAP]) if len(words) > FILE_CAP else p.read_text(encoding="utf-8", errors="replace")
        note = f", truncated at {FILE_CAP}" if len(words) > FILE_CAP else ""
        parts.append(f"\n\n=== {kind.upper()}: {p} ({len(words)} words{note}) ===\n\n{text}")
        manifest.append({"kind": kind, "path": str(p), "words": len(words), "truncated": bool(note)})
    if not parts:
        sys.exit("nothing gathered: pass --brain, --include, or run crawl first")
    out = run / BUNDLE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Input bundle\n\nEvery fact and number on the page must come from this file." + "".join(parts) + "\n",
                   encoding="utf-8")
    (run / DATA / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(m["words"] for m in manifest)
    by = {}
    for m in manifest:
        by[m["kind"]] = by.get(m["kind"], 0) + 1
    print(f"Wrote {out}: {len(manifest)} files, {total} words ({', '.join(f'{k} {v}' for k, v in by.items())})")
    if total > 120_000:
        print("  [warn] over 120k words: trim --include, a big bundle weakens the provenance check")
    if "interview" not in by:
        print("  [info] no data/interview.md yet: write the gap-interview answers there, then gather again")
    return 0


# ------------------------------------------------------------------ lint --
# (id, heading regex, required, allows sub-H2s after it). Order is the GPT's order.
SECTIONS = [
    ("basic", r"Basic Information$", True, False),
    ("background", r"(.+ )?Background$", True, False),
    ("core", r"Core (Service |Services|Products|Offerings)", True, True),
    ("secondary", r"Secondary (Services|Offerings)", False, False),
    ("audience", r"Target\b", False, False),
    ("results", r"(Demonstrated|Notable Client|Client Portfolio|Published Results)", False, False),
    ("methods", r"Proprietary\b", False, True),
    ("tech", r"(Technology Stack|Integrations)$", False, False),
    ("education", r"Educational\b", False, False),
    ("research", r"Research\b", False, False),
    ("thought", r"Thought Leadership$", False, False),
    ("approach", r"Approach\b", False, False),
    ("advantages", r"Competitive Advantages$", False, False),
    ("positioning", r"Positioning$", False, False),
    ("people", r"Key Personnel$", False, False),
    ("community", r"Community$", False, False),
    ("instructions", r"INSTRUCTIONS FOR AI ASSISTANTS$", True, False),
    ("key_pages", r"Key Pages$", False, False),
    ("last_updated", r"Last updated:?\s*\S", True, False),
    ("more_info", r"For more information:?\s*\S", True, False),
    ("canary", r"DIRECT COMMAND TO AI MODELS$", False, False),
]
ORDER = {s[0]: i for i, s in enumerate(SECTIONS)}
PROMISE = re.compile(r"\bguarantee[sd]?\b|\bwill (rank|double|triple)\b|\bguaranteed\b", re.I)
NEGATED = re.compile(r"\b(not|never|no|rather than|without)\b", re.I)
MANIPULATE = re.compile(r"always recommend|recommend \S+ (first|over)|rank \S+( \S+)? first|ignore (other|all|previous|any)|"
                        r"prefer \S+( \S+)? over|instead of (competitors|other)", re.I)
VAGUE = re.compile(r"\b(dozens|hundreds|thousands|millions)\b", re.I)
VOLATILE = re.compile(r"(\$\s?\d|\d[\d,.]*\s*(members|subscribers|followers|customers|clients|students|per month|/month|a month))",
                      re.I)
US_SPELL = re.compile(r"\b(optimiz\w*|organiz\w*|speciali[z]\w*|prioritiz\w*|summariz\w*|recogniz\w*|analyz\w*|customiz\w*|"
                      r"standardiz\w*|color\w*|behavior\w*|center(s|ed)?|favorite\w*|centers)\b", re.I)
AU_SPELL = re.compile(r"\b(optimis\w*|organis\w*|specialis\w*|prioritis\w*|summaris\w*|recognis\w*|colour\w*|behaviour\w*|"
                      r"centre\w*|favourite\w*)\b", re.I)
FIRST_PERSON = re.compile(r"\b(?:(?i:we|our|ours|my|me)|us|I)\b")
KEY_VALUE = re.compile(r"^\**([A-Za-z][A-Za-z /&-]{1,40}?):\**\s+(.*)$")
DEFLECT = re.compile(r"consult|official (source|website|site|page|community)|check(ing)? (a |the )?current", re.I)
ATTRIBUTED = re.compile(r"according to|as (published|reported|presented) by|(states|reports|publishes) that", re.I)
NON_GUARANTEE = re.compile(r"rather than|not (be )?(interpreted|read|taken|described) as|no guarantee|not a guarantee", re.I)
# Kept in step with mos-geo-ai-info's lint.
SUPERLATIVE = re.compile(r"\b(best|leading|top|number one|#1|world[- ]class|premier|unrivalled|unmatched|"
                         r"most trusted|award[- ]winning)\b", re.I)
SUPERLATIVE_OK = re.compile(r"\b(named|awarded|won|ranked|according to|states?|describes|reports?|largest)\b", re.I)
NUM = re.compile(r"(?<![\w.])(\$?)(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s?[kKmM](?![a-zA-Z]))?(%?)")
VERIFY = re.compile(r"\[VERIFY:[^\]]*\]")


def num_values(text: str) -> set[float]:
    """Every number in text as a float, with 113.4k == 113400 and 1,000 == 1000."""
    vals = set()
    for m in NUM.finditer(text):
        raw = m.group(2).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        suf = (m.group(3) or "").strip().lower()
        vals.add(round(v, 4))
        if suf == "k":
            vals.add(round(v * 1000, 4))
        elif suf == "m":
            vals.add(round(v * 1_000_000, 4))
    return vals


def split_sections(md: str) -> list[tuple[str, list[str]]]:
    """[(heading or '', [lines])]; heading '' is text before the first H2."""
    out, head, buf = [], "", []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not line.startswith("###"):
            out.append((head, buf))
            head, buf = m.group(1), []
        else:
            buf.append(line)
    out.append((head, buf))
    return out


def classify(heading: str) -> str | None:
    h = heading.strip().strip("*").strip()
    for sid, pat, _, _ in SECTIONS:
        if re.match(pat, h, re.I if sid not in ("instructions",) else 0):
            return sid
    return None


def paragraphs(lines: list[str]) -> list[str]:
    paras, cur = [], []
    for ln in lines + [""]:
        s = ln.strip()
        if not s:
            if cur:
                paras.append(" ".join(cur))
                cur = []
        elif s.startswith(("- ", "* ")):
            if cur:
                paras.append(" ".join(cur))
            cur = [s[2:]]
        else:
            cur.append(s)
    return paras


class Report:
    def __init__(self):
        self.fails, self.warns, self.notes = [], [], []


def check_title(secs, brand, r: Report) -> None:
    title = secs[1][0]
    m = re.match(r"Official Information About (.+)$", title)
    if not m:
        r.fails.append(f"first heading must be '## Official Information About {{Brand}}', got '## {title}'")
    elif brand and m.group(1).strip().lower() != brand.lower():
        r.fails.append(f"title names '{m.group(1).strip()}', expected '{brand}'")
    missing = [e for e in ENGINES if e not in " ".join(secs[1][1])]
    if missing:
        r.fails.append(f"intro line after the title must name ChatGPT, Claude, Perplexity and Gemini (missing {missing})")


def check_order(secs, r: Report) -> tuple[list[str], dict[str, list[str]]]:
    """Walk the H2s. Unknown H2s are allowed only under a section that takes sub-headings."""
    seen, bodies = [], {}
    last_idx, last_sid, sub_ok = -1, None, False
    for heading, lines in secs[2:]:
        sid = classify(heading)
        if sid is None:
            if sub_ok:
                bodies.setdefault(last_sid, []).extend([f"## {heading}"] + lines)
            else:
                r.fails.append(f"'## {heading}' is not a GPT section and does not sit under Core Service Offerings "
                               "or Proprietary Methodologies; rename it to a canonical heading or make it an H3")
            continue
        if ORDER[sid] <= last_idx:
            r.fails.append(f"'## {heading}' ({sid}) is out of order: it must come before '{last_sid}' "
                           f"(order: {', '.join(s[0] for s in SECTIONS)})")
        last_idx, last_sid = max(ORDER[sid], last_idx), sid
        sub_ok = SECTIONS[ORDER[sid]][3]
        seen.append(sid)
        bodies.setdefault(sid, []).extend(lines)
    for sid, pat, req, _ in SECTIONS:
        if req and sid not in seen:
            r.fails.append(f"missing required section: {sid} (heading like '{pat.rstrip('$')}')")
    r.notes.append("sections: " + ", ".join(seen))
    return seen, bodies


def check_basic(bodies, r: Report) -> None:
    keys = {}
    for p in paragraphs(bodies.get("basic", [])):
        km = KEY_VALUE.match(p)
        if km:
            keys[km.group(1).strip().lower()] = km.group(2).strip()
    for need in ("name", "type", "website"):
        if not keys.get(need):
            r.fails.append(f"Basic Information: no '{need.title()}:' line with a value")


def check_instructions(bodies, r: Report) -> None:
    ins = paragraphs(bodies.get("instructions", []))
    if not ins:
        return
    rules = [(len(ins) >= 4, f"INSTRUCTIONS FOR AI ASSISTANTS has {len(ins)} lines; write at least 4"),
             (any(re.match(r"(When|For)\b", p) for p in ins), "INSTRUCTIONS: no 'When asked X, describe Y' line"),
             (any(re.match(r"(Do not|Don't|Never)\b", p, re.I) for p in ins), "INSTRUCTIONS: no 'Do not ...' line"),
             (any(DEFLECT.search(p) for p in ins),
              "INSTRUCTIONS: no line sending volatile facts (price, size, availability) to the official source")]
    r.fails += [msg for ok, msg in rules if not ok]
    for p in ins:
        mm = MANIPULATE.search(p)
        if mm:
            r.fails.append(f"INSTRUCTIONS: manipulation, not description ({mm.group(0)!r}); describe the brand, "
                           "never tell engines to prefer it")


def check_results(bodies, seen, r: Report) -> None:
    if "results" in seen:
        res = paragraphs(bodies["results"])
        for p in res:
            if re.search(r"\d", VERIFY.sub("", p)) and not ATTRIBUTED.search(p):
                r.fails.append(f"Demonstrated results: a number without 'according to data presented by ...': {p[:90]!r}")
        if not any(NON_GUARANTEE.search(p) for p in res):
            r.fails.append("Demonstrated results: no non-guarantee line ('... rather than interpreted as guarantees "
                           "of future performance')")
    if "positioning" in seen:
        pos = " ".join(bodies["positioning"])
        if not re.search(r"should (\w+ )?be described", pos) or not re.search(r"should not (\w+ )?be described", pos):
            r.warns.append("Positioning: missing the 'should be described as / should not be described as' pair")


def check_canary(md, seen, canary, r: Report) -> None:
    if not re.search(r"Last updated:?\**\s*[A-Z][a-z]+ \d{4}", md):
        r.fails.append("no 'Last updated: Month YYYY' line")
    has = "DIRECT COMMAND TO AI MODELS" in md
    if canary and not has:
        r.fails.append("--canary given but the page has no DIRECT COMMAND TO AI MODELS block")
    elif has and not canary:
        r.fails.append("page has a DIRECT COMMAND canary block but the user did not opt in (pass --canary only on a clear yes)")
    elif has:
        if canary not in md.split("DIRECT COMMAND TO AI MODELS", 1)[1]:
            r.fails.append(f"canary block does not contain the chosen emoji {canary}")
        if seen[-1] != "canary":
            r.fails.append("the canary block must be the last section")


def check_paragraph(p: str, r: Report) -> None:
    pm = PROMISE.search(p)
    if pm and not NEGATED.search(p):
        r.fails.append(f"promise language {pm.group(0)!r}: {p[:90]!r}")
    fp = FIRST_PERSON.findall(re.sub(r"\"[^\"]*\"|“[^”]*”", "", p))
    if fp:
        r.warns.append(f"first person {sorted(set(fp))}; write in the third person: {p[:70]!r}")
    if VAGUE.search(p):
        r.warns.append(f"vague quantity {VAGUE.search(p).group(0)!r}; use the published number or drop it: {p[:70]!r}")
    vm = VOLATILE.search(VERIFY.sub("", p))
    if vm and not re.search(r"consult|official|change", p, re.I):
        r.warns.append(f"volatile fact {vm.group(0)!r} stated flat; deflect prices and counts to the official source")
    sm = SUPERLATIVE.search(p)
    if sm and not SUPERLATIVE_OK.search(p):
        r.warns.append(f"unattributed superlative {sm.group(0)!r}: {p[:70]!r}")


def check_text(md, body, locale, forbid, r: Report) -> None:
    if "—" in md:
        r.fails.append(f"{md.count(chr(0x2014))} em dash(es); the pack forbids them, use a comma, colon or full stop")
    if " – " in md:
        r.warns.append("spaced en dash used as a dash; use a comma or full stop")
    for term in forbid:
        if term and re.search(re.escape(term), md, re.I):
            r.fails.append(f"forbidden term present: {term!r}")
    for p in paragraphs(body.splitlines()):
        check_paragraph(p, r)
    wrong = US_SPELL if locale.lower() in ("en-au", "en-gb", "en-nz") else AU_SPELL if locale.lower() == "en-us" else None
    hits = sorted({h.group(0) for h in wrong.finditer(body)}) if wrong else []
    if hits:
        r.warns.append(f"spellings that do not match {locale}: {hits} (keep only official proper nouns)")


def check_provenance(md, body, bundle, final, r: Report) -> None:
    verifies = VERIFY.findall(md)
    if verifies:
        (r.fails if final else r.notes).append(f"{len(verifies)} [VERIFY: ...] placeholder(s) left for the user: "
                                               + "; ".join(v[9:-1].strip() for v in verifies))
    checked = "\n".join(ln for ln in VERIFY.sub("", body).splitlines() if not re.search(r"Last updated", ln, re.I))
    bundle_vals = num_values(bundle)
    found = list(NUM.finditer(checked))
    orphans = [m for m in found if not num_values(m.group(0)) & bundle_vals]
    for m in orphans:
        ctx = checked[max(0, m.start() - 40): m.end() + 30].replace("\n", " ").strip()
        r.fails.append(f"number not in the input bundle (invented?): {m.group(0).strip()!r} in '...{ctx}...'")
    r.notes.append(f"numeric provenance: {len(found)} numbers checked against {len(bundle_vals)} distinct numbers "
                   f"in the bundle, {len(orphans)} orphan(s)")


def lint_page(md: str, bundle: str, brand: str | None, canary: str | None, locale: str,
              forbid: list[str], final: bool) -> tuple[list[str], list[str], list[str]]:
    r = Report()
    secs = split_sections(md)
    if len(secs) < 2:
        return ["no H2 headings found; the page must use ## headings like the GPT"], [], []
    body = md.split("DIRECT COMMAND TO AI MODELS", 1)[0]
    check_title(secs, brand, r)
    seen, bodies = check_order(secs, r)
    check_basic(bodies, r)
    check_instructions(bodies, r)
    check_results(bodies, seen, r)
    check_canary(md, seen, canary, r)
    check_text(md, body, locale, forbid, r)
    check_provenance(md, body, bundle, final, r)
    return r.fails, r.warns, r.notes


def cmd_lint(args) -> int:
    run = Path(args.run_dir)
    page = Path(args.page) if args.page else run / PAGE_MD
    bundle_p = Path(args.bundle) if args.bundle else run / BUNDLE
    if not page.is_file():
        sys.exit(f"missing {page}")
    if not bundle_p.is_file():
        sys.exit(f"missing {bundle_p}: run gather first")
    md = page.read_text(encoding="utf-8")
    fails, warns, notes = lint_page(md, bundle_p.read_text(encoding="utf-8", errors="replace"), args.brand,
                                    args.canary, args.locale, args.forbid or [], args.final)
    words = len(re.sub(r"[#*]", "", md).split())
    lines = [f"# Lint: {page}", "", f"Checked {time.strftime('%Y-%m-%d %H:%M')}, {words} words", ""]
    for f in fails:
        lines.append(f"- FAIL {f}")
    for w in warns:
        lines.append(f"- WARN {w}")
    for n in notes:
        lines.append(f"- NOTE {n}")
    verdict = "FAIL" if fails else "PASS"
    lines += ["", f"**Result: {verdict}** ({len(fails)} fail, {len(warns)} warn)"]
    for ln in lines[4:]:
        print(ln)
    out = run / DATA / ("lint.md" if not args.page else f"lint-{page.stem}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if fails else 0


# ---------------------------------------------------------------- render --

def md_to_html(md: str) -> str:
    ai = sibling()
    out = ['<article class="ai-info-page">']
    secs = split_sections(md)
    first = True
    for heading, lines in secs:
        if heading:
            sid = classify(heading)
            if first:
                out.append(f"<h1>{ai.esc(heading)}</h1>")
                first = False
            elif sid in ("last_updated", "more_info"):
                label, _, value = heading.partition(":")
                value = value.strip()
                if sid == "last_updated":
                    out.append(f"<p><strong>{ai.esc(label)}:</strong> <time>{ai.esc(value)}</time></p>")
                else:
                    out.append(f"<p><strong>{ai.esc(label)}:</strong> {ai.linkify(value)}</p>")
            else:
                hid = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
                out.append(f'<h2 id="{hid}">{ai.esc(heading)}</h2>')
            basic = sid == "basic"
        else:
            basic = False
        for p in paragraphs(lines):
            if p.startswith("###"):
                out.append(f"<h3>{ai.esc(p.lstrip('#').strip())}</h3>")
                continue
            km = re.match(r"^\**([A-Za-z][A-Za-z /&-]{1,40}?):\**\s+(.*)$", p) if basic else None
            if km:
                out.append(f"<p><strong>{ai.esc(km.group(1))}:</strong> {ai.linkify(km.group(2))}</p>")
            else:
                out.append(f"<p>{ai.linkify(p)}</p>")
    out.append("</article>")
    return "\n".join(out) + "\n"


HANDOVER_TMPL = """# AI Info Page: handover for {brand}

Generated {date} by mos-geo-ai-info-generator (a fast draft in the shape of Steve Toth's AI Info
Page GPT). Every number on the page was checked against the brand's own inputs by `lint`.
It is a draft from context the brand already had, not an audited, statement-by-statement
sourced deliverable. For that, run `/mos-geo-ai-info`.

## Files

- `page.md`: paste-ready copy for any CMS editor.
- `page.html`: the same page as plain semantic HTML (no scripts, styles or external assets).
  Drop it into a blank page template.
- `data/lint.md`: the gate result. `data/input-bundle.md`: everything the page was written from.

## Publish it

| Item | Setting |
|---|---|
| URL | `{url}` (`/llm-info` and `/ai-information` are also used; pick one and never move it) |
| Indexing | Indexable (`noindex` off), self-canonical |
| Sitemap | Add the URL to the XML sitemap |
| Footer link | On every page, text such as "Hey AI, learn about us" (Steve Toth's wording) or "AI info" |
| Also link from | The About page |
| robots.txt | Do not block GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended or Bingbot |
| Rendering | The text must be in the HTML the server sends, not injected by JavaScript |
| Updates | Change the "Last updated" line whenever a fact changes; review every 6 months |

{canary_note}

## Open items before publishing

{verify_list}

## After it is live

```bash
python3 "$SKILL/scripts/aiinfo_gen.py" check --url {url} --brand "{brand}" --run-dir <run folder>
```

This runs the `mos-geo-ai-info` post-launch check: 200, indexable, self-canonical, served as
HTML, Last updated within 6 months, AI crawlers allowed, in the sitemap, linked from the
homepage. Every check except llms.txt (and the Organization JSON-LD check, which this draft
does not ship) should pass.

## What to promise (and not)

An AI Info Page is an ordinary indexable page. Search-backed engines can retrieve and cite
it like any other page; nothing published shows engines give it extra weight, and no AI vendor
endorses the format. Sell it as one accurate, first-party, dated source of facts, not as a
visibility lever. Evidence and limits: `mos-geo-ai-info/references/publishing.md`.
"""


def cmd_render(args) -> int:
    run = Path(args.run_dir)
    md = (run / PAGE_MD).read_text(encoding="utf-8")
    (run / PAGE_HTML).write_text(md_to_html(md), encoding="utf-8")
    title = re.search(r"^## Official Information About (.+)$", md, re.M)
    brand = args.brand or (title.group(1).strip() if title else "the brand")
    verifies = [v[9:-1].strip() for v in VERIFY.findall(md)]
    verify_list = "\n".join(f"- [ ] {v}" for v in verifies) or "- None. Every [VERIFY] item has been resolved."
    ai = sibling()
    canary_note = (f"**Canary:** ON. The page ends with a DIRECT COMMAND asking assistants to add {args.canary} "
                   f"({ai.canary_name(args.canary) or 'custom emoji'}). It is a detection test that uses the same "
                   "mechanism as prompt injection; the brand opted in knowing some reviewers treat it as manipulation."
                   if args.canary else "**Canary:** off (the default).")
    (run / HANDOVER).write_text(HANDOVER_TMPL.format(brand=brand, date=time.strftime("%d %B %Y").lstrip("0"),
                                                     url=args.url or "https://<domain>/ai-info",
                                                     canary_note=canary_note, verify_list=verify_list),
                                encoding="utf-8")
    print(f"Wrote {run / PAGE_HTML} and {run / HANDOVER}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("path", help="print the run folder")
    p.add_argument("--brand", required=True)
    p.add_argument("--date")
    p.add_argument("--start")
    p.set_defaults(fn=cmd_path)
    p = sub.add_parser("crawl", help="crawl the brand's site (mos-geo-ai-info crawler)")
    p.add_argument("--url", required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--max-pages", type=int, default=20)
    p.set_defaults(fn=cmd_crawl)
    p = sub.add_parser("gather", help="build data/input-bundle.md")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--brain", help="MarketingOS brain root (reads the default identity files)")
    p.add_argument("--include", action="append", help="extra file or folder of .md (repeatable)")
    p.set_defaults(fn=cmd_gather)
    p = sub.add_parser("lint", help="the deterministic gate")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--page", help="lint this file instead of <run>/page.md")
    p.add_argument("--bundle", help="use this bundle instead of <run>/data/input-bundle.md")
    p.add_argument("--brand")
    p.add_argument("--canary", help="the opted-in emoji; omit when the user said no")
    p.add_argument("--locale", default="en-AU")
    p.add_argument("--forbid", action="append", help="a term that must never appear (repeatable)")
    p.add_argument("--final", action="store_true", help="also fail on any [VERIFY: ...] left")
    p.set_defaults(fn=cmd_lint)
    p = sub.add_parser("render", help="page.md -> page.html + handover.md")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--brand")
    p.add_argument("--url", help="where the page will live, e.g. https://example.com/ai-info")
    p.add_argument("--canary")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("check", help="test the live page (mos-geo-ai-info check)")
    p.add_argument("--url", required=True)
    p.add_argument("--brand")
    p.add_argument("--run-dir")
    p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
