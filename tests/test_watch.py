"""Offline tests for the watcher and the issue sync. No network: a fake fetcher and a fake Parallel."""
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeo_audit import audit  # noqa: E402
from aeo_watch import issues, watch  # noqa: E402
from tests.test_audit import BAD, CLEAN, SG, WEB, fake_web  # noqa: E402

A, B, C = (f"{SG}/blog-posts/{x}/" for x in ("a", "b", "c"))
NOW = datetime(2026, 11, 15, 15, 0, tzinfo=timezone.utc)


class FakeAI:
    calls, skipped = 0, None

    def newer(self, claim, page_url, today, old_sources=()):
        return None


def ticking(step):
    """A clock that advances `step` seconds every time it's read."""
    t = [0.0]

    def clock():
        t[0] += step
        return t[0]
    return clock


class WatchRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["AEO_STATE"] = self.tmp.name
        self.addCleanup(os.environ.pop, "AEO_STATE", None)
        audit._service_urls, audit._link_status, audit._videos = None, {}, {}
        web = {**WEB, A: (200, BAD), B: (200, CLEAN), C: (404, "")}
        p = mock.patch.object(audit, "fetch", fake_web(web))
        p.start()
        self.addCleanup(p.stop)

    def go(self, posts, **kw):
        kw.setdefault("ai", FakeAI())
        kw.setdefault("now", NOW)
        return watch.run(posts=posts, **kw)

    def test_first_run_checks_posts_since_baseline_only(self):
        posts = [(A, "2026-10-20"), (B, "2026-09-01")]
        s, checked, _ = self.go(posts)
        self.assertEqual([p["url"] for p in checked], [A])  # B is older than 2026-10-14
        self.assertEqual(s["failing_now"], 1)

    def test_new_mode_skips_unchanged_and_rechecks_updated(self):
        self.go([(A, "2026-10-20"), (B, "2026-10-21")])
        _, again, _ = self.go([(A, "2026-10-20"), (B, "2026-10-21")])
        self.assertEqual(again, [])
        _, upd, _ = self.go([(A, "2026-11-14"), (B, "2026-10-21")])
        self.assertEqual([p["url"] for p in upd], [A])

    def test_all_mode_checks_every_post(self):
        _, checked, _ = self.go([(A, "2026-10-20"), (B, "2020-01-01")], mode="all")
        self.assertEqual({p["url"] for p in checked}, {A, B})

    def test_since_mode(self):
        _, checked, _ = self.go([(A, "2026-10-20"), (B, "2026-09-02")], mode="since", since="2026-09-01")
        self.assertEqual({p["url"] for p in checked}, {A, B})

    def test_budget_leaves_a_queue_and_the_next_run_continues(self):
        posts = [(A, "2026-10-20"), (B, "2026-10-21"), (C, "2026-10-22")]
        s, checked, _ = self.go(posts, mode="all", budget_min=1, clock=ticking(25))  # 2 posts fit in 60 s
        self.assertEqual((len(checked), s["queued_left"]), (2, 1))
        s2, checked2, _ = self.go(posts, mode="new")
        self.assertEqual([p["url"] for p in checked2], [C])
        self.assertEqual(s2["queued_left"], 0)

    def test_dead_post_is_recorded_not_failed(self):
        _, checked, _ = self.go([(C, "2026-10-22")])
        self.assertFalse(checked[0]["live"])
        self.assertEqual(checked[0]["hard"], [])

    def test_a_crashing_post_is_skipped_not_a_poison_pill(self):
        # Review, Nov 15: a post that raised stayed at the head of the queue and stopped every later run.
        real = watch.check_post

        def flaky(url, *a):
            if url == A:
                raise KeyError("boom")
            return real(url, *a)
        with mock.patch.object(watch, "check_post", flaky):
            s, checked, st = self.go([(A, "2026-10-20"), (B, "2026-10-21")])
        self.assertEqual([p["url"] for p in checked], [A, B])
        self.assertEqual((s["retry_next_run"], s["queued_left"]), (1, 0))
        self.assertNotIn(A, st["seen"])  # so the next run tries it again
        _, again, _ = self.go([(A, "2026-10-20"), (B, "2026-10-21")])
        self.assertEqual([p["url"] for p in again], [A])

    def test_a_transient_error_keeps_the_last_result_and_is_retried(self):
        self.go([(A, "2026-10-20")])  # failing
        with mock.patch.object(audit, "fetch", fake_web({**WEB, A: ("network-error", "")})):
            s, checked, st = self.go([(A, "2026-10-25")])
        self.assertTrue(checked[0]["retry"])
        self.assertEqual((s["failing_now"], s["fixed"], s["not_live"]), (1, 0, 0))  # not "fixed", not "gone"
        self.assertEqual(st["seen"][A], "2026-10-20")

    def test_a_post_that_is_gone_closes_out(self):
        self.go([(A, "2026-10-20")])  # failing
        with mock.patch.object(audit, "fetch", fake_web({**WEB, A: (404, "")})):
            s, checked, st = self.go([(A, "2026-10-25")])
        self.assertEqual((s["failing_now"], s["fixed"], s["not_live"]), (0, 0, 1))
        payload = watch.issues_payload(checked, st)
        self.assertEqual([g["url"] for g in payload["gone"]], [A])
        self.assertIn("Not live", watch.dashboard(s, st))

    def test_failing_posts_not_checked_this_run_are_the_backlog(self):
        _, _, st = self.go([(A, "2026-10-20"), (B, "2026-10-21")])
        _, checked, st = self.go([(A, "2026-10-20"), (B, "2026-10-22")])  # only B re-checked
        payload = watch.issues_payload(checked, st)
        self.assertEqual([p["url"] for p in payload["backlog"]], [A])

    def test_cli_fetches_fresh(self):
        old = watch.fetch_mod.CACHE_TTL_S
        self.addCleanup(setattr, watch.fetch_mod, "CACHE_TTL_S", old)
        with mock.patch.object(watch, "run", return_value=({}, [], {})):
            watch.main(["watch.py", "run"])
        self.assertEqual(watch.fetch_mod.CACHE_TTL_S, 0)

    def test_fixed_post_is_counted(self):
        self.go([(A, "2026-10-20")])
        with mock.patch.object(audit, "fetch", fake_web({**WEB, A: (200, CLEAN)})):
            s, _, _ = self.go([(A, "2026-10-25")])
        self.assertEqual((s["fixed"], s["failing_now"]), (1, 0))

    def test_outputs_are_written_and_html_is_escaped(self):
        with tempfile.TemporaryDirectory() as out:
            self.go([(A, "2026-10-20"), (B, "2026-10-21")], out=out)
            names = sorted(os.listdir(out))
            self.assertEqual(names, ["index.html", "issues.json", "report.md", "run.json"])
            payload = json.loads(Path(out, "issues.json").read_text(encoding="utf-8"))
            self.assertEqual([p["url"] for p in payload["failing"]], [A])
            self.assertEqual(payload["passing"], [B])
            self.assertIn("modified on or after 2026-10-14", Path(out, "index.html").read_text(encoding="utf-8"))
        st = {"posts": {A: {"url": A, "title": "<script>x</script>", "live": True, "checked_at": "t",
                            "hard": [{"name": "n", "evidence": "<b>"}], "warn": [], "suggestions": []}}}
        page = watch.dashboard({"run_at": "t", "mode": "new", "failing_now": 1, "checked": 1,
                                "queued_left": 0, "parallel_cost_usd": 0}, st)
        self.assertNotIn("<script>x", page)
        self.assertIn("&lt;script&gt;", page)


