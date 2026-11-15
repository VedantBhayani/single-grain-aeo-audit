Type: task
Status: resolved
Blocked by:

## Question

Create `aeo-watcher` from `agent-browser` on the free plan, then find out and record:
- the Python version
- whether the box can make outbound HTTPS requests to www.singlegrain.com and api.parallel.ai
- the path of the persistent disk

## Answer

Created 2026-11-15 13:13 UTC: `aeo-watcher` (m_agq56v2vx46zj5kbn5glitb5im), agent-browser 2026-11-14.2815, 4 vCPU / 8 GiB, free. maxRunMinutes 120, auto-suspend 30 min (fixed on free).
- Python 3.13.5; git 2.47.3; gh 2.102.0.
- Persistent disk `/data` (20 GiB, 16 GiB free); HOME is `/data/home`.
- Outbound HTTPS works: singlegrain.com robots.txt 200, YouTube oEmbed 200, github.com 200, api.parallel.ai 401 (reachable, no key sent).
- instabox has its own Secrets (`--secret-env`), but they're fixed at create; we use a `.env` on /data instead (ticket 03).
