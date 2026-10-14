"""AEO shipped-post audit for singlegrain.com.

Checks what the AEO pipeline actually published against the gates Eric Siu described on camera,
plus a few objective defects. Every check says which it is. Read-only, public pages only.

  python aeo_audit/audit.py run [--since 2026-08-01]   # all /blog-posts/ updated since the date
  python aeo_audit/audit.py check <url-or-draft.html>  # gate one page; exit 1 on a hard failure
"""
import html
import json
import re
import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common.fetch import fetch, write_csv  # noqa: E402

SITE = "https://www.singlegrain.com"
RESULTS = ROOT / "results"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Sources are YouTube video IDs; "L" = line range in the auto-generated transcript, since the
# transcripts have no timestamps. 1jQJlxZNsFY is a re-edit of 45AWhSkkaQ4 and repeats these lines.
WEBINAR = "youtu.be/45AWhSkkaQ4"
TEAM = "youtu.be/O2D8DvQ6zWA"

# key: (name, source, his exact words, needs judgment, kind)
RULES = {
    "stale_source": ("Pre-2020 source", f"{WEBINAR} L635-639",
                     "a 2011 maybe that's a little too old right maybe I need to refine a little bit and say hey "
                     "we we only want stuff after 2020", False, "Eric, stated (as an intended fix)"),
    "video_not_embedded": ("His video linked, not embedded", f"{WEBINAR} L285-289",
                           "if Eric actually talked about this, and this is in a YouTube video, why don't we just "
                           "embed that part of the YouTube video inside of the blog post?", False,
                           "Eric, a gate he described (he also says 'sometimes it'll embed the video')"),
    "video_unavailable": ("Cited video does not resolve", f"{WEBINAR} L282-284",
                          "do you actually have real statistics to back this up or are you just making stuff up?",
                          False, "Eric, a gate he described"),
    "no_images": ("No images in the body", f"{WEBINAR} L289-291",
                  "are we putting in images in there as well", False, "Eric, a gate he described"),
    "unsourced_claim": ("Claimed stat with no link in its paragraph", f"{TEAM} L318-321",
                        "stats must already be named. They must be hyperl[inked]", False, "his team's criteria"),
    "process_leak": ("Pipeline instructions published as article text", "-", "", False,
                     "defect, not a stated rule"),
    "broken_internal_link": ("Internal link that 404s or redirects", "-", "", False, "defect, not a stated rule"),
    "repeated_passage": ("Same 15+ word passage in 3+ posts", f"{WEBINAR} L277-282",
                         "have we actually published this piece of content before? ... you don't want to publish "
                         "more duplicate content", False,
                         "defect (his gate is about repeating a topic; reused passages are an extension)"),
    "video_no_timestamp": ("Video link has no timestamp", f"{WEBINAR} L285-289", "embed that part of the YouTube video",
                           False, "defect (a reading of 'that part', not his words)"),
    "no_service_link": ("No link to a service page", f"{WEBINAR} L624-627",
                        "internal links to our services pages, right? ... Those are always helpful.", False,
                        "defect (he called them helpful, not a rule)"),
    "no_toc": ("No table of contents", f"{WEBINAR} L596-598",
               "here's a table of contents down here, which should probably honestly go higher", False,
               "defect (an observation, not a rule)"),
    "title_promise": ("Title promise drift", f"{TEAM} L318-319", "the title must pay a promise", True,
                      "his team's criteria"),
    "fake_reviews": ("Fake anonymized reviews", f"{TEAM} L342-344", "fake anonymized reviews", True,
                     "his team's criteria"),
    "robotic_voice": ("Robotic voice", f"{TEAM} L345", "robotic voice", True, "his team's criteria"),
}
HARD = {"stale_source", "video_unavailable"}  # `check` exits 1 on these

