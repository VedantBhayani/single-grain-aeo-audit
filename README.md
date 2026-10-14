# Single Grain AEO audit

Two read-only tools built for Single Grain, run on its public pages:

1. **[AEO post audit + pre-publish gate](aeo_audit/):** checks what the AEO pipeline published on singlegrain.com against the gates Eric Siu described on camera, and blocks a draft before it ships if it fails one.
2. **[Tracking guard](tracking_guard/):** snapshots the tracking tags, forms and index signals on singlegrain.com, singlebrain.com and clickflow.com every week, and alerts when one disappears.

By Vedant Bhayani. Built with Claude Code. I chose what to check, then verified every finding by hand against the live pages and the transcripts.

## Results, 2026-10-14

**AEO audit:** 48 `/blog-posts/` pages updated since Aug 1, of which 40 are in the flat `/blog-posts/<slug>/` format Eric showed on camera. Full report: [`results/2026-10-14/aeo/report.md`](results/2026-10-14/aeo/report.md).

| What | Flat posts |
|---|---|
| Cite a 2011 source after Eric said "we only want stuff after 2020" (Sep 30). All 9 link the same Harvard Business Review lead study he read out on camera. | **9 of 40** |
| Publish the pipeline's own instructions to readers ("…three on-angle Eric tape inputs for this job, not a link dump.") | **4 of 40** |
| Link to internal pages that 404 or redirect, including `/agency/managed-marketing-agents/` | **19 of 40** |
| Link Eric's videos instead of embedding them | 28 of 40 |
| Cite a video that doesn't exist | 0 of 40 |

The newest post, `/blog-posts/seedance-2-0-ai-video-ads/` (Oct 13), passes every hard check.

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
- Honors each site's robots.txt and waits at least 2 seconds between requests.
- Caches every page for 24 hours in `.cache/` (not committed) and logs every request to `.cache/fetch_log.csv`.

## Limits

- **Public pages only.** I can't see Search Console, analytics, drafts, or who or what wrote each post. "The AEO pipeline's posts" means posts in the flat format Eric showed on camera.
- **The checks are text and link rules, with no AI in them,** so the same page always gives the same answer. Three judgment checks from his team's review (title promise, fake reviews, robotic voice) are not scored, because that would need hand-labelled posts first.
- **"The video exists" doesn't mean the video says what the post claims.**
- **The tracking guard reads the HTML the server sends.** Tags injected later by JavaScript don't show up.

## Layout

```
common/fetch.py           polite fetcher: robots.txt, 2 s delay, 24 h cache, request log
aeo_audit/audit.py        audit + gate; skill/SKILL.md tells an agent when and how to run the gate
tracking_guard/guard.py   snapshot + diff
tests/                    offline unit tests (fake fetcher, handwritten HTML)
results/                  dated reports and snapshots; the weekly workflow adds to these
.github/workflows/        tests on every push; tracking guard every Monday
```
