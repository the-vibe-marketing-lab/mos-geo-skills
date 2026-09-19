"""Offline tests for preferred_sources.py. No network.

Run: python3 -m unittest discover -s scripts -p 'test_*.py' -v  (from the skill folder)
"""

import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import preferred_sources as ps  # noqa: E402

URL = "https://www.example.com/blog/some-post/"
SCRIPT = '<script async src="https://news.google.com/swg/js/v1/publisher.js"></script>'
BODY_TEXT = "<p>" + ("This is a real server rendered article with plenty of words. " * 30) + "</p>"


def page(head="", body=""):
    return f"<!doctype html><html><head><title>t</title>{head}</head><body>{body}{BODY_TEXT}</body></html>"


class Install(unittest.TestCase):
    def test_standard_install_passes(self):
        r = ps.detect_install(page(SCRIPT, '<div google-add-preferred-source-btn data-theme="dark" data-lang="en"></div>'), URL)
        self.assertEqual(r["status"], ps.PASS, r)
        self.assertEqual(r["script"]["count"], 1)
        self.assertTrue(r["script"]["tags"][0]["async"])
        self.assertTrue(r["script"]["tags"][0]["in_head"])
        self.assertEqual(r["buttons"][0]["data_theme"], "dark")
        self.assertEqual(r["buttons"][0]["data_lang"], "en")

    def test_manual_mode_passes(self):
        head = ('<script async src="https://news.google.com/swg/js/v1/publisher.js" '
                'preferred-sources-control="manual"></script>')
        body = ("<button id='ps'>Add us on Google</button><script>"
                "(self.PREFERRED_SOURCE = self.PREFERRED_SOURCE || []).push(function(preferredSource) {"
                " preferredSource.init({});"
                " document.getElementById('ps').onclick = function(){ preferredSource.addPreferredSource(); };"
                "});</script>")
        r = ps.detect_install(page(head, body), URL)
        self.assertEqual(r["status"], ps.PASS, r)
        self.assertTrue(r["script"]["manual_attr"])
        self.assertTrue(r["manual"]["queue"])
        self.assertTrue(r["manual"]["add_call"])

    def test_module_variant_counts_as_script(self):
        body = ("<script type='module'>import {preferredSource} from "
                "'https://news.google.com/swg/js/v1/publisher.mjs'; preferredSource.addPreferredSource();</script>")
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["script"]["module_imports"], 1)
        self.assertEqual(r["status"], ps.PASS, r)

    def test_deeplink_only_passes(self):
        body = '<a href="https://www.google.com/preferences/source?q=www.example.com">Add us</a>'
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.PASS, r)
        self.assertEqual(r["deeplinks"][0]["q"], "www.example.com")

    def test_deeplink_www_difference_is_only_a_note(self):
        body = '<a href="https://www.google.com/preferences/source?q=example.com">Add us</a>'
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.PASS, r)
        self.assertTrue(any("www." in n for n in r["notes"]))

    def test_script_without_button_fails(self):
        r = ps.detect_install(page(SCRIPT, ""), URL)
        self.assertEqual(r["status"], ps.FAIL)
        self.assertTrue(any("nothing renders" in e for e in r["errors"]))

    def test_button_without_script_fails(self):
        r = ps.detect_install(page("", "<div google-add-preferred-source-btn></div>"), URL)
        self.assertEqual(r["status"], ps.FAIL)
        self.assertTrue(any("not loaded" in e for e in r["errors"]))

    def test_duplicate_script_warns(self):
        r = ps.detect_install(page(SCRIPT + SCRIPT, "<div google-add-preferred-source-btn></div>"), URL)
        self.assertEqual(r["status"], ps.WARN)
        self.assertEqual(r["script"]["count"], 2)
        self.assertTrue(any("duplicate" in w for w in r["warnings"]))

    def test_missing_async_warns_and_body_placement_is_a_note(self):
        body = ('<script src="https://news.google.com/swg/js/v1/publisher.js"></script>'
                "<div google-add-preferred-source-btn></div>")
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.WARN)
        self.assertFalse(r["script"]["tags"][0]["in_head"])
        self.assertTrue(any("async" in w for w in r["warnings"]))

    def test_manual_attr_without_call_fails(self):
        head = ('<script async src="https://news.google.com/swg/js/v1/publisher.js" '
                'preferred-sources-control="manual"></script>')
        r = ps.detect_install(page(head, ""), URL)
        self.assertEqual(r["status"], ps.FAIL)
        self.assertTrue(any("addPreferredSource" in e for e in r["errors"]))

    def test_deeplink_host_mismatch_fails(self):
        body = '<a href="https://www.google.com/preferences/source?q=other.com">Add us</a>'
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.FAIL)
        self.assertTrue(any("does not match" in e for e in r["errors"]))

    def test_deeplink_with_subdirectory_fails(self):
        body = '<a href="https://www.google.com/preferences/source?q=www.example.com/blog">Add us</a>'
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.FAIL)
        self.assertTrue(any("path" in e for e in r["errors"]))

    def test_spa_empty_page_needs_browser(self):
        html = ('<!doctype html><html><head><script src="/_next/static/chunks/main.js"></script></head>'
                '<body><div id="__next"></div><script id="__NEXT_DATA__" type="application/json">{}</script>'
                "</body></html>")
        r = ps.detect_install(html, URL)
        self.assertEqual(r["status"], ps.NEEDS_BROWSER)
        self.assertTrue(r["client_rendered"])

    def test_code_sample_and_tool_link_are_not_an_install(self):
        body = ('<pre><code>&lt;script async src="https://news.google.com/swg/js/v1/publisher.js"&gt;'
                '&lt;/script&gt;</code></pre><a href="https://www.google.com/preferences/source">tool</a>')
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.FAIL)
        self.assertEqual(r["script"]["raw_mentions"], 0)
        self.assertEqual(r["deeplinks"], [])
        self.assertEqual(len(r["tool_links"]), 1)

    def test_framework_loaded_script_needs_browser(self):
        body = ('<div google-add-preferred-source-btn></div><script>self.__next_f.push([1,"'
                'https://news.google.com/swg/js/v1/publisher.js"])</script>')
        r = ps.detect_install(page("", body), URL)
        self.assertEqual(r["status"], ps.NEEDS_BROWSER, r)

    def test_plain_page_without_install_fails(self):
        r = ps.detect_install(page("", ""), URL)
        self.assertEqual(r["status"], ps.FAIL)

    def test_csp_block_fails_an_installed_page(self):
        html = page(SCRIPT, "<div google-add-preferred-source-btn></div>")
        r = ps.detect_install(html, URL, {"content-security-policy": ["script-src 'self' https://cdn.example.com"]})
        self.assertEqual(r["csp"]["script"], "BLOCKS")
        self.assertEqual(r["status"], ps.FAIL)


