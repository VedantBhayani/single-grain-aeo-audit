"""Read-only: on issue #6's post, print the HBR 2011 paragraph, the <figure> right after it, and the next paragraph."""
import re
import sys

sys.path.insert(0, r"E:\Single Grain\single-grain-aeo-audit")
from aeo_audit import audit  # noqa: E402
from common import fetch as F  # noqa: E402

F.CACHE_TTL_S = 0
URL = "https://www.singlegrain.com/blog-posts/forward-deployed-marketer/"
st, page, _ = F.fetch(URL)
body = audit.article_html(page)
print(f"===== #6 {URL} status {st}")
print("  modified:", audit.meta(page, "article:modified_time"))
m = re.search(r'href="(https?://hbr\.org/2011[^"]*)"', body)
s = body.rfind("<p", 0, m.start())
e = body.find("</p>", m.end()) + 4
print("  HBR PARAGRAPH:", audit.strip(body[s:e]))
fs = body.find("<figure", e)
fe = body.find("</figure>", fs) + 9
print("  BETWEEN (stripped):", repr(audit.strip(body[e:fs])))
fig = body[fs:fe]
print("  FIGURE:", re.search(r"<figure[^>]*>", fig).group(0))
img = re.search(r"<img[^>]*>", fig).group(0)
print("    img src:", re.search(r'\ssrc="([^"]*)"', img).group(1))
print("    img alt:", re.search(r'\salt="([^"]*)"', img).group(1))
print("    figure text (stripped):", repr(audit.strip(fig)))
ns = body.find("<p", fe)
ne = body.find("</p>", ns) + 4
print("  BETWEEN (stripped):", repr(audit.strip(body[fe:ns])))
print("  NEXT PARAGRAPH:", audit.strip(body[ns:ne]))