STAT = re.compile(r"\b\d+(?:\.\d+)?\s?%|\$\d[\d,.]*\s?(?:[kmb]|million|billion)?\b|\b\d+\s+(?:of|out of)\s+\d+\b", re.I)
ATTRIBUTION = re.compile(r"\b(study|studies|survey|report(?:ed|s)?|research|according to|found that|"
                         r"data (?:shows|show)|benchmark)\b", re.I)
YEAR = re.compile(r"\b(19[5-9]\d|20[01]\d)\b")
# Pipeline vocabulary that should never reach a reader. Seeded from text found live on 2026-10-13; extend as found.
PROCESS_LEAK = re.compile(r"\b(?:tape inputs?|link dump|on-angle|this job, not|as instructed|per the brief)\b", re.I)
YT = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([\w-]{11})([^\"'\s<]*)")
EMBED = re.compile(r"<iframe[^>]+youtube|lite-youtube|wp-block-embed-youtube")


# ---------------------------------------------------------------- page parsing

def article_html(page):
    """Post body: the first `<article class="container post-...">` up to its author box. Whole page if absent."""
    s = page.find('<article class="container post-')
    if s < 0:
        s = page.find("<article")
    if s < 0:
        return page
    e = page.find("</article>", s)
    body = page[s:e if e > 0 else len(page)]
    cut = body.find("Written By")
    return body[:cut] if cut > 0 else body


def strip(html_text):
    t = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", html_text)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def meta(page, prop):
    m = re.search(rf'<meta[^>]+(?:property|name)="{re.escape(prop)}"[^>]+content="([^"]*)"', page)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- lookups (cached per run)

_service_urls, _link_status, _videos = None, {}, {}


def service_urls():
    global _service_urls
    if _service_urls is None:
        st, xml, _ = fetch(f"{SITE}/service-sitemap.xml")
        _service_urls = {u.rstrip("/") for u in re.findall(r"<loc>([^<]+)</loc>", xml)} if st == 200 else set()
    return _service_urls


def is_service_url(u):
    path = u[len(SITE):] if u.startswith(SITE) else u
    return path.startswith(("/agency/", "/services/")) or u.rstrip("/") in service_urls()


def link_status(u):
    if u not in _link_status:
        st, _, final = fetch(u)
        _link_status[u] = (st, final)
    st, final = _link_status[u]
    return st == 200 and final.rstrip("/") == u.rstrip("/"), st, final


def video_info(vid):
    if vid not in _videos:
        q = urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}", safe="")
        st, body, _ = fetch(f"https://www.youtube.com/oembed?url={q}&format=json")
        info = {"status": st, "title": "", "author": ""}
        if st == 200:
            try:
                d = json.loads(body)
                info.update(title=d.get("title", ""), author=d.get("author_name", ""))
            except json.JSONDecodeError:
                info["status"] = "bad-json"
        _videos[vid] = info
    return _videos[vid]


# ---------------------------------------------------------------- audit one page

