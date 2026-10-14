"""Tracking guard: snapshot the tracking tags, forms and index signals on Eric Siu's public sites and
alert when a later run differs.

Built for a failure Eric described on camera: an AI CRO loop "started to make changes to the site
and it removed tags and it removed uh analytics codes" (youtu.be/tcgfrAAgRK4, transcript L1171-1176).

  python tracking_guard/guard.py run          # snapshot + diff vs the latest snapshot; exit 1 on ALERT
  python tracking_guard/guard.py diff OLD NEW  # diff two snapshot files

Reads the HTML the server sends. Tags injected later by JavaScript are not visible here, so a page
with no tags in its HTML is reported as a question, not as broken.
"""
import html
import json
import re
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common.fetch import fetch  # noqa: E402

RESULTS = ROOT / "results"
SNAPS = RESULTS / "snapshots"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Page lists come from each site's sitemap. singlegrain.com post sitemaps are left out on purpose:
# its ~2,700 posts share one template, so the page + service sitemaps cover every template that matters.
SOURCES = [
    "https://www.singlegrain.com/page-sitemap.xml",
    "https://www.singlegrain.com/service-sitemap.xml",
    "https://singlebrain.com/sitemap.xml",
    "https://gateway.singlebrain.com/sitemap.xml",
    "https://clickflow.com/sitemap.xml",
]
# Pages Eric sends people to that are not in those sitemaps (checked 2026-10-13).
EXTRA_PAGES = [
    "https://www.singlegrain.com/",
    "https://www.singlegrain.com/contact-us/",
    "https://www.singlegrain.com/apply/",
    "https://www.singlegrain.com/careers/",
    "https://www.singlegrain.com/skills/",
    "https://www.singlebrain.com/gateway",
    "https://www.singlegrain.com/agency/aeo-services/",
    "https://www.singlegrain.com/agency/ai-seo-services/",
]

TRACKERS = {
    "hubspot": r"js\.hs-scripts\.com|js\.hsforms\.net|js\.hs-analytics\.net",
    "meta_pixel": r"connect\.facebook\.net/[^\"']*fbevents\.js|fbq\(\s*['\"]init",
    "linkedin_insight": r"snap\.licdn\.com|_linkedin_partner_id",
    "vercel_analytics": r"/_vercel/insights|va\.vercel-scripts\.com",
    "posthog": r"posthog\.init|i\.posthog\.com",
    "segment": r"cdn\.segment\.com",
    "clarity": r"clarity\.ms/tag",
    "plausible": r"plausible\.io/js",
}
WATCHED = ["status", "redirected", "gtm", "ga4", "ua", "trackers", "forms", "form_actions", "canonical", "noindex"]


def norm(u):
    return u.replace("://www.", "://").rstrip("/")


def facts(url):
    st, body, final = fetch(url)
    f = {"status": st, "final_url": final, "redirected": norm(final) != norm(url)}
    if st != 200 or not body:
        return f
    m_title = re.search(r"(?s)<title[^>]*>(.*?)</title>", body)
    canonical = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', body)
    robots_meta = re.search(r'<meta[^>]+name="robots"[^>]+content="([^"]*)"', body)
    f.update(
        title=" ".join(html.unescape(m_title.group(1)).split()) if m_title else "",
        gtm=sorted(set(re.findall(r"GTM-[A-Z0-9]{4,10}", body))),
        ga4=sorted(set(re.findall(r"\bG-[A-Z0-9]{8,12}\b", body))),
        ua=sorted(set(re.findall(r"\bUA-\d{4,10}-\d{1,3}\b", body))),
        trackers=sorted(k for k, pat in TRACKERS.items() if re.search(pat, body, re.I)),
        forms=len(re.findall(r"<form\b", body)),
        form_actions=sorted({html.unescape(a) for a in re.findall(r"<form\b[^>]*\baction=\"([^\"]*)\"", body)}),
        canonical=canonical.group(1) if canonical else "",
        noindex="noindex" in (robots_meta.group(1).lower() if robots_meta else ""),
        js_app=bool(re.search(r"__NEXT_DATA__|/_next/static|id=\"__nuxt\"", body)),
    )
    f["any_tracking"] = bool(f["gtm"] or f["ga4"] or f["ua"] or f["trackers"])
    return f


def discover():
    """{url: 'sitemap' | 'manual'}, de-duplicated across www/non-www and trailing slashes."""
    pages = {}
    for sm in SOURCES:
        st, xml, _ = fetch(sm)
        if st != 200:
            print(f"WARN {sm} -> {st}")
            continue
        for u in re.findall(r"<loc>([^<]+)</loc>", xml):
            u = html.unescape(u.strip())
            pages.setdefault(norm(u), (u, "sitemap"))
    for u in EXTRA_PAGES:
        pages.setdefault(norm(u), (u, "manual"))
    return {u: src for u, src in pages.values()}


