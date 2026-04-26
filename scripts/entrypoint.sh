#!/bin/sh
# P11 — container entrypoint with cgroup memory guard sidecar.
#
# Launches scripts/cgroup_memory_guard.py in the background so it
# polls the container's cgroup memory accounting (warns at
# $AGENT_MEMORY_WARN_PCT, kills sub-agent PIDs at
# $AGENT_MEMORY_KILL_PCT). Then exec's the primary command (uvicorn
# in API service, prefect worker etc.) as PID 1's foreground child so
# signals from the runtime still reach it cleanly.
#
# Disable the guard with AGENT_MEMORY_GUARD_DISABLED=1 (e.g. local
# dev where /sys/fs/cgroup is not mounted in a useful way).
set -eu

GUARD="${AGENT_MEMORY_GUARD_DISABLED:-0}"
PID_DIR="${AGENT_MEMORY_PID_DIR:-/tmp/agency_os/agents}"
WARN_PCT="${AGENT_MEMORY_WARN_PCT:-80}"
KILL_PCT="${AGENT_MEMORY_KILL_PCT:-95}"
INTERVAL="${AGENT_MEMORY_INTERVAL:-10}"

mkdir -p "${PID_DIR}" 2>/dev/null || true

if [ "${GUARD}" != "1" ]; then
  python3 /app/scripts/cgroup_memory_guard.py \
      --pid-dir "${PID_DIR}" \
      --warn-pct "${WARN_PCT}" \
      --kill-pct "${KILL_PCT}" \
      --interval "${INTERVAL}" &
  GUARD_PID=$!
  # Reap the guard if the primary process exits, so the container can
  # cycle cleanly under Railway's restart policy.
  trap 'kill ${GUARD_PID} 2>/dev/null || true' INT TERM EXIT
fi

# exec replaces the shell so signals reach the primary process.
exec "$@"
