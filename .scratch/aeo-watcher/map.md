# Map: AEO watcher

Labels: wayfinder:map

## Destination

The existing AEO audit runs every day by itself on one instabox box (free plan). Each run checks only new or updated singlegrain.com posts, and a full run of all posts is available on demand. Hard failures become GitHub issues, every run is committed to `results/`, and a dashboard page shows the latest run. Parallel adds one AI step: it suggests a newer source for pre-2020 stats. It must be live, with real findings, before the Shaun Merritt call (Tue Nov 17 / Wed Nov 18, 2026).

## Notes

- Domain: `aeo_audit/audit.py` (the rule checks; the watcher's one change is in "Decisions so far"), `common/fetch.py` (polite fetcher), `.github/workflows/tracking-guard.yml` (the scheduling pattern to copy). Parallel usage follows `USE_CASES.md` #5 in github.com/VedantBhayani/jev-vs-parallel.
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
  - **Checks:** the existing rules. Changed after the first live run (ce951a9): a pre-2020 year in plain prose is a warning in the watcher, not a hard failure; the pre-publish gate stays strict.
  - **AI:** Parallel runs only on pre-2020 years found in a stat or study sentence, or in a linked URL's path, capped at 25 per run. Its link is shown as "suggested newer source, check it". It is a warning, never a hard failure.
  - **Alerts:** the Action opens one issue per post that hard-fails, using GitHub's own built-in token. A repeat failure gets a comment; a fixed post's issue closes.
  - **Output:** a dated report committed to `results/`, and a dashboard on GitHub Pages as the main link.
  - **Box:** template `agent-browser`, name `aeo-watcher`. Code goes in `aeo_watch/` in this repo.
  - **Cut:** the Jev duplicate-topic check, and escalating to Parallel when Jev is unsure (unmeasured; not enough time).
- [Create box and prove it reaches the site](issues/01-create-box-and-prove-it-reaches-the-site.md): aeo-watcher is up; Python 3.13, /data persists, outbound HTTPS works.
- [Can a GitHub Action drive the box](issues/02-can-a-github-action-drive-the-box.md): yes, with exec --background, jobs wait and cp. The 120-min free run means a full run must queue over several days.
- [Watcher code](issues/04-watcher-code.md): built and tested. "Updated" means the sitemap lastmod changed (simple, and no body storage). A box test checked 14 posts with 0 hard failures.
- [Workflow, issues, Pages](issues/05-workflow-issues-pages.md): built; Pages enabled; the first Actions run waits on the keys.
- [Keys on the box and in GitHub, unread](issues/03-keys-on-the-box-and-in-github-unread.md): both set by Vedant; checked by presence, mode and size only, never the value.
- [First live run and hand check](issues/06-first-live-run-and-hand-check.md): Vedant hand-checked all 10 findings: 0 wrong, 5 real, 5 where the post labels the old stat as old; a rule now makes those warnings. Headline: 5 real problems.
- [Hardening from the two-axis review](issues/07-hardening-from-the-two-axis-review.md): three review rounds; an error never closes an issue or blocks the queue, closing comes from the whole state, pages fetched fresh, least privilege in the workflow.

## Not yet specified

- Nothing open. The map is done; the next step is the call.

## Out of scope

- A pre-publish gate on WordPress drafts: it needs Single Grain's access. This is the day-one proposal for the call.
- Messaging Single Grain about findings.
- The Jev duplicate-topic check and Parallel for company facts.
- Changes to the tracking guard.
- The box serving its own dashboard URL: Pages is the only link, which is simpler and can't be in cooldown.
