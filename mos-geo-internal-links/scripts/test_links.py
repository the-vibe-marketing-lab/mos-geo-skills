"""Offline tests for links.py. No network.

Run: python3 -m unittest scripts/test_links.py  (from the skill folder)
"""

import csv
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import links as L  # noqa: E402

CFG = L.load_config()
SITE = "https://acme.example"
STOP = set(CFG["stopwords"])


def article(title, body, slug, related=""):
    """An Oxygen-style post: header menu, breadcrumb and byline outside the content root,
    TOC and author box inside it, a dynamic related list, a footer."""
    return f"""<html><head><title>{title} - Acme</title>
<link rel="canonical" href="{SITE}{slug}" /></head>
<body class="wp-singular single single-post">
<header class="oxy-header-wrapper"><ul class="menu"><li><a href="{SITE}/guides/">Guides</a></li></ul></header>
<section id="section-4">
 <nav class="rank-math-breadcrumb"><p><a href="{SITE}/guides/">Guides</a></p></nav>
 <div class="byline">Written by <a href="{SITE}/author/jo/">Jo</a></div>
 <h1>{title}</h1>
 <div class="ct-inner-content">
  <div class="lwptoc"><div class="lwptoc_item"><a href="#intro">Intro</a></div></div>
  {body}
  <div class="saboxplugin-wrap"><div class="saboxplugin-authorname"><a href="{SITE}/author/jo/">Jo</a></div>
   <p>Jo has written about widgets for years and knows them well.</p></div>
 </div>
 <div class="oxy-dynamic-list">{related}</div>
</section>
<footer><a href="{SITE}/category/old/">Old</a></footer></body></html>"""


BODY_A = """<h2 id="intro">Choosing a widget</h2>
<p>Most people start with a steel widget because it lasts. If you care about weight, read our
<a href="/guides/aluminium-widgets/">aluminium widget guide</a> before you buy anything at all.</p>
<p>Cleaning a widget after every use keeps the hinges moving and stops rust forming on the steel.</p>
<h2>Other guides</h2>
<ul><li><a href="{SITE}/guides/widget-cleaning/">Widget Cleaning Guide</a></li></ul>
<h3>Widget maintenance schedule</h3>
<p>Oil the hinges of your widget every month. A widget that is oiled and cleaned regularly will last
for years, and a rusty widget hinge is the most common reason people replace one early.</p>""".replace("{SITE}", SITE)

BODY_B = """<h2>Why aluminium</h2>
<p>An aluminium widget weighs half as much as steel and never rusts, which matters for travel widgets.
Aluminium widgets cost more but they are easier to carry around every single day. If you clean your
widget after use and oil the hinges, an aluminium widget will outlast most steel widgets.</p>"""

BODY_C = """<h2>How to clean a widget</h2>
<p>Wipe the widget with warm soapy water, dry the hinges and oil them. Cleaning takes five minutes
and prevents rust on every steel widget you own, which keeps the hinges moving freely. Aluminium
widgets need less cleaning because they never rust, but their hinges still need oil.</p>"""

INTERNAL_COLS = ["Address", "Content Type", "Status Code", "Status", "Indexability", "Indexability Status",
                 "Title 1", "Meta Description 1", "H1-1", "Canonical Link Element 1", "Word Count", "Crawl Depth",
                 "Link Score", "Inlinks", "Unique Inlinks", "Outlinks", "Redirect URL", "Clicks", "Impressions",
                 "CTR", "Position", "Closest Near Duplicate Match", "Closest Semantically Similar Address",
                 "Semantic Similarity Score"]
INLINK_COLS = ["Type", "Source", "Destination", "Alt Text", "Anchor", "Status Code", "Status", "Follow",
               "Link Path", "Link Position"]


def sf_row(url, status="200", idx="Indexable", title="", h1="", depth="2", imp="0", pos="", redirect=""):
    return {"Address": url, "Content Type": "text/html; charset=UTF-8", "Status Code": status, "Status": "",
            "Indexability": idx, "Indexability Status": "" if idx == "Indexable" else "Redirected",
            "Title 1": title, "Meta Description 1": "", "H1-1": h1, "Canonical Link Element 1": url if status == "200" else "",
            "Word Count": "300", "Crawl Depth": depth, "Link Score": "10", "Inlinks": "5", "Unique Inlinks": "3",
            "Outlinks": "10", "Redirect URL": redirect, "Clicks": "0", "Impressions": imp, "CTR": "", "Position": pos,
            "Closest Near Duplicate Match": "", "Closest Semantically Similar Address": "", "Semantic Similarity Score": ""}