def audit_page(url, page):
    """Return (row, findings, sentences). findings = [(rule, evidence)]."""
    body = article_html(page)
    text = strip(body)
    sents = sentences(text)
    f = []

    for sent in sents:
        for y in YEAR.findall(sent):
            f.append(("stale_source", f"{y}: {sent[:240]}"))
        if PROCESS_LEAK.search(sent):
            f.append(("process_leak", sent[:240]))
    for href in re.findall(r'href="(https?://[^"]+)"', body):
        if "youtube" not in href and re.search(r"/(19[5-9]\d|20[01]\d)/", urllib.parse.urlparse(href).path):
            f.append(("stale_source", f"link {href}"))

    for _, inner in re.findall(r"(?s)<(p|li)\b[^>]*>(.*?)</\1>", body):
        if "<a " in inner:
            continue
        for sent in sentences(strip(inner)):
            if STAT.search(sent) and ATTRIBUTION.search(sent):
                f.append(("unsourced_claim", sent[:240]))

    vids = defaultdict(list)
    for vid, rest in YT.findall(body):
        vids[vid].append(rest)
    if vids and not EMBED.search(body):
        f.append(("video_not_embedded", f"{len(vids)} video(s) linked, 0 players embedded"))
    for vid, rests in vids.items():
        if not any(re.search(r"[?&#]t=|start=", r) for r in rests):
            f.append(("video_no_timestamp", f"https://www.youtube.com/watch?v={vid}"))
        info = video_info(vid)
        if info["status"] != 200:
            f.append(("video_unavailable", f"https://www.youtube.com/watch?v={vid} -> oEmbed {info['status']}"))

    links = {html.unescape(h).split("?")[0].split("#")[0]
             for h in re.findall(r'href="(https?://www\.singlegrain\.com[^"]*)"', body)}
    service_links = {u for u in links if is_service_url(u)}
    if not service_links:
        f.append(("no_service_link", f"{len(links)} internal links, none to /agency/, /services/ or the service sitemap"))
    for u in sorted(links):
        ok, st, final = link_status(u)
        if not ok:
            f.append(("broken_internal_link", f"{u} -> {st}" + ("" if final == u else f" (redirects to {final})")))

    if "auto-toc" not in body:
        f.append(("no_toc", "no auto-toc block"))
    n_img = len(re.findall(r"<img\b", body))
    if n_img == 0:
        f.append(("no_images", "0 <img> in body"))

    title = re.search(r"(?s)<title>(.*?)</title>", page)
    canonical = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', page)
    row = {
        "url": url,
        "segment": "flat" if url.startswith(SITE) and url.rstrip("/").count("/") == 4 else "nested",
        "title": strip(title.group(1)) if title else "",
        "published": meta(page, "article:published_time")[:10],
        "modified": meta(page, "article:modified_time")[:10],
        "words": len(text.split()),
        "canonical_self": "yes" if canonical and canonical.group(1).rstrip("/") == url.rstrip("/") else "no",
        "noindex": "yes" if "noindex" in meta(page, "robots").lower() else "no",
        "videos_linked": len(vids),
        "video_channels": "; ".join(sorted({video_info(v)["author"] or str(video_info(v)["status"]) for v in vids})),
        "service_links": len(service_links),
        "images": n_img,
    }
    for r, spec in RULES.items():
        row[r] = "" if spec[3] else sum(1 for k, _ in f if k == r)
    return row, f, sents


def repeated_passages(sents_by_url, min_words=15, min_posts=3):
    seen = defaultdict(set)
    for u, ss in sents_by_url.items():
        for s in ss:
            if len(s.split()) >= min_words:
                seen[re.sub(r"\W+", " ", s.lower()).strip()].add(u)
    return {k: v for k, v in seen.items() if len(v) >= min_posts}


# ---------------------------------------------------------------- inventory

def post_urls(since):
    """(url, lastmod) for every /blog-posts/ URL in the post sitemaps with lastmod >= since."""
    st, index, _ = fetch(f"{SITE}/sitemap_index.xml")
    if st != 200:
        sys.exit(f"sitemap index fetch failed: {st}")
    out = []
    for sm in re.findall(r"<loc>([^<]+/post-sitemap\d*\.xml)</loc>", index):
        st, xml, _ = fetch(sm)
        if st != 200:
            print(f"WARN {sm} -> {st}")
            continue
        for block in re.findall(r"(?s)<url>(.*?)</url>", xml):
            loc = re.search(r"<loc>([^<]+)</loc>", block)
            mod = re.search(r"<lastmod>([^<]+)</lastmod>", block)
            if loc and "/blog-posts/" in loc.group(1) and mod and mod.group(1)[:10] >= since:
                out.append((html.unescape(loc.group(1).strip()), mod.group(1)[:10]))
    return out


# ---------------------------------------------------------------- commands

