#!/usr/bin/env bash
# LAW XVIII dispatch wrapper — preflight ATLAS, then drop unsigned
# task_dispatch JSON in /tmp/telegram-relay-atlas/inbox/.
#
# Usage:
#   scripts/dispatch_to_atlas.sh --brief "fix H1 persistence" \
#       --task-ref B4P2-T1 [--max-minutes 30]
#
# Sender callsign comes from $CALLSIGN (defaults to 'elliot').
# Currently writes UNSIGNED JSON — watcher accepts when INBOX_HMAC_SECRET
# is unset in its env. After HMAC enablement (see docs/governance/
# HMAC_ENABLEMENT.md) this wrapper switches to call sign_dispatch.py.
#
# Exits:
#   0 — dispatched (path printed on stdout)
#   1 — preflight failed (ATLAS dead) or write failed
#   2 — bad arguments

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATLAS_INBOX="/tmp/telegram-relay-atlas/inbox"
FROM_CALLSIGN="${CALLSIGN:-elliot}"

BRIEF=""
TASK_REF=""
MAX_MINUTES="30"

while [ $# -gt 0 ]; do
    case "$1" in
        --brief) BRIEF="${2:-}"; shift 2 ;;
        --task-ref) TASK_REF="${2:-}"; shift 2 ;;
        --max-minutes) MAX_MINUTES="${2:-}"; shift 2 ;;
        -h|--help)
            echo "usage: $0 --brief <text> --task-ref <slug> [--max-minutes N]"
            exit 0
            ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [ -z "$BRIEF" ] || [ -z "$TASK_REF" ]; then
    echo "usage: $0 --brief <text> --task-ref <slug> [--max-minutes N]" >&2
    exit 2
fi

# Preflight — abort on dead ATLAS
"$SCRIPT_DIR/check_atlas_alive.sh" >/dev/null || {
    echo "ABORT: ATLAS preflight failed (run scripts/check_atlas_alive.sh for detail)" >&2
    exit 1
}

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="$ATLAS_INBOX/${TASK_REF}_${TS}.json"

# Build JSON via env vars (avoids shell-quoting hazards in BRIEF).
BRIEF="$BRIEF" \
TASK_REF="$TASK_REF" \
MAX_MINUTES="$MAX_MINUTES" \
FROM_CALLSIGN="$FROM_CALLSIGN" \
python3 -c '
import json, os, time
payload = {
    "id": os.environ["TASK_REF"],
    "type": "task_dispatch",
    "from": os.environ["FROM_CALLSIGN"],
    "target": "atlas",
    "brief": os.environ["BRIEF"],
    "max_task_minutes": int(os.environ["MAX_MINUTES"]),
    "task_ref": os.environ["TASK_REF"],
    "created_at": int(time.time()),
}
print(json.dumps(payload))
' > "$OUT_FILE"

echo "$OUT_FILE"
exit 0