def write_csv(path, rows, cols):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def build_site(tmp: Path) -> dict:
    a, b, c = f"{SITE}/guides/steel-widgets/", f"{SITE}/guides/aluminium-widgets/", f"{SITE}/guides/widget-cleaning/"
    src = tmp / "html"
    src.mkdir()
    (src / "original_https_acme.example_guides_steel-widgets_.html").write_text(
        article("Steel Widgets Explained", BODY_A, "/guides/steel-widgets/",
                related=f'<a href="{c}">Widget Cleaning Guide</a>'), encoding="utf-8")
    (src / "original_https_acme.example_guides_aluminium-widgets_.html").write_text(
        article("Aluminium Widgets Guide", BODY_B, "/guides/aluminium-widgets/"), encoding="utf-8")
    (src / "original_https_acme.example_guides_widget-cleaning_.html").write_text(
        article("How To Clean A Widget", BODY_C, "/guides/widget-cleaning/"), encoding="utf-8")
    rows = [sf_row(f"{SITE}/", title="Acme - Acme", depth="0"),
            sf_row(a, title="Steel Widgets Explained - Acme", h1="Steel Widgets Explained", imp="40"),
            sf_row(b, title="Aluminium Widgets Guide - Acme", h1="Aluminium Widgets Guide", imp="10"),
            sf_row(c, title="How To Clean A Widget - Acme", h1="How To Clean A Widget", imp="120", pos="9", depth="4"),
            sf_row(f"{SITE}/category/old/", status="301", idx="Non-Indexable", redirect=f"{SITE}/guides/"),
            sf_row(f"{SITE}/guides/", status="404", idx="Non-Indexable")]
    write_csv(tmp / "internal.csv", rows, INTERNAL_COLS)
    body = "//body/section[@id='section-4']/div/p/a"

    def hl(s, d, anchor, pos="Content", path=body, status="200"):
        return {"Type": "Hyperlink", "Source": s, "Destination": d, "Alt Text": "", "Anchor": anchor,
                "Status Code": status, "Status": "", "Follow": "true", "Link Path": path, "Link Position": pos}
    inl = []
    for s in (a, b, c):
        inl += [hl(s, f"{SITE}/guides/", "Guides", "Header", "//body/header/ul/li/a", "404"),
                hl(s, f"{SITE}/guides/", "Guides", status="404"),
                hl(s, f"{SITE}/author/jo/", "Jo"),
                hl(s, s, "Intro"),
                hl(s, f"{SITE}/author/jo/", "Jo"),
                hl(s, f"{SITE}/category/old/", "Old", "Footer", "//body/footer/a", "301")]
    inl += [hl(a, b, "aluminium widget guide"), hl(a, c, "Widget Cleaning Guide"), hl(a, c, "Widget Cleaning Guide")]
    write_csv(tmp / "inlinks.csv", inl, INLINK_COLS)
    return {"a": a, "b": b, "c": c, "src": src}


def quiet(fn, *args, **kw):
    with redirect_stdout(io.StringIO()):
        return fn(*args, **kw)


