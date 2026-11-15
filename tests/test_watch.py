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

    def newer(self, claim, page_url, today):
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

    def test_suggestion_drops_own_site_and_the_old_source(self):
        resp = {"answers": {"newer": {"noul": 0.9}},
                "citations": [{"url": "https://www.singlegrain.com/x", "title": "own"},
                              {"url": "https://hbr.org/2011/03/x/", "title": "old"},
                              {"url": "https://example.org/2024-report", "title": "new"}]}
        s = watch.suggestion(resp, "link https://hbr.org/2011/03/x")
        self.assertEqual(s, {"p": 0.9, "sources": [{"url": "https://example.org/2024-report", "title": "new"}]})

    def test_parallel_is_capped_cached_and_never_fatal(self):
        calls = []

        def ask(key, claim, url, today):
            calls.append(claim)
            return {"answers": {"newer": {"noul": 0.5}}, "citations": []}
        cache = {}
        ai = watch.Parallel("k", cache, cap=2, ask=ask)
        for c in ("one", "two", "one", "three"):
            ai.newer(c, "u", "d")
        self.assertEqual(calls, ["one", "two"])  # "one" again came from the cache; "three" hit the cap
        self.assertIn("cap", ai.skipped)

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


if __name__ == "__main__":
    unittest.main()
