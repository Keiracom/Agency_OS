#!/usr/bin/env bash
# install_completion_sync_worker.sh — install + start the KEI-74 completion
# sync worker as a systemd user service.
#
# References:
#   - infra/systemd/completion-sync-worker.service
#   - scripts/orchestrator/completion_sync_worker.py
#   - LAW XV four-store completion (Linear / ceo_memory / drive_manual)
#
# The worker drains public.completion_sync_queue rows and dispatches to:
#   linear        — POST Linear GraphQL issueUpdate
#   ceo_memory    — INSERT public.ceo_memory row
#   drive_manual  — invoke scripts/write_manual_mirror.py
#
# Without this worker, completion events sit unprocessed → cross-store drift
# between Linear / ceo_memory / Drive mirror. Gap-hunt (2026-05-20) found the
# .service file shipped but no installer; this script closes that gap.
#
# Prerequisites:
#   1. /home/elliotbot/clawd/Agency_OS worktree on origin/main with KEI-74
#      schema (public.completion_sync_queue) applied.
#   2. /home/elliotbot/.config/agency-os/.env populated with DATABASE_URL
#      (or SUPABASE_DB_URL) and LINEAR_API_KEY.
#   3. /home/elliotbot/clawd/Agency_OS/.venv has psycopg installed.
#
# Idempotent: copies the unit fresh, reloads daemon, enables + starts.
# Re-running on an already-active service is a no-op (enable --now is a
# no-op when active; cp overwrites in place — service stays running).

set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE="${REPO_DIR}/infra/systemd/completion-sync-worker.service"

if [[ ! -f "${UNIT_SOURCE}" ]]; then
    echo "missing source unit: ${UNIT_SOURCE}" >&2
    exit 2
fi

mkdir -p "${UNITS_DIR}"
cp "${UNIT_SOURCE}" "${UNITS_DIR}/completion-sync-worker.service"
echo "installed: ${UNITS_DIR}/completion-sync-worker.service"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now completion-sync-worker.service
    echo "completion-sync-worker.service enabled and started"
    echo
    echo "To check status:  systemctl --user status completion-sync-worker.service"
    echo "To view logs:     journalctl --user -u completion-sync-worker.service -f"
    echo "                  (or: tail -F /home/elliotbot/clawd/logs/completion-sync-worker.log)"
else
    echo "WARN: systemctl not on PATH; unit copied but not enabled." >&2
    echo "Run manually: systemctl --user daemon-reload && systemctl --user enable --now completion-sync-worker.service" >&2
fi
