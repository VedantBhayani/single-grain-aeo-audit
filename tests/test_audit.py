"""Offline tests for the AEO audit. A fake fetcher stands in for the network; the HTML here is handwritten."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeo_audit import audit  # noqa: E402

SG = "https://www.singlegrain.com"
OK_VIDEO = json.dumps({"title": "A video", "author_name": "Leveling Up with Eric Siu"})


def oembed(vid):
    return f"https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D{vid}&format=json"


def fake_web(pages):
    """fetch() replacement: known URLs return what's given, everything else 200 with empty body."""
    def fetch(url):
        if url in pages:
            st, body = pages[url]
            return st, body, url
        return 200, "", url
    return fetch


def post(body):
    return f'<html><head><title>T</title></head><body><article class="container post-1">{body}</article></body></html>'


BAD = post(
    '<div class="auto-toc">TOC</div><img src="x.png">'
    "<p>A 2011 Harvard Business Review article reported an audit of 2,241 companies "
    '(<a href="https://hbr.org/2011/03/the-short-life-of-online-sales-leads">HBR</a>).</p>'
    "<p>Together with the embedded scene above, that is three on-angle Eric tape inputs for this job, not a link dump.</p>"
    '<p>See <a href="https://www.youtube.com/watch?v=AAAAAAAAAAA">Eric\'s video</a> and '
    '<a href="https://www.youtube.com/watch?v=BBBBBBBBBBB">this one</a>.</p>'
    f'<p>Read <a href="{SG}/artificial-intelligence/missing-post/">this</a> and '
    f'<a href="{SG}/agency/aeo-services/">our AEO services</a>.</p>'
)
CLEAN = post(
    '<div class="auto-toc">TOC</div><img src="x.png">'
    "<p>A 2024 survey found that 37% of buyers use AI search "
    '(<a href="https://example.com/2024-survey">source</a>).</p>'
    '<figure class="wp-block-embed-youtube"><iframe src="https://www.youtube.com/embed/AAAAAAAAAAA?start=95"></iframe></figure>'
    f'<p>Our <a href="{SG}/agency/aeo-services/">AEO services</a>.</p>'
)
WEB = {
    oembed("AAAAAAAAAAA"): (200, OK_VIDEO),
    oembed("BBBBBBBBBBB"): (404, ""),
    f"{SG}/artificial-intelligence/missing-post/": (404, ""),
    f"{SG}/service-sitemap.xml": (200, ""),
}