class AIStepTests(unittest.TestCase):
    def test_only_stat_or_study_sentences_and_dated_links_go_to_parallel(self):
        f = [("stale_source", "2011: A 2011 study found that 71% of leads go cold."),
             ("stale_source", "2009: Single Grain was founded in 2009."),
             ("stale_source", "link https://hbr.org/2011/03/x"),
             ("no_toc", "no auto-toc block")]
        self.assertEqual(watch.stale_claims(f), [f[0][1], f[2][1]])

    def test_suggestion_drops_own_site_the_old_source_its_variants_and_archives(self):
        # Regression (live run, Nov 15): the old HBR article came back with "?page=3" and as a web.archive.org copy.
        old = "https://hbr.org/2011/03/x"
        resp = {"answers": {"newer": {"noul": 0.9123}},
                "citations": [{"url": "https://www.singlegrain.com/x", "title": "own"},
                              {"url": "https://hbr.org/2011/03/x/", "title": "old"},
                              {"url": "https://hbr.org/2011/03/x?639a0fac_page=3", "title": "old, query"},
                              {"url": "https://web.archive.org/web/2023/https://hbr.org/2011/03/x", "title": "archive"},
                              {"url": "https://example.org/2024-report", "title": "new"}]}
        s = watch.suggestion(resp, [old])
        self.assertEqual(s, {"p": 0.91, "sources": [{"url": "https://example.org/2024-report", "title": "new"}]})

    def test_suggestion_survives_junk_and_keeps_only_http_links(self):
        # Review: a null title crashed the post; a javascript: URL would have reached the dashboard's href.
        resp = {"answers": {"newer": {"noul": 0.9}},
                "citations": [None, {"url": None, "title": None}, {"url": "javascript:alert(1)", "title": "x"},
                              {"url": "https://example.org/r", "title": None}]}
        self.assertEqual(watch.suggestion(resp, []), {"p": 0.9, "sources": [{"url": "https://example.org/r", "title": ""}]})
        for junk in (None, [], {"answers": None}, {"answers": {"newer": {"noul": "high"}}}):
            self.assertEqual(watch.suggestion(junk, [])["sources"], [])

    def test_low_probability_shows_no_sources(self):
        # Regression (live run): p=0.06 means "no newer data"; its citations were shown as if they were.
        resp = {"answers": {"newer": {"noul": 0.061}}, "citations": [{"url": "https://example.org/a", "title": "a"}]}
        s = watch.suggestion(resp, [])
        self.assertEqual(s, {"p": 0.06, "sources": []})
        self.assertIn("no newer data found", watch.ai_line({"claim": "c", **s}))

    def test_prose_year_is_a_warning_not_a_hard_failure(self):
        # Regression (live run): "launched ... in 2019" in an example sentence opened a public issue.
        audit._service_urls, audit._link_status, audit._videos = None, {}, {}
        page = ('<html><body><article class="container post-1"><div class="auto-toc"></div><img src=x>'
                "<p>The company launched its first programmatic ad campaign in 2019.</p>"
                "<p>A 2011 study found that 71% of leads go cold.</p></article></body></html>")
        u = f"{SG}/blog-posts/prose/"
        with mock.patch.object(audit, "fetch", fake_web({**WEB, u: (200, page)})):
            res = watch.check_post(u, "2026-11-01", FakeAI(), "2026-11-15")
        self.assertEqual([h["evidence"][:4] for h in res["hard"]], ["2011"])
        self.assertTrue(any(w["name"] == "Pre-2020 year, not a cited stat" and w["evidence"].startswith("2019")
                            for w in res["warn"]))

    def test_parallel_is_capped_cached_and_never_fatal(self):
        calls = []

        def ask(key, claim, url, today):
            calls.append(claim)
            return {"answers": {"newer": {"noul": 0.5}}, "citations": []}
        cache = {"old-format": {"p": 0.9, "sources": []}}  # first-run cache shape: no raw answer, so re-asked
        ai = watch.Parallel("k", cache, cap=2, ask=ask)
        for c in ("one", "two", "one", "three"):
            ai.newer(c, "u", "d")
        self.assertEqual(calls, ["one", "two"])  # "one" again came from the cache; "three" hit the cap
        self.assertIn("cap", ai.skipped)
        self.assertEqual(cache["one"], {"raw": {"answers": {"newer": {"noul": 0.5}}, "citations": []}})
        ai3 = watch.Parallel("k", cache, ask=ask)
        ai3.newer("old-format", "u", "d")
        self.assertEqual(calls[-1], "old-format")

        def broken(*a):
            raise urllib.error.URLError("down")
        ai2 = watch.Parallel("k", {}, ask=broken)
        self.assertIsNone(ai2.newer("x", "u", "d"))
        self.assertIn("error", ai2.skipped)
        self.assertIsNone(watch.Parallel(None, {}).newer("x", "u", "d"))


