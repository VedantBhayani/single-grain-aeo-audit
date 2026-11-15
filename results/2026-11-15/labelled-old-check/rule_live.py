"""Read-only: run the new rule on every currently failing post, live, and print hard vs labelled-old."""
import json
import sys

sys.path.insert(0, r"E:\Single Grain\single-grain-aeo-audit")
from aeo_audit import audit  # noqa: E402
from aeo_watch import watch  # noqa: E402
from common import fetch as F  # noqa: E402

F.CACHE_TTL_S = 0
REPO = r"E:\Single Grain\single-grain-aeo-audit"


class NoAI:
    calls, skipped = 0, None

    def newer(self, *a, **k):
        return None


run = json.loads(open(REPO + r"\results\watch\2026-11-15T1407Z\run.json", encoding="utf-8").read())
failing = [p for p in run["posts"] if p["hard"]]
for p in failing:
    r = watch.check_post(p["url"], p.get("lastmod", ""), NoAI(), "2026-11-15")
    lab = [w["evidence"][:90] for w in r.get("warn", []) if w["name"].startswith("Pre-2020 stat, labelled")]
    print(f"{'HARD' if r['hard'] else 'WARN-ONLY'}  {p['url'].split('/blog-posts/')[1][:60]}")
    for h in r["hard"]:
        print("    hard:", h["evidence"][:110])
    for x in lab:
        print("    labelled old:", x)