class Pipeline(unittest.TestCase):
    """inventory -> graph -> audit -> candidates -> judge/place --dry-run on a synthetic site."""

    @classmethod
    def setUpClass(cls):
        cls.tmpd = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.tmpd.name)
        cls.site = build_site(cls.tmp)
        cls.rundir = cls.tmp / "run"
        quiet(L.cmd_inventory, Namespace(config=None, internal_html=str(cls.tmp / "internal.csv"),
                                         inlinks=str(cls.tmp / "inlinks.csv"), sources=str(cls.site["src"]),
                                         out=str(cls.rundir)))
        quiet(L.cmd_graph, Namespace(config=None, run_dir=str(cls.rundir), inlinks=None))
        quiet(L.cmd_audit, Namespace(config=None, run_dir=str(cls.rundir)))
        quiet(L.cmd_candidates, Namespace(config=None, run_dir=str(cls.rundir), k=5))
        cls.inv = json.loads((cls.rundir / "data/pages.json").read_text())
        cls.graph = json.loads((cls.rundir / "data/links.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmpd.cleanup()

    def test_eligibility(self):
        p = self.inv["pages"]
        self.assertTrue(p[self.site["a"]]["eligible_target"])
        self.assertTrue(p[self.site["a"]]["eligible_source"])
        self.assertFalse(p[f"{SITE}/"]["eligible_target"])  # home is not a contextual target
        self.assertEqual(p[self.site["a"]]["page_type"], "article")
        self.assertEqual(p[self.site["a"]]["title"], "Steel Widgets Explained")  # site suffix stripped

    def test_sections_exclude_chrome(self):
        secs = self.inv["pages"][self.site["a"]]["sections"]
        text = " ".join(s["text"] for sec in secs for s in sec["sentences"])
        self.assertNotIn("Intro", text)            # TOC
        self.assertNotIn("written about widgets", text)  # author box
        self.assertNotIn("Written by", text)      # byline outside the content root
        heads = [s["heading"] for s in secs]
        self.assertIn("Choosing a widget", heads)
        self.assertIn("Widget maintenance schedule", heads)
        other = next(s for s in secs if s["heading"] == "Other guides")
        self.assertTrue(all(x["link_only"] for x in other["sentences"]))

    def test_link_classes(self):
        cls = {(l["destination"], l["anchor"], l["sf_position"]): l["class"] for l in self.graph["links"]
               if l["source"] == self.site["a"]}
        self.assertEqual(cls[(self.site["b"], "aluminium widget guide", "Content")], "contextual")
        self.assertEqual(cls[(self.site["a"], "Intro", "Content")], "toc")
        self.assertEqual(cls[(f"{SITE}/guides/", "Guides", "Header")], "header")
        self.assertEqual(cls[(f"{SITE}/guides/", "Guides", "Content")], "breadcrumb")
        self.assertEqual(cls[(f"{SITE}/category/old/", "Old", "Footer")], "footer")
        both = sorted(l["class"] for l in self.graph["links"]
                      if l["source"] == self.site["a"] and l["destination"] == f"{SITE}/author/jo/")
        self.assertEqual(both, ["author_box", "template"])
        wc = sorted(l["class"] for l in self.graph["links"]
                    if l["source"] == self.site["a"] and l["destination"] == self.site["c"])
        self.assertEqual(wc, ["link_list", "related_repeater"])
        self.assertEqual(self.graph["summary"]["true_contextual"], 1)

    def test_audit(self):
        t = L.audit_tables(self.inv, self.graph, CFG)
        orphans = {r["url"] for r in t["orphans"]}
        self.assertIn(self.site["c"], orphans)          # only a link list and a repeater point at it
        self.assertNotIn(self.site["b"], orphans)
        self.assertEqual([r["url"] for r in t["deep"]], [self.site["c"]])
        bad = {(r["destination"], r["status"]) for r in t["broken"]}
        self.assertIn((f"{SITE}/category/old/", "301"), bad)
        self.assertIn((f"{SITE}/guides/", "404"), bad)
        self.assertTrue((self.rundir / "deliverables/01-audit/audit.md").is_file())
        self.assertTrue((self.rundir / "deliverables/01-audit/audit.csv").is_file())

    def test_candidates_exclude_already_linked(self):
        c = json.loads((self.rundir / "data/candidates.json").read_text())
        for sec in c["sources"][self.site["a"]]["sections"]:
            urls = {x["url"] for x in sec["candidates"]}
            self.assertNotIn(self.site["a"], urls)
            self.assertNotIn(self.site["b"], urls)  # already linked in the body
            self.assertNotIn(self.site["c"], urls)  # already linked from a list: any position counts
        self.assertEqual(c["recall"]["existing_contextual_links_tested"], 1)
        self.assertEqual(c["recall"]["section_recall"]["@5"], 1.0)

    def test_dry_run_payloads(self):
        quiet(L.cmd_judge, Namespace(config=None, run_dir=str(self.rundir), env_file=None, dry_run=True, limit=2, workers=None))
        quiet(L.cmd_place, Namespace(config=None, run_dir=str(self.rundir), env_file=None, dry_run=True, limit=2, workers=None))
        lines = (self.rundir / "data/jev_requests.jsonl").read_text().splitlines()
        meta = [json.loads(m) for m in (self.rundir / "data/jev_requests.index.jsonl").read_text().splitlines()]
        self.assertEqual(len(lines), len(meta))
        self.assertEqual({m["stage"] for m in meta}, {"judge", "place"})
        for line in lines:
            p = json.loads(line)
            self.assertEqual(set(p), {"state", "model", "questions"})
            self.assertEqual(L.validate_payload(p), [])
        # re-running one stage replaces its own lines and keeps the other stage's
        quiet(L.cmd_judge, Namespace(config=None, run_dir=str(self.rundir), env_file=None, dry_run=True, limit=1, workers=None))
        meta2 = [json.loads(m) for m in (self.rundir / "data/jev_requests.index.jsonl").read_text().splitlines()]
        self.assertEqual(sum(m["stage"] == "judge" for m in meta2), 2)
        self.assertEqual(sum(m["stage"] == "place" for m in meta2), sum(m["stage"] == "place" for m in meta))


    def test_score_and_build_from_jev_answers(self):
        b, c = self.site["b"], self.site["c"]
        sec = self.inv["pages"][b]["sections"][0]
        sent = next(s for s in sec["sentences"] if "clean your" in s["text"])
        key = f"{b}#{sec['id']}"
        (self.rundir / "data/judgements.json").write_text(json.dumps({key: {
            "source": b, "section": sec["id"], "model": "jev-1.13.0", "link_opportunity": 0.8,
            "best_target": "/guides/widget-cleaning/", "best_target_probs": {"/guides/widget-cleaning/": 0.9},
            "source_intent": "informational",
            "targets": {c: {"adds_value": 0.9, "intent": "informational", "best_target_prob": 0.9}}}}))
        (self.rundir / "data/placements.json").write_text(json.dumps({f"{key}->{c}": {
            "source": b, "section": sec["id"], "target": c, "sentence": sent["id"], "exists": 0.9,
            "anchor": "clean your widget", "anchor_confidence": 0.8}}))
        quiet(L.cmd_score, Namespace(config=None, run_dir=str(self.rundir)))
        quiet(L.cmd_build, Namespace(config=None, run_dir=str(self.rundir)))
        d = self.rundir / "deliverables"
        with open(d / "03-add-internal-links/recommendations.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target"], c)
        self.assertEqual(rows[0]["sentence"], sent["text"])  # verbatim, no markup in the CSV
        self.assertEqual((rows[0]["approved"], rows[0]["status"], rows[0]["note"]), ("", "", ""))
        md = (d / "03-add-internal-links/recommendations.md").read_text(encoding="utf-8")
        self.assertIn("[[clean your widget]]", md)
        self.assertIn("1 new links to add", (d / "README.md").read_text(encoding="utf-8"))

    def test_deliverables_layout(self):
        quiet(L.cmd_score, Namespace(config=None, run_dir=str(self.rundir)))  # works with or without Jev results
        quiet(L.cmd_build, Namespace(config=None, run_dir=str(self.rundir)))
        d = self.rundir / "deliverables"
        files = {str(p.relative_to(d)).replace("\\", "/") for p in d.rglob("*") if p.is_file()}
        self.assertEqual(files, {"README.md", "01-audit/audit.md", "01-audit/audit.csv",
                                 "02-fix-broken-links/broken-links.md", "02-fix-broken-links/broken-links.csv",
                                 "03-add-internal-links/recommendations.md", "03-add-internal-links/recommendations.csv"})
        for md, csv_name in (("01-audit/audit.md", "audit.csv"), ("02-fix-broken-links/broken-links.md", "broken-links.csv"),
                             ("03-add-internal-links/recommendations.md", "recommendations.csv")):
            text = (d / md).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("## What this is\n"), md)
            i, j, k = text.index("## What to do"), text.index("## Prompt for your AI"), text.index("```text")
            self.assertTrue(i < j < k, md)
            prompt = text[k + 8: text.index("```", k + 8)]
            self.assertIn(f"`{csv_name}`", prompt)            # names its CSV by relative path
            self.assertNotIn("acme", prompt.lower())          # generic: nothing site-specific in prompts
        readme = (d / "README.md").read_text(encoding="utf-8")
        for h in ("## What this is", "## Start here", "## The two bands", "## Safety", "## Words used here"):
            self.assertIn(h, readme)
        for step in ("01-audit/audit.md", "02-fix-broken-links/broken-links.md",
                     "03-add-internal-links/recommendations.md", "Screaming Frog"):
            self.assertIn(step, readme)
        for name, first in (("02-fix-broken-links/broken-links.csv", L.BROKEN_FIELDS),
                            ("03-add-internal-links/recommendations.csv", L.REC_FIELDS)):
            with open(d / name, encoding="utf-8") as fh:
                self.assertEqual(next(csv.reader(fh)), first)  # header row first, no prompt rows
        self.assertEqual(L.REC_FIELDS[:8], ["page", "page_title", "section_heading", "sentence", "anchor", "target",
                                            "target_title", "band"])
        with open(d / "02-fix-broken-links/broken-links.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        scopes = {(r["scope"], r["old_url"]) for r in rows}
        self.assertIn(("template", f"{SITE}/category/old/"), scopes)   # footer: fixed once, site-wide
        self.assertIn(("template", f"{SITE}/guides/"), scopes)         # header + breadcrumb are template too
        self.assertFalse([r for r in rows if r["scope"] == "body"])    # no broken links in body text here



class Units(unittest.TestCase):
    def test_norm_url(self):
        self.assertEqual(L.norm_url("/a/b/#x", "https://Acme.example/c/"), "https://acme.example/a/b/")
        self.assertEqual(L.norm_url("https://acme.example"), "https://acme.example/")
        self.assertIsNone(L.norm_url("mailto:hi@acme.example"))
        self.assertIsNone(L.norm_url("javascript:void(0)"))

    def test_split_sentences(self):
        s = L.split_sentences("Floyd Mayweather Jr. trained hard. He ran daily! Did he rest? Yes.")
        self.assertEqual(s, ["Floyd Mayweather Jr. trained hard.", "He ran daily!", "Did he rest?", "Yes."])

    def test_page_type(self):
        self.assertEqual(L.page_type(f"{SITE}/", "", None), "home")
        self.assertEqual(L.page_type(f"{SITE}/blog/page/2/", "archive", None), "pagination")
        self.assertEqual(L.page_type(f"{SITE}/author/jo/", "archive author", None), "author")
        self.assertEqual(L.page_type(f"{SITE}/x/", "archive category", None), "category")
        self.assertEqual(L.page_type(f"{SITE}/about/", "wp-singular page", None), "page")
        self.assertEqual(L.page_type(f"{SITE}/x/y/", "single single-post", None), "article")

    def test_html_mapping_prefers_canonical_but_breaks_ties_by_name(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name in ("original_https_acme.example_.html", "original_https_acme.example_page_2_.html"):
                (d / name).write_text(f'<link rel="canonical" href="{SITE}/" />', encoding="utf-8")
            (d / "misnamed.html").write_text(f'<link rel="canonical" href="{SITE}/real/" />', encoding="utf-8")
            m, _ = L.map_html_files(d, set())
            self.assertEqual(m[f"{SITE}/"].name, "original_https_acme.example_.html")
            self.assertEqual(m[f"{SITE}/page/2/"].name, "original_https_acme.example_page_2_.html")
            self.assertEqual(m[f"{SITE}/real/"].name, "misnamed.html")

    def test_resolve_redirect_chain(self):
        sf = {"http://acme.example/old/": {"Status Code": "301", "Redirect URL": "http://acme.example/"},
              "http://acme.example/": {"Status Code": "301", "Redirect URL": "https://acme.example/"},
              "https://acme.example/": {"Status Code": "200"}}
        self.assertEqual(L.resolve_redirect("http://acme.example/old/", sf), ("https://acme.example/", "200"))

    def test_bm25_ranks_relevant_first(self):
        bm = L.BM25({"clean": L.tokens("how to clean a widget cleaning", STOP),
                     "alu": L.tokens("aluminium widgets guide", STOP)})
        top = L.shortlist(bm, L.tokens("cleaning the widget hinges", STOP), set(), 2)
        self.assertEqual(top[0][0], "clean")
        self.assertEqual(L.shortlist(bm, L.tokens("cleaning", STOP), {"clean"}, 2), [])

    def test_anchor_options(self):
        sent = {"text": "Wipe the steel widget hinges, then read about cleaning a widget properly here.",
                "links": [{"href": f"{SITE}/x/", "anchor": "steel widget"}]}
        tgt = {"title": "How To Clean A Widget", "h1": "How To Clean A Widget", "url": f"{SITE}/guides/widget-cleaning/"}
        opts = L.anchor_options(sent, tgt, CFG, STOP)
        self.assertIn("cleaning a widget", opts)
        for o in opts:
            self.assertIn(o, sent["text"])                   # verbatim
            self.assertTrue(2 <= len(o.split()) <= 6)
            self.assertNotIn(",", o)                          # never crosses punctuation
            self.assertNotIn("steel widget", o)               # never overlaps an existing link
            self.assertNotIn(o.split()[0].lower(), STOP)
            self.assertNotIn(o.split()[-1].lower(), STOP)
        self.assertNotIn("here", [o.lower() for o in opts])

    def test_blocks_group_to_h2_and_keep_sentence_ids(self):
        sec = lambda i, lvl, h: {"id": i, "level": lvl, "heading": h, "words": 10,
                                 "sentences": [{"id": f"{i}.01", "text": f"{h} text."}]}
        page = {"sections": [sec("S01", "intro", ""), sec("S02", "h2", "A"), sec("S03", "h3", "A1"),
                             sec("S04", "h4", "A1a"), sec("S05", "h2", "B"), sec("S06", "h3", "B1")]}
        b = L.blocks_of(page, CFG)
        self.assertEqual([x["members"] for x in b], [["S01"], ["S02", "S03", "S04"], ["S05", "S06"]])
        self.assertEqual([s["id"] for s in b[1]["sentences"]], ["S02.01", "S03.01", "S04.01"])
        self.assertEqual(b[1]["words"], 30)
        self.assertEqual(b[1]["subheadings"], ["A1", "A1a"])
        fine = L.deep_merge(CFG, {"sections": {"group_level": "h4"}})
        self.assertEqual(len(L.blocks_of(page, fine)), 6)

    def test_block_text_truncated_by_whole_sentences(self):
        sents = [{"id": f"S01.{i:02d}", "text": "word " * 40} for i in range(20)]  # ~51 tokens each
        kept, cut = L.budget_sentences(sents, 200)
        self.assertTrue(cut)
        self.assertEqual(len(kept), 3)
        cfg = L.deep_merge(CFG, {"sections": {"max_block_tokens": 200}})
        st = L.section_state({"title": "T", "url": "u", "h1": "T"}, {"heading": "H", "sentences": sents}, cfg)
        self.assertIn("[truncated: first 3 of 20 sentences]", st["source_section"]["text"])
        self.assertFalse(L.budget_sentences(sents[:2], 200)[1])

    def test_anchor_shape_rejects_clauses_and_verb_openers(self):
        tgt = {"title": "Boxing Gloves", "h1": "Boxing Gloves", "url": f"{SITE}/boxing-gloves/"}
        cases = {
            "Height and reach are essential factors in a fight.": "reach are essential factors",
            "We cover the history of why boxing gloves exist.": "history of why boxing gloves",
            "Deciding what type of glove to buy is hard.": "Deciding what type of glove",
            "Prioritize mastering the fundamentals first.": "Prioritize mastering the fundamentals",
        }
        for text, bad in cases.items():
            opts = L.anchor_options({"text": text, "links": []}, tgt, CFG, STOP)
            self.assertNotIn(bad, opts, text)
            for o in opts:
                self.assertIn(o, text)
        opts = L.anchor_options({"text": "Boxing gloves protect your hands during sparring sessions.", "links": []},
                                tgt, CFG, STOP)
        self.assertIn("Boxing gloves", opts)  # a sentence-opening -ing noun is still fine
        self.assertIn("sparring sessions", opts)
        opts = L.anchor_options({"text": "Read the history of boxing gloves today.", "links": []}, tgt, CFG, STOP)
        self.assertIn("history of boxing gloves", opts)  # 'of' inside a noun phrase is fine
        self.assertEqual(opts[0], "boxing gloves")  # target-overlapping noun phrase ranks first

    def test_anchor_shape_edges(self):
        ok = lambda ws, start=False: L.anchor_shape_ok(ws, start, STOP, set(CFG["anchors"]["inner_break_words"]),
                                                       set(CFG["anchors"]["edge_verbs"]), CFG["anchors"]["verbish_suffixes"])
        self.assertFalse(ok(["the", "gloves"]))
        self.assertFalse(ok(["gloves", "for"]))
        self.assertFalse(ok(["using", "hand", "wraps"]))
        self.assertTrue(ok(["hand", "wraps"]))
        self.assertTrue(ok(["tips", "and", "tricks"]))

    def test_broken_rows_split_template_and_body(self):
        br = lambda src, where: {"source": src, "destination": f"{SITE}/old/", "anchor": "Old", "status": "301",
                                 "fix_to": f"{SITE}/new/", "action": "update the href to the final URL", "where": where}
        rows = L.broken_rows({"broken": [br("p1", "footer:1"), br("p2", "footer:1 contextual:1"), br("p3", "nav:2")]})
        tm = [r for r in rows if r["scope"] == "template"]
        bd = [r for r in rows if r["scope"] == "body"]
        self.assertEqual(len(tm), 1)                       # one site-wide fix per old URL
        self.assertEqual((tm[0]["instances"], tm[0]["pages_affected"]), (4, 3))
        self.assertEqual([(r["page"], r["instances"]) for r in bd], [("p2", 1)])
        self.assertTrue(all(r["status"] == "" and r["note"] == "" for r in rows))

    def test_validate_payload(self):
        good = {"state": {}, "model": "jev-latest",
                "questions": {"q": {"type": "choice", "instructions": "x", "criteria": {"a": None, "none": "n"}}}}
        self.assertEqual(L.validate_payload(good), [])
        big = json.loads(json.dumps(good))
        big["questions"]["q"]["criteria"] = {str(i): None for i in range(256)}
        self.assertTrue(L.validate_payload(big))
        extra = dict(good, stream=True)
        self.assertTrue(L.validate_payload(extra))

    def test_load_env_file_and_environment(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".env"
            f.write_text("export TYPESAFE_API_KEY='from-file'\n# comment\n", encoding="utf-8")
            with mock.patch.dict("os.environ", {}, clear=True):
                self.assertEqual(L.load_env(str(f))["TYPESAFE_API_KEY"], "from-file")
            with mock.patch.dict("os.environ", {"TYPESAFE_API_KEY": "from-env"}):
                self.assertEqual(L.load_env(str(f))["TYPESAFE_API_KEY"], "from-env")


def page(url, source=True, target=True, silo="/g/"):
    return {"url": url, "eligible_source": source, "eligible_target": target, "silo": silo, "near_duplicate": None,
            "similar": {}, "gsc": {"impressions": 0, "clicks": 0, "ctr": None, "position": None}, "depth": 2}


class Rules(unittest.TestCase):
    def setUp(self):
        self.pages = {u: page(u) for u in ("s1", "s2", "t1", "t2", "t3", "t4")}
        self.pages["bad"] = page("bad", target=False)
        self.gp = {"s1": {"all_out": ["t3"]}, "s2": {"all_out": []}}

    def cand(self, s, t, anchor, score=0.9, sentence="x.01", text=None):
        return {"source": s, "target": t, "anchor": anchor, "score": score, "sentence": sentence,
                "sentence_text": text if text is not None else f"We cover {anchor} in depth today."}

    def test_rules(self):
        cands = [
            self.cand("s1", "t1", "widget cleaning tips", 0.9, "a"),
            self.cand("s1", "t3", "hinge oiling guide", 0.8, "b"),            # already linked (nav, list, anywhere)
            self.cand("s1", "bad", "noindex page thing", 0.8, "c"),           # ineligible target
            self.cand("s1", "t2", "click here", 0.8, "d"),                    # generic
            self.cand("s2", "t2", "widget cleaning tips", 0.7, "a"),          # anchor already means t1
            self.cand("s2", "t2", "aluminium widgets", 0.6, "b", text="nothing matches"),  # not verbatim
            self.cand("s2", "t2", "old steel widgets", 0.5, "c"),
            self.cand("s2", "t1", "rust prevention", 0.4, "c"),               # same sentence as a kept link
            self.cand("s2", "t1", "brand", 0.3, "e"),                         # one word
            self.cand("s2", "t3", "existing anchor text", 0.3, "f"),          # existing site anchor -> t1
        ]
        kept, dropped = L.apply_rules(cands, self.pages, self.gp, {"existing anchor text": "t1"}, CFG)
        self.assertEqual([(c["source"], c["target"], c["anchor"]) for c in kept],
                         [("s1", "t1", "widget cleaning tips"), ("s2", "t2", "old steel widgets")])
        reasons = {c["anchor"]: c["drop_reason"] for c in dropped}
        self.assertIn("already links", reasons["hinge oiling guide"])
        self.assertIn("not eligible", reasons["noindex page thing"])
        self.assertEqual(reasons["click here"], "generic anchor")
        self.assertIn("already points at t1", reasons["widget cleaning tips"])
        self.assertIn("not verbatim", reasons["aluminium widgets"])
        self.assertIn("sentence already", reasons["rust prevention"])
        self.assertIn("2-6 words", reasons["brand"])
        self.assertIn("already points at t1", reasons["existing anchor text"])

    def test_budgets(self):
        cfg = L.deep_merge(CFG, {"budgets": {"per_source_new_links": 2, "per_target_new_links": 1}})
        cands = [self.cand("s1", "t1", "first good anchor", 0.9, "a"),
                 self.cand("s1", "t2", "second good anchor", 0.8, "b"),
                 self.cand("s1", "t4", "third good anchor", 0.7, "c"),
                 self.cand("s2", "t1", "fourth good anchor", 0.6, "a")]
        kept, dropped = L.apply_rules(cands, self.pages, self.gp, {}, cfg)
        self.assertEqual(len(kept), 2)
        reasons = sorted(c["drop_reason"] for c in dropped)
        self.assertEqual(reasons, ["source over its new-link budget", "target over its new-link cap"])

    def test_one_recommendation_per_pair_and_dupes_free_no_budget(self):
        cfg = L.deep_merge(CFG, {"budgets": {"per_source_new_links": 2}})
        cands = [self.cand("s1", "t1", "second best anchor", 0.8, "b"),
                 self.cand("s1", "t1", "best anchor here", 0.9, "a"),
                 self.cand("s1", "t1", "third anchor option", 0.7, "c"),
                 self.cand("s1", "t2", "other target anchor", 0.6, "d")]
        kept, dropped = L.apply_rules(cands, self.pages, self.gp, {}, cfg)
        self.assertEqual([(c["target"], c["anchor"]) for c in kept],
                         [("t1", "best anchor here"), ("t2", "other target anchor")])
        self.assertEqual(len({(c["source"], c["target"]) for c in kept}), len(kept))
        self.assertTrue(all("duplicate pair" in c["drop_reason"] for c in dropped))
        self.assertEqual(len(dropped), 2)

    def test_near_duplicates_never_linked(self):
        self.pages["t1"]["similar"] = {"url": "s1", "score": 0.97}
        kept, dropped = L.apply_rules([self.cand("s1", "t1", "widget cleaning tips")], self.pages, self.gp, {}, CFG)
        self.assertFalse(kept)
        self.assertIn("near-duplicate", dropped[0]["drop_reason"])

    def test_bands(self):
        self.assertEqual(L.band_for(0.9, 0.9, CFG), "auto")
        self.assertEqual(L.band_for(0.9, 0.1, CFG), "review")  # low anchor confidence never auto
        self.assertEqual(L.band_for(0.3, 0.9, CFG), "review")
        self.assertEqual(L.band_for(0.1, 0.9, CFG), "drop")

    def test_target_need_rewards_orphans_and_near_top_pages(self):
        p = page("t")
        base = L.target_need(p, 5, CFG)
        p["gsc"].update({"position": 8, "impressions": 200, "ctr": 0.01})
        self.assertGreater(L.target_need(p, 0, CFG), base)
        self.assertLessEqual(L.target_need(p, 0, CFG), CFG["scoring"]["target_need"]["max"])


class Client(unittest.TestCase):
    def test_retry_cache_and_usage(self):
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = json.dumps(
            {"model": "jev-1.13.0", "answers": {}, "usage": {"input_tokens": 100, "output_tokens": 3}}).encode()
        err = urllib.error.HTTPError("u", 429, "slow down", {"retry-after": "0"}, io.BytesIO(b""))
        with tempfile.TemporaryDirectory() as d:
            c = L.JevClient(CFG, {"TYPESAFE_API_KEY": "k"}, Path(d) / "cache.jsonl")
            with mock.patch("urllib.request.urlopen", side_effect=[err, ok]) as u, mock.patch("time.sleep"):
                r = c.call({"state": "s", "model": "m", "questions": {}})
                self.assertEqual(r["model"], "jev-1.13.0")
                self.assertEqual(u.call_count, 2)
                req = u.call_args[0][0]
                self.assertEqual(req.get_header("Authorization"), "Bearer k")
                self.assertEqual(req.full_url, CFG["jev"]["endpoint"])
            self.assertEqual(c.usage["input_tokens"], 100)
            c2 = L.JevClient(CFG, {"TYPESAFE_API_KEY": "k"}, Path(d) / "cache.jsonl")
            with mock.patch("urllib.request.urlopen") as u:
                c2.call({"state": "s", "model": "m", "questions": {}})
                u.assert_not_called()  # served from the on-disk cache

    def test_client_error_is_raised_not_retried(self):
        err = urllib.error.HTTPError("u", 422, "bad", {}, io.BytesIO(b'{"detail":"x"}'))
        with tempfile.TemporaryDirectory() as d:
            c = L.JevClient(CFG, {"TYPESAFE_API_KEY": "k"}, Path(d) / "cache.jsonl")
            with mock.patch("urllib.request.urlopen", side_effect=[err]) as u:
                with self.assertRaises(RuntimeError):
                    c.call({"state": "s", "model": "m", "questions": {}})
                self.assertEqual(u.call_count, 1)

    def test_workers_capped(self):
        with tempfile.TemporaryDirectory() as d:
            c = L.JevClient(CFG, {"TYPESAFE_API_KEY": "k"}, Path(d) / "cache.jsonl")
            with mock.patch("concurrent.futures.ThreadPoolExecutor", wraps=L.concurrent.futures.ThreadPoolExecutor) as ex, \
                    mock.patch.object(c, "call", return_value={}):
                c.run_all([{}], 50)
                self.assertEqual(ex.call_args.kwargs["max_workers"], CFG["jev"]["max_workers"])


if __name__ == "__main__":
    unittest.main()
