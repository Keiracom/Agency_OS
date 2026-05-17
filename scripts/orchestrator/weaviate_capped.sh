#!/usr/bin/env bash
# weaviate_capped.sh — launch Weaviate under a 3 GB systemd memory cap.
#
# Default cap raised from 2.5G → 3G on 2026-05-17 (KEI-107, Dave directive)
# to align with KEI-44 discovery + Max's verified cgroup pattern for
# Python+numpy+Go services on Vultr Sydney.
#
# Closes Beads Agency_OS-... / Linear KEI-48 (Install Weaviate on Vultr Sydney).
# Same pattern as scripts/orchestrator/cognee_capped.sh (KEI-44 sha 3b133132).
#
# Why a cgroup cap:
#   Vultr Sydney has 7.7 GB RAM (already 4+ GB committed to claude sessions +
#   cognee + systemd services). Without a hard ceiling, a Weaviate memory leak
#   or large vector batch could OOM-kill the host. systemd-run --user --scope
#   with MemoryMax wraps the daemon — cgroup memory.max enforces a hard RSS
#   ceiling; the kernel OOM-kills the Weaviate child only, not the host.
#
# Why --scope (not --service):
#   - scope wraps the foreground command; calling shell blocks until exit
#   - exit code propagates back to the caller
#   - unit dies cleanly when child exits, no leftover service to clean up
#
# Usage:
#   scripts/orchestrator/weaviate_capped.sh           # start with defaults
#   scripts/orchestrator/weaviate_capped.sh --no-cap  # local dev / non-systemd
#   scripts/orchestrator/weaviate_capped.sh --max-mem=2G
#
# Env overrides:
#   WEAVIATE_BIN              default /home/elliotbot/clawd/weaviate-bin/weaviate
#   WEAVIATE_HOST             default 127.0.0.1 (loopback-only; reverse-proxy if exposing)
#   WEAVIATE_PORT             default 8090 (crowdsec holds 8080)
#   WEAVIATE_DATA_DIR         default /home/elliotbot/clawd/weaviate-data
#   AGENCY_OS_WEAVIATE_MAX_MEM    default 3G (passed to -p MemoryMax=, KEI-107)
#   AGENCY_OS_SYSTEMD_RUN     path to systemd-run binary (default 'systemd-run')
#   AGENCY_OS_SYSTEMD_RUN_SKIP    if set, print resolved command + exit 0 (tests)
#
# Exit codes: child process exit code on success path; 2 on bad arguments;
# 3 if systemd-run is unavailable and --no-cap was not requested.

set -euo pipefail

MAX_MEM="${AGENCY_OS_WEAVIATE_MAX_MEM:-3G}"
SYSTEMD_RUN="${AGENCY_OS_SYSTEMD_RUN:-systemd-run}"
WEAVIATE_BIN="${WEAVIATE_BIN:-/home/elliotbot/clawd/weaviate-bin/weaviate}"
WEAVIATE_HOST="${WEAVIATE_HOST:-127.0.0.1}"
WEAVIATE_PORT="${WEAVIATE_PORT:-8090}"
WEAVIATE_DATA_DIR="${WEAVIATE_DATA_DIR:-/home/elliotbot/clawd/weaviate-data}"
NO_CAP=0

while (( $# )); do
    case "$1" in
        --no-cap) NO_CAP=1; shift ;;
        --max-mem=*) MAX_MEM="${1#*=}"; shift ;;
        --max-mem) MAX_MEM="$2"; shift 2 ;;
        -h | --help) sed -n '2,40p' "$0"; exit 0 ;;
        *) echo "error: unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ ! -x "$WEAVIATE_BIN" ]]; then
    echo "error: weaviate binary missing or not executable: $WEAVIATE_BIN" >&2
    exit 3
fi

if [[ ! -d "$WEAVIATE_DATA_DIR" ]]; then
    echo "error: data dir missing: $WEAVIATE_DATA_DIR (mkdir -p first)" >&2
    exit 3
fi

# Weaviate config is env-driven; export the required vars.
export PERSISTENCE_DATA_PATH="$WEAVIATE_DATA_DIR"
export QUERY_DEFAULTS_LIMIT="${QUERY_DEFAULTS_LIMIT:-25}"
export AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED="${AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED:-true}"
export DEFAULT_VECTORIZER_MODULE="${DEFAULT_VECTORIZER_MODULE:-none}"
export ENABLE_MODULES="${ENABLE_MODULES:-}"

# Single-node cluster config — Weaviate's Raft layer wants explicit names + an
# advertise address even when not clustered. CLUSTER_ADVERTISE_ADDR=127.0.0.1
# pins the bind to loopback (matches WEAVIATE_HOST). RAFT_JOIN points at self
# so the single node bootstraps cleanly. CLUSTER_GOSSIP/DATA_BIND_PORT keep the
# Raft/memberlist sockets off the public-listen port.
export CLUSTER_HOSTNAME="${CLUSTER_HOSTNAME:-node1}"
export CLUSTER_ADVERTISE_ADDR="${CLUSTER_ADVERTISE_ADDR:-127.0.0.1}"
export CLUSTER_GOSSIP_BIND_PORT="${CLUSTER_GOSSIP_BIND_PORT:-7946}"
export CLUSTER_DATA_BIND_PORT="${CLUSTER_DATA_BIND_PORT:-7947}"
export RAFT_BOOTSTRAP_EXPECT="${RAFT_BOOTSTRAP_EXPECT:-1}"
export RAFT_JOIN="${RAFT_JOIN:-node1}"

CHILD_CMD=("$WEAVIATE_BIN" --host "$WEAVIATE_HOST" --port "$WEAVIATE_PORT" --scheme http)
UNIT_NAME="weaviate-$$.scope"

if (( NO_CAP )); then
    exec "${CHILD_CMD[@]}"
fi

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
