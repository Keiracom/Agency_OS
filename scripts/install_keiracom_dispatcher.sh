#!/usr/bin/env bash
# install_keiracom_dispatcher.sh — Install + enable Phase A8 ephemeral-agent
# dispatcher systemd template for one or more callsigns.
#
# Filed under Agency_OS-awec (§7 piece 4 of PR #1140 ephemeral-agent scoping).
#
# DEPENDS ON §7 pieces 1 + 5 (P1 KEIs):
#   - Piece 1: scripts/dispatcher/dispatcher_main.py must be installed +
#     executable at the path baked into the template's ExecStartPre.
#   - Piece 5: spawn-with-context composer library imported by piece 1.
#
# If those binaries are missing, the unit will fail at ExecStartPre (test -x
# check). This script installs the unit + env files anyway so the scaffold is
# ready; operators run `systemctl --user start` once pieces 1+5 ship.
#
# Usage:
#   install_keiracom_dispatcher.sh                    # install for all 7 callsigns
#   install_keiracom_dispatcher.sh elliot scout       # install for specific callsigns
#   install_keiracom_dispatcher.sh --no-enable elliot # install but don't enable
#   install_keiracom_dispatcher.sh --uninstall elliot # disable + remove
#
# Idempotent: re-running copies the unit + env file fresh + reloads daemon +
# enables if not already enabled. Safe in any bootstrap pipeline.

set -euo pipefail

ALL_CALLSIGNS=(elliot aiden max atlas orion scout nova)

UNITS_DIR="${HOME}/.config/systemd/user"
ENV_DIR="${HOME}/.config/agency-os"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE="${REPO_DIR}/systemd/keiracom-dispatcher@.service"
ENV_SOURCE_DIR="${REPO_DIR}/systemd/dispatcher-env"

# ----------------------------------------------------------------------------
# Flags + arg parsing
# ----------------------------------------------------------------------------
do_enable=1
do_uninstall=0
declare -a callsigns

for arg in "$@"; do
    case "${arg}" in
        --no-enable)
            do_enable=0
            ;;
        --uninstall)
            do_uninstall=1
            do_enable=0
            ;;
        --help|-h)
            sed -n '2,/^set -euo/p' "$0" | head -n 25
            exit 0
            ;;
        -*)
            echo "unknown flag: ${arg}" >&2
            exit 2
            ;;
        *)
            callsigns+=("${arg}")
            ;;
    esac
done

if [[ ${#callsigns[@]} -eq 0 ]]; then
    callsigns=("${ALL_CALLSIGNS[@]}")
fi

# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------
if [[ ! -f "${UNIT_SOURCE}" ]]; then
    echo "missing source unit: ${UNIT_SOURCE}" >&2
    exit 2
fi

mkdir -p "${UNITS_DIR}" "${ENV_DIR}" /home/elliotbot/clawd/logs

# ----------------------------------------------------------------------------
# Install template unit (one file, instantiated per callsign at enable time)
# ----------------------------------------------------------------------------
if [[ ${do_uninstall} -eq 0 ]]; then
    cp "${UNIT_SOURCE}" "${UNITS_DIR}/keiracom-dispatcher@.service"
    systemctl --user daemon-reload
fi

# ----------------------------------------------------------------------------
# Per-callsign env + enable/disable
# ----------------------------------------------------------------------------
for callsign in "${callsigns[@]}"; do
    env_source="${ENV_SOURCE_DIR}/dispatcher-${callsign}.env"
    env_dest="${ENV_DIR}/dispatcher-${callsign}.env"

    if [[ ${do_uninstall} -eq 1 ]]; then
        systemctl --user disable --now "keiracom-dispatcher@${callsign}.service" 2>/dev/null || true
        rm -f "${env_dest}"
        echo "uninstalled: keiracom-dispatcher@${callsign}.service"
        continue
    fi

    if [[ ! -f "${env_source}" ]]; then
        echo "warning: missing env file for ${callsign}: ${env_source} — skipping" >&2
        continue
    fi

    cp "${env_source}" "${env_dest}"

    if [[ ${do_enable} -eq 1 ]]; then
        # `enable` without `--now` so we don't try to start a unit that fails
        # at ExecStartPre until §7 piece 1 binary lands. Operator runs
        # `systemctl --user start keiracom-dispatcher@<callsign>.service`
        # manually once the binary is in place.
        systemctl --user enable "keiracom-dispatcher@${callsign}.service"
        echo "installed + enabled: keiracom-dispatcher@${callsign}.service"
    else
        echo "installed (not enabled): keiracom-dispatcher@${callsign}.service"
    fi
done

if [[ ${do_uninstall} -eq 1 ]]; then
    systemctl --user daemon-reload
fi
