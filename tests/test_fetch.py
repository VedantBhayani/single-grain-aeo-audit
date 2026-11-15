"""Offline tests for the polite fetcher's robots.txt handling (RFC 9309). No network."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import fetch  # noqa: E402

PAGE = "https://example.org/blog/post/"


class RobotsTests(unittest.TestCase):
    def setUp(self):
        fetch._robots.clear()
        self.addCleanup(fetch._robots.clear)

    def allowed_when_robots_is(self, status, body=""):
        with mock.patch.object(fetch, "_get", return_value=(status, body, "")):
            return fetch.allowed(PAGE)

    def test_rules_are_followed(self):
        self.assertFalse(self.allowed_when_robots_is(200, "User-agent: *\nDisallow: /blog/"))
        fetch._robots.clear()
        self.assertTrue(self.allowed_when_robots_is(200, "User-agent: *\nDisallow: /wp-admin/"))

    def test_4xx_means_no_rules(self):
        self.assertTrue(self.allowed_when_robots_is(404))
        fetch._robots.clear()
        self.assertTrue(self.allowed_when_robots_is(403))

    def test_5xx_or_unreachable_means_stay_off(self):
        self.assertFalse(self.allowed_when_robots_is(503))
        fetch._robots.clear()
        self.assertFalse(self.allowed_when_robots_is("network-error"))

    def test_disallowed_page_is_never_fetched(self):
        fetch._robots["https://example.org"] = mock.Mock(can_fetch=lambda ua, u: False)
        with mock.patch.object(fetch, "_get") as get:
            self.assertEqual(fetch.fetch(PAGE)[0], "robots-disallowed")
        get.assert_not_called()


class CacheTests(unittest.TestCase):
    """_get itself, with urlopen faked: what is cached, what isn't, and a corrupt cache file."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (("CACHE", Path(self.tmp.name)), ("LOG", Path(self.tmp.name) / "log.csv"),
                            ("DELAY_S", 0), ("CACHE_TTL_S", 3600)):
            p = mock.patch.object(fetch, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.calls = []

    def serve(self, *answers):
        """Fake urlopen: each call returns the next answer (an int status or an exception)."""
        import io
        import urllib.error
        seq = list(answers)

        def urlopen(req, timeout=None):
            self.calls.append(req.full_url)
            a = seq.pop(0)
            if isinstance(a, Exception):
                raise a
            if a != 200:
                raise urllib.error.HTTPError(req.full_url, a, "x", {}, io.BytesIO(b""))
            r = mock.MagicMock()
            r.__enter__.return_value = mock.Mock(status=200, geturl=lambda: req.full_url,
                                                 read=lambda: b"<html>ok</html>")
            return r
        return mock.patch.object(fetch.urllib.request, "urlopen", urlopen)

    def test_a_200_is_cached(self):
        with self.serve(200):
            self.assertEqual(fetch._get(PAGE)[0], 200)
            self.assertEqual(fetch._get(PAGE)[0], 200)
        self.assertEqual(len(self.calls), 1)

    def test_errors_are_not_cached(self):
        import urllib.error
        with mock.patch.object(fetch.time, "sleep"), self.serve(*([503] * 3), 200):
            self.assertEqual(fetch._get(PAGE)[0], 503)
            self.assertEqual(fetch._get(PAGE)[0], 200)  # retried live, not served the cached 503
        with mock.patch.object(fetch.time, "sleep"), self.serve(*([urllib.error.URLError("down")] * 3)):
            self.assertEqual(fetch._get(PAGE + "x")[0], "network-error")
        self.assertFalse(list(Path(self.tmp.name).glob("*.tmp")))

    def test_a_corrupt_cache_file_is_refetched(self):
        import hashlib
        (Path(self.tmp.name) / (hashlib.sha1(PAGE.encode()).hexdigest() + ".json")).write_text('{"trunc')
        with self.serve(200):
            self.assertEqual(fetch._get(PAGE)[0], 200)
        self.assertEqual(len(self.calls), 1)

    def test_ttl_zero_always_fetches(self):
        with mock.patch.object(fetch, "CACHE_TTL_S", 0), self.serve(200, 200):
            fetch._get(PAGE)
            fetch._get(PAGE)
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main()
