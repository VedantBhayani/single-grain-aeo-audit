"""Sync GitHub issues with a watcher run. Runs in the GitHub Action, not on the box.

  python aeo_watch/issues.py path/to/issues.json   # needs GITHUB_TOKEN and GITHUB_REPOSITORY

One open issue per failing post, found by a hidden marker in its body:
- failing, no open issue  -> open one (at most NEW_CAP per run, so a full run can't flood the repo)
- failing, open issue     -> comment with this run's findings
- passing, open issue     -> close it with a comment
"""
import json
import os
import sys
import urllib.error
import urllib.request

LABEL = "aeo-watch"
NEW_CAP = 20
API = "https://api.github.com"


def marker(url):
    return f"<!-- aeo-watch:{url} -->"


def url_of(body):
    s = (body or "").find("<!-- aeo-watch:")
    if s < 0:
        return None
    return body[s + len("<!-- aeo-watch:"):body.find(" -->", s)]


def findings_md(p):
    lines = [f"Checked {p['checked_at']} UTC: {p['url']}", ""]
    lines += [f"- **{h['name']}**: {h['evidence']}" for h in p["hard"]]
    for g in p.get("suggestions", []):
        src = ", ".join(x["url"] for x in g["sources"]) or "none found"
        lines.append(f"- AI suggestion (Parallel, p={g['p']}, unverified): newer data → {src}")
    return "\n".join(lines)


def plan(open_issues, payload, cap=NEW_CAP):
    """open_issues: [{number, body}]. Returns (actions, skipped_new)."""
    by_url = {url_of(i["body"]): i["number"] for i in open_issues if url_of(i["body"])}
    actions, new = [], 0
    for p in payload["failing"]:
        n = by_url.get(p["url"])
        if n:
            actions.append(("comment", n, findings_md(p)))
        elif new < cap:
            new += 1
            path = p["url"].split("singlegrain.com", 1)[-1]
            body = (findings_md(p) + "\n\nOpened by the AEO watcher. It closes this issue itself once the post "
                    "passes the hard checks.\n" + marker(p["url"]))
            actions.append(("open", f"AEO hard failure: {path}", body))
    skipped = sum(1 for p in payload["failing"] if not by_url.get(p["url"])) - new
    for u in payload["passing"]:
        if u in by_url:
            actions.append(("close", by_url[u], "The latest watcher run found no hard failures on this post. Closing."))
    return actions, skipped


def gh(method, path, token, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def open_issues(repo, token):
    out, page = [], 1
    while True:
        batch = gh("GET", f"/repos/{repo}/issues?state=open&labels={LABEL}&per_page=100&page={page}", token)
        out += [{"number": i["number"], "body": i.get("body") or ""} for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            return out
        page += 1


def main(argv):
    token, repo = os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"]
    payload = json.loads(open(argv[1], encoding="utf-8").read())
    try:
        gh("POST", f"/repos/{repo}/labels", token, {"name": LABEL, "color": "b42318"})
    except urllib.error.HTTPError as e:
        if e.code != 422:  # 422 = the label already exists
            raise
    actions, skipped = plan(open_issues(repo, token), payload)
    for kind, a, b in actions:
        if kind == "open":
            gh("POST", f"/repos/{repo}/issues", token, {"title": a, "body": b, "labels": [LABEL]})
        elif kind == "comment":
            gh("POST", f"/repos/{repo}/issues/{a}/comments", token, {"body": b})
        else:
            gh("POST", f"/repos/{repo}/issues/{a}/comments", token, {"body": b})
            gh("PATCH", f"/repos/{repo}/issues/{a}", token, {"state": "closed"})
        print(kind, a if kind != "open" else a)
    if skipped:
        print(f"{skipped} failing posts got no new issue this run (cap {NEW_CAP}); they're on the dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
