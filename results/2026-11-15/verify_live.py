"""Independent re-check of the Oct 14 claims against the live site: plain urllib and substring search,
no code from the audit (on purpose, so a bug in the audit can't confirm itself). Read-only, honours
robots.txt, 2 s between requests, and an honest User-Agent.

  python results/2026-11-15/verify_live.py results/2026-10-14/aeo/findings.csv
"""
import csv
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "SingleGrainAEOAudit-verify/1.0 (read-only re-check; one request per 2s; github.com/VedantBhayani)"
_robots = {}


def allowed(u):
    p = urllib.parse.urlparse(u)
    host = f"{p.scheme}://{p.netloc}"
    if host not in _robots:
        # Fetch robots.txt with our own UA: RobotFileParser.read() uses Python's default UA, which this
        # site answers with 403, and read() turns any 403 into "disallow everything".
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(host + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:  # RFC 9309: 4xx = no rules, 5xx = stay off
            rp.parse([] if e.code < 500 else ["User-agent: *", "Disallow: /"])
        except (urllib.error.URLError, TimeoutError, OSError):
            rp.parse(["User-agent: *", "Disallow: /"])
        _robots[host] = rp
    return _robots[host].can_fetch(UA, u)


def get(u):
    if not allowed(u):
        return "robots-disallowed", u, ""
    time.sleep(2)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=30) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, u, ""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return f"network-error: {str(e)[:60]}", u, ""


def main(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    hbr = sorted({r["url"] for r in rows if "hbr.org/2011" in r["evidence"]})
    print(f"== HBR 2011 link: {len(hbr)} posts flagged on Oct 14")
    for u in hbr:
        st, _, body = get(u)
        n = body.count("hbr.org/2011/03/the-short-life-of-online-sales-leads")
        m = re.search(r'article:modified_time" content="([^"]+)', body)
        print(f"  {st} hbr_links={n} modified={m.group(1)[:10] if m else '?'}  {u.split('/blog-posts/')[1]}")

    leak = [r for r in rows if r["rule"] == "process_leak"]
    print(f"\n== Pipeline instructions published: {len(leak)} on Oct 14")
    for r in leak:
        st, _, body = get(r["url"])
        m = re.search(r"(tape inputs?|link dump|on-angle|this job, not)", r["evidence"], re.I)
        if not m:
            print(f"  {st} no known phrase in the Oct 14 evidence, not checked  {r['url']}")
            continue
        text = re.sub(r"<[^>]+>", " ", body)
        print(f"  {st} still_there={m.group(1).lower() in text.lower()} [{m.group(1)}]  "
              f"{r['url'].split('/blog-posts/')[1]}")
        print(f"     Oct 14 evidence: {r['evidence'][:150]}")

    dead = sorted({r["evidence"].split(" -> ")[0] for r in rows
                   if r["rule"] == "broken_internal_link" and " -> 404" in r["evidence"]})
    print(f"\n== Internal links that 404'd on Oct 14: {len(dead)} distinct, all re-checked")
    for u in dead:
        st, fin, _ = get(u)
        print(f"  now {st}{' -> ' + fin if fin != u else ''}  {u}")


if __name__ == "__main__":
    main(sys.argv[1])
