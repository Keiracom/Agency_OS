#!/usr/bin/env bash
# install_postgres_backup.sh — KEI-126 install entry-point.
#
# KEI-108 CI-gate requirement: per-unit install wrapper anchors the literal
# `postgres-backup.service` for the grep gate.
#
# Installs postgres-backup.service (oneshot) + postgres-backup.timer
# (daily 01:00 UTC). Verifies aws CLI is on PATH + .env carries the
# required S3 + Postgres credentials before enabling.
#
# Usage:
#   bash scripts/install_postgres_backup.sh
#
# Anchored units: postgres-backup.service, postgres-backup.timer

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITS_DIR="${HOME}/.config/systemd/user"
AGENTS_DIR="${REPO_DIR}/infra/systemd/agents"
LOG_DIR="${HOME}/clawd/logs"
ENV_FILE="${HOME}/.config/agency-os/.env"

mkdir -p "${UNITS_DIR}" "${LOG_DIR}"

# ----- 1. Verify required env in .env -----
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "install_postgres_backup: missing ${ENV_FILE}" >&2
    exit 2
fi

missing=()
for var in DATABASE_URL AWS_S3_BUCKET AWS_S3_ENDPOINT AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY; do
    if ! grep -q "^${var}=" "${ENV_FILE}"; then
        # Allow DATABASE_URL OR SUPABASE_DB_URL for the Postgres DSN.
        if [[ "${var}" == "DATABASE_URL" ]] && grep -q "^SUPABASE_DB_URL=" "${ENV_FILE}"; then
            continue
        fi
        missing+=("${var}")
    fi
done
if ((${#missing[@]} > 0)); then
    echo "install_postgres_backup: ${ENV_FILE} missing required env vars:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    exit 2
fi

# ----- 2. Verify aws CLI -----
if ! command -v aws >/dev/null 2>&1; then
    echo "install_postgres_backup: aws CLI missing (install: pip install awscli OR apt install awscli)" >&2
    exit 2
fi

# ----- 3. Install units -----
install -m 0644 "${AGENTS_DIR}/postgres-backup.service" "${UNITS_DIR}/postgres-backup.service"
install -m 0644 "${AGENTS_DIR}/postgres-backup.timer"   "${UNITS_DIR}/postgres-backup.timer"

systemctl --user daemon-reload
systemctl --user enable --now postgres-backup.timer

systemctl --user is-active postgres-backup.timer
echo "install_postgres_backup: postgres-backup.timer installed + enabled + active"
systemctl --user --no-pager list-timers postgres-backup.timer | head -5

echo
echo "Next fire: 01:00 UTC daily. To test a backup now: systemctl --user start postgres-backup.service"
echo "Restore procedure: docs/RUNBOOK_POSTGRES_RESTORE.md"
