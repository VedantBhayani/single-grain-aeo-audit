# Single Grain AEO audit

Two read-only tools built for Single Grain, run on its public pages:

1. **[AEO post audit + pre-publish gate](aeo_audit/):** checks what the AEO pipeline published on singlegrain.com against what Eric Siu said on camera, plus a source-date check, and blocks a draft before it ships if it fails a hard check.
2. **[Tracking guard](tracking_guard/):** snapshots the tracking tags, forms and index signals on singlegrain.com, singlebrain.com and clickflow.com every week, and alerts when one disappears.

By Vedant Bhayani. Built with Claude Code, which wrote most of the code. I chose the problem and had every Oct 14 finding re-checked against the live pages and the transcripts before trusting it. The watcher's daily findings are machine output: leads to check, not verdicts.

## AEO watcher: the audit, every day, on its own

[`aeo_watch/`](aeo_watch/) runs the audit's checks every day on a small cloud machine (instabox, free plan). Only the two hard checks (a pre-2020 cited source, a cited video that doesn't resolve) open issues; the other checks are recorded as warnings in each run's `run.json` (and shown on the dashboard under failing posts).

- **Which posts:** by default, posts whose sitemap date changed since the last run, starting from posts modified on or after 2026-10-14. Older posts are checked only when a manual run chooses `all` (every `/blog-posts/` post) or `since <date>`. A big run that hits its 75-minute budget saves its place, and the next run carries on, unless the machine is in its free-plan cooldown; then that day's run fails loudly in Actions and nothing is lost.
- **Pages are fetched fresh** every run (the repo's fetch cache is off for the watcher). A post that can't be checked keeps its last result and is retried on the next run, whatever its date; it never blocks the queue. "Can't be checked" means a network error, robots.txt, a 5xx, a 429, a 401/403 (what a bot block looks like), a YouTube check that failed, or a crash in the check. Only a 404, a 410 or a redirect away counts as "no longer live".
- **One change to the rules:** a pre-2020 year in plain prose ("operating since 2008") is a warning here, not a hard failure, because the watcher opens public issues. A pre-2020 year in a stat or study sentence, or in a linked URL, is still hard. The pre-publish gate (`audit.py check`) stays stricter and blocks both.
- **One AI step:** for those stat or study years, Parallel's Decisions API is asked whether newer data exists, and its sources are shown as suggestions to check. Capped at 25 requests per run (about $0.025, assuming $0.001 a request; not from billing), answers cached, never a hard failure.
- **Output:** a GitHub issue per failing post, at most 20 new ones per run (the rest open on later runs). A re-checked post that still fails gets a comment (at most 30 a run). An issue closes when that post's latest result passes or it's no longer live; a failing post that drops out of the sitemap is re-checked to find out. Closing is worked out from all results, so a run whose issue sync failed is caught up by the next one. Each run's log goes to its own folder in [`results/watch/`](results/watch/), and the dashboard to GitHub Pages.
- **How it runs:** a GitHub Action ([`aeo-watch.yml`](.github/workflows/aeo-watch.yml)) wakes the machine at 15:00 UTC (GitHub may start scheduled runs late) and starts the run there. A lock on the machine stops a second run, and the code update, while one is still going. The state and the key stay on the machine's disk; the machine's key is given only to the steps that talk to it.

```bash
python aeo_watch/watch.py run                                   # new or updated posts
python aeo_watch/watch.py run --mode all                        # everything (spans several runs)
python aeo_watch/watch.py run --mode since --since 2026-10-14   # from a date
```

Limits: it checks public posts **after** they're published, because it can't see drafts. With WordPress draft access, the same checks become a gate before publishing. Parallel's suggestions are unverified leads, not fixes.

## Results, 2026-10-14

**AEO audit:** 48 `/blog-posts/` pages updated since Aug 1, of which 40 are in the flat `/blog-posts/<slug>/` format Eric showed on camera. Full report: [`results/2026-10-14/aeo/report.md`](results/2026-10-14/aeo/report.md).

| What | Flat posts |
|---|---|
| Cite the 2011 Harvard Business Review lead study Eric read out on camera, where he said "maybe I need to refine a little bit and say, hey, we only want stuff after 2020" (AEO webinar, published Oct 1). All 9 link the same study. | **9 of 40** |
| Publish the pipeline's own instructions to readers ("…three on-angle Eric tape inputs for this job, not a link dump.") | **4 of 40** |
| Link to internal pages that return 404, including `/agency/managed-marketing-agents/` (8 more only link to old addresses that redirect and still work) | **11 of 40** |
| Link Eric's videos instead of embedding them | 28 of 40 |
| Cite a video that doesn't exist | 0 of 40 |

The newest post, `/blog-posts/seedance-2-0-ai-video-ads/` (Oct 13), passes every hard check.

**Re-checked Nov 15 with separate code:** all 9 HBR links and all 4 pipeline-instruction leaks are still live a month later, and all 10 internal links that 404'd still 404. See [`results/2026-11-15/verification.md`](results/2026-11-15/verification.md).

**Tracking guard:** 251 pages across 4 sites. Full report: [`results/2026-10-14/tracking/report.md`](results/2026-10-14/tracking/report.md).
- Every live singlegrain.com page carries GTM-K3ZSFV; singlebrain.com and clickflow.com carry theirs.
- gateway.singlebrain.com has no tracking tag in its served HTML on any of its 4 pages. It may track server-side, so this is a question, not a verdict.
- 49 sitemap URLs redirect elsewhere and 2 case studies in the sitemap return 404.

## Run it

Python 3.10+, standard library only, nothing to install.

```bash
python aeo_audit/audit.py run --since 2026-08-01      # site-wide audit  -> results/<date>/aeo/
python aeo_audit/audit.py check path/to/draft.html    # gate one draft   -> exit 1 = don't publish
python tracking_guard/guard.py run                    # snapshot + diff  -> results/<date>/tracking/
python -m unittest discover -s tests                  # offline tests
```

## How it behaves on someone else's site

- Read-only: no logins, no forms submitted, nothing written anywhere.
- Honors each site's robots.txt (RFC 9309: a 4xx robots.txt means no rules, a 5xx or no answer means stay off) and waits at least 2 seconds between requests.
- Caches definitive answers for 24 hours in `.cache/` (not committed); errors and rate limits are never cached. The watcher and the pre-publish `check` always fetch fresh. Every request is logged to `.cache/fetch_log.csv`.

## Limits

- **Public pages only.** I can't see Search Console, analytics, drafts, or who or what wrote each post. "The AEO pipeline's posts" means posts in the flat format Eric showed on camera.
- **The checks are text and link rules, with no AI in them,** so the same page always gives the same answer. Three judgment checks from his team's review (title promise, fake reviews, robotic voice) are not scored, because that would need hand-labelled posts first.
- **"The video exists" doesn't mean the video says what the post claims.**
- **The tracking guard reads the HTML the server sends.** Tags injected later by JavaScript don't show up.

## Layout

```
common/fetch.py           polite fetcher: robots.txt, 2 s delay, 24 h cache of definitive answers, request log
aeo_audit/audit.py        audit + gate; skill/SKILL.md tells an agent when and how to run the gate
aeo_watch/watch.py        daily watcher: new posts only, queue + time budget, Parallel step, dashboard
aeo_watch/issues.py       one GitHub issue per failing post (runs in the Action)
aeo_watch/box_run.sh      what the Action starts on the instabox machine
tracking_guard/guard.py   snapshot + diff
tests/                    offline unit tests (fake fetcher, handwritten HTML)
results/                  dated reports and snapshots; the weekly and daily workflows add to these
.github/workflows/        tests on every push; tracking guard every Monday; AEO watcher daily
```
