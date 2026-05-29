#!/usr/bin/env bash
# install_dead_letter_notifier.sh — install the dead-letter → #ceo notifier unit
# (Agency_OS-gl3v). Satisfies the KEI-108 deployment contract: every shipped unit
# is referenced by an installer. Mirrors scripts/install_work_loop.sh.
#
# ⚠ GATED — enable once the work-loop consumer's dead-letter columns are live:
# public.tasks needs status='dead_letter' + retry_count + last_error (confirm with
# Atlas / the producer stack). The notifier is SAFE to run early (read-only watch +
# #ceo post, no spend, no auto-spawn) but its SELECT errors-and-retries until those
# columns exist, so enabling before they land just logs noise. The script EXISTS to
# satisfy the contract + give a one-command install at go-live.
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${REPO_DIR}/systemd"

mkdir -p "${UNITS_DIR}"

cp "${SYSTEMD_DIR}/dead-letter-notifier.service" "${UNITS_DIR}/"

systemctl --user daemon-reload
systemctl --user enable --now dead-letter-notifier.service

echo "dead-letter notifier installed and started"
