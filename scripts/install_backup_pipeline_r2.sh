#!/usr/bin/env bash
# install_backup_pipeline_r2.sh — install the Cloudflare R2 backup pipeline
# systemd units (KEI-242 Weaviate snapshots + KEI-243 Postgres dumps).
#
# Installs + enables (user scope):
#   - weaviate-snapshot-r2.service     (daily 02:00 UTC via .timer)
#   - postgres-dump-r2.service         (hourly via .timer)
#   - weaviate-restore-verify.service  (weekly Sun 03:00 UTC via .timer — hard gate)
#
# Prerequisites on the fleet host:
#   - /home/elliotbot/.config/agency-os/.env has R2_ACCOUNT_ID, R2_ACCESS_KEY_ID,
#     R2_SECRET_ACCESS_KEY, R2_BACKUP_BUCKET (and BACKUP_PG_DSN for Postgres).
#   - postgresql-client installed (pg_dump) for the Postgres dump.
#   - /home/elliotbot/clawd/venv has boto3.
#
# Idempotent: re-running re-copies the units, reloads, and re-enables.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITS_DIR="${HOME}/.config/systemd/user"
SRC="${REPO_DIR}/infra/systemd/agents"
LOG_DIR="${HOME}/clawd/logs"

UNITS=(
    weaviate-snapshot-r2.service
    weaviate-snapshot-r2.timer
    postgres-dump-r2.service
    postgres-dump-r2.timer
    weaviate-restore-verify.service
    weaviate-restore-verify.timer
)

mkdir -p "${UNITS_DIR}" "${LOG_DIR}"
for unit in "${UNITS[@]}"; do
    if [[ ! -f "${SRC}/${unit}" ]]; then
        echo "install_backup_pipeline_r2: missing ${SRC}/${unit}" >&2
        exit 2
    fi
    install -m 0644 "${SRC}/${unit}" "${UNITS_DIR}/${unit}"
done

systemctl --user daemon-reload
systemctl --user enable --now weaviate-snapshot-r2.timer
systemctl --user enable --now postgres-dump-r2.timer
systemctl --user enable --now weaviate-restore-verify.timer

echo "install_backup_pipeline_r2: installed + enabled"
echo "  weaviate-snapshot-r2.service   — daily 02:00 UTC"
echo "  postgres-dump-r2.service       — hourly"
echo "  weaviate-restore-verify.service — weekly Sun 03:00 UTC (hard gate)"
echo "Verify R2 round-trip once creds are set:"
echo "  python3 -m src.keiracom_system.backup.weaviate_snapshot --dry-run"