class ReviewFixes(unittest.TestCase):
    CUSTOM = ('<a class="btn js-preferred-source" href="https://www.google.com/preferences/source?q=www.example.com">'
              "Add us on Google</a>")
    WIRING = ("<script>(self.PREFERRED_SOURCE = self.PREFERRED_SOURCE || []).push(function(ps) {"
              " ps.init({}); document.querySelector('.js-preferred-source').onclick = function(e) {"
              " e.preventDefault(); ps.addPreferredSource(); }; });</script>")
    MANUAL = ('<script async src="https://news.google.com/swg/js/v1/publisher.js" '
              'preferred-sources-control="manual"></script>')

    def test_custom_button_without_script_or_queue_warns(self):
        r = ps.detect_install(page("", self.CUSTOM), URL)
        self.assertEqual(r["status"], ps.WARN, r)
        self.assertTrue(r["deeplinks"][0]["custom"])
        self.assertTrue(any("popup won't open" in w for w in r["warnings"]))

    def test_custom_button_fully_wired_passes(self):
        r = ps.detect_install(page(self.MANUAL, self.CUSTOM + self.WIRING), URL)
        self.assertEqual(r["status"], ps.PASS, r)

    def test_plain_deeplink_still_passes(self):
        body = '<a class="btn" href="https://www.google.com/preferences/source?q=www.example.com">Add us</a>'
        self.assertEqual(ps.detect_install(page("", body), URL)["status"], ps.PASS)

    def test_inline_wiring_blocked_by_csp_warns(self):
        html = page(self.MANUAL, self.CUSTOM + self.WIRING)
        r = ps.detect_install(html, URL, {"content-security-policy": ["script-src 'self' https://news.google.com"]})
        self.assertEqual(r["csp"]["script"], "allows")
        self.assertEqual(r["csp"]["inline"], "may block")
        self.assertEqual(r["status"], ps.WARN, r)
        self.assertTrue(any("inline wiring" in w for w in r["warnings"]))

    def test_unsafe_inline_ignored_with_nonce(self):
        self.assertEqual(ps.csp_check(["script-src 'unsafe-inline' https://news.google.com"])["inline"], "allows")
        self.assertEqual(ps.csp_check(["script-src 'nonce-x' 'unsafe-inline' https://news.google.com"])["inline"],
                         "may block")
        self.assertEqual(ps.csp_check(["img-src 'self'"])["inline"], "allows")

    def test_inline_warning_not_raised_for_standard_install(self):
        html = page(SCRIPT, "<div google-add-preferred-source-btn></div>")
        r = ps.detect_install(html, URL, {"content-security-policy": ["script-src 'self' https://news.google.com"]})
        self.assertEqual(r["status"], ps.PASS, r)

    def test_strict_dynamic_warns_not_fails_and_says_host_is_not_enough(self):
        html = page(SCRIPT, "<div google-add-preferred-source-btn></div>")
        r = ps.detect_install(html, URL, {"content-security-policy":
                                          ["script-src 'nonce-abc' 'strict-dynamic' https://news.google.com"]})
        self.assertEqual(r["status"], ps.WARN, r)
        self.assertTrue(any("not sufficient" in w for w in r["warnings"]), r["warnings"])

    def test_expect_absent_pass_and_fail(self):
        clean = ps.expect_absent(ps.detect_install(page("", ""), "https://www.example.com/checkout/"))
        self.assertEqual(clean["status"], ps.PASS)
        dirty = ps.expect_absent(ps.detect_install(page(SCRIPT, "<div google-add-preferred-source-btn></div>"),
                                                   "https://www.example.com/checkout/"))
        self.assertEqual(dirty["status"], ps.FAIL)
        self.assertTrue(dirty["expect_absent"])

    def test_expect_absent_flag_parses(self):
        with unittest.mock.patch.object(ps, "verify_url", side_effect=lambda u: ps.detect_install(page("", ""), u)):
            with unittest.mock.patch("sys.stdout"):
                self.assertEqual(ps.main(["verify", "--expect-absent", "https://www.example.com/",
                                          "--expect-absent", "https://www.example.com/checkout/"]), 0)


