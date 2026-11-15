"""Sync GitHub issues with a watcher run. Runs in the GitHub Action, not on the box.

  python aeo_watch/issues.py path/to/issues.json   # needs GITHUB_TOKEN and GITHUB_REPOSITORY

One open issue per failing post, found by a hidden marker in its body:
- failing this run, open issue    -> comment with this run's findings
- failing this run, no open issue -> open one (a human-closed one is reopened as new only if it's still failing)
- failing earlier, never an issue -> open one (the backlog: posts over an earlier run's cap)
- passing or no longer live, open issue -> close it with a comment
New issues are capped at NEW_CAP per run so a full run can't flood the repo; the rest wait for the next run.
Comments are capped at COMMENT_CAP per run. Closing is driven by the whole state, never by one run alone.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aeo_watch import watch  # noqa: E402  (one wording for an AI answer, shared with the report)

LABEL = "aeo-watch"
NEW_CAP = 20
COMMENT_CAP = 30  # an `all` run re-checking hundreds of failing posts mustn't hit GitHub's secondary rate limit
API = "https://api.github.com"


def marker(url):
    return f"<!-- aeo-watch:{url} -->"


def url_of(body):
    s = (body or "").find("<!-- aeo-watch:")
    e = (body or "").find(" -->", s)
    if s < 0 or e < 0:
        return None
    return body[s + len("<!-- aeo-watch:"):e] or None


def quiet(s):
    """Scraped text goes into an issue body: break @mentions so a post can't notify a GitHub user."""
    return re.sub(r"@(?=[A-Za-z0-9])", "@​", str(s))


def findings_md(p):
    lines = [f"Checked {p['checked_at']} UTC: {p['url']}", ""]
    lines += [f"- **{h['name']}**: {quiet(h['evidence'])}" for h in p["hard"]]
    lines += [f"- AI (Parallel, unverified): {quiet(watch.ai_line(g))}" for g in p.get("suggestions", [])]
    return "\n".join(lines)


def when(s):
    """ISO time from the watcher ("2026-11-15T15:26+00:00") or GitHub ("2026-11-15T15:26:31Z"), or None."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def closable(p, by_url, updated, checked):
    """Close an open issue if this run re-checked the post, or (catching up after a lost sync) if the
    post's result is newer than the issue's last activity. A human reopening the issue is newer activity,
    so a reopened issue stays open until the post is re-checked again."""
    u = p["url"]
    if u not in by_url:
        return False
    if u in checked:
        return True
    a, b = when(p.get("checked_at")), when(updated.get(u))
    return bool(a and b and a > b)


def plan(issues, payload, cap=NEW_CAP, comment_cap=COMMENT_CAP):
    """issues: [{number, body, state}] with this label, open and closed. Returns (actions, skipped_new).
    Closing is never capped: it's what keeps the issue list true."""
    by_url = {url_of(i["body"]): i["number"] for i in issues
              if i.get("state", "open") == "open" and url_of(i["body"])}
    updated = {url_of(i["body"]): i.get("updated_at", "") for i in issues
               if i.get("state", "open") == "open" and url_of(i["body"])}
    checked = set(payload.get("checked", []))
    ever = {url_of(i["body"]) for i in issues}
    want = [p for p in payload["failing"] if p["url"] not in by_url]
    want += [p for p in payload.get("backlog", []) if p["url"] not in ever]
    # Comment only on news: a re-check that finds the same thing again would just be noise.
    comments = [p for p in payload["failing"] if p["url"] in by_url and p.get("news", True)]
    actions = [("comment", by_url[p["url"]], findings_md(p)) for p in comments[:comment_cap]]
    for p in want[:cap]:
        path = p["url"].split("singlegrain.com", 1)[-1]
        body = (findings_md(p) + "\n\nOpened by the AEO watcher. It closes this issue itself once the post "
                "passes the hard checks or is no longer live.\n" + marker(p["url"]))
        actions.append(("open", f"AEO hard failure: {path}", body))
    for p in payload["passing"]:
        if closable(p, by_url, updated, checked):
            why = ("The latest watcher run found no hard failures on this post. Closing."
                   if not p.get("labelled_old") else
                   "The post labels its pre-2020 stat as old (\"historical\", \"older\", \"not a current "
                   "benchmark\"), so it isn't presented as current: now a warning, not a hard failure. "
                   f"Hand-checked on the live page: {watch.HAND_CHECK}. Closing.")
            actions.append(("close", by_url[p["url"]], why))
    for g in payload.get("gone", []):
        if closable(g, by_url, updated, checked):
            where = f", now redirects to {quiet(g['final'])}" if g.get("final") and g["final"] != g["url"] else ""
            actions.append(("close", by_url[g["url"]],
                            f"The post is no longer live (status {g['status']}{where}). Closing."))
    return actions, max(0, len(want) - cap)


def gh(method, path, token, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def watcher_issues(repo, token):
    """Every issue with the label, open and closed."""
    out, page = [], 1
    while True:
        batch = gh("GET", f"/repos/{repo}/issues?state=all&labels={LABEL}&per_page=100&page={page}", token)
        out += [{"number": i["number"], "body": i.get("body") or "", "state": i["state"],
                 "updated_at": i.get("updated_at") or ""}
                for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            return out
        page += 1


def main(argv):
    token, repo = os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"]
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    try:
        gh("POST", f"/repos/{repo}/labels", token, {"name": LABEL, "color": "b42318"})
    except urllib.error.HTTPError as e:
        if e.code != 422:  # 422 = the label already exists
            raise
    actions, skipped = plan(watcher_issues(repo, token), payload)
    for kind, a, b in actions:
        if kind == "open":
            gh("POST", f"/repos/{repo}/issues", token, {"title": a, "body": b, "labels": [LABEL]})
        elif kind == "comment":
            gh("POST", f"/repos/{repo}/issues/{a}/comments", token, {"body": b})
        else:
            gh("POST", f"/repos/{repo}/issues/{a}/comments", token, {"body": b})
            gh("PATCH", f"/repos/{repo}/issues/{a}", token, {"state": "closed"})
        print(kind, a)
    if skipped:
        print(f"{skipped} failing posts wait for an issue (cap {NEW_CAP} per run); the next run opens them.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
