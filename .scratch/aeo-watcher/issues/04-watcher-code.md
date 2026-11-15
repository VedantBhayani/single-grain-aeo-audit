Type: task
Status: resolved
Blocked by:

## Question

What is the smallest `aeo_watch/` that does all of the following, with offline tests for each part?
- runs in `new` mode (since the last run), `all` mode or `since <date>` mode
- keeps its state on the box
- reuses `audit_page` unchanged
- adds the Parallel newer-source suggestion (filtered, capped at 25)
- writes `run.json`, `report.md`, `issues.json` and `index.html`

## Answer

`aeo_watch/watch.py` (modes new/all/since, a queue with a 75-min budget, atomic state saves after every post, Parallel step filtered and capped at 25 and cached, outputs run.json/report.md/issues.json/index.html) and `aeo_watch/box_run.sh`. 13 new offline tests; 30/30 pass. Box test 2026-11-15 13:23 UTC: mode since 2026-11-10 checked 14 posts in about 4 min with 0 hard failures. The AI step skipped cleanly with no key. One bug was found on the box and fixed (ea55f7b): the env path was a directory.