class Csp(unittest.TestCase):
    def test_no_csp(self):
        self.assertEqual(ps.csp_check([], [])["script"], "no CSP")

    def test_allows_exact_host(self):
        r = ps.csp_check(["default-src 'self'; script-src 'self' https://news.google.com; "
                          "frame-src https://news.google.com; connect-src 'self' https://news.google.com"])
        self.assertEqual(r["script"], "allows")
        self.assertEqual(r["frame"], "allows")
        self.assertEqual(r["connect"], "allows")

    def test_allows_wildcard_and_path(self):
        self.assertEqual(ps.csp_check(["script-src *.google.com"])["script"], "allows")
        self.assertEqual(ps.csp_check(["script-src https://news.google.com/swg/"])["script"], "allows")
        self.assertEqual(ps.csp_check(["script-src https:"])["script"], "allows")

    def test_blocks(self):
        r = ps.csp_check(["default-src 'self'"])
        self.assertEqual(r["script"], "BLOCKS")
        self.assertEqual(r["frame"], "BLOCKS")
        self.assertEqual(ps.csp_check(["script-src 'self' https://www.google.com"])["script"], "BLOCKS")
        self.assertEqual(ps.csp_check(["script-src https://news.google.com/other/"])["script"], "BLOCKS")

    def test_default_src_falls_through_when_script_src_missing(self):
        self.assertEqual(ps.csp_check(["img-src 'self'"])["script"], "allows")

    def test_strict_dynamic_is_unclear(self):
        r = ps.csp_check(["script-src 'nonce-abc' 'strict-dynamic' https://news.google.com"])
        self.assertEqual(r["script"], "unclear")

    def test_meta_policy_counts_and_worst_wins(self):
        r = ps.csp_check(["script-src https://news.google.com"], ["script-src 'self'"])
        self.assertEqual(r["script"], "BLOCKS")

    def test_meta_http_equiv_is_read_from_html(self):
        html = page('<meta http-equiv="Content-Security-Policy" content="script-src \'self\'">' + SCRIPT,
                    "<div google-add-preferred-source-btn></div>")
        r = ps.detect_install(html, URL)
        self.assertEqual(r["csp"]["script"], "BLOCKS")


class Eligibility(unittest.TestCase):
    def test_subdirectory_url_normalises_to_host(self):
        info = ps.normalise_url("https://www.example.com/blog/")
        self.assertEqual(info["eligible_unit"], "https://www.example.com/")
        self.assertEqual(info["host"], "www.example.com")
        self.assertTrue(info["has_path"])
        self.assertTrue(any("Only a domain or subdomain" in w for w in info["warnings"]))
        self.assertEqual(info["deeplink"], "https://www.google.com/preferences/source?q=www.example.com")
        self.assertEqual(info["eligibility_check"]["status"], "MANUAL CHECK")

    def test_bare_host_gets_https_and_no_warning(self):
        info = ps.normalise_url("code.example.com")
        self.assertEqual(info["eligible_unit"], "https://code.example.com/")
        self.assertEqual(info["warnings"], [])

    def test_bad_url_raises(self):
        with self.assertRaises(ValueError):
            ps.normalise_url("https://")


