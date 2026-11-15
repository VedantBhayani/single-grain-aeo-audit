"""Offline tests for the tracking guard's change detection."""
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tracking_guard import guard  # noqa: E402

HOME = "https://www.singlegrain.com/"
CONTACT = "https://www.singlegrain.com/contact-us/"


def page(**kw):
    base = {"status": 200, "final_url": "", "redirected": False, "title": "T", "gtm": ["GTM-K3ZSFV"], "ga4": [],
            "ua": [], "trackers": ["hubspot"], "forms": 2, "form_actions": ["/submit"], "canonical": "c",
            "noindex": False, "js_app": False, "any_tracking": True, "source": "sitemap"}
    base.update(kw)
    return base


class DiffTests(unittest.TestCase):
    def setUp(self):
        self.old = {HOME: page(final_url=HOME), CONTACT: page(final_url=CONTACT)}

    def alerts(self, new):
        return [(lvl, url, k) for lvl, url, k, _, _ in guard.diff(self.old, new) if lvl == "ALERT"]

    def test_no_change_no_alert(self):
        self.assertEqual(guard.diff(self.old, copy.deepcopy(self.old)), [])

    def test_removed_gtm_and_hubspot_alert(self):
        new = copy.deepcopy(self.old)
        new[HOME].update(gtm=[], trackers=[])
        self.assertEqual(sorted(self.alerts(new)), [("ALERT", HOME, "gtm"), ("ALERT", HOME, "trackers")])

    def test_fewer_forms_changed_action_and_noindex_alert(self):
        new = copy.deepcopy(self.old)
        new[CONTACT].update(forms=1, form_actions=["/elsewhere"], noindex=True)
        self.assertEqual({k for _, _, k in self.alerts(new)}, {"forms", "form_actions", "noindex"})

    def test_added_tag_and_title_change_are_not_alerts(self):
        new = copy.deepcopy(self.old)
        new[HOME].update(trackers=["hubspot", "meta_pixel"], title="New title")
        self.assertEqual(self.alerts(new), [])


class BaselineTests(unittest.TestCase):
    def test_www_only_redirect_is_not_reported_and_real_redirect_is_named(self):
        # Built through facts(), not by hand: the old test hand-built a state facts() can't produce.
        web = {"https://clickflow.com": (200, "<html></html>", "https://www.clickflow.com/"),
               "https://www.singlegrain.com/old-page/": (200, "<html></html>", "https://www.singlegrain.com/")}
        with mock.patch.object(guard, "fetch", lambda u: web[u]):
            snap = {u: {**guard.facts(u), "source": "sitemap"} for u in web}
        self.assertEqual([(k, u) for k, u, _ in guard.baseline(snap) if "redirect" in k],
                         [("listed (sitemap) but redirects", "https://www.singlegrain.com/old-page/")])

    def test_failed_sitemap_keeps_last_snapshot_pages_and_alerts(self):
        old = {HOME: page(), CONTACT: page()}
        pages = guard.with_previous({HOME: "sitemap"}, old, [("https://x/sitemap.xml", 503)])
        self.assertEqual(pages[CONTACT], "previous snapshot (sitemap failed)")
        self.assertEqual(guard.with_previous({HOME: "sitemap"}, old, []), {HOME: "sitemap"})

    def test_page_without_tags_is_reported_not_called_broken(self):
        snap = {"https://gateway.singlebrain.com/": page(gtm=[], trackers=[], any_tracking=False, js_app=True,
                                                          final_url="https://gateway.singlebrain.com/")}
        self.assertEqual(guard.baseline(snap)[0][0], "no tracking tag in served HTML (JS app)")


if __name__ == "__main__":
    unittest.main()