def diff(old, new):
    """[(level, url, field, old, new)]. ALERT = something tracking- or index-relevant was lost or changed."""
    alerts = []
    for url, n in new.items():
        o = old.get(url)
        if o is None:
            continue
        for k in WATCHED:
            if o.get(k) == n.get(k):
                continue
            level = "INFO"
            if k in ("gtm", "ga4", "ua", "trackers") and set(o.get(k) or []) - set(n.get(k) or []):
                level = "ALERT"
            elif k == "noindex" and n.get(k):
                level = "ALERT"
            elif k == "forms" and (n.get(k) or 0) < (o.get(k) or 0):
                level = "ALERT"
            elif k in ("status", "form_actions", "canonical", "redirected"):
                level = "ALERT"
            alerts.append((level, url, k, o.get(k), n.get(k)))
    for url in set(old) - set(new):
        alerts.append(("INFO", url, "page", "present", "no longer listed"))
    return alerts


def baseline(snap):
    """What a single snapshot already shows, before any change."""
    out = []
    sites = {}
    for url, f in snap.items():
        sites.setdefault(urllib.parse.urlparse(url).netloc.replace("www.", ""), []).append((url, f))
    for items in sites.values():
        gtms = Counter(g for _, f in items for g in f.get("gtm", []))
        main = gtms.most_common(1)[0][0] if gtms else None
        for url, f in items:
            if f["status"] == "robots-disallowed":
                out.append((f"listed ({f.get('source', '?')}) but blocked by robots.txt, not checked", url, ""))
            elif f["status"] != 200:
                out.append(("not 200", url, str(f["status"])))
            elif f["redirected"]:
                if norm(f["final_url"]) == norm(url):
                    out.append(("www / non-www redirect only (low priority)", url, f["final_url"]))
                else:
                    out.append((f"listed ({f.get('source', '?')}) but redirects", url, f["final_url"]))
            else:
                if not f["any_tracking"]:
                    out.append(("no tracking tag in served HTML" + (" (JS app)" if f.get("js_app") else ""), url, ""))
                elif main and f["gtm"] and main not in f["gtm"]:
                    out.append(("different GTM container from the rest of its site", url, f"{f['gtm']} vs {main}"))
                if f.get("noindex"):
                    out.append(("noindex", url, ""))
    return out


def write_report(snap, alerts, prev_name, findings, path):
    sites = Counter(urllib.parse.urlparse(u).netloc.replace("www.", "") for u in snap)
    lines = [
        "# Tracking guard",
        "",
        f"Run {datetime.now(timezone.utc).isoformat(timespec='minutes')} UTC: {len(snap)} pages ("
        + ", ".join(f"{s} {n}" for s, n in sites.items()) + ").",
        f"Compared with: {prev_name or 'nothing, first run (baseline)'}.",
        "",
        f"## Changes since last run: {sum(a[0] == 'ALERT' for a in alerts)} alerts, "
        f"{sum(a[0] == 'INFO' for a in alerts)} info",
        "",
    ]
    lines += [f"- **{lvl}** {url} `{k}`: {o} -> {n}" for lvl, url, k, o, n in alerts] or ["- none"]
    lines += ["", "## Tags per site (served HTML)", "",
              "| Site | Live pages | GTM | GA4 in HTML | Other trackers |", "|---|---|---|---|---|"]
    for s in sites:
        live = [f for u, f in snap.items() if urllib.parse.urlparse(u).netloc.replace("www.", "") == s
                and f["status"] == 200 and not f["redirected"]]
        cnt = lambda key: dict(Counter(x for f in live for x in f.get(key, []))) or "-"  # noqa: E731
        lines.append(f"| {s} | {len(live)} | {cnt('gtm')} | {cnt('ga4')} | {cnt('trackers')} |")
    lines += ["", f"## What this snapshot shows ({len(findings)})", ""]
    lines += [f"- {kind}: {url} {extra}".rstrip() for kind, url, extra in sorted(findings)] or ["- nothing"]
    lines += ["", "GA4 loaded through GTM does not appear in served HTML; the GTM container is what's checked there."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"-> {path}")


def cmd_run():
    pages = discover()
    print(f"{len(pages)} pages")
    snap = {}
    for i, (u, src) in enumerate(pages.items(), 1):
        snap[u] = facts(u)
        snap[u]["source"] = src
        if i % 50 == 0:
            print(f"  {i}/{len(pages)}")
    SNAPS.mkdir(parents=True, exist_ok=True)
    prev = sorted(SNAPS.glob("*.json"))
    old = json.loads(prev[-1].read_text(encoding="utf-8")) if prev else {}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    (SNAPS / f"{stamp}.json").write_text(json.dumps(snap, indent=1, sort_keys=True), encoding="utf-8")
    alerts = diff(old, snap) if old else []
    out = RESULTS / stamp[:10] / "tracking"
    out.mkdir(parents=True, exist_ok=True)
    write_report(snap, alerts, prev[-1].name if prev else "", baseline(snap), out / "report.md")
    return 1 if any(a[0] == "ALERT" for a in alerts) else 0


def main(argv):
    if argv[1:2] == ["run"]:
        return cmd_run()
    if argv[1:2] == ["diff"] and len(argv) == 4:
        old = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        new = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
        alerts = diff(old, new)
        for a in alerts:
            print(*a)
        return 1 if any(a[0] == "ALERT" for a in alerts) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
