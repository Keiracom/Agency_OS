#!/usr/bin/env bash
# cognee_capped.sh — launch cognee under a 3 GB systemd memory cap.
#
# Closes Beads Agency_OS-ely / Linear KEI-44. 2026-05-13 OOM crash:
# uncapped Cognee Streams 3+4 consumed all 6 GB of server RAM, killed
# six agent tmux sessions. Permanent fix is a cgroup hard ceiling.
#
# Implementation: systemd-run --user --scope -p MemoryMax=3G wraps the
# child process. cgroup memory.max enforces — when the cap is hit the
# kernel OOM-kills the child only (no host-wide drag-down). Visible via
# `systemctl --user status <unit>` and /proc/<pid>/limits.
#
# Why --scope (not --service):
#   - scope wraps the foreground command; calling shell blocks until exit
#   - exit code propagates back to the caller
#   - unit dies cleanly when child exits, no leftover service to clean up
#
# Why not ulimit -v:
#   - virtual-memory limit produces false OOM on Python+numpy reservations
#   - MemoryMax measures RSS only; matches the OOM failure mode we hit
#
# Modes:
#   ingest   wraps `python scripts/cognee_ingest.py <args>`
#   server   wraps `python -m uvicorn cognee.api.client:app --host 0.0.0.0 --port 8000 <args>`
#   exec     wraps an arbitrary command after `--` (escape hatch)
#
# Usage:
#   scripts/orchestrator/cognee_capped.sh ingest [-- args...]
#   scripts/orchestrator/cognee_capped.sh server [-- args...]
#   scripts/orchestrator/cognee_capped.sh exec -- /path/to/cmd args...
#   scripts/orchestrator/cognee_capped.sh --no-cap ingest [-- args...]
#   scripts/orchestrator/cognee_capped.sh --max-mem=2G ingest [-- args...]
#
# Env overrides:
#   AGENCY_OS_COGNEE_CAP_MAX_MEM  default 3G (passed to -p MemoryMax=)
#   AGENCY_OS_COGNEE_CAP_PYTHON   default $(command -v python3)
#   AGENCY_OS_SYSTEMD_RUN         path to systemd-run binary (default 'systemd-run')
#   AGENCY_OS_SYSTEMD_RUN_SKIP    if set, print resolved command + exit 0 (tests)
#
# Exit codes: child process exit code on success path; 2 on bad arguments;
# 3 if systemd-run is unavailable and --no-cap was not requested.

set -euo pipefail

MAX_MEM="${AGENCY_OS_COGNEE_CAP_MAX_MEM:-3G}"
PYTHON_BIN="${AGENCY_OS_COGNEE_CAP_PYTHON:-$(command -v python3 || true)}"
SYSTEMD_RUN="${AGENCY_OS_SYSTEMD_RUN:-systemd-run}"
NO_CAP=0

# ─── Args ──────────────────────────────────────────────────────────────
POSITIONAL=()
while (( $# )); do
    case "$1" in
        --no-cap) NO_CAP=1; shift ;;
        --max-mem=*) MAX_MEM="${1#*=}"; shift ;;
        --max-mem) MAX_MEM="$2"; shift 2 ;;
        -h | --help)
            sed -n '2,40p' "$0"
            exit 0
            ;;
        --) shift; POSITIONAL+=("$@"); break ;;
        -*) echo "error: unknown arg: $1" >&2; exit 2 ;;
        *) POSITIONAL+=("$1"); shift ;;
    esac
done

if (( ${#POSITIONAL[@]} == 0 )); then
    echo "error: missing mode (ingest|server|exec)" >&2
    exit 2
fi

MODE="${POSITIONAL[0]}"
EXTRA=("${POSITIONAL[@]:1}")

# ─── Resolve mode → child argv ─────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
case "$MODE" in
    ingest)
        if [[ -z "$PYTHON_BIN" ]]; then
            echo "error: python3 not found on PATH" >&2; exit 3
        fi
        CHILD_CMD=("$PYTHON_BIN" "$REPO_ROOT/scripts/cognee_ingest.py" "${EXTRA[@]}")
        UNIT_NAME="cognee-ingest-$$.scope"
        ;;
    server)
        if [[ -z "$PYTHON_BIN" ]]; then
            echo "error: python3 not found on PATH" >&2; exit 3
        fi
        CHILD_CMD=("$PYTHON_BIN" -m uvicorn cognee.api.client:app
                   --host 0.0.0.0 --port 8000 "${EXTRA[@]}")
        UNIT_NAME="cognee-server-$$.scope"
        ;;
    exec)
        if (( ${#EXTRA[@]} == 0 )); then
            echo "error: exec mode requires '-- <cmd> [args]'" >&2; exit 2
        fi
        CHILD_CMD=("${EXTRA[@]}")
        UNIT_NAME="cognee-exec-$$.scope"
        ;;
    *) echo "error: unknown mode: $MODE (want ingest|server|exec)" >&2; exit 2 ;;
esac

# ─── --no-cap escape (local dev / non-systemd hosts) ───────────────────
if (( NO_CAP )); then
    exec "${CHILD_CMD[@]}"
fi

# ─── Resolve systemd-run and dispatch ──────────────────────────────────
if ! command -v "$SYSTEMD_RUN" >/dev/null 2>&1; then
    echo "error: $SYSTEMD_RUN not available; pass --no-cap to bypass" >&2
    exit 3
fi

FULL_CMD=("$SYSTEMD_RUN" --user --scope --unit="$UNIT_NAME"
          -p "MemoryMax=$MAX_MEM" -p "MemoryAccounting=yes"
          -- "${CHILD_CMD[@]}")

if [[ -n "${AGENCY_OS_SYSTEMD_RUN_SKIP:-}" ]]; then
    printf '%s\n' "${FULL_CMD[@]}"
    exit 0
fi

exec "${FULL_CMD[@]}"