def cmd_run(since):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = RESULTS / day / "aeo"
    posts = post_urls(since)
    print(f"auditing {len(posts)} /blog-posts/ URLs with sitemap lastmod >= {since}")
    rows, findings, sents_by_url = [], [], {}
    for url, _ in posts:
        st, page, final = fetch(url)
        if st != 200 or final.rstrip("/") != url.rstrip("/"):
            findings.append({"url": url, "rule": "not_a_live_post", "evidence": f"status {st}, final {final}"})
            continue
        row, f, sents = audit_page(url, page)
        rows.append(row)
        sents_by_url[url] = sents
        findings += [{"url": url, "rule": k, "evidence": e} for k, e in f]
    if not rows:
        sys.exit("no live posts found")

    repeated = repeated_passages(sents_by_url)
    for r in rows:
        r["repeated_passage"] = sum(1 for v in repeated.values() if r["url"] in v)
    for k, urls in sorted(repeated.items(), key=lambda kv: -len(kv[1])):
        findings.append({"url": f"{len(urls)} posts: " + " ".join(sorted(urls)), "rule": "repeated_passage",
                         "evidence": k[:240]})

    write_csv(out / "posts.csv", rows, list(rows[0].keys()))
    write_csv(out / "findings.csv", findings, ["url", "rule", "evidence"])
    write_report(out, rows, findings, since)


def write_report(out, rows, findings, since):
    n = len(rows)
    seg = {s: [r for r in rows if r["segment"] == s] for s in ("flat", "nested")}
    lines = [
        "# What shipped vs the rules: singlegrain.com /blog-posts/",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='minutes')} UTC on {n} live posts "
        f"(sitemap lastmod >= {since}). Public pages only.",
        "",
        "**flat** = `/blog-posts/<slug>/`, the format of the posts Eric showed on camera. "
        "**nested** = `/blog-posts/<category>/<slug>/`.",
        "",
        "| Check | Kind | Flat posts failing | Nested posts failing |",
        "|---|---|---|---|",
    ]
    for key, (name, src, quote, judgment, kind) in RULES.items():
        if judgment:
            lines.append(f"| {name} | {kind} | not checked (needs human labels first) | |")
            continue
        cells = []
        for s in ("flat", "nested"):
            k, m = sum(1 for r in seg[s] if r[key]), len(seg[s])
            cells.append(f"{k} of {m}" if m else "n/a")
        lines.append(f"| {name} | {kind} | {cells[0]} | {cells[1]} |")
    lines += ["", "## Where each check comes from", ""]
    lines += [f"- **{name}** ({kind}): \"{quote}\" ({src})" if quote else f"- **{name}** ({kind})"
              for name, src, quote, _, kind in RULES.values()]
    lines += ["", "## Examples (first 3 per check; all in findings.csv)", ""]
    by_rule = defaultdict(list)
    for f in findings:
        by_rule[f["rule"]].append(f)
    for rule, fs in by_rule.items():
        lines.append(f"### {RULES.get(rule, (rule,))[0]} ({len(fs)})")
        lines += [f"- {f['url'][:160]}: {f['evidence']}" for f in fs[:3]]
        lines.append("")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:lines.index("## Where each check comes from")]))
    print(f"-> {out}")


def cmd_check(target):
    path = Path(target)
    if path.exists():
        page, url = path.read_text(encoding="utf-8", errors="replace"), str(path)
    else:
        st, page, _ = fetch(target)
        if st != 200:
            sys.exit(f"fetch failed: {st}")
        url = target
    _, f, _ = audit_page(url, page)
    for k, e in f:
        print(f"{'FAIL' if k in HARD else 'warn'} {k}: {e}")
    hard = sum(1 for k, _ in f if k in HARD)
    print(f"\n{len(f)} findings, {hard} hard failures")
    return 1 if hard else 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "run":
        cmd_run(argv[argv.index("--since") + 1] if "--since" in argv else "2026-08-01")
        return 0
    if len(argv) == 3 and argv[1] == "check":
        return cmd_check(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
