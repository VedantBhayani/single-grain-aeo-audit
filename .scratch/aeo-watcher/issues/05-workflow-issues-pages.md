Type: task
Status: open
Blocked by: 02, 04

## Question

Build the GitHub Action:
- runs daily at 15:00 UTC, plus a manual run with a mode input
- wakes the box and runs the watcher there
- copies the outputs back
- commits the outputs to `results/`
- syncs one issue per post that hard-fails
- publishes `index.html` to Pages
