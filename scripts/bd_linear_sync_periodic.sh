#!/usr/bin/env bash
# bd_linear_sync_periodic.sh — Agency_OS-iosu.
#
# Cron-driven wrapper around `bd linear sync --pull --threshold 5m`. Closes the
# "Linear data is Xh stale" warning loop that long-running agent sessions hit
# because the session-start sync drifts during multi-hour work.
#
# Fail-open: a single sync miss should never crash the timer. systemd retries
# on the next tick. Exit 0 always.

set -u

LOG_FILE="${BD_LINEAR_SYNC_LOG:-/home/elliotbot/clawd/logs/bd-linear-sync.log}"
mkdir -p "$(dirname "$LOG_FILE")"

if ! command -v bd >/dev/null 2>&1; then
    echo "$(date -u +%FT%TZ) bd_linear_sync_periodic: bd CLI not on PATH — skipping" >>"$LOG_FILE"
    exit 0
fi

echo "$(date -u +%FT%TZ) bd_linear_sync_periodic: starting" >>"$LOG_FILE"
bd linear sync --pull --threshold 5m >>"$LOG_FILE" 2>&1 || true
echo "$(date -u +%FT%TZ) bd_linear_sync_periodic: done (exit=$?)" >>"$LOG_FILE"
exit 0
