#!/usr/bin/env bash
# agent_session_launcher.sh — Drevon PR-C Claude Code session resumption.
#
# Looks up the most-recent watchdog-fresh session_uuid for the given callsign
# in the sessions table; if found, exec's `claude --resume <uuid>`, else
# generates a new UUID and exec's `claude --session-id <new>`. Either way the
# row is claimed in the sessions table so subsequent launches see it.
#
# Usage:
#     scripts/agent_session_launcher.sh <callsign> [extra claude args...]
#
# Env overrides (optional):
#     SESSION_FRESH_MINUTES   — watchdog-fresh window (default 30)
#     SESSION_LAUNCHER_DRY    — if set, print the resolved command instead of exec
#
# Best-effort semantics: any DB failure falls through to a fresh UUID rather
# than blocking startup. Operator can inspect logs via the python module.

set -euo pipefail

callsign="${1:?usage: agent_session_launcher.sh <callsign> [extra claude args...]}"
shift

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
fresh_minutes="${SESSION_FRESH_MINUTES:-30}"

# DRY mode: skip ALL Supabase I/O (no resolve, no claim). Always emits a
# fresh UUID so the CLI surface (flag selection, arg forwarding, exit codes)
# can be tested without touching prod data.
if [ -n "${SESSION_LAUNCHER_DRY:-}" ]; then
    sid="$(python3 -c 'import uuid; print(uuid.uuid4())')"
    resolution="fresh $sid"
else
    # Resolve session uuid via Python module. Outputs a single line:
    #   "resume <uuid>" | "fresh <uuid>"
    resolution=$(
        cd "$repo_root" && python3 - "$callsign" "$fresh_minutes" <<'PY'
import sys
import uuid

callsign = sys.argv[1]
fresh_minutes = int(sys.argv[2])

try:
    from src.session_resumption.resolver import claim_session_uuid, resolve_session_uuid
except Exception as exc:
    # Module load failure (env, schema) — fall through to fresh UUID, no claim.
    print(f"fresh {uuid.uuid4()}", flush=True)
    sys.stderr.write(f"[launcher] resolver import failed, fresh fallback: {exc}\n")
    sys.exit(0)

import os

existing = resolve_session_uuid(callsign, fresh_minutes=fresh_minutes)
if existing:
    sid = existing
    mode = "resume"
else:
    sid = str(uuid.uuid4())
    mode = "fresh"
    # Best-effort claim — never block on failure.
    try:
        claim_session_uuid(callsign, sid, os.getcwd())
    except Exception as exc:
        sys.stderr.write(f"[launcher] claim_session_uuid failed (non-fatal): {exc}\n")

print(f"{mode} {sid}", flush=True)
PY
    )
fi

mode="${resolution%% *}"
sid="${resolution##* }"

if [ "$mode" = "resume" ]; then
    flag="--resume"
else
    flag="--session-id"
fi

if [ -n "${SESSION_LAUNCHER_DRY:-}" ]; then
    echo "[launcher] mode=$mode callsign=$callsign sid=$sid"
    echo "[launcher] would exec: claude $flag $sid $*"
    exit 0
fi

exec claude "$flag" "$sid" "$@"
