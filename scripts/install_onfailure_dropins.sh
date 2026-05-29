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
# Template units (foo@.service) ARE covered (Agency_OS-cws5): the drop-in lands
# in foo@.service.d/, which systemd applies to every instance foo@<x>.service.
# When an instance fails, %n is its full unit name; the handler
# keiracom-ops-failure-alert@%n.service passes it verbatim to the publisher via
# %i (NOT %I — %I unescapes '-' to '/'). The resulting double-@ instance name
# resolves correctly — verified live via --selftest.
#
# EXCLUSIONS (never add a drop-in to):
#   - keiracom-ops-failure-alert@.service + its instances (prevents recursion)
#
# Idempotent: re-running writes the same content without error.
#
# Usage:
#   bash scripts/install_onfailure_dropins.sh            # install
#   bash scripts/install_onfailure_dropins.sh --remove   # remove all drop-ins
#   bash scripts/install_onfailure_dropins.sh --selftest # live double-@ test
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITS_DIR="${HOME}/.config/systemd/user"
TEMPLATE_UNIT="keiracom-ops-failure-alert@.service"
DROPIN_FILENAME="00-onfailure.conf"

REMOVE=0
if [[ "${1:-}" == "--remove" ]]; then
    REMOVE=1
fi

# ── --selftest: live double-@ regression test (Agency_OS-cws5) ─────────────────
# Proves a drop-in on a TEMPLATE applies to its instances AND the failing
# instance's full unit name survives %n -> handler -> %i (no '-'->'/' corruption).
if [[ "${1:-}" == "--selftest" ]]; then
    install -m 0644 "${REPO_DIR}/infra/systemd/agents/keiracom-ops-failure-alert@.service" \
        "${HOME}/.config/systemd/user/keiracom-ops-failure-alert@.service"
    U="${HOME}/.config/systemd/user"
    T="zz-onfail-selftest"
    alert_log="/home/elliotbot/clawd/logs/ops-failure-alert.log"
    printf '[Unit]\nDescription=cws5 double-@ selftest\n[Service]\nType=oneshot\nExecStart=/bin/false\n' \
        >"${U}/${T}@.service"
    mkdir -p "${U}/${T}@.service.d"
    printf '[Unit]\nOnFailure=keiracom-ops-failure-alert@%%n.service\n' \
        >"${U}/${T}@.service.d/00-onfailure.conf"
    systemctl --user daemon-reload
    systemctl --user start "${T}@probe.service" 2>/dev/null || true
    sleep 4
    st_rc=1
    if grep -q "unit=${T}@probe.service" "$alert_log" 2>/dev/null; then
        echo "SELFTEST PASS: alert fired with correct instance unit '${T}@probe.service'"
        st_rc=0
    else
        echo "SELFTEST FAIL: no 'unit=${T}@probe.service' in $alert_log" >&2
        echo "  (ensure keiracom-ops-failure-alert@ template + NATS are deployed)" >&2
    fi
    systemctl --user reset-failed "${T}@probe.service" 2>/dev/null || true
    rm -f "${U}/${T}@.service" "${U}/${T}@.service.d/00-onfailure.conf"
    rmdir "${U}/${T}@.service.d" 2>/dev/null || true
    systemctl --user daemon-reload
    exit "$st_rc"
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

    # Templates (foo@.service) ARE covered: dropin_dir resolves to
    # foo@.service.d/, which systemd applies to every instance (cws5).

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
