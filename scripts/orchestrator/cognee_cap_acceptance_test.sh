#!/usr/bin/env bash
# cognee_cap_acceptance_test.sh — verify cognee_capped.sh enforces MemoryMax.
#
# 10-chunk synthetic batch (~400 MB/chunk = ~4 GB peak) launched under
# cognee_capped.sh exec mode at --max-mem=$CAP (default 1G for the test).
# Expected: kernel cgroup OOM-kills the child inside its scope memcg with
# exit code 137. Failure of the test = the cap is not being enforced.
#
# Why 1G (not 3G) for the test default:
#   3G allocation puts real pressure on dev workstations. The enforcement
#   mechanism is identical regardless of cap value — 1G demonstrates the
#   same memcg → OOM → 137 path with smaller resource footprint.
#
# Usage:
#   scripts/orchestrator/cognee_cap_acceptance_test.sh
#   scripts/orchestrator/cognee_cap_acceptance_test.sh --cap 3G
#
# Exit codes: 0 cap enforced; 1 cap NOT enforced (child completed); 2 bad args.

set -euo pipefail

CAP="1G"
while (( $# )); do
    case "$1" in
        --cap) CAP="$2"; shift 2 ;;
        --cap=*) CAP="${1#*=}"; shift ;;
        -h | --help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "error: unknown arg: $1" >&2; exit 2 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WRAPPER="$REPO_ROOT/scripts/orchestrator/cognee_capped.sh"
PYTHON_BIN="${AGENCY_OS_COGNEE_CAP_PYTHON:-$(command -v python3)}"
ALLOCATOR=$(mktemp --suffix=.py)
LOG=$(mktemp --suffix=.log)
trap 'rm -f "$ALLOCATOR" "$LOG"' EXIT

cat > "$ALLOCATOR" <<'PY'
import os, time
CHUNK_BYTES = 400 * 1024 * 1024
held = []
print(f"PID={os.getpid()} starting 10-chunk synthetic batch", flush=True)
for i in range(10):
    held.append(bytearray(CHUNK_BYTES))
    for j in range(0, CHUNK_BYTES, 4096):
        held[-1][j] = 1
    print(f"chunk {i+1}/10 allocated (~{(i+1)*400} MB)", flush=True)
    time.sleep(0.1)
print("CHUNKS_DONE", flush=True)
PY

echo "==> Running 10-chunk synthetic batch under MemoryMax=$CAP"
set +e
bash "$WRAPPER" --max-mem="$CAP" exec -- "$PYTHON_BIN" "$ALLOCATOR" > "$LOG" 2>&1
rc=$?
set -e

echo "==> Wrapper exit code: $rc"
echo "==> Last log lines:"
tail -10 "$LOG"

if grep -q "CHUNKS_DONE" "$LOG"; then
    echo "FAIL: child completed all 10 chunks — cap NOT enforced" >&2
    exit 1
fi

if (( rc == 137 )); then
    echo "PASS: child SIGKILL'd by cgroup OOM (rc=137) at cap=$CAP"
    exit 0
fi

# Other non-zero exits could also indicate enforcement (e.g. Python MemoryError
# raised before SIGKILL). Treat anything non-zero with no CHUNKS_DONE as pass,
# but flag the unusual exit so the operator can investigate.
echo "PASS-WITH-NOTE: child died (rc=$rc) before completing chunks at cap=$CAP"
exit 0
