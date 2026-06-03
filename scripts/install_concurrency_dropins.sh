#!/usr/bin/env bash
# install_concurrency_dropins.sh — install spawn-gate drop-ins for the
# 6 non-Elliot agent services (KEI Agency_OS-03w4).
#
# Idempotent. Copies systemd/concurrency_dropin/<callsign>.conf to the
# host's per-service drop-in dir, then daemon-reload + restart each
# unit so ExecStartPre/ExecStopPost take effect.
#
# Elliot's service is NEVER touched — Elliot bypasses the cap.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${REPO_DIR}/systemd/concurrency_dropin"
DEST_BASE="${HOME}/.config/systemd/user"
CALLSIGNS=(aiden max atlas nova orion scout)

for cs in "${CALLSIGNS[@]}"; do
  src="${SRC_DIR}/${cs}.conf"
  dest_dir="${DEST_BASE}/${cs}-agent.service.d"
  dest="${dest_dir}/concurrency.conf"
  if [[ ! -f "${src}" ]]; then
    echo "MISSING: ${src}" >&2
    exit 1
  fi
  mkdir -p "${dest_dir}"
  if cmp -s "${src}" "${dest}" 2>/dev/null; then
    echo "unchanged: ${dest}"
    continue
  fi
  cp "${src}" "${dest}"
  echo "installed: ${dest}"
done

systemctl --user daemon-reload
echo "daemon-reload complete. Restart units to apply (e.g. systemctl --user restart aiden-agent)."
