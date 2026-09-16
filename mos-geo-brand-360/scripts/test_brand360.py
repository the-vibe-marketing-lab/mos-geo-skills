"""Offline tests for brand360.py. No network, no keys.

Run: python3 -m unittest scripts/test_brand360.py  (from the skill folder)
"""

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import brand360 as b  # noqa: E402

ENV = {"DATAFORSEO_LOGIN": "l", "DATAFORSEO_PASSWORD": "p", "OPENROUTER_API_KEY": "o",
       "BRIGHTDATA_API_KEY": "k", "BRIGHTDATA_SERP_ZONE": "z"}
PROMPTS = {"closed_book": [{"id": "cb01", "text": "What is Acme Widgets?"}],
           "branded": [{"id": "br01", "text": "Is Acme Widgets any good?"}],
           "unbranded": [{"id": "un01", "text": "Best widget maker in Australia"}]}


def dfs_ok(result, cost=0.01):
    return 200, {"status_code": 20000, "tasks": [{"status_code": 20000, "cost": cost, "result": [result]}]}


def fake_http(method, url, headers=None, body=None, timeout=0):
    if "llm_scraper/locations" in url:
        return dfs_ok({"location_code": 2036, "country_iso_code": "AU", "location_type": "Country"})
    if "claude/llm_responses/live" in url:  # primary fails for Claude only
        return 200, {"status_code": 20000, "tasks": [{"status_code": 40200, "status_message": "Payment required.", "cost": 0}]}
    if "llm_responses/live" in url:
        assert "system_message" not in body[0]
        return dfs_ok({"items": [{"type": "reasoning", "sections": None},
                                 {"type": "message", "sections": [
                                     {"type": "text", "text": "Acme Widgets is ", "annotations": None},
                                     {"type": "text", "text": "a widget maker.",
                                      "annotations": [{"title": "acme.example", "url": "https://acme.example/"}]}]}],
                       "fan_out_queries": ["Acme Widgets"]})
    if "openrouter.ai" in url:
        assert body["messages"][0]["role"] == "user" and len(body["messages"]) == 1
        return 200, {"choices": [{"message": {"content": "Acme Widgets via OpenRouter.",
                                              "annotations": [{"type": "url_citation", "url_citation": {"url": "https://acme.example/about"}}]}}],
                     "usage": {"cost": 0.002}}
    if "llm_scraper/live" in url:
        return dfs_ok({"markdown": "Acme Widgets builds widgets.", "fan_out_queries": ["acme widgets australia"],
                       "sources": [{"url": "https://acme.example/", "title": "Acme"}], "items": []})
    if "ai_mode/live" in url:  # primary fails for AI Mode -> Bright Data batch
        return 200, {"status_code": 20000, "tasks": [{"status_code": 40101, "status_message": "Internal SE Server Error.", "cost": 0}]}
    if "organic/live" in url:
        if "Best widget" in body[0]["keyword"]:
            return dfs_ok({"items": [{"type": "organic"}]})  # no AI Overview shown
        return dfs_ok({"items": [{"type": "ai_overview", "markdown": "Acme Widgets is a maker.",
                                  "references": [{"url": "https://www.reddit.com/r/widgets", "domain": "reddit.com"}]}]})
    if "datasets/v3/trigger" in url:
        assert "gd_mcswdt6z2elth3zqr2" in url and "udm=50&q=" in body[0]["url"] and body[0]["country"] == "AU"
        return 200, {"snapshot_id": "sd_1"}
    if "datasets/v3/progress" in url:
        return 200, {"status": "ready"}
    if "datasets/v3/snapshot" in url:
        return 200, [{"prompt": p["text"], "answer_text": f"Bright Data says: {p['text']} Acme Widgets",
                      "citations": [{"url": "https://acme.example/faq"}]}
                     for p in PROMPTS["branded"] + PROMPTS["unbranded"]]
    raise AssertionError(f"unexpected call: {url}")


