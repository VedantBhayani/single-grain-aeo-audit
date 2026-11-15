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


if __name__ == "__main__":
    unittest.main()