class AuditPageTests(unittest.TestCase):
    def setUp(self):
        audit._service_urls, audit._link_status, audit._videos = None, {}, {}
        patcher = mock.patch.object(audit, "fetch", fake_web(WEB))
        patcher.start()
        self.addCleanup(patcher.stop)

    def rules(self, html):
        _, findings, _ = audit.audit_page(f"{SG}/blog-posts/test/", html)
        return [k for k, _ in findings]

    def test_bad_post_hits_each_rule(self):
        r = self.rules(BAD)
        self.assertEqual(r.count("stale_source"), 2)  # the year in the text and the year in the link path
        self.assertIn("process_leak", r)
        self.assertIn("video_not_embedded", r)
        self.assertEqual(r.count("video_no_timestamp"), 2)
        self.assertEqual(r.count("video_unavailable"), 1)  # BBBBBBBBBBB returns 404
        self.assertEqual(r.count("broken_internal_link"), 1)
        self.assertNotIn("no_service_link", r)  # /agency/ counts as a service page
        self.assertNotIn("no_toc", r)
        self.assertNotIn("no_images", r)

    def test_clean_post_has_no_findings(self):
        self.assertEqual(self.rules(CLEAN), [])

    def test_missing_toc_images_and_service_link_are_flagged(self):
        r = self.rules(post("<p>Just text.</p>"))
        for rule in ("no_toc", "no_images", "no_service_link"):
            self.assertIn(rule, r)

    def test_each_leak_phrase_is_caught(self):
        for phrase in ("three Eric tape inputs here", "this is not a link dump", "an on-angle clip"):
            self.assertIn("process_leak", self.rules(post(f"<p>{phrase}.</p>")), phrase)

    def test_year_in_url_slug_is_not_a_source_year(self):
        # Regression: a "2000" inside a share link slug was once read as a 2000-era source.
        html = post('<p>Ask <a href="https://chatgpt.com/?q=jev-vs-sdr-queue-60000-leads-2000-icp">ChatGPT</a>.</p>')
        self.assertNotIn("stale_source", self.rules(html))

    def test_hypothetical_numbers_are_not_unsourced_claims(self):
        # Regression: worked examples ("a site doing 500,000 sessions might pay...") are not claimed stats.
        html = post("<p>A site doing 500,000 sessions/month might pay $50-150/month.</p>")
        self.assertNotIn("unsourced_claim", self.rules(html))

    def test_claimed_stat_without_a_link_is_flagged(self):
        html = post("<p>A recent study found that 64% of teams skip QA.</p>")
        self.assertIn("unsourced_claim", self.rules(html))

    def test_video_gone_is_hard_but_a_failed_check_is_not(self):
        # Review round 3: a 429 or 5xx from oEmbed was reported as "video unavailable", a hard failure.
        vid = "CCCCCCCCCCC"
        html = post(f'<p><a href="https://youtu.be/{vid}?t=1">clip</a></p><lite-youtube></lite-youtube>')
        for status, rule in ((401, "video_unavailable"), (403, "video_unavailable"), (404, "video_unavailable"),
                             (429, "video_unchecked"), (503, "video_unchecked"), ("network-error", "video_unchecked")):
            audit._videos = {}
            with mock.patch.object(audit, "fetch", fake_web({**WEB, oembed(vid): (status, "")})):
                r = self.rules(html)
            self.assertIn(rule, r, status)
            self.assertNotIn({"video_unavailable": "video_unchecked", "video_unchecked": "video_unavailable"}[rule],
                             r, status)

    def test_check_fetches_fresh_and_restores_the_cache_setting(self):
        from common import fetch as fetch_mod
        seen, before = [], fetch_mod.CACHE_TTL_S

        def spy(u):
            seen.append(fetch_mod.CACHE_TTL_S)  # what the real fetcher would see on every request
            return fake_web(WEB)(u)
        with mock.patch.object(audit, "fetch", spy), redirect_stdout(io.StringIO()):
            audit.cmd_check(f"{SG}/blog-posts/clean/")
        self.assertTrue(seen)
        self.assertEqual(set(seen), {0})
        self.assertEqual(fetch_mod.CACHE_TTL_S, before)

    def test_gate_does_not_pass_a_video_it_could_not_check(self):
        vid = "DDDDDDDDDDD"
        html = post(f'<p><a href="https://youtu.be/{vid}?t=1">clip</a></p><lite-youtube></lite-youtube>')
        with tempfile.TemporaryDirectory() as d:
            draft = Path(d) / "draft.html"
            draft.write_text(html, encoding="utf-8")
            for status, code in ((429, 3), (403, 1), (200, 0)):
                audit._videos = {}
                web = {**WEB, oembed(vid): (status, OK_VIDEO if status == 200 else "")}
                with mock.patch.object(audit, "fetch", fake_web(web)), redirect_stdout(io.StringIO()):
                    self.assertEqual(audit.cmd_check(str(draft)), code, status)

    def test_an_internal_link_that_could_not_be_checked_is_not_called_broken(self):
        link = f"{SG}/some-page/"
        html = post(f'<p>See <a href="{link}">this</a> and <a href="{SG}/agency/x/">us</a>.</p>')
        for status, rule in ((404, "broken_internal_link"), (429, "link_unchecked"), (503, "link_unchecked"),
                             (403, "link_unchecked"), ("robots-disallowed", "link_unchecked")):
            audit._link_status = {}
            with mock.patch.object(audit, "fetch", fake_web({**WEB, link: (status, "")})):
                r = self.rules(html)
            self.assertIn(rule, r, status)
            self.assertEqual(r.count("broken_internal_link") + r.count("link_unchecked"), 1, status)

    def test_odd_oembed_json_is_bad_json_not_a_crash(self):
        vid = "EEEEEEEEEEE"
        html = post(f'<p><a href="https://youtu.be/{vid}?t=1">clip</a></p><lite-youtube></lite-youtube>')
        for body in ("[1, 2]", '"text"', "not json"):
            audit._videos = {}
            with mock.patch.object(audit, "fetch", fake_web({**WEB, oembed(vid): (200, body)})):
                self.assertIn("video_unchecked", self.rules(html), body)

    def test_gate_says_unchecked_not_fail_when_the_page_does_not_load(self):
        with mock.patch.object(audit, "fetch", fake_web({**WEB, f"{SG}/blog-posts/preview/": (503, "")})), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(audit.cmd_check(f"{SG}/blog-posts/preview/"), 3)

    def test_site_run_says_fetch_failed_not_not_live_for_a_blip(self):
        posts = [(f"{SG}/blog-posts/ok/", "2026-10-01"), (f"{SG}/blog-posts/blip/", "2026-10-01"),
                 (f"{SG}/blog-posts/gone/", "2026-10-01")]
        web = {**WEB, posts[0][0]: (200, CLEAN), posts[1][0]: (503, ""), posts[2][0]: (404, "")}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(audit, "RESULTS", Path(d)), \
                mock.patch.object(audit, "post_urls", lambda since: posts), \
                mock.patch.object(audit, "fetch", fake_web(web)), redirect_stdout(io.StringIO()):
            audit.cmd_run("2026-08-01")
            rows = next(Path(d).glob("*/aeo/findings.csv")).read_text(encoding="utf-8")
        self.assertIn("blip/,fetch_failed", rows)
        self.assertIn("gone/,not_a_live_post", rows)
        self.assertNotIn("blip/,not_a_live_post", rows)

    def test_since_without_a_date_is_a_usage_error_not_a_crash(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["audit.py", "run", "--since"]), 2)
            self.assertEqual(audit.main(["audit.py", "run", "--since", "yesterday"]), 2)

    def test_check_on_a_local_draft_file(self):
        with tempfile.TemporaryDirectory() as d:
            bad, clean = Path(d) / "bad.html", Path(d) / "clean.html"
            bad.write_text(BAD, encoding="utf-8")
            clean.write_text(CLEAN, encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(audit.cmd_check(str(bad)), 1)
                self.assertEqual(audit.cmd_check(str(clean)), 0)


class RepeatedPassageTests(unittest.TestCase):
    def test_passage_in_three_posts_is_reported(self):
        s = "if the note lives in a random slack thread next week starts from folklore again for everyone involved here"
        found = audit.repeated_passages({"a": [s], "b": [s], "c": [s], "d": ["something else entirely"]})
        self.assertEqual(len(found), 1)
        self.assertEqual(next(iter(found.values())), {"a", "b", "c"})

    def test_short_or_twice_repeated_text_is_ignored(self):
        long = "this sentence is long enough to count but it only appears in two of the posts we checked"
        self.assertEqual(audit.repeated_passages({"a": [long, "Book a call."], "b": [long, "Book a call."]}), {})


if __name__ == "__main__":
    unittest.main()
