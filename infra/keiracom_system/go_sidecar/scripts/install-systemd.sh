#!/usr/bin/env bash
# Install + enable the user-scope systemd unit for the Go sidecar.
#
# Idempotent. Uses --user systemd (consistent with the rest of Agency OS
# infra/ units that run under the elliotbot user). Anchor: Wave 1 dispatch
# Agency_OS-2c7m. Pair with scripts/build.sh which produces the binary.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT="keiracom-go-sidecar.service"
USER_UNIT_DIR="${HOME}/.config/systemd/user"

mkdir -p "${USER_UNIT_DIR}"
install -m 0644 "${ROOT}/${UNIT}" "${USER_UNIT_DIR}/${UNIT}"

# bin/ is gitignored, so it's absent on a fresh checkout. The unit whitelists
# it via ReadWritePaths under ProtectHome=read-only; systemd fails to start a
# unit whose ReadWritePaths target does not exist. Create it before enabling so
# the ExecStartPre build.sh can write bin/sidecar.
mkdir -p "${ROOT}/bin"

systemctl --user daemon-reload
systemctl --user enable "${UNIT}"
systemctl --user restart "${UNIT}"

echo "install-systemd.sh: enabled + restarted ${UNIT}"
echo "Logs: tail -f /home/elliotbot/clawd/logs/keiracom-go-sidecar.log"
echo "Health: curl -fsS http://127.0.0.1:4100/health"
