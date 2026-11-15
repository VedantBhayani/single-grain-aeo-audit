import urllib.request, urllib.robotparser
UA = "SingleGrainAEOAudit-verify/1.0 (read-only re-check; one request per 2s; github.com/VedantBhayani)"
for ua in ("Python-urllib/3.12", UA):
    try:
        with urllib.request.urlopen(urllib.request.Request("https://www.singlegrain.com/robots.txt", headers={"User-Agent": ua}), timeout=30) as r:
            body = r.read().decode("utf-8", "replace"); print(ua[:25], r.status, len(body))
    except Exception as e:
        print(ua[:25], "ERR", e)
rp = urllib.robotparser.RobotFileParser(); rp.parse(body.splitlines())
print("can_fetch blog-post:", rp.can_fetch(UA, "https://www.singlegrain.com/blog-posts/forward-deployed-marketer/"))
print("can_fetch /artificial-intelligence/x:", rp.can_fetch(UA, "https://www.singlegrain.com/artificial-intelligence/x/"))
print([l for l in body.splitlines() if l.lower().startswith(("user-agent","disallow"))][:20])
