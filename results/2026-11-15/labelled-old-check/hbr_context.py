"""Read-only: for each HBR-2011 post, print the stale_source findings and the text around the hbr.org link."""
import re
import sys

sys.path.insert(0, r"E:\Single Grain\single-grain-aeo-audit")
from aeo_audit import audit  # noqa: E402
from common import fetch as F  # noqa: E402

F.CACHE_TTL_S = 0
SG = "https://www.singlegrain.com/blog-posts/"
POSTS = {
    "#1": "how-to-hire-or-build-ai-marketing-agents-that-own-pipeline-jobs-without-a-chatbot-demo/",
    "#2": "startups-test-thousands-of-ads/",
    "#3": "slas-kill-switches-managed-marketing-agents/",
    "#4": "which-ai-marketing-services-to-buy-when-you-need-pipeline-not-another-content-calendar/",
    "#5": "forward-deployed-marketer/",
    "#6": "which-marketing-jobs-a-founder-can-hand-gpt-6-astra-for-a-full-day-before-hiring/",
}
for n, slug in POSTS.items():
    st, page, _ = F.fetch(SG + slug)
    body = audit.article_html(page)
    _, f, _ = audit.audit_page(SG + slug, page)
    print(f"===== {n} {slug} status {st}")
    for k, e in f:
        if k == "stale_source":
            print("  FINDING:", e[:200])
    for m in re.finditer(r'href="(https?://hbr\.org/2011[^"]*)"', body):
        s = max(body.rfind("<p", 0, m.start()), body.rfind("<li", 0, m.start()))
        e = min(x for x in (body.find("</p>", m.end()), body.find("</li>", m.end())) if x > 0)
        print("  BLOCK:", audit.strip(body[s:e + 5])[:700])
