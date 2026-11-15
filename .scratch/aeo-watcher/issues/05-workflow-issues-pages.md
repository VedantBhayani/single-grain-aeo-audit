Type: task
Status: resolved
Blocked by: 02, 04

## Question

Build the GitHub Action:
- runs daily at 15:00 UTC, plus a manual run with a mode input
- wakes the box and runs the watcher there
- copies the outputs back
- commits the outputs to `results/`
- syncs one issue per post that hard-fails
- publishes `index.html` to Pages

## Answer

`.github/workflows/aeo-watch.yml`: daily 15:00 UTC, plus a manual run with mode and since inputs. It wakes the box and resets its repo copy to origin, runs box_run.sh as a background job, waits up to 100 min, copies aeo-out.tgz back, commits `results/watch/<day>/`, runs `aeo_watch/issues.py` (one issue per post, found by marker, new issues capped at 20 per run, auto-close) and deploys `index.html` to Pages. Pages is enabled (build_type workflow): https://vedantbhayani.github.io/single-grain-aeo-audit/. Not yet run in Actions: it needs the INSTABOX_API_KEY secret (ticket 03).
