"""Polite, read-only HTTP for every tool in this repo.

- Honors each host's robots.txt.
- At least 2 s between live requests.
- Caches definitive answers (2xx, 3xx, 404, 410) for CACHE_TTL_S, 24 h by default, in .cache/, so re-runs
  don't hit the site again. Errors (network, 5xx, 429, 401/403) are never cached: the next run retries.
  The watcher and the pre-publish `check` set CACHE_TTL_S = 0: they always fetch today's page.
- Logs every request (live or cached) to .cache/fetch_log.csv.
"""
import csv
import hashlib
import http.client
import json
import os
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
        if st == 200:
            rp.parse(body.splitlines())
        elif isinstance(st, int) and st < 500 and st != 429:
            rp.parse([])  # RFC 9309: a 4xx robots.txt means no rules
        else:
            rp.parse(["User-agent: *", "Disallow: /"])  # 5xx, 429 or unreachable: stay off (RFC 9309)
        _robots[host] = rp
    return _robots[host].can_fetch(USER_AGENT, url)


def fetch(url):
    """Return (status, body, final_url). Never raises on HTTP errors; status is an int or a short string."""
    if not allowed(url):
        _log(url, "robots-disallowed", 0, False)
        return "robots-disallowed", "", url
    return _get(url)


def cacheable(status):
    """A definitive answer worth reusing: 2xx, 3xx, 404 or 410. Everything else (network, 5xx, 429, and
    401/403, which is what a bot block looks like) is retried instead of being remembered for a day."""
    return isinstance(status, int) and (200 <= status < 400 or status in (404, 410))


def _cached(key):
    """The cached response, or None if missing, expired or unreadable (a kill mid-write, a bad disk)."""
    if CACHE_TTL_S <= 0 or not key.exists():
        return None
    try:
        c = json.loads(key.read_text(encoding="utf-8"))
        if time.time() - c["fetched_at"] < CACHE_TTL_S and cacheable(c["status"]):
            return c
    except (ValueError, KeyError, TypeError, OSError):
        pass
    return None


def _get(url, retries=3):
    global _last_live
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    c = _cached(key)
    if c:
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
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            # OSError covers timeouts, resets and SSL errors; HTTPException covers IncompleteRead.
            status, body, note = "network-error", "", f"{type(e).__name__}: {e}, attempt {attempt + 1}"
        if attempt < retries - 1:
            time.sleep(DELAY_S * (2 ** attempt))  # back off before the next try (none after the last)
    if cacheable(status):
        tmp = key.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"url": url, "status": status, "body": body, "final_url": final,
                                   "fetched_at": time.time()}), encoding="utf-8")
        tmp.replace(key)  # atomic: a killed run never leaves half a cache file
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
