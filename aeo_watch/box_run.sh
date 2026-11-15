#!/usr/bin/env bash
# Runs on the instabox machine. The GitHub Action pulls the repo, then starts this as a background job.
#   bash aeo_watch/box_run.sh [--mode new|all|since] [--since YYYY-MM-DD]
# State and the Parallel key live on the persistent disk, outside the repo:
#   $AEO_HOME/aeo-state/state.json   seen posts, queue, results
#   $AEO_HOME/aeo.env                PARALLEL_API_KEY=...  (written by Vedant, never committed)
# AEO_HOME defaults to /data/home (the box's persistent disk); tests point it at a temp folder.
set -euo pipefail
cd "$(dirname "$0")/.."
H=${AEO_HOME:-/data/home}
export AEO_STATE="$H/aeo-state" AEO_ENV_FILE="$H/aeo.env"
OUT="$H/aeo-out"
# One run at a time on the box: a job the Action stopped waiting for keeps running here.
exec 9>"$H/aeo.lock"
flock -n 9 || { echo "another watcher run is still going on this box; not starting a second one"; exit 75; }
rm -rf "$OUT" "$H/aeo-out.tgz"
python3 aeo_watch/watch.py run --out "$OUT" "$@"
tar czf "$H/aeo-out.tgz" -C "$H" aeo-out
echo "outputs: $H/aeo-out.tgz"
