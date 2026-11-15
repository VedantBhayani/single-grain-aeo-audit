Type: task
Status: claimed
Blocked by: 06 (the live run it reviews; the hand check can run in parallel)

## Question

A two-axis review (Standards + Spec) of 0cc83c1...HEAD, run on Nov 15, found that the watcher works on a good day but fails silently on a bad one. Fix the defects that make it quietly do the wrong thing, each with an offline test, and make every README claim match the code. (AFK, override in the map's Notes.)

In scope:
1. A post that crashes the check is recorded and skipped, never left at the head of the queue (poison pill). A malformed Parallel answer can't crash a post.
2. The watcher fetches pages fresh (the shared 24 h cache made Run 2, 52 s for 97 posts, a re-score of cached pages). A transient error (network, 5xx, 429, robots) is never marked "seen", so it's retried next run.
3. A post that is no longer live closes its issue with a comment and is listed on the dashboard.
4. The dashboard and README state the 2026-10-14 baseline. A failing post that got no issue (over the cap, or failing before this run) gets one on a later run; one a human closed is not reopened unless it is re-checked and still fails.
5. Only http(s) links from Parallel reach the dashboard. Marker parsing returns nothing when the marker is broken.
6. Two box runs can't overlap (a lock in box_run.sh), because a timed-out job keeps running on the box.
7. README claims match the code. Run `new` mode live once.

## Progress

- Round 1 (1fe6181): items 1-7. Live: `new` run at 15:02 checked 0 posts (nothing changed), no duplicate issues.
- Round 2 (f8c847b): Vedant asked for everything, so the "not worth it" list below was done too: Pages rights in their own job, no `${{ }}` in shell, one results folder per run, robots.txt per RFC 9309 in common/fetch, verify_live.py polite and re-run (same results, all 10 404s), @mentions quieted, one AI wording. Live: `since 2026-11-10` run checked 14 posts in 4m50s (fresh fetches; Run 2's 97 in 52 s was the cache).
- Round 3 (whole-repo review): a 403/401 no longer closes issues (only 404/410/redirect is "gone"); a failed YouTube check is never a hard failure (video_unchecked, retried); errored posts are retried in every mode via a retry list; a failing post that leaves the sitemap is re-checked; closing is computed from the whole state; comments capped; the box lock also guards the code update; the instabox key only reaches box steps; common/fetch never caches errors, survives a corrupt cache file, writes atomically, catches IncompleteRead/SSL; `audit.py check` fetches fresh; `--since` with no date is a usage error; tracking guard keeps last snapshot's pages and alerts when a sitemap fails, rebases before push, alerts even if the commit fails; dead redirect branch removed; tests.yml read-only. The three runs that shared one folder were restored byte-for-byte into their own folders. Every fix has a test; reverting each fix makes a test fail (mutation check).

Left on purpose, with reasons:
- Actions pinned to major tags, not SHAs: all are GitHub's own actions; SHA pinning adds upkeep with little gain for a read-only repo.
- robots.txt not re-checked after a redirect: urllib follows redirects before we can ask; the redirect targets here are the same site.
- Status as int-or-string, result dicts built in three places, audit's evidence strings parsed by the watcher: refactors, not defects; a test now pins the evidence format so drift fails loudly.
- The pre-publish gate is stricter than the watcher on prose years: deliberate (a draft is cheap to fix; a public issue isn't), documented in the README.

Out of this ticket (judged not worth it before the call; later done in round 2 at Vedant's request): splitting Pages permissions into its own job, the `${{ }}`-in-shell cleanup, the duplicated "newer data" line, the evidence-string coupling to audit.py, same-day runs sharing one results folder (git history keeps both).
