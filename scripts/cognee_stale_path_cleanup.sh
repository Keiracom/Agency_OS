#!/bin/bash
# cognee_stale_path_cleanup.sh — KEI-77 follow-on cleanup.
#
# Q1 audit (docs/audits/hybrid_memory_q1_atlas.md) flagged two cognee DB paths:
#   1. /home/elliotbot/clawd/cognee_data/      — STALE (215 MB SQLite, last 5/13)
#   2. .venv/.../cognee/.cognee_system/databases/ — LIVE (what cognee actually uses)
#
# The stale path likely originated from an earlier cognee version that read
# DB_PATH from env; the live cognee 1.0.9 ignores DB_PATH and writes inside
# the venv. Stale path serves no purpose and confuses operators looking for
# "cognee data" (was the Q1 audit's first-pass conclusion until I traced the
# live process's database_path log line).
#
# Move-to-trash (not rm) so it's recoverable if someone needed it. Dave's
# 2026-05-16 dispatch authorised cleanup in the KEI-77 PR.
#
# Run ONCE post-merge. Idempotent — exits 0 if path already gone.

set -euo pipefail

STALE_PATH="/home/elliotbot/clawd/cognee_data"

if [[ ! -e "$STALE_PATH" ]]; then
    echo "cognee_stale_path_cleanup: $STALE_PATH already absent — no-op"
    exit 0
fi

# Verify the live cognee process is NOT using this path (paranoid check).
# Cognee structlog wraps fields in ANSI colour codes — match the literal
# field name (no `=` required) and filter for the stale-path substring.
# Failed grep returns 1 — use `|| true` to play nice with `set -e`.
LIVE_HITS=$(grep -h "database_path" /home/elliotbot/clawd/logs/cognee.log 2>/dev/null \
            | tail -50 | grep -c "/clawd/cognee_data" || true)
if [[ "$LIVE_HITS" -gt 0 ]]; then
    echo "cognee_stale_path_cleanup: ABORT — live cognee.log database_path mentions /clawd/cognee_data ($LIVE_HITS hits in tail -50)" >&2
    grep -h "database_path" /home/elliotbot/clawd/logs/cognee.log 2>/dev/null \
        | tail -1 >&2
    exit 1
fi

# Move to ~/.local/share/Trash (gio) if available, else mv to backup dir.
if command -v gio >/dev/null; then
    gio trash "$STALE_PATH"
    echo "cognee_stale_path_cleanup: moved $STALE_PATH to trash"
else
    BACKUP="/home/elliotbot/.cognee_data_stale_backup_$(date +%Y%m%d_%H%M%S)"
    mv "$STALE_PATH" "$BACKUP"
    echo "cognee_stale_path_cleanup: moved $STALE_PATH to $BACKUP (gio not available)"
fi
