#!/usr/bin/env bash
# Runs on the instabox machine. The GitHub Action pulls the repo, then starts this as a background job.
#   bash aeo_watch/box_run.sh [--mode new|all|since] [--since YYYY-MM-DD]
# State and the Parallel key live on the persistent disk, outside the repo:
#   /data/home/aeo-state/state.json   seen posts, queue, results
#   /data/home/aeo.env                PARALLEL_API_KEY=...  (written by Vedant, never committed)
set -euo pipefail
cd "$(dirname "$0")/.."
export AEO_STATE=/data/home/aeo-state AEO_ENV_FILE=/data/home/aeo.env
OUT=/data/home/aeo-out
# One run at a time on the box: a job the Action stopped waiting for keeps running here.
exec 9>/data/home/aeo.lock
flock -n 9 || { echo "another watcher run is still going on this box; not starting a second one"; exit 75; }
rm -rf "$OUT" /data/home/aeo-out.tgz
python3 aeo_watch/watch.py run --out "$OUT" "$@"
tar czf /data/home/aeo-out.tgz -C /data/home aeo-out
echo "outputs: /data/home/aeo-out.tgz"
