"""Polite, read-only HTTP for every tool in this repo.

- Honors each host's robots.txt.
- At least 2 s between live requests.
- Caches every response for 24 h in .cache/ so re-runs don't hit the site again.
- Logs every request (live or cached) to .cache/fetch_log.csv.
"""
import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
LOG = CACHE / "fetch_log.csv"
USER_AGENT = "SingleGrainAEOAudit/1.0 (read-only; one request per 2s; github.com/VedantBhayani)"
DELAY_S = 2.0
CACHE_TTL_S = 24 * 3600

_last_live = 0.0
_robots = {}


def _log(url, status, nbytes, from_cache, note=""):
    CACHE.mkdir(parents=True, exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "url", "status", "bytes", "from_cache", "note"])
        w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), url, status, nbytes, from_cache, note])


def allowed(url):
    p = urllib.parse.urlparse(url)
    host = f"{p.scheme}://{p.netloc}"
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        st, body, _ = _get(host + "/robots.txt")
        rp.parse(body.splitlines() if st == 200 else [])
        _robots[host] = rp
    return _robots[host].can_fetch(USER_AGENT, url)


def fetch(url):
    """Return (status, body, final_url). Never raises on HTTP errors; status is an int or a short string."""
    if not allowed(url):
        _log(url, "robots-disallowed", 0, False)
        return "robots-disallowed", "", url
    return _get(url)


def _get(url, retries=3):
    global _last_live
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if key.exists():
        c = json.loads(key.read_text(encoding="utf-8"))
        if time.time() - c["fetched_at"] < CACHE_TTL_S:
            _log(url, c["status"], len(c["body"]), True)
            return c["status"], c["body"], c["final_url"]
    status, body, final, note = None, "", url, ""
    for attempt in range(retries):
        wait = DELAY_S - (time.time() - _last_live)
        if wait > 0:
            time.sleep(wait)
        _last_live = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=30) as r:
                status, final = r.status, r.geturl()
                body = r.read().decode("utf-8", errors="replace")
            note = ""
            break
        except urllib.error.HTTPError as e:
            status, note = e.code, f"http error, attempt {attempt + 1}"
            if e.code < 500 and e.code != 429:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            status, note = "network-error", f"{e}, attempt {attempt + 1}"
        time.sleep(DELAY_S * (2 ** attempt))
    key.write_text(json.dumps({"url": url, "status": status, "body": body, "final_url": final,
                               "fetched_at": time.time()}), encoding="utf-8")
    _log(url, status, len(body), False, note or (f"redirected to {final}" if final != url else ""))
    return status, body, final


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
