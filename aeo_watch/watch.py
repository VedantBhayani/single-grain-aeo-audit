"""AEO watcher: the existing audit, on a schedule, on new or updated posts (or all, or since a date).

  python aeo_watch/watch.py run                       # new or updated posts since the last run
  python aeo_watch/watch.py run --mode all            # every /blog-posts/ post (spans several runs)
  python aeo_watch/watch.py run --mode since --since 2026-10-14
  python aeo_watch/watch.py run ... --budget-min 75 --out DIR

The rule checks are aeo_audit.audit_page. One change: a pre-2020 year in plain prose (not in a
stat or study sentence, not in a link) is a warning here, not a hard failure, because the watcher
opens public issues. The one AI step: for a pre-2020 year in a sentence that cites a stat or study
(or in a linked URL's path), Parallel is asked whether newer data exists, and its sources are shown
as suggestions to check. It is never a hard failure.

State (seen posts, queue, results) lives in AEO_STATE (default .state/ in the repo; /data on the box),
so a run that hits its time budget leaves the rest queued and the next run carries on. A post that
can't be checked (network, robots, 5xx, 429, 401/403, a crash, or a failed YouTube check on a post with
no other hard failure) keeps its last result, goes on the retry list, and is tried every run until a
check succeeds. Only 404/410 or a redirect away means "no longer live".
"""
import argparse
import html
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aeo_audit import audit  # noqa: E402
from common import fetch as fetch_mod  # noqa: E402

FIRST_RUN_SINCE = "2026-10-14"  # the day of the last manual audit
PARALLEL_URL = "https://api.parallel.ai/v1/decisions"
PARALLEL_USD = 0.001            # assumed price per request, for the cost estimate (not from billing)
PARALLEL_CAP = 25               # requests per run, at most
NEWER_Q = ("A credible source published in 2020 or later gives data on the same claim "
           "as this sentence or source.")


# ---------------------------------------------------------------- state

def state_dir():
    return Path(os.environ.get("AEO_STATE") or ROOT / ".state")


def load_state(d):
    p = d / "state.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"baseline": None, "seen": {}, "queue": [], "retry": [], "posts": {}, "parallel_cache": {}, "runs": []}


def save_state(d, st):
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / "state.json")  # atomic: a killed run never leaves half a file


# ---------------------------------------------------------------- which posts

def candidates(mode, since, posts, st):
    """posts: [(url, lastmod)]. Returns the URLs this run should check, oldest change first."""
    if mode == "all":
        picked = posts
    elif mode == "since":
        picked = [(u, m) for u, m in posts if m >= since]
    else:  # new: changed since we last saw it, and not older than the first run's baseline
        base = st["baseline"]
        picked = [(u, m) for u, m in posts if m >= base and st["seen"].get(u) != m]
    urls = [u for u, _ in sorted(picked, key=lambda x: (x[1], x[0]))]
    # Every mode also re-tries posts that errored last time (whatever their date), and re-checks a failing
    # post that left the sitemap: a deleted post usually drops out, so its lastmod never changes again.
    listed = {u for u, _ in posts}
    urls += st.get("retry", [])
    urls += sorted(u for u, p in st["posts"].items() if p.get("hard") and u not in listed)
    return list(dict.fromkeys(urls))


def enqueue(st, urls):
    q = st["queue"]
    have = set(q)
    q += [u for u in urls if u not in have]


# ---------------------------------------------------------------- the one AI step

def env_key(name):
    if os.environ.get(name):
        return os.environ[name]
    f = Path(os.environ.get("AEO_ENV_FILE", ROOT / ".env"))
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == name and v.strip():
                return v.strip().strip('"').strip("'")
    return None


