#!/usr/bin/env bash
# install_onfailure_dropins.sh — wire OnFailure= drop-ins for every user-scope
# systemd service so failures publish to NATS keiracom.ops.failure (Agency_OS-ja8d).
#
# For every *.service unit in $UNITS_DIR this script creates a drop-in:
#   $UNITS_DIR/<unit>.service.d/00-onfailure.conf
# containing:
#   [Unit]
#   OnFailure=keiracom-ops-failure-alert@%n.service
#
# EXCLUSIONS (never add a drop-in to):
#   - keiracom-ops-failure-alert@.service (the template itself)
#   - keiracom-ops-failure-alert@*.service instances (prevents recursion)
#   - Any template unit whose name contains '@' with empty instance (e.g. foo@.service)
#
# Idempotent: re-running writes the same content without error.
#
# Usage:
#   bash scripts/install_onfailure_dropins.sh           # install
#   bash scripts/install_onfailure_dropins.sh --remove  # remove all drop-ins
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITS_DIR="${HOME}/.config/systemd/user"
TEMPLATE_UNIT="keiracom-ops-failure-alert@.service"
DROPIN_FILENAME="00-onfailure.conf"

REMOVE=0
if [[ "${1:-}" == "--remove" ]]; then
    REMOVE=1
fi

# ── Install the template unit ─────────────────────────────────────────────────
template_src="${REPO_DIR}/infra/systemd/agents/${TEMPLATE_UNIT}"
if [[ ! -f "$template_src" ]]; then
    echo "ERROR: template not found at $template_src" >&2
    exit 1
fi

mkdir -p "$UNITS_DIR"

if [[ "$REMOVE" -eq 1 ]]; then
    # Remove drop-ins and the template
    removed=0
    for unit_file in "${UNITS_DIR}"/*.service; do
        [[ -f "$unit_file" ]] || continue
        unit_basename="$(basename "$unit_file")"
        dropin_dir="${UNITS_DIR}/${unit_basename}.d"
        dropin_conf="${dropin_dir}/${DROPIN_FILENAME}"
        if [[ -f "$dropin_conf" ]]; then
            rm -f "$dropin_conf"
            echo "removed drop-in: $dropin_conf"
            removed=$((removed + 1))
            # Remove dir if now empty
            if [[ -d "$dropin_dir" ]] && [[ -z "$(ls -A "$dropin_dir")" ]]; then
                rmdir "$dropin_dir"
            fi
        fi
    done
    # Remove the template itself
    if [[ -f "${UNITS_DIR}/${TEMPLATE_UNIT}" ]]; then
        rm -f "${UNITS_DIR}/${TEMPLATE_UNIT}"
        echo "removed template: ${UNITS_DIR}/${TEMPLATE_UNIT}"
    fi
    systemctl --user daemon-reload
    echo "done — removed $removed drop-in(s)"
    exit 0
fi

# ── Install mode ──────────────────────────────────────────────────────────────
install -m 0644 "$template_src" "${UNITS_DIR}/${TEMPLATE_UNIT}"
echo "installed template: ${UNITS_DIR}/${TEMPLATE_UNIT}"

written=0
skipped=0

for unit_file in "${UNITS_DIR}"/*.service; do
    [[ -f "$unit_file" ]] || continue
    unit_basename="$(basename "$unit_file")"

    # Skip the alert template itself and any keiracom-ops-failure-alert instances
    if [[ "$unit_basename" == keiracom-ops-failure-alert* ]]; then
        skipped=$((skipped + 1))
        continue
    fi

    # Skip template units (name contains '@' with empty instance, e.g. foo@.service)
    # A concrete instance looks like foo@bar.service; a bare template is foo@.service
    if [[ "$unit_basename" == *@.service ]]; then
        skipped=$((skipped + 1))
        continue
    fi

    dropin_dir="${UNITS_DIR}/${unit_basename}.d"
    dropin_conf="${dropin_dir}/${DROPIN_FILENAME}"

    mkdir -p "$dropin_dir"
    cat > "$dropin_conf" <<'DROPIN'
[Unit]
OnFailure=keiracom-ops-failure-alert@%n.service
DROPIN
    echo "wrote drop-in: $dropin_conf"
    written=$((written + 1))
done

systemctl --user daemon-reload
echo "done — wrote $written drop-in(s), skipped $skipped unit(s)"
