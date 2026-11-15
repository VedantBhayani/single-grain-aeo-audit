Type: research
Status: resolved
Blocked by: 01

## Question

Using an instabox API key, can a GitHub Action:
- wake the paused box
- run a job longer than the 10-minute limit on a single exec command
- wait for that job to finish
- copy the results back

What are the exact commands that work, and what does a cooled-down box look like to the Action?

## Answer

Tested 2026-11-15 from the laptop CLI (instabox 0.8.274). An Action does the same with `INSTABOX_API_KEY` set.
- Start: `instabox exec --background --json aeo-watcher -- '<cmd>'` prints `{jobId, pid}`; the job has no time limit.
- Wait: `instabox jobs wait aeo-watcher <job> --timeout 100m` exits with the job's exit code (124 on timeout). Tested: a 20 s job waited 20 s and returned exit 0.
- Logs: `instabox jobs logs aeo-watcher <job>`.
- Files out: `instabox cp aeo-watcher:/data/home/aeo-out.tgz .`. Bundle the outputs into one tarball on the box.
- exec wakes a paused box (it waits up to 45 s to resume). In cooldown, exec is refused with 409 machine_cooldown: the Action fails loudly and tomorrow's run tries again.
- **Constraint found:** on the free plan a run has 120 min, then a cooldown. A full run of every post takes hours (2 s per request), so it **can't finish in one run**. The watcher must keep a queue and a time budget (75 min), saving progress per post and continuing on the next run.