class Stack(unittest.TestCase):
    def test_wordpress_with_elementor(self):
        html = ('<html><head><meta name="generator" content="WordPress 6.6.2">'
                '<link rel="stylesheet" href="/wp-content/plugins/elementor/assets/css/frontend.min.css">'
                '</head><body class="elementor-default"><script src="/wp-includes/js/jquery.js"></script></body></html>')
        r = ps.detect_stack(html, {"link": ['<https://example.com/wp-json/>; rel="https://api.w.org/"']})
        self.assertEqual(r["stack"], "WordPress (Elementor)")
        self.assertTrue(any("generator" in s for s in r["signals"]))

    def test_nextjs(self):
        html = ('<html><head><script src="/_next/static/chunks/webpack.js"></script></head><body><div id="__next">'
                '</div><script id="__NEXT_DATA__" type="application/json">{}</script></body></html>')
        r = ps.detect_stack(html, {"x-powered-by": ["Next.js"]})
        self.assertEqual(r["stack"], "Next.js")
        self.assertGreaterEqual(len(r["signals"]), 2)

    def test_unknown(self):
        self.assertEqual(ps.detect_stack("<html><body>hi</body></html>")["stack"], "unknown [VERIFY]")


class Sitemaps(unittest.TestCase):
    def test_robots_sitemap_lines(self):
        robots = "User-agent: *\nDisallow:\nSitemap: https://example.com/sitemap_index.xml\nsitemap: https://example.com/a.xml"
        self.assertEqual(ps.robots_sitemaps(robots),
                         ["https://example.com/sitemap_index.xml", "https://example.com/a.xml"])

    def test_parse_index_and_urlset(self):
        idx = ('<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               "<sitemap><loc>https://example.com/post-sitemap.xml</loc></sitemap></sitemapindex>")
        self.assertEqual(ps.parse_sitemap(idx), ("index", ["https://example.com/post-sitemap.xml"]))
        us = "<urlset><url><loc>https://example.com/a?x=1&amp;y=2</loc></url></urlset>"
        self.assertEqual(ps.parse_sitemap(us), ("urlset", ["https://example.com/a?x=1&y=2"]))

    def test_article_picking_excludes_tag_category(self):
        urls = [
            "https://www.example.com/",
            "https://www.example.com/tag/seo/",
            "https://www.example.com/category/news/",
            "https://www.example.com/author/jane/",
            "https://www.example.com/blog/page/2/",
            "https://www.example.com/about/",
            "https://www.example.com/wp-content/uploads/a.jpg",
            "https://other.com/blog/how-to-rank-in-ai-search/",
            "https://www.example.com/services/",
            "https://www.example.com/blog/how-to-rank-in-ai-search/",
            "https://example.com/2026/09/google-preferred-sources-explained/",
            "https://www.example.com/news/core-update-recap-for-september/",
        ]
        picked = ps.pick_articles(urls, "www.example.com", 3)
        self.assertEqual(len(picked), 3)
        for bad in ("/tag/", "/category/", "/author/", "/page/", "/about/", "other.com", ".jpg"):
            self.assertFalse(any(bad in u for u in picked), (bad, picked))
        self.assertIn("https://www.example.com/blog/how-to-rank-in-ai-search/", picked)

    def test_find_articles_follows_one_index_level(self):
        pages = {
            "https://example.com/sitemap_index.xml": "<sitemapindex><sitemap><loc>https://example.com/page-sitemap.xml</loc>"
                                                     "</sitemap><sitemap><loc>https://example.com/post-sitemap.xml</loc>"
                                                     "</sitemap></sitemapindex>",
            "https://example.com/post-sitemap.xml": "<urlset><url><loc>https://example.com/blog/first-long-post-title/</loc>"
                                                    "</url></urlset>",
            "https://example.com/page-sitemap.xml": "<urlset><url><loc>https://example.com/contact/</loc></url></urlset>",
        }

        def fake(url):
            body = pages.get(url)
            return (200, {}, body.encode(), url, "") if body else (404, {}, b"", url, "HTTP 404")

        r = ps.find_articles("https://example.com/", "example.com",
                             "Sitemap: https://example.com/sitemap_index.xml", fetcher=fake)
        self.assertEqual(r["articles"], ["https://example.com/blog/first-long-post-title/"])
        self.assertEqual(r["source"], "robots.txt")


class Cli(unittest.TestCase):
    def test_usage_error_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            ps.main(["verify"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
