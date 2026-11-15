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

Out of this ticket (judged not worth it before the call): splitting Pages permissions into its own job, the `${{ }}`-in-shell cleanup, the duplicated "newer data" line, the evidence-string coupling to audit.py, same-day runs sharing one results folder (git history keeps both).
