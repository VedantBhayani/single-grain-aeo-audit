"""Independent re-check of the Oct 14 claims against the live site. Plain urllib + substring search,
no code from the audit. 2 s between requests."""
import csv, re, time, urllib.request, urllib.error, sys

UA = {"User-Agent": "Mozilla/5.0 (verification re-check; 1 req/2s)"}
F = sys.argv[1]
rows = list(csv.DictReader(open(F, encoding="utf-8")))

def get(u):
    time.sleep(2)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, u, ""
    except Exception as e:
        return str(e)[:60], u, ""

hbr = sorted({r["url"] for r in rows if "hbr.org/2011" in r["evidence"]})
print(f"== HBR 2011 link: {len(hbr)} posts flagged on Oct 14")
for u in hbr:
    st, fin, body = get(u)
    n = body.count("hbr.org/2011/03/the-short-life-of-online-sales-leads")
    m = re.search(r'article:modified_time" content="([^"]+)', body)
    print(f"  {st} hbr_links={n} modified={m.group(1)[:10] if m else '?'}  {u.split('/blog-posts/')[1]}")

leak = [r for r in rows if r["rule"] == "process_leak"]
print(f"\n== Pipeline instructions published: {len(leak)} on Oct 14")
for r in leak:
    st, fin, body = get(r["url"])
    phrase = re.search(r"(tape inputs?|link dump|on-angle|this job, not)", r["evidence"], re.I).group(1)
    text = re.sub(r"<[^>]+>", " ", body)
    print(f"  {st} still_there={phrase.lower() in text.lower()} [{phrase}]  {r['url'].split('/blog-posts/')[1]}")
    print(f"     Oct 14 evidence: {r['evidence'][:150]}")

dead = sorted({r["evidence"].split(" -> ")[0] for r in rows if r["rule"] == "broken_internal_link" and " -> 404" in r["evidence"]})
print(f"\n== Internal links that 404'd on Oct 14: {len(dead)} distinct (re-checking up to 8)")
for u in dead[:8]:
    st, fin, _ = get(u)
    print(f"  now {st}{' -> ' + fin if fin != u else ''}  {u}")