def stale_claims(findings):
    """The stale_source findings worth asking about: a stat or study sentence, or a dated link path."""
    out = []
    for rule, ev in findings:
        if rule != "stale_source":
            continue
        if ev.startswith("link "):
            out.append(ev)
            continue
        sent = ev.split(": ", 1)[-1]
        if audit.STAT.search(sent) or audit.ATTRIBUTION.search(sent):
            out.append(ev)
    return list(dict.fromkeys(out))


def ask_parallel(key, claim, page_url, today):
    body = json.dumps({"state": {"claim": claim, "found_on": page_url, "today": today},
                       "questions": {"newer": {"type": "noul", "instructions": NEWER_Q}}}).encode()
    req = urllib.request.Request(PARALLEL_URL, data=body, method="POST",
                                 headers={"x-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


SHOW_AT = 0.5  # below this Parallel is saying "no newer data", so its citations are not suggestions


def bare(u):
    """URL without scheme, query, fragment or trailing slash, for comparing sources."""
    return re.sub(r"^https?://(www\.)?", "", u.split("#")[0].split("?")[0]).rstrip("/").lower()


def suggestion(resp, old_sources):
    """Parallel's answer -> {p, sources}. Sources only when p >= SHOW_AT, and never singlegrain.com,
    the old source itself (any query string), or an archived copy of it."""
    resp = resp if isinstance(resp, dict) else {}
    newer = (resp.get("answers") if isinstance(resp.get("answers"), dict) else {}).get("newer")
    p = newer.get("noul") if isinstance(newer, dict) else None
    p = round(p, 2) if isinstance(p, (int, float)) and not isinstance(p, bool) else None
    if p is None or p < SHOW_AT:
        return {"p": p, "sources": []}
    olds = {bare(o) for o in old_sources}
    src = []
    cites = resp.get("citations")
    for c in cites if isinstance(cites, list) else []:
        if not isinstance(c, dict):
            continue
        u = str(c.get("url") or "")
        b = bare(u)
        if (not re.match(r"https?://", u, re.I)  # third-party data goes into an href: http(s) only
                or "singlegrain.com" in b or b in olds or any(o and o in b for o in olds if "web.archive.org" in b)):
            continue
        src.append({"url": u, "title": str(c.get("title") or "")[:140]})
    return {"p": p, "sources": src[:3]}


class Parallel:
    """Capped, cached, and never fatal: an error stops the AI step for this run, not the run."""

    def __init__(self, key, cache, cap=PARALLEL_CAP, ask=ask_parallel):
        self.key, self.cache, self.cap, self.ask = key, cache, cap, ask
        self.calls, self.skipped = 0, None if key else "no PARALLEL_API_KEY on the box"

    def newer(self, claim, page_url, today, old_sources=()):
        hit = self.cache.get(claim)
        if isinstance(hit, dict) and "raw" in hit:  # the raw answer is cached, so filters can change later
            return suggestion(hit["raw"], old_sources)
        if self.skipped:
            return None
        if self.calls >= self.cap:
            self.skipped = f"cap of {self.cap} requests reached"
            return None
        try:
            self.calls += 1
            raw = self.ask(self.key, claim, page_url, today)
        except (urllib.error.URLError, http.client.HTTPException, ValueError, OSError) as e:
            # HTTPException covers a connection dropped mid-answer: the AI step stops, the post doesn't.
            self.skipped = f"Parallel error: {str(e)[:120]}"
            return None
        self.cache[claim] = {"raw": raw}
        return suggestion(raw, old_sources)


# ---------------------------------------------------------------- check one post

def transient(status):
    """Anything except 200, 404 and 410 means "couldn't check": network, robots, 5xx, 429, and 401/403,
    which is what a bot block looks like. Only a 404/410 or a redirect away says a post is gone, so a
    Cloudflare block can never close an issue."""
    return status not in (200, 404, 410)


def not_checked(url, lastmod, status, note=""):
    return {"url": url, "lastmod": lastmod, "live": False, "status": str(status), "retry": True,
            "note": note, "hard": [], "warn": [], "suggestions": []}


def check_post(url, lastmod, ai, today):
    st, page, final = audit.fetch(url)
    if transient(st):
        return not_checked(url, lastmod, st)
    if st != 200 or final.rstrip("/") != url.rstrip("/"):
        return {"url": url, "lastmod": lastmod, "live": False, "status": str(st), "final": final,
                "hard": [], "warn": [], "suggestions": []}
    row, f, _ = audit.audit_page(url, page)
    unchecked = [e for k, e in f if k == "video_unchecked"]
    cited = set(stale_claims(f))
    if unchecked and not any(k in audit.HARD and (k != "stale_source" or e in cited) for k, e in f):
        # A video we couldn't check could be this post's only hard failure: don't call it clean, retry.
        return not_checked(url, lastmod, "video-unchecked", unchecked[0])
    hard, warn = [], []
    for k, e in f:
        if k == "stale_source" and e not in cited:
            # A pre-2020 year in plain prose ("operating since 2008", an example sentence) is not a source.
            # The watcher opens public issues, so only a cited stat/study or a dated link counts as hard.
            warn.append({"rule": k, "name": "Pre-2020 year, not a cited stat", "evidence": e})
        elif k in audit.HARD:
            hard.append({"rule": k, "name": audit.RULES[k][0], "evidence": e})
        else:
            warn.append({"rule": k, "name": audit.RULES[k][0], "evidence": e})
    old_links = [c[5:] for c in cited if c.startswith("link ")]
    sugg = []
    for claim in stale_claims(f):
        s = ai.newer(claim, url, today, old_links)
        if s is not None:
            sugg.append({"claim": claim, **s})
    # Failing anyway, so record it; but the unchecked video still needs checking: keep it on the retry list.
    return {"url": url, "lastmod": lastmod, "live": True, "title": row["title"],
            "published": row["published"], "modified": row["modified"],
            "hard": hard, "warn": warn, "suggestions": sugg, "recheck": bool(unchecked)}


# ---------------------------------------------------------------- run

def run(mode="new", since=None, budget_min=75.0, out=None, posts=None, ai=None,
        clock=time.monotonic, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    d = state_dir()
    st = load_state(d)
    if mode == "since" and not since:
        sys.exit("--mode since needs --since YYYY-MM-DD")
    if st["baseline"] is None or (mode == "new" and since and not st["seen"]):
        # Where `new` mode starts tracking: 2026-10-14, or the date a first `new` run was given.
        # A `since` or `all` run checks old posts without moving it.
        st["baseline"] = since if mode == "new" and since else FIRST_RUN_SINCE

    sitemap_errors = []
    if posts is None:
        posts = audit.post_urls("0")  # every /blog-posts/ URL with a lastmod
        sitemap_errors = [f"{u} -> {s}" for u, s in audit.sitemap_errors]
    lastmod = dict(posts)
    enqueue(st, candidates(mode, since, posts, st))
    ai = ai or Parallel(env_key("PARALLEL_API_KEY"), st["parallel_cache"])

    start, checked = clock(), []
    while st["queue"] and (clock() - start) < budget_min * 60:
        url = st["queue"][0]
        prev = st["posts"].get(url)
        try:
            res = check_post(url, lastmod.get(url, ""), ai, today)
        except Exception as e:  # one bad post must never stop this run and every run after it
            res = not_checked(url, lastmod.get(url, ""), "check-error", f"{type(e).__name__}: {e}"[:200])
        res["checked_at"] = now.isoformat(timespec="minutes")
        res["was_failing"] = bool(prev and prev.get("hard"))
        # News for the issue: a first result, different hard findings, or an edit that didn't fix it.
        # A re-check that finds exactly the same thing again (a retry, an unlisted post) isn't news.
        res["news"] = (not prev or prev.get("hard") != res["hard"] or prev.get("lastmod") != res["lastmod"])
        retry, since_ = st.setdefault("retry", []), st.setdefault("retry_since", {})
        if not res.get("retry"):  # a real result: store it (an error keeps the last real one)
            st["posts"][url] = res
            st["seen"][url] = lastmod.get(url, "")
        if res.get("retry") or res.get("recheck"):  # tried again next run; the dashboard says since when
            if url not in retry:
                retry.append(url)
            since_.setdefault(url, today)
        elif url in retry:
            retry.remove(url)
            since_.pop(url, None)
        st["queue"].pop(0)
        checked.append(res)
        save_state(d, st)  # progress survives a pause, a cooldown or a kill

    summary = {
        "run_at": now.isoformat(timespec="minutes"), "mode": mode, "since": since, "baseline": st["baseline"],
        "checked": len(checked), "queued_left": len(st["queue"]),
        "failing_now": sum(1 for p in st["posts"].values() if p.get("hard")),
        "new_failures": sum(1 for p in checked if p["hard"] and not p["was_failing"]),
        "fixed": sum(1 for p in checked if p["live"] and not p["hard"] and p["was_failing"]),
        "not_live": sum(1 for p in checked if not p["live"] and not p.get("retry")),
        "retry_next_run": sum(1 for p in checked if p.get("retry")),
        "cannot_check": len(st.get("retry", [])),  # all posts on the retry list, whatever run put them there
        "parallel_calls": ai.calls, "parallel_cost_usd": round(ai.calls * PARALLEL_USD, 3),
        "ai_note": ai.skipped,
        "sitemap_errors": sitemap_errors,  # post sitemaps that failed: their posts weren't seen this run
    }
    st["runs"] = (st["runs"] + [summary])[-60:]
    save_state(d, st)
    if out:
        write_outputs(Path(out), summary, checked, st)
    return summary, checked, st


# ---------------------------------------------------------------- outputs

def issues_payload(checked, st):
    """What the GitHub side needs. Built from the whole state, not just this run, so if an earlier
    run's issue sync never happened (a timeout, a failed push), this run still closes what it should.
    failing: checked this run and failing (comment on its issue, or open one)
    backlog: failing in the state but not checked this run (open an issue only if it never had one)
    passing / gone: passing, or no longer live, by the latest result for each post (close its issue)"""
    def row(p):
        return {"url": p["url"], "title": p.get("title", ""), "hard": p["hard"], "news": p.get("news", True),
                "suggestions": p.get("suggestions", []), "checked_at": p.get("checked_at", "")}
    now = {p["url"] for p in checked if not p.get("retry")}
    posts = sorted(st["posts"].items())
    return {"checked": sorted(now),
            "failing": [row(p) for p in checked if p["hard"]],
            "backlog": [row(p) for u, p in posts if p.get("hard") and u not in now],
            "passing": [{"url": u, "checked_at": p.get("checked_at", "")}
                        for u, p in posts if p.get("live") and not p.get("hard")],
            "gone": [{"url": u, "status": p.get("status", ""), "final": p.get("final", ""),
                      "checked_at": p.get("checked_at", "")} for u, p in posts if not p.get("live")]}


def report_md(summary, checked):
    s = summary
    lines = [f"# AEO watcher run, {s['run_at']} UTC", "",
             f"Mode `{s['mode']}`{' since ' + s['since'] if s['since'] else ''}. "
             f"Checked {s['checked']} posts; {s['queued_left']} still queued for the next run.", "",
             f"- Failing now (all tracked posts): **{s['failing_now']}**",
             f"- New failures this run: {s['new_failures']} · fixed this run: {s['fixed']} · not live: {s['not_live']}"
             f" · errors, retried next run: {s['retry_next_run']}"
             f" · on the retry list in total: {s['cannot_check']}",
             f"- Tracks posts modified on or after {s['baseline']}; older posts are checked only by an `all` "
             "or `since` run.",
             f"- Parallel: {s['parallel_calls']} requests, ${s['parallel_cost_usd']}"
             + (f" ({s['ai_note']})" if s["ai_note"] else "")]
    if s.get("sitemap_errors"):
        lines.append("- **Post sitemaps that failed (their posts weren't seen this run):** "
                     + "; ".join(s["sitemap_errors"]))
    lines.append("")
    for p in checked:
        if p.get("retry"):
            mark = f"error ({p['status']}{', ' + p['note'] if p.get('note') else ''}), retried next run"
        else:
            mark = "FAIL" if p["hard"] else ("pass" if p["live"] else f"not live ({p['status']})")
        lines.append(f"## {mark}: {p['url']}")
        for h in p["hard"]:
            lines.append(f"- **{h['name']}**: {h['evidence']}")
        for sg in p["suggestions"]:
            lines.append(f"- AI (Parallel): {ai_line(sg)} · `{sg['claim'][:120]}`")
        if p["warn"]:
            lines.append(f"- {len(p['warn'])} warnings (see run.json)")
        lines.append("")
    return "\n".join(lines) + "\n"


def ai_line(sg, text=str, link=lambda x: x["url"]):
    """One honest line per Parallel answer: the single wording for the report, issues and dashboard.
    The dashboard passes text=esc and a link that renders an <a>."""
    if not sg["sources"]:
        return text(f"no newer data found (p={sg['p']})")
    return text(f"newer data likely (p={sg['p']}), check: ") + ", ".join(link(x) for x in sg["sources"])


def esc(s):
    return html.escape(str(s or ""))


def dashboard(summary, st):
    posts = sorted(st["posts"].values(), key=lambda p: p.get("checked_at", ""), reverse=True)
    failing = [p for p in posts if p.get("hard")]
    passing = [p for p in posts if p.get("live") and not p.get("hard")]
    gone = [p for p in posts if not p.get("live")]
    stuck = [(u, st.get("retry_since", {}).get(u, "?")) for u in st.get("retry", [])]
    s = summary
    base = st.get("baseline") or FIRST_RUN_SINCE

    def card(p):
        hard = "".join(f"<li><b>{esc(h['name'])}</b>: {esc(h['evidence'])}</li>" for h in p["hard"])
        sugg = "".join(
            f"<li><span class=ai>AI</span> <q>{esc(g['claim'][:160])}</q>: "
            + ai_line(g, text=esc, link=lambda x: f"<a href='{esc(x['url'])}'>{esc(x['title'] or x['url'])}</a>")
            + "</li>"
            for g in p.get("suggestions", []))
        warn = "".join(f"<li>{esc(w['name'])}: {esc(w['evidence'])}</li>" for w in p.get("warn", []))
        return (f"<article><h3><a href='{esc(p['url'])}'>{esc(p.get('title') or p['url'])}</a></h3>"
                f"<p class=meta>modified {esc(p.get('modified'))} · checked {esc(p.get('checked_at'))}</p>"
                f"<ul>{hard}{sugg}</ul>"
                + (f"<details><summary>{len(p['warn'])} warnings</summary><ul>{warn}</ul></details>" if warn else "")
                + "</article>")

    rows = "".join(f"<li><a href='{esc(p['url'])}'>{esc(p.get('title') or p['url'])}</a> "
                   f"<span class=meta>{esc(p.get('checked_at'))}</span></li>" for p in passing)
    gone_rows = "".join(f"<li>{esc(p['url'])} <span class=meta>status {esc(p.get('status'))}"
                        + (f" → {esc(p['final'])}" if p.get("final") and p["final"] != p["url"] else "")
                        + f" · checked {esc(p.get('checked_at'))}</span></li>" for p in gone)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>AEO Watcher</title>
<style>
:root{{--bg:#fbfbfa;--fg:#1b1b1a;--mute:#6b6b66;--line:#e4e4e0;--bad:#b42318;--ai:#5b4bdb;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111112;--fg:#ededea;--mute:#9a9a94;--line:#2a2a2c;--bad:#f97066;--ai:#a99cff;--card:#18181a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:880px;margin:0 auto;padding:24px 16px}} a{{color:inherit}}
h1{{margin:0 0 4px;font-size:26px}} .meta{{color:var(--mute);font-size:13px;margin:0}}
.stats{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}} .stats div{{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:10px 14px}}
.stats b{{display:block;font-size:22px}} .bad b{{color:var(--bad)}}
article{{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:12px 16px;margin:12px 0;overflow-wrap:anywhere}}
article h3{{margin:0 0 2px;font-size:16px}} li{{margin:4px 0}} .ai{{color:var(--ai);font-weight:700;font-size:12px}}
footer{{color:var(--mute);font-size:13px;border-top:1px solid var(--line);margin-top:28px;padding-top:12px}}
</style></head><body><main>
<h1>AEO Watcher · singlegrain.com</h1>
<p class=meta>Last run {esc(s['run_at'])} UTC · mode {esc(s['mode'])} · runs daily on an instabox machine</p>
<p class=meta>Tracks posts modified on or after {esc(base)}. Older posts are checked only by a manual
<code>all</code> or <code>since</code> run, so older failures are not counted here until one runs.</p>
{''.join(f"<p class=meta><b>Sitemap failed this run:</b> {esc(e)}</p>" for e in s.get('sitemap_errors') or [])}
<div class=stats>
<div class=bad><b>{s['failing_now']}</b>posts failing a hard check</div>
<div><b>{len(passing)}</b>passing</div>
<div><b>{s['checked']}</b>checked this run</div>
<div><b>{s['queued_left']}</b>queued for next run</div>
<div><b>${s['parallel_cost_usd']}</b>AI cost this run</div>
</div>
<h2>Failing</h2>{''.join(card(p) for p in failing) or '<p>None.</p>'}
<h2>Passing</h2><details><summary>{len(passing)} posts</summary><ul>{rows}</ul></details>
<h2>Not live</h2>{f'<details><summary>{len(gone)} posts (404 or redirected)</summary><ul>{gone_rows}</ul></details>' if gone else '<p>None.</p>'}
<h2>Couldn't check</h2>{('<p class=meta>Retried every run. Until one succeeds, each keeps its last result above.</p><ul>'
  + ''.join(f"<li>{esc(u)} <span class=meta>since {esc(d)}</span></li>" for u, d in stuck) + '</ul>') if stuck else '<p>None.</p>'}
<footer>Hard checks are text and link rules with no AI: a pre-2020 source, a cited video that doesn't resolve.
<span class=ai>AI</span> lines are Parallel's suggested newer sources: unverified, check before using.
Public pages only, checked after publishing. Read-only, robots.txt respected, 2 s between requests.
Code: github.com/VedantBhayani/single-grain-aeo-audit</footer>
</main></body></html>
"""


def write_outputs(out, summary, checked, st):
    out.mkdir(parents=True, exist_ok=True)
    (out / "run.json").write_text(json.dumps({"summary": summary, "posts": checked}, indent=1,
                                             ensure_ascii=False), encoding="utf-8")
    (out / "report.md").write_text(report_md(summary, checked), encoding="utf-8")
    (out / "issues.json").write_text(json.dumps(issues_payload(checked, st), indent=1, ensure_ascii=False),
                                     encoding="utf-8")
    (out / "index.html").write_text(dashboard(summary, st), encoding="utf-8")


def main(argv):
    ap = argparse.ArgumentParser(prog="watch.py")
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--mode", choices=["new", "all", "since"], default="new")
    ap.add_argument("--since")
    ap.add_argument("--budget-min", type=float, default=75.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    if a.since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.since):
        sys.exit("--since must be YYYY-MM-DD")
    fetch_mod.CACHE_TTL_S = 0  # the watcher's job is today's page: never serve the shared 24 h cache
    summary, _, _ = run(a.mode, a.since, a.budget_min, a.out)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
