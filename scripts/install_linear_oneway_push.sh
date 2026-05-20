#!/usr/bin/env bash
# install_linear_oneway_push.sh — Agency_OS-1x3x installer.
#
# Installs linear-oneway-push.service + .timer (15min cadence) into the
# user-systemd config dir. The push is the sole sanctioned Supabase→Linear
# status writer.
#
# KEI-108 CI-gate compliance: anchors the literal unit name
# `linear-oneway-push.service` for the grep gate.
#
# Prerequisites verified below (fail-loud — the push's loop-safety depends
# on them):
#   LINEAR_API_KEY        — Linear write auth.
#   LINEAR_VIEWER_ID      — the API key's user id. The Linear webhook's
#                           KEI-238 self-echo suppression drops updates
#                           whose actor == LINEAR_VIEWER_ID; unset means a
#                           push echoes back as a Supabase change.
#   LINEAR_STATE_ID_DONE / _CANCELED — terminal-state UUIDs the push writes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/infra/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/clawd/logs"
ENV_FILE="/home/elliotbot/.config/agency-os/.env"

missing=()
for var in LINEAR_API_KEY LINEAR_VIEWER_ID LINEAR_STATE_ID_DONE LINEAR_STATE_ID_CANCELED; do
    if ! grep -q "^${var}=" "${ENV_FILE}" 2>/dev/null; then
        missing+=("${var}")
    fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "install_linear_oneway_push: missing required env var(s) in ${ENV_FILE}:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    echo "  LINEAR_VIEWER_ID gates KEI-238 echo suppression — set it before install." >&2
    exit 2
fi

mkdir -p "${SYSTEMD_DST}" "${LOG_DIR}"
cp -v "${SYSTEMD_SRC}/linear-oneway-push.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/linear-oneway-push.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now linear-oneway-push.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status linear-oneway-push.timer"
echo "  systemctl --user list-timers --all | grep linear-oneway-push"
echo "  journalctl --user -u linear-oneway-push.service -n 50 --no-pager"
echo "  tail -n 50 ~/clawd/logs/linear-oneway-push.log"
