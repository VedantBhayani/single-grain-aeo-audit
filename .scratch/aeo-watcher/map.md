# Map: AEO watcher

Labels: wayfinder:map

## Destination

The existing AEO audit runs every day by itself on one instabox box (free plan). Each run checks only new or updated singlegrain.com posts, and a full run of all posts is available on demand. Hard failures become GitHub issues, every run is committed to `results/`, and a dashboard page shows the latest run. Parallel adds one AI step: it suggests a newer source for pre-2020 stats. It must be live, with real findings, before the Shaun Merritt call (Tue Nov 17 / Wed Nov 18, 2026).

## Notes

- Domain: `aeo_audit/audit.py` (the 10 rule checks, unchanged), `common/fetch.py` (polite fetcher), `.github/workflows/tracking-guard.yml` (the scheduling pattern to copy). Parallel usage follows `USE_CASES.md` #5 in github.com/VedantBhayani/jev-vs-parallel.
- Skills: grilling and domain-modeling for open decisions; vocabulary is in `GLOSSARY.md`.
- **Override (approved by Vedant, Nov 15):** this map carries execution. A settled ticket may be built in the same session, and several tickets may be resolved per session because of the deadline.
- Standing rules:
  - read-only on Single Grain's sites: respect robots.txt and wait 2 s between requests
  - nothing is sent to Single Grain
  - Claude never reads API keys: they live in `.env` on the box and in GitHub secrets, both set by Vedant
  - Python standard library only
  - every new piece gets an offline test
  - scope is "schedule it and tweak it", not a new system

## Decisions so far

- Grilling, Nov 15 (accepted; trimmed later the same day):
  - **Trigger:** a GitHub Actions schedule wakes the box with `instabox exec`, and the audit runs on the box. Daily at 15:00 UTC, plus a manual button.
  - **Scope:** a scheduled run checks posts that are new or updated since the last run. A manual run can choose `all` (every `/blog-posts/` URL) or `since <date>`. The first run covers posts since 2026-10-14.
  - **Checks:** the existing 10 rules, unchanged.
  - **AI:** Parallel runs only on pre-2020 years found in a stat or study sentence, or in a linked URL's path, capped at 25 per run. Its link is shown as "suggested newer source, check it". It is a warning, never a hard failure.
  - **Alerts:** the Action opens one issue per post that hard-fails, using GitHub's own built-in token. A repeat failure gets a comment; a fixed post's issue closes.
  - **Output:** a dated report committed to `results/`, and a dashboard on GitHub Pages as the main link.
  - **Box:** template `agent-browser`, name `aeo-watcher`. Code goes in `aeo_watch/` in this repo.
  - **Cut:** the Jev duplicate-topic check, and escalating to Parallel when Jev is unsure (unmeasured; not enough time).

## Not yet specified

- Whether the box also serves the dashboard at its own URL; this depends on ticket 01.
- How an exact "updated" post is detected (sitemap lastmod vs body hash); settle while building ticket 04.

## Out of scope

- A pre-publish gate on WordPress drafts: it needs Single Grain's access. This is the day-one proposal for the call.
- Messaging Single Grain about findings.
- The Jev duplicate-topic check and Parallel for company facts.
- Changes to the tracking guard.
