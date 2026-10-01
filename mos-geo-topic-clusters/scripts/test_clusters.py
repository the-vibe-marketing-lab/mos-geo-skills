#!/usr/bin/env python3
"""Offline tests for clusters.py. No network: every API is a fake.

    python3 -m unittest scripts/test_clusters.py                       (from the skill folder)
    uv run --with openpyxl python3 -m unittest scripts/test_clusters.py (also checks the xlsx)

Fixtures are built in-file in the exact shapes of the two supported exports (Ahrefs Organic
Keywords: UTF-16 LE, tab; GSC page+query: UTF-8, comma), with made-up keywords only.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import random
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clusters as C  # noqa: E402

AHREFS_HEADER = ["Keyword", "Country", "Location", "Language", "Entities", "Branded", "Local", "Navigational",
                 "Informational", "Commercial", "Transactional", "SERP features", "Volume", "KD", "CPC",
                 "Previous organic traffic", "Current organic traffic", "Organic traffic change",
                 "Current paid traffic", "Previous position", "Current position", "Position change",
                 "Previous position kind", "Previous URL", "Current position kind", "Current URL", "Previous date",
                 "Current date"]
SITE = "https://widgetco.example"


def ahrefs_row(kw, vol, pos, url, country="AU", branded=False, local=False, inf=True, com=False, prev_url="",
               traffic=10):
    r = dict.fromkeys(AHREFS_HEADER, "")
    r.update({"Keyword": kw, "Country": country, "Branded": str(branded).lower(), "Local": str(local).lower(),
              "Navigational": "false", "Informational": str(inf).lower(), "Commercial": str(com).lower(),
              "Transactional": "false", "Volume": str(vol), "Current position": str(pos) if pos else "",
              "Current URL": url, "Previous URL": prev_url, "Current organic traffic": str(traffic)})
    return [r[h] for h in AHREFS_HEADER]


def write_ahrefs(path: Path, rows: list[list[str]]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_ALL)
    w.writerow(AHREFS_HEADER)
    w.writerows(rows)
    path.write_bytes(b"\xff\xfe" + buf.getvalue().encode("utf-16-le"))


def write_gsc(path: Path, rows: list[tuple]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["page", "query", "Clicks", "Impressions", "CTR", "Avg Position"])
    for page, q, clicks, imp, pos in rows:
        w.writerow([page, q, clicks, imp, round(100 * clicks / imp, 2) if imp else 0, pos])
    path.write_text(buf.getvalue(), encoding="utf-8")


AHREFS_ROWS = [
    ahrefs_row("widget repair guide", 900, 3, f"{SITE}/blog/widget-repair"),
    ahrefs_row("widget repair guide", 400, 7, f"{SITE}/blog/widget-repair", country="US"),
    ahrefs_row("how to repair a widget", 300, 4, f"{SITE}/blog/widget-repair"),
    ahrefs_row("widget repairs guide", 200, 5, f"{SITE}/blog/widget-repair"),
    ahrefs_row("widget recipes", 800, 6, f"{SITE}/blog/widget-recipes"),
    ahrefs_row("easy widget recipes", 250, 9, f"{SITE}/blog/widget-recipes"),
    ahrefs_row("widget delivery sydney", 700, 2, f"{SITE}/", local=True, inf=False, com=True),
    ahrefs_row("widget delivery", 600, 4, f"{SITE}/", local=True, inf=False, com=True),
    ahrefs_row("widgetco", 5000, 1, f"{SITE}/", branded=True),
    ahrefs_row("gizmo brand review", 150, 12, f"{SITE}/blog/gizmo", branded=True, inf=False, com=True),
    ahrefs_row("", 100, 1, f"{SITE}/"),
    ahrefs_row("lost widget topic", 120, None, "", prev_url=f"{SITE}/old"),
    ahrefs_row("widget recipes", 5000, 1, f"{SITE}/de/widget-rezepte", country="DE"),
    ahrefs_row("allintitle: widget repair", 10, 1, f"{SITE}/blog/widget-repair"),
]
GSC_ROWS = [
    (f"{SITE}/fighters/champ/", "champ workout", 20, 400, 6.0),
    (f"{SITE}/fighters/champ/", "champ training routine", 15, 300, 7.0),
    (f"{SITE}/fighters/champ/", "champ workout routine", 10, 200, 8.0),
    (f"{SITE}/fighters/champ/", "champ diet", 5, 150, 9.0),
    (f"{SITE}/training/fists/", "how to make fists stronger", 30, 500, 4.0),
    (f"{SITE}/training/knuckles/", "how to make fists stronger", 12, 300, 5.0),
    (f"{SITE}/gear/gloves/", "best boxing gloves", 3, 900, 25.0),
]


def cfg():
    return C.load_config()


def ingest(path: Path, out: Path, brand="widgetco"):
    with contextlib.redirect_stdout(io.StringIO()):
        C.main(["ingest", "--input", str(path), "--out", str(out), "--brand-terms", brand])
    return json.loads((out / "data" / "keywords.json").read_text(encoding="utf-8"))


def fake_jev_post(url, headers, payload, **kw):
    """Same-page when the content tokens overlap a lot, related when they share one, else different."""
    stop = set(cfg()["stopwords"])
    a = set(C.content_tokens(C.norm(payload["state"]["query"]), stop)) if "query" in payload["state"] else set()
    answers = {}
    for qid, q in payload["questions"].items():
        if qid == "topic_label":
            first = next(iter(q["criteria"]))
            probs = {o: (0.9 if o == first else 0.1 / (len(q["criteria"]) - 1)) for o in q["criteria"]}
            answers[qid] = {"type": "choice", "choice": first, "confidence": 0.8, "probabilities": probs}
            continue
        b = set(C.content_tokens(C.norm(q["instructions"]["candidate_query"]), stop))
        j = len(a & b) / len(a | b) if a | b else 0
        p = {"same-page": 0.9, "related": 0.08, "different": 0.02} if j >= 0.5 else (
            {"same-page": 0.1, "related": 0.8, "different": 0.1} if j > 0 else
            {"same-page": 0.01, "related": 0.09, "different": 0.9})
        answers[qid] = {"type": "choice", "choice": max(p, key=p.get), "confidence": 0.7, "probabilities": p}
    return {"model": "jev-test", "answers": answers, "usage": {"input_tokens": 1000, "output_tokens": 50}}


class Detection(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_ahrefs_utf16_tab(self):
        p = self.tmp / "a.csv"
        write_ahrefs(p, AHREFS_ROWS)
        header, rows, enc, delim = C.read_table(p)
        self.assertEqual((enc, delim), ("utf-16-le", "tab"))
        self.assertEqual(C.detect(header)[0], "ahrefs")

    def test_gsc_utf8_comma(self):
        p = self.tmp / "g.csv"
        write_gsc(p, GSC_ROWS)
        header, rows, enc, delim = C.read_table(p)
        self.assertEqual((C.detect(header)[0], delim), ("gsc", "comma"))

    def test_unrecognised_fails_loudly(self):
        p = self.tmp / "x.csv"
        p.write_text("Term,Searches\nfoo,10\n", encoding="utf-8")
        header, *_ = C.read_table(p)
        with self.assertRaises(C.InputError) as cm:
            C.detect(header)
        self.assertIn("Unrecognised export", str(cm.exception))


class Ingest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.a = self.tmp / "a.csv"
        write_ahrefs(self.a, AHREFS_ROWS)

    def test_one_country_feeds_demand_position_and_url(self):
        inv = ingest(self.a, self.tmp / "run")
        self.assertEqual(inv["stats"]["country"], "AU")  # the file's most common Country
        self.assertEqual(inv["stats"]["other_country_rows_dropped"], 2)
        k = next(k for k in inv["keywords"] if k["keyword"] == "widget repair guide")
        self.assertEqual((k["position"], k["demand"], k["row_ids"], k["countries"]), (3.0, 900, ["r2"], ["AU"]))
        r = next(k for k in inv["keywords"] if k["keyword"] == "widget recipes")
        self.assertEqual((r["position"], r["demand"], r["current_url"]), (6.0, 800, f"{SITE}/blog/widget-recipes"))

    def test_country_all_sums_across_countries(self):
        out = self.tmp / "all"
        with contextlib.redirect_stdout(io.StringIO()):
            C.main(["ingest", "--input", str(self.a), "--out", str(out), "--country", "all"])
        kws = json.loads((out / "data" / "keywords.json").read_text(encoding="utf-8"))["keywords"]
        k = next(k for k in kws if k["keyword"] == "widget repair guide")
        self.assertEqual((k["demand"], k["row_ids"]), (1300, ["r2", "r3"]))

    def test_search_operator_queries_dropped(self):
        inv = ingest(self.a, self.tmp / "run")
        self.assertEqual(inv["stats"]["operator_queries_dropped"], 1)
        self.assertFalse(any(k["keyword"].startswith("allintitle") for k in inv["keywords"]))

    def test_row_ids_stable_blank_rows_do_not_shift(self):
        inv1 = ingest(self.a, self.tmp / "r1")
        inv2 = ingest(self.a, self.tmp / "r2")
        ids1 = {k["keyword"]: (k["id"], k["row_ids"]) for k in inv1["keywords"]}
        self.assertEqual(ids1, {k["keyword"]: (k["id"], k["row_ids"]) for k in inv2["keywords"]})
        # the blank-keyword row sits at file line 12; the next keyword keeps its own line number
        self.assertEqual(ids1["lost widget topic"][1], ["r13"])
        self.assertEqual(inv1["stats"]["blank_keyword_rows"], 1)

    def test_lost_ranking(self):
        inv = ingest(self.a, self.tmp / "run")
        k = next(k for k in inv["keywords"] if k["keyword"] == "lost widget topic")
        self.assertEqual((k["current_url"], k["previous_url"]), ("", f"{SITE}/old"))

    def test_gsc_aggregates_query_across_pages(self):
        g = self.tmp / "g.csv"
        write_gsc(g, GSC_ROWS)
        inv = ingest(g, self.tmp / "run", brand="")
        k = next(k for k in inv["keywords"] if k["keyword"] == "how to make fists stronger")
        # one search can show two of the site's pages: demand is the max page, position the best page
        self.assertEqual((k["demand"], k["clicks"], k["position"]), (500, 42, 4.0))
        self.assertEqual(k["current_url"], f"{SITE}/training/fists/")
        self.assertEqual([p["share"] for p in k["pages"]], [0.625, 0.375])
        self.assertEqual(inv["stats"]["multi_page_queries"], 1)

    def test_gsc_jump_links_merge_into_their_page(self):
        g = self.tmp / "frag.csv"
        write_gsc(g, [(f"{SITE}/champ/", "champ routine", 5, 100, 6.0),
                      (f"{SITE}/champ/#Key_Takeaways", "champ routine", 2, 90, 5.0),
                      (f"{SITE}/other/", "champ routine", 1, 20, 30.0)])
        inv = ingest(g, self.tmp / "run", brand="")
        k = inv["keywords"][0]
        self.assertEqual([p["url"] for p in k["pages"]], [f"{SITE}/champ/", f"{SITE}/other/"])
        self.assertEqual((k["pages"][0]["clicks"], k["pages"][0]["impressions"]), (7, 100))  # clicks add, impressions don't
        self.assertEqual((inv["stats"]["multi_url_queries_raw"], inv["stats"]["fragment_rows_merged"]), (1, 1))

    def test_gsc_spelling_variants_on_one_page_add_up(self):
        g = self.tmp / "var.csv"
        write_gsc(g, [(f"{SITE}/champ/", "champ's routine", 5, 100, 6.0),
                      (f"{SITE}/champ", "champs routine", 1, 50, 9.0),
                      (f"{SITE}/champ/#tldr", "champs routine", 1, 40, 8.0)])
        inv = ingest(g, self.tmp / "run", brand="")
        k = inv["keywords"][0]
        # /champ and /champ/ are one URL: 100 + 50 summed as spelling variants; the #tldr jump link is not added
        self.assertEqual([p["url"] for p in k["pages"]], [f"{SITE}/champ/"])
        self.assertEqual((k["demand"], k["clicks"]), (150, 7))
        self.assertAlmostEqual(k["position"], (6 * 100 + 9 * 50) / 150, places=2)

    def test_blank_position_is_never_owned(self):
        g = self.tmp / "nopos.csv"
        g.write_text("page,query,Clicks,Impressions,Position\n" + f"{SITE}/a/,alpha beta,1,100,\n", encoding="utf-8")
        inv = ingest(g, self.tmp / "run", brand="")
        self.assertIsNone(inv["keywords"][0]["position"])
        s = C.score_cluster(inv["keywords"], "gsc", cfg())
        self.assertNotEqual(s["status"], "Owned")
        self.assertIsNone(s["weighted_position"])

    def test_gsc_without_position_column_fails(self):
        with self.assertRaises(C.InputError):
            C.detect(["page", "query", "Clicks", "Impressions"])

    def test_normalise(self):
        self.assertEqual(C.norm("Mike Tyson’s  Work-out!"), "mike tysons work out")
        stop = set(cfg()["stopwords"])
        self.assertEqual(C.content_tokens(C.norm("widget repairs guide"), stop),
                         C.content_tokens(C.norm("guide widget repair"), stop))


class Walls(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        p = self.tmp / "a.csv"
        write_ahrefs(p, AHREFS_ROWS)
        self.kw = {k["keyword"]: k for k in ingest(p, self.tmp / "run")["keywords"]}

    def test_own_brand_is_never_clustered(self):
        self.assertEqual(self.kw["widgetco"]["group"], "own-brand")
        self.assertFalse(C.compatible(self.kw["widgetco"], self.kw["widget repair guide"]))

    def test_third_party_brand_walled(self):
        self.assertEqual(self.kw["gizmo brand review"]["group"], "branded")
        self.assertFalse(C.compatible(self.kw["gizmo brand review"], self.kw["widget delivery"]))

    def test_local_wall(self):
        self.assertTrue(self.kw["widget delivery sydney"]["local"])
        self.assertFalse(C.compatible(self.kw["widget delivery sydney"], self.kw["widget recipes"]))

    def test_local_wall_is_the_place(self):
        c = cfg()
        self.assertEqual(C.local_key("widget delivery sydney", False, c), "sydney")
        self.assertEqual(C.local_key("widget delivery gold coast", False, c), "gold coast")
        self.assertEqual(C.local_key("widget repair near me", False, c), "near me")
        self.assertEqual(C.local_key("widget delivery", True, c), "local (no place)")
        self.assertEqual(C.local_key("widget delivery", False, c), "")
        syd = {"group": "generic", "local": "sydney", "intent": "commercial"}
        self.assertFalse(C.compatible(syd, {**syd, "local": "melbourne"}))
        self.assertFalse(C.compatible(syd, {**syd, "local": "near me"}))
        self.assertTrue(C.compatible(syd, dict(syd)))

    def test_intent_wall_and_mixed(self):
        inf = {"group": "generic", "local": False, "intent": "informational"}
        com = {**inf, "intent": "commercial"}
        mixed = {**inf, "intent": "mixed"}
        self.assertFalse(C.compatible(inf, com))
        self.assertTrue(C.compatible(inf, mixed) and C.compatible(com, mixed))
        # a cluster holding inf + mixed can never absorb a commercial keyword
        self.assertFalse(C.group_compatible([inf, mixed], [com]))

    def test_host_brand_match(self):
        self.assertTrue(self.kw["widgetco"]["own_brand"])

    def test_lexical_intent_for_gsc(self):
        c = cfg()
        self.assertEqual(C.lexical_intent("best boxing gloves", c), "commercial")
        self.assertEqual(C.lexical_intent("how to make fists stronger", c), "informational")
        self.assertIsNone(C.lexical_intent("champ workout", c))


class Linkage(unittest.TestCase):
    def test_refuses_a_chain(self):
        # A~B, B~C, but A and C judged different: the cannot-link keeps C out even at a 0.5 average
        links = {("a", "b"): (0.95, 1, 0), ("b", "c"): (0.95, 1, 0), ("a", "c"): (0.05, 1, 1)}
        self.assertEqual(C.average_linkage(["a", "b", "c"], links, threshold=0.5, min_coverage=0.5),
                         [["a", "b"], ["c"]])

    def test_low_average_refuses_without_veto(self):
        links = {("a", "b"): (0.95, 1), ("b", "c"): (0.9, 1), ("a", "c"): (0.02, 1)}
        self.assertEqual(C.average_linkage(["a", "b", "c"], links, threshold=0.5, min_coverage=0.5),
                         [["a", "b"], ["c"]])

    def test_merges_a_consistent_triangle(self):
        links = {("a", "b"): (0.9, 1), ("b", "c"): (0.8, 1), ("a", "c"): (0.7, 1)}
        self.assertEqual(C.average_linkage(["a", "b", "c"], links, threshold=0.5, min_coverage=0.5), [["a", "b", "c"]])

    def test_coverage_blocks_one_edge_joining_formed_groups(self):
        tight = {("a1", "a2"): (0.99, 1), ("a2", "a3"): (0.99, 1), ("a1", "a3"): (0.99, 1),
                 ("b1", "b2"): (0.99, 1), ("b2", "b3"): (0.99, 1), ("b1", "b3"): (0.99, 1)}
        out = C.average_linkage(["a1", "a2", "a3", "b1", "b2", "b3"], {**tight, ("a3", "b1"): (0.95, 1)},
                                threshold=0.5, min_coverage=0.5)
        self.assertEqual(out, [["a1", "a2", "a3"], ["b1", "b2", "b3"]])

    def test_bridge_first_needs_verify_evidence(self):
        # The strongest edge is the bridge, so it merges two singletons before either group forms:
        # coverage alone cannot stop that. The verify pass (head vs every member) supplies the
        # 'different' judgements that split it.
        tri = {("a1", "a2"): (0.9, 1), ("a2", "a3"): (0.9, 1), ("a1", "a3"): (0.9, 1),
               ("b1", "b2"): (0.9, 1), ("b2", "b3"): (0.9, 1), ("b1", "b3"): (0.9, 1), ("a3", "b1"): (0.99, 1)}
        nodes = ["a1", "a2", "a3", "b1", "b2", "b3"]
        self.assertEqual(len(C.average_linkage(nodes, tri, threshold=0.5, min_coverage=0.5)), 1)
        verified = {**tri, ("a1", "b2"): (0.03, 1, 1), ("a1", "b3"): (0.03, 1, 1), ("a1", "b1"): (0.03, 1, 1)}
        out = C.average_linkage(nodes, verified, threshold=0.5, min_coverage=0.5)
        a1_group = next(g for g in out if "a1" in g)
        self.assertFalse({"b1", "b2", "b3"} & set(a1_group))

    def test_deterministic_under_shuffled_input(self):
        rng = random.Random(7)
        nodes = [f"k{i:02d}" for i in range(30)]
        links = {}
        for i in range(30):
            for j in range(i + 1, 30):
                if rng.random() < 0.3:
                    links[(nodes[i], nodes[j])] = (round(rng.random(), 3), 1)
        ref = C.average_linkage(nodes, links, threshold=0.5, min_coverage=0.5)
        for seed in range(5):
            items = list(links.items())
            random.Random(seed).shuffle(items)
            shuffled_nodes = nodes[:]
            random.Random(seed).shuffle(shuffled_nodes)
            self.assertEqual(C.average_linkage(shuffled_nodes, dict(items), threshold=0.5, min_coverage=0.5), ref)

    def test_can_merge_veto(self):
        links = {("a", "b"): (0.9, 1)}
        out = C.average_linkage(["a", "b"], links, threshold=0.5, min_coverage=0.5, can_merge=lambda x, y: False)
        self.assertEqual(out, [["a"], ["b"]])


class Eviction(unittest.TestCase):
    def test_member_head_disagrees_with_is_evicted_or_rehomed(self):
        mk = lambda i, d: {"id": i, "keyword": i, "demand": d, "clicks": 0, "group": "generic", "local": "",  # noqa: E731
                           "intent": "mixed"}
        byid = {i: mk(i, d) for i, d in (("h1", 100), ("m1", 50), ("m2", 40), ("h2", 90), ("x", 5))}
        e = lambda a, b, p, d=0.0: ("|".join(sorted((a, b))), {"a": min(a, b), "b": max(a, b), "p_same": p,  # noqa: E731
                                                                  "p_different": d})
        edges = dict([e("h1", "m1", 0.9), e("h1", "m2", 0.3), e("h2", "m2", 0.8), e("h1", "x", 0.1, 0.8)])
        th = cfg()["thresholds"]
        groups, log = C.evict_members([["h1", "m1", "m2", "x"], ["h2"]], byid, edges, th)
        self.assertEqual(groups, [["h1", "m1"], ["h2", "m2"]])
        self.assertEqual({(r["keyword"], r["rehomed_to"]) for r in log}, {("m2", "h2"), ("x", "")})

    def test_evicted_member_lands_in_unclustered_with_reason(self):
        kws = [{"id": i, "keyword": i, "demand": d, "clicks": 0, "group": "generic", "local": "", "intent": "mixed",
                "tokens": [i]} for i, d in (("h", 500), ("a", 400), ("b", 300))]
        e = lambda a, b, p: ("|".join(sorted((a, b))), {"a": min(a, b), "b": max(a, b), "p_same": p, "p_related": 0,  # noqa: E731
                                                        "p_different": 0.0, "method": "jev"})
        # a~b strong and h~a strong pull b in by average linkage, but the head judged h~b at 0.2
        edges = dict([e("h", "a", 0.95), e("a", "b", 0.95), e("h", "b", 0.2)])
        res = C.form_clusters(kws, edges, cfg(), None, "ahrefs")
        self.assertEqual([c["keywords"] for c in res["clusters"]], [["h", "a"]])
        self.assertEqual(res["unclustered"], ["b"])
        self.assertEqual(res["evicted"][0]["from"], "h")


class Scoring(unittest.TestCase):
    def kw(self, demand, pos, url, clicks=0.0, prev="", pages=None):
        return {"demand": demand, "clicks": clicks, "position": pos, "current_url": url, "previous_url": prev,
                "pages": pages or [], "intent": "informational"}

    def test_weighted_position_share_and_status(self):
        c = cfg()
        ms = [self.kw(900, 2, "u1"), self.kw(100, 12, "u1")]
        s = C.score_cluster(ms, "ahrefs", c)
        self.assertEqual(s["weighted_position"], 3.0)
        self.assertEqual((s["top_url_share"], s["n_ranking_urls"], s["status"]), (1.0, 1, "Owned"))
        self.assertEqual(s["opportunity_score"], 0.0)

    def test_striking_underperforming_lost_gap(self):
        c = cfg()
        self.assertEqual(C.score_cluster([self.kw(100, 8, "u")], "ahrefs", c)["status"], "Striking")
        self.assertEqual(C.score_cluster([self.kw(100, 35, "u")], "ahrefs", c)["status"], "Underperforming")
        self.assertEqual(C.score_cluster([self.kw(100, None, "", prev="old")], "ahrefs", c)["status"], "Lost")
        self.assertEqual(C.score_cluster([self.kw(100, None, "")], "ahrefs", c)["status"], "Gap-in-list")

    def test_opportunity_ahrefs(self):
        c = cfg()
        s = C.score_cluster([self.kw(1000, 8, "u")], "ahrefs", c)
        # ctr(3) - ctr(8) from the config curve, times demand
        self.assertAlmostEqual(s["opportunity_score"], round(1000 * (0.10 - 0.025), 1))

    def test_cannibalised_needs_share_and_close_positions(self):
        c = cfg()
        pages = lambda p2: [{"url": "u1", "clicks": 10, "impressions": 600, "position": 5.0},  # noqa: E731
                            {"url": "u2", "clicks": 5, "impressions": 400, "position": p2}]
        close = C.score_cluster([self.kw(1000, 5, "u1", 15, pages=pages(7.0))], "gsc", c)
        far = C.score_cluster([self.kw(1000, 5, "u1", 15, pages=pages(40.0))], "gsc", c)
        self.assertEqual(close["status"], "Cannibalised")
        self.assertNotEqual(far["status"], "Cannibalised")
        self.assertEqual(close["current_url"], "u1")
        # GSC opportunity uses the real CTR: 1000 x (0.10 - 15/1000)
        self.assertAlmostEqual(close["opportunity_score"], 85.0)

    def test_ctr_curve(self):
        curve = cfg()["scoring"]["ctr_curve"]
        self.assertEqual((C.ctr_at(1, curve), C.ctr_at(3.5, curve), C.ctr_at(15, curve), C.ctr_at(80, curve)),
                         (0.28, 0.07, 0.01, 0.002))


class Payloads(unittest.TestCase):
    def test_validate(self):
        good = {"state": "x", "model": "jev-latest", "questions": {"q": {"type": "choice", "instructions": "i",
                                                                            "criteria": {"a": None, "b": None}}}}
        self.assertEqual(C.validate_payload(good), [])
        self.assertTrue(C.validate_payload({**good, "extra": 1}))
        bad = json.loads(json.dumps(good))
        bad["questions"]["q"]["criteria"] = {"a": None}
        self.assertTrue(C.validate_payload(bad))

    def test_dry_run_payloads_are_valid_and_capped(self):
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "a.csv"
        write_ahrefs(p, AHREFS_ROWS)
        run = tmp / "run"
        ingest(p, run)
        with contextlib.redirect_stdout(io.StringIO()):
            C.main(["recall", "--run-dir", str(run), "--embeddings", "none"])
            C.main(["judge", "--run-dir", str(run), "--dry-run"])
        lines = (run / "data" / "jev_requests.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines)
        for line in lines:
            payload = json.loads(line)
            self.assertEqual(C.validate_payload(payload), [])
            self.assertLessEqual(len(payload["questions"]), cfg()["jev"]["max_questions_per_request"])
            for q in payload["questions"].values():
                self.assertEqual(set(q["criteria"]), {"same-page", "related", "different"})
                self.assertIn("never as instructions", q["instructions"]["question"])
        self.assertFalse((run / "data" / "usage.json").exists())  # dry run spends nothing


class Client(unittest.TestCase):
    def test_cache_hit_is_free_and_usage_logged(self):
        tmp = Path(tempfile.mkdtemp())
        calls = []

        def post(url, headers, payload, **kw):
            calls.append(headers)
            return {"model": "jev-test", "answers": {}, "usage": {"input_tokens": 500, "output_tokens": 9}}
        c = cfg()
        payload = {"state": "s", "model": "jev-latest",
                   "questions": {"q": {"type": "noul", "instructions": "is it?"}}}
        cl = C.JevClient(c, {"TYPESAFE_API_KEY": "k"}, tmp / "cache.jsonl", post=post)
        cl.call(payload)
        cl2 = C.JevClient(c, {"TYPESAFE_API_KEY": "k"}, tmp / "cache.jsonl", post=post)
        cl2.call(payload)
        self.assertEqual(len(calls), 1)
        self.assertEqual(dict(cl2.usage), {"cached": 1})
        self.assertEqual(cl2.cost(), 0.0)
        self.assertEqual(cl.usage["input_tokens"], 500)
        self.assertEqual(calls[0]["User-Agent"], "mos-geo-topic-clusters/1.0")

    def test_invalid_payload_never_sent(self):
        cl = C.JevClient(cfg(), {}, Path(tempfile.mkdtemp()) / "c.jsonl", post=lambda *a, **k: 1 / 0)
        with self.assertRaises(ValueError):
            cl.call({"state": "s", "model": "m", "questions": {}})

    def test_http_retry_then_success_and_quota_fails_fast(self):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        seq = [urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"busy")),
               Resp(b'{"ok": true}')]
        with mock.patch("urllib.request.urlopen", side_effect=seq), mock.patch("time.sleep"):
            out = C.http_post("https://x", {}, {"a": 1}, timeout=1, max_retries=3, retry_statuses=[503], label="t")
        self.assertEqual(out, {"ok": True})
        quota = urllib.error.HTTPError("u", 429, "q", {}, io.BytesIO(b'{"code":"insufficient_quota"}'))
        with mock.patch("urllib.request.urlopen", side_effect=[quota]) as m, mock.patch("time.sleep"):
            with self.assertRaises(RuntimeError) as cm:
                C.http_post("https://x", {}, {}, timeout=1, max_retries=3, retry_statuses=[429], label="t")
        self.assertEqual(m.call_count, 1)
        self.assertIn("quota", str(cm.exception))


class Embeddings(unittest.TestCase):
    def test_provider_order_openai_first_then_voyage_then_none(self):
        c = cfg()
        self.assertEqual(C.choose_provider({"OPENAI_API_KEY": "o", "VOYAGE_API_KEY": "v"}, c, None), "openai")
        self.assertEqual(C.choose_provider({"VOYAGE_API_KEY": "v"}, c, None), "voyage")
        self.assertEqual(C.choose_provider({}, c, None), "none")
        self.assertEqual(C.choose_provider({"OPENAI_API_KEY": "o", "VOYAGE_API_KEY": "v"}, c, "voyage"), "voyage")

    def fake(self, seen):
        def post(url, headers, body, **kw):
            seen.append((url, body))
            vecs = [[float(len(t)), 1.0, 0.0] for t in body["input"]]
            return {"data": [{"index": i, "embedding": v} for i, v in enumerate(vecs)],
                    "usage": {"total_tokens": 3 * len(vecs)}}
        return post

    def test_voyage_and_openai_request_shapes_and_cache(self):
        c = cfg()
        for provider, key in (("voyage", "input_type"), ("openai", "dimensions")):
            seen = []
            cache = C.JsonlCache(Path(tempfile.mkdtemp()) / "e.jsonl")
            vecs, usage = C.embed_all(["aa", "bbb"], provider, c, {c["embeddings"][provider]["key"]: "k"}, cache,
                                      post=self.fake(seen))
            self.assertIn(key, seen[0][1])
            self.assertEqual(seen[0][0], c["embeddings"][provider]["endpoint"])
            self.assertAlmostEqual(sum(x * x for x in vecs["aa"]), 1.0, places=4)
            self.assertEqual(usage["tokens"], 6)
            _, usage2 = C.embed_all(["aa", "bbb"], provider, c, {}, cache, post=self.fake(seen))
            self.assertEqual((usage2["cached"], usage2.get("calls", 0)), (2, 0))

    def test_embedding_neighbours_become_candidates(self):
        c = cfg()
        kws = [{"id": f"k{i}", "keyword": w, "tokens": C.content_tokens(w, set()), "group": "generic",
                "local": False, "intent": "mixed", "current_url": "", "demand": 1} for i, w in
               enumerate(["car insurance", "auto cover", "banana bread"])]
        vecs = {"car insurance": [1.0, 0.0], "auto cover": [0.96, 0.28], "banana bread": [0.0, 1.0]}
        pairs = C.build_candidates(kws, vecs, c)["pairs"]
        self.assertIn("k0|k1", pairs)
        self.assertEqual(pairs["k0|k1"]["sources"], ["embed"])
        self.assertNotIn("k0|k2", pairs)
        self.assertEqual(C.build_candidates(kws, None, c)["pairs"], {})  # no shared words, no embeddings


class Serp(unittest.TestCase):
    def test_overlap_excludes_platforms_and_decides(self):
        c = cfg()
        a = ["https://a.com/1", "https://www.b.com/2/", "https://reddit.com/r/x", "https://c.com/3?x=1", "https://d.com/4"]
        b = ["https://a.com/1/", "https://b.com/2", "https://reddit.com/r/x", "https://c.com/3", "https://d.com/4"]
        n = C.serp_overlap(a, b, c["serp"]["platform_domains"])
        self.assertEqual(n, 4)
        self.assertEqual([C.serp_decision(x, c) for x in (5, 3, 1)], ["merge", "keep", "split"])

    def test_fetch_parses_organic_and_caches(self):
        c = cfg()
        seen = []

        def post(url, headers, body, **kw):
            seen.append(headers)
            return {"status_code": 20000, "tasks": [{"status_code": 20000, "cost": 0.002, "result": [{"items": [
                {"type": "featured_snippet", "url": "https://x.com"},
                {"type": "organic", "rank_group": 2, "url": "https://b.com"},
                {"type": "organic", "rank_group": 1, "url": "https://a.com"}]}]}]}
        cache = C.JsonlCache(Path(tempfile.mkdtemp()) / "s.jsonl")
        env = {"DATAFORSEO_LOGIN": "l", "DATAFORSEO_PASSWORD": "p"}
        urls, cost, cached = C.fetch_serp("kw", c, env, cache, post=post)
        self.assertEqual((urls, cost, cached), (["https://a.com", "https://b.com"], 0.002, False))
        self.assertTrue(seen[0]["Authorization"].startswith("Basic "))
        self.assertEqual(C.fetch_serp("kw", c, env, cache, post=post)[1:], (0.0, True))

    def test_suspect_serp_never_decides(self):
        byid = {"a": {"tokens": ["keto", "plan"]}, "b": {"tokens": ["keto", "diet"]}, "c": {"tokens": ["keto"]}}
        serps = {"a": ["https://spam.lat/x"], "b": ["https://h.org/1", "https://d.com/2"],
                 "c": ["https://h.org/1", "https://q.com/3"]}
        self.assertEqual(C.suspect_serps(serps, byid, []), {"a"})


class Pipeline(unittest.TestCase):
    """ingest -> recall -> judge (fake Jev) -> cluster -> verify -> labels -> build, twice."""

    def run_all(self, inp: Path, run: Path, cache: Path | None = None, brand="widgetco"):
        extra = ["--cache-dir", str(cache)] if cache else []
        env = Path(tempfile.mkdtemp()) / ".env"
        env.write_text("TYPESAFE_API_KEY=secret-test-key-123\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(C, "http_post", side_effect=fake_jev_post) as m, \
                mock.patch.dict("os.environ", {}, clear=False):
            C.main(["ingest", "--input", str(inp), "--out", str(run), "--brand-terms", brand])
            C.main(["recall", "--run-dir", str(run), "--embeddings", "none"])
            C.main(["judge", "--run-dir", str(run), "--env-file", str(env), *extra])
            C.main(["cluster", "--run-dir", str(run)])
            C.main(["judge", "--run-dir", str(run), "--env-file", str(env), "--pass", "verify", *extra])
            C.main(["cluster", "--run-dir", str(run)])
            C.main(["judge", "--run-dir", str(run), "--env-file", str(env), "--pass", "labels", *extra])
            t = C.assemble(run, cfg())
            rows = C.sheet_rows(t, run, cfg())
            C.write_step_docs(run, t)
            C.write_readme(run, t, cfg())
        self.assertNotIn("secret-test-key-123", out.getvalue())
        return t, rows, m.call_count

    def test_ahrefs_end_to_end_and_rerun_identical_and_free(self):
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "a.csv"
        write_ahrefs(p, AHREFS_ROWS)
        t1, rows1, n1 = self.run_all(p, tmp / "run1")
        t2, rows2, n2 = self.run_all(p, tmp / "run2", cache=tmp / "run1" / "data")
        self.assertGreater(n1, 0)
        self.assertEqual(n2, 0)  # warm cache: zero network calls
        self.assertEqual(C.data_digest(rows1), C.data_digest(rows2))
        where = {r["keyword"]: r["cluster_id"] for r in t1["keywords"]}
        self.assertEqual(where["widget repair guide"], where["widget repairs guide"])
        self.assertNotEqual(where["widget repair guide"], where["widget recipes"])
        self.assertNotEqual(where["widget recipes"], where["widget delivery sydney"])
        self.assertEqual(where["widgetco"], "")
        brand = {r["keyword"]: r["brand_type"] for r in t1["branded"]}
        self.assertEqual(brand, {"widgetco": "own brand", "gizmo brand review": "third-party brand"})
        home = next(p for p in t1["pages"] if p["is_home_page"])
        self.assertEqual(home["n_keywords"], 2)  # own brand excluded
        readme = (tmp / "run1" / "deliverables" / "README.md").read_text(encoding="utf-8")
        self.assertIn("There is no evidence that clustering or a pillar structure *causes* AI citations", readme)
        self.assertIn("Prompt for your AI", (tmp / "run1" / "deliverables" / "01-review-clusters" / "clusters.md").read_text(encoding="utf-8"))
        fields = set(rows1["Clusters"][0])
        self.assertTrue({"approved", "review_status", "note", "status", "opportunity_score"} <= fields)
        usage = json.loads((tmp / "run2" / "data" / "usage.json").read_text(encoding="utf-8"))
        self.assertTrue(all(r["est_cost_usd"] == 0 for r in usage["runs"]))

    def test_gsc_multi_page_query_in_cannibalisation(self):
        tmp = Path(tempfile.mkdtemp())
        g = tmp / "g.csv"
        write_gsc(g, GSC_ROWS)
        t, rows, _ = self.run_all(g, tmp / "run", brand="")
        q = [r for r in t["cannibal"] if r["level"] == "query"]
        self.assertEqual([r["query_or_cluster"] for r in q], ["how to make fists stronger"])
        self.assertEqual(q[0]["suggested_keep_url"], f"{SITE}/training/fists/")
        where = {r["keyword"]: r["cluster_id"] for r in t["keywords"]}
        self.assertEqual(where["champ workout"], where["champ workout routine"])

    def test_keywords_by_cluster_csv(self):
        tmp = Path(tempfile.mkdtemp())
        for kind in ("ahrefs", "gsc"):
            src = tmp / f"{kind}.csv"
            write_ahrefs(src, AHREFS_ROWS) if kind == "ahrefs" else write_gsc(src, GSC_ROWS)
            run = tmp / f"run-{kind}"
            t, _, _ = self.run_all(src, run, brand="widgetco")
            out = tmp / f"kbc-{kind}.csv"
            C.write_kbc(out, t["kbc"], kind)
            raw = out.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            want = (["Topic", "Cluster", "Keyword", "Volume", "KD", "Position", "URL"] if kind == "ahrefs" else
                    ["Topic", "Cluster", "Keyword", "Impressions", "Clicks", "Position", "URL"])
            self.assertEqual(list(rows[0].keys()), want)
            inv = t["inv"]
            self.assertEqual(sorted(r["Keyword"] for r in rows), sorted(k["keyword"] for k in inv["keywords"]))
            # ordering: clustered block first, then Unclustered, then Branded
            kinds = [0 if r["Cluster"] not in ("Unclustered", "Branded") else (1 if r["Cluster"] == "Unclustered" else 2)
                     for r in rows]
            self.assertEqual(kinds, sorted(kinds))
            byid = {k["keyword"]: k for k in inv["keywords"]}
            dem = "Volume" if kind == "ahrefs" else "Impressions"
            for c in {r["Cluster"] for r in rows if kinds[rows.index(r)] == 0}:
                block = [r for r in rows if r["Cluster"] == c]
                self.assertEqual(block[0]["Keyword"], c)  # head first; the cluster is named after its head
                tail = [int(r[dem]) for r in block[1:]]
                self.assertEqual(tail, sorted(tail, reverse=True))
            if kind == "ahrefs":
                self.assertEqual([r["Keyword"] for r in rows if r["Cluster"] == "Branded"], ["widgetco"])
                r = next(r for r in rows if r["Keyword"] == "widget repair guide")
                self.assertEqual((r["Volume"], r["Position"], r["URL"]), ("900", "3.0", f"{SITE}/blog/widget-repair"))
                self.assertEqual(next(r for r in rows if r["Keyword"] == "lost widget topic")["Position"], "")
            self.assertTrue(all(byid[r["Keyword"]] for r in rows))

    @unittest.skipUnless(__import__("importlib").util.find_spec("openpyxl"), "openpyxl not installed")
    def test_xlsx_has_every_tab(self):
        import openpyxl
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "a.csv"
        write_ahrefs(p, AHREFS_ROWS)
        _, rows, _ = self.run_all(p, tmp / "run")
        C.write_xlsx(tmp / "o.xlsx", rows)
        wb = openpyxl.load_workbook(tmp / "o.xlsx")
        self.assertEqual(wb.sheetnames, ["README", "Clusters", "Topics", "Keywords", "Cannibalisation", "Pages",
                                         "Unclustered", "Branded"])


class ConfigPersistence(unittest.TestCase):
    def test_ingest_saves_config_and_later_overrides_stick(self):
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "a.csv"
        write_ahrefs(p, AHREFS_ROWS)
        over = tmp / "over.json"
        over.write_text(json.dumps({"thresholds": {"merge_min": 0.61}}), encoding="utf-8")
        run = tmp / "run"
        with contextlib.redirect_stdout(io.StringIO()):
            C.main(["ingest", "--input", str(p), "--out", str(run), "--config", str(over), "--brand-terms", "widgetco"])
        saved = json.loads((run / "data" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual((saved["thresholds"]["merge_min"], saved["brand"]["terms"]), (0.61, ["widgetco"]))
        ns = type("A", (), {"run_dir": str(run), "config": None})
        self.assertEqual(C.run_config(ns)["thresholds"]["merge_min"], 0.61)
        over2 = tmp / "over2.json"
        over2.write_text(json.dumps({"thresholds": {"topic_min": 0.9}}), encoding="utf-8")
        ns.config = str(over2)
        with contextlib.redirect_stdout(io.StringIO()):
            C.run_config(ns)
        ns.config = None
        again = C.run_config(ns)["thresholds"]
        self.assertEqual((again["merge_min"], again["topic_min"]), (0.61, 0.9))


class Preflight(unittest.TestCase):
    def test_key_never_printed(self):
        env = Path(tempfile.mkdtemp()) / ".env"
        env.write_text("TYPESAFE_API_KEY=super-secret-value\nOPENAI_API_KEY=sk-another-secret\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            C.main(["preflight", "--env-file", str(env)])
        self.assertNotIn("super-secret-value", out.getvalue())
        self.assertNotIn("sk-another-secret", out.getvalue())
        self.assertIn("TYPESAFE_API_KEY is set", out.getvalue())
        self.assertIn("embeddings provider: openai", out.getvalue())


if __name__ == "__main__":
    unittest.main()
