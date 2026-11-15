"""Read-only: modified time of the 6 HBR posts now, vs what the watcher recorded earlier today."""
import json
import subprocess
import sys

sys.path.insert(0, r"E:\Single Grain\single-grain-aeo-audit")
from aeo_audit import audit  # noqa: E402
from common import fetch as F  # noqa: E402

F.CACHE_TTL_S = 0
REPO = r"E:\Single Grain\single-grain-aeo-audit"
SG = "https://www.singlegrain.com/blog-posts/"
POSTS = ["how-to-hire-or-build-ai-marketing-agents-that-own-pipeline-jobs-without-a-chatbot-demo/",
         "startups-test-thousands-of-ads/", "slas-kill-switches-managed-marketing-agents/",
         "which-ai-marketing-services-to-buy-when-you-need-pipeline-not-another-content-calendar/",
         "forward-deployed-marketer/",
         "which-marketing-jobs-a-founder-can-hand-gpt-6-astra-for-a-full-day-before-hiring/"]
earlier = json.loads(open(REPO + r"\results\watch\2026-11-15T1407Z\run.json", encoding="utf-8").read())
then = {p["url"]: p for p in earlier["posts"]}
lastmod = dict(audit.post_urls("2026-01-01"))
for slug in POSTS:
    u = SG + slug
    st, page, _ = F.fetch(u)
    now_mod = audit.meta(page, "article:modified_time")
    p = then.get(u, {})
    print(f"{slug[:50]:50} modified then={p.get('modified')} now={now_mod} | sitemap lastmod then={p.get('lastmod')} now={lastmod.get(u)}")