class IssueSyncTests(unittest.TestCase):
    def failing(self, url):
        return {"url": url, "title": "t", "checked_at": "2026-11-15T15:00", "suggestions": [],
                "hard": [{"name": "Pre-2020 source", "evidence": "2011: ..."}]}

    def test_gone_closes_and_backlog_opens_only_if_never_issued(self):
        D = f"{SG}/blog-posts/d/"
        all_ = [{"number": 7, "body": issues.marker(A), "state": "open"},
                {"number": 9, "body": issues.marker(B), "state": "closed"}]  # a human closed B
        payload = {"failing": [], "passing": [], "gone": [{"url": A, "status": "404", "final": A}],
                   "backlog": [self.failing(B), self.failing(D)]}
        actions, skipped = issues.plan(all_, payload)
        self.assertEqual([(k, a if k != "open" else "new") for k, a, _ in actions], [("open", "new"), ("close", 7)])
        self.assertIn(issues.marker(D), actions[0][2])
        self.assertIn("no longer live (status 404)", actions[1][2])

    def test_backlog_over_the_cap_waits_for_the_next_run(self):
        payload = {"failing": [self.failing(f"{SG}/blog-posts/p{i}/") for i in range(3)], "passing": [],
                   "backlog": [self.failing(f"{SG}/blog-posts/q{i}/") for i in range(3)]}
        actions, skipped = issues.plan([], payload, cap=4)
        self.assertEqual((len(actions), skipped), (4, 2))
        self.assertTrue(all("/p" in a for _, a, _ in actions[:3]))  # this run's failures go first

    def test_open_comment_close(self):
        open_ = [{"number": 7, "body": "x " + issues.marker(A)}, {"number": 8, "body": issues.marker(B)}]
        payload = {"failing": [self.failing(A), self.failing(C)], "passing": [B]}
        actions, skipped = issues.plan(open_, payload)
        kinds = [(k, a if k != "open" else "new") for k, a, _ in actions]
        self.assertEqual(kinds, [("comment", 7), ("open", "new"), ("close", 8)])
        self.assertEqual(skipped, 0)
        self.assertIn(issues.marker(C), actions[1][2])

    def test_new_issues_are_capped(self):
        payload = {"failing": [self.failing(f"{SG}/blog-posts/p{i}/") for i in range(5)], "passing": []}
        actions, skipped = issues.plan([], payload, cap=3)
        self.assertEqual((len(actions), skipped), (3, 2))

    def test_marker_round_trip(self):
        self.assertEqual(issues.url_of("text\n" + issues.marker(A)), A)
        self.assertIsNone(issues.url_of("no marker"))
        self.assertIsNone(issues.url_of("<!-- aeo-watch:https://x/ no end"))


if __name__ == "__main__":
    unittest.main()