class Brand360Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "prompts.json").write_text(json.dumps(PROMPTS))
        b._LOCATION_CACHE.clear()
        patches = [mock.patch.object(b, "http_json", side_effect=fake_http),
                   mock.patch.object(b, "load_env", return_value=dict(ENV)),
                   mock.patch.object(b.time, "sleep"),
                   mock.patch.object(b, "resolve_grounding_url", side_effect=lambda c: c)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_all(self, **kw):
        args = Namespace(env_file=None, config=None, brand="Acme Widgets", industry="widgets",
                         prompts=str(self.dir / "prompts.json"), out=str(self.dir / "run"),
                         phases="closed-book,api-search,app", only=None, workers=4,
                         country="AU", dry_run=False)
        vars(args).update(kw)
        with mock.patch("builtins.print"):
            self.assertEqual(b.cmd_run(args), 0)
        return [json.loads(l) for l in (self.dir / "run" / "results.jsonl").read_text().splitlines()]

    def test_primary_and_fallbacks(self):
        rows = self.run_all()
        by = {(r["phase"], r["engine"], r["prompt_id"]): r for r in rows}
        # 3 closed-book + 8 api-search + 8 app
        self.assertEqual(len(rows), 19)
        self.assertFalse([r for r in rows if r["error"]])
        gpt = by[("api-search", "chatgpt", "br01")]
        self.assertEqual((gpt["provider"], gpt["answer"]), ("dataforseo", "Acme Widgets is a widget maker."))
        self.assertEqual(gpt["fan_out"], ["Acme Widgets"])
        claude = by[("closed-book", "claude", "cb01")]
        self.assertEqual(claude["provider"], "openrouter")
        self.assertIn("40200", claude["fallback_from"][0])
        aimode = by[("app", "aimode", "un01")]
        self.assertEqual(aimode["provider"], "brightdata")
        self.assertTrue(aimode["answer"].startswith("Bright Data says"))
        self.assertEqual(by[("app", "google-aio", "un01")]["answer"], b.NO_AIO)
        self.assertNotIn(("closed-book", "perplexity", "cb01"), by)

    def test_only_and_summary(self):
        self.run_all()
        rows = self.run_all(phases="app", only="google-aio")  # a retry appends
        self.assertEqual(len(rows), 21)
        args = Namespace(run_dir=str(self.dir / "run"), brand=None, alias=["Acme"],
                         own_domain=["acme.example"], competitor=["reddit.com"], check_links=False,
                         excerpt=200, no_excerpts=False, top_domains=30, fan_out=12)
        with mock.patch("builtins.print"):
            b.cmd_summarise(args)
        md = (self.dir / "run" / "visibility.md").read_text()
        self.assertIn("| Claude (API) | api | openrouter |", md)
        self.assertIn("| Google AI Mode | app | brightdata |", md)
        self.assertIn("| acme.example | own |", md)
        self.assertIn("| reddit.com | platform |", md)  # platform beats competitor
        self.assertIn("## 6. Search queries", md)
        self.assertIn("| ChatGPT (app) | br01 | Is Acme Widgets any good? | acme widgets australia |", md)
        self.assertIn("| Engine | Mentions brand | Top cited domains | What it said |", md)
        self.assertIn("| ChatGPT (API) | **Yes** | acme.example |", md)
        self.assertIn("| Google AI Overviews | No | - |", md)
        self.assertNotIn("## 7. Failed calls", md)
        # the retry replaced, not duplicated, the AI Overview rows
        self.assertIn("| Google AI Overviews | app | dataforseo | - | 1/1 | 1/1 | 0/1 | 0 |", md)

    def test_run_dir_inside_and_outside_a_brain(self):
        brain = self.dir / "brain"
        (brain / ".mos").mkdir(parents=True)
        (brain / ".mos" / "config.yaml").write_text("{}")
        (brain / "content").mkdir()
        inside = b.run_dir_for("The Vibe Marketing Lab", "2026-09-16", brain / "content")
        self.assertEqual(inside, (brain / "campaigns/geo/2026-09/the-vibe-marketing-lab").resolve())
        inside.mkdir(parents=True)
        (inside / "brand-360-report.md").write_text("x")
        again = b.run_dir_for("The Vibe Marketing Lab", "2026-09-30", brain)
        self.assertEqual(again.name, "the-vibe-marketing-lab-2")  # never overwrite a run
        outside = b.run_dir_for("Acme & Co.", "2026-01-05", self.dir)
        self.assertEqual(outside, (self.dir / "outputs/brand-360/2026-01/acme-co").resolve())
        with self.assertRaises(SystemExit):
            b.run_dir_for("Acme", "16-09-2026", self.dir)

    def test_plain_table_cell(self):
        self.assertEqual(b.plain("## Top **pick**: [Acme](https://acme.example) ([acme.example](https://acme.example))[1][2] a|b"),
                         "Top pick: Acme a\\|b")

    def test_prompt_limit(self):
        long = dict(PROMPTS, branded=[{"text": "x" * 501}])
        (self.dir / "prompts.json").write_text(json.dumps(long))
        with self.assertRaises(SystemExit):
            b.load_prompts(str(self.dir / "prompts.json"))

    def test_grounding_title_fallback(self):
        mock.patch.stopall()
        with mock.patch.object(b.urllib.request, "build_opener") as bo:
            bo.return_value.open.side_effect = OSError("offline")
            out = b.resolve_grounding_url({"url": "https://vertexaisearch.cloud.google.com/x", "title": "acme.example"})
        self.assertEqual(out["url"], "https://acme.example/")


if __name__ == "__main__":
    unittest.main()
