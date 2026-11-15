Type: task
Status: claimed
Blocked by:

## Question

What is the smallest `aeo_watch/` that does all of the following, with offline tests for each part?
- runs in `new` mode (since the last run), `all` mode or `since <date>` mode
- keeps its state on the box
- reuses `audit_page` unchanged
- adds the Parallel newer-source suggestion (filtered, capped at 25)
- writes `run.json`, `report.md`, `issues.json` and `index.html`
