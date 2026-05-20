#!/usr/bin/env bash
# migrate_relay_tmpfs_to_durable.sh — KEI-142 / Agency_OS-jhdf25.
#
# Move a callsign's relay state from the volatile tmpfs path
#   /tmp/telegram-relay-<callsign>
# to the durable
#   /var/lib/agency-os/relay-<callsign>
# and replace the tmpfs entry with a symlink so the existing ~18 in-tree
# call sites that hardcode /tmp/telegram-relay-* keep working without
# change. Boot-time symlink recreation is handled by
# infra/tmpfiles.d/agency-os-relay.conf.
#
# Idempotent: re-running on an already-migrated callsign is a no-op + 0
# exit. Safe to chain via --all.
#
# Usage:
#   bash scripts/migrate_relay_tmpfs_to_durable.sh <callsign>
#   bash scripts/migrate_relay_tmpfs_to_durable.sh --all
#   AGENCY_OS_RELAY_BASE=/path bash scripts/migrate_relay_tmpfs_to_durable.sh elliot   # tests
#
# Prereqs: /var/lib/agency-os (or $AGENCY_OS_RELAY_BASE) must exist and be
# writable by the invoking user. The runbook
# docs/runbooks/relay-tmpfs-migration.md covers the one-time sudo setup.

set -euo pipefail

CALLSIGNS=("elliot" "aiden" "max" "orion" "atlas" "scout" "nova")
RELAY_BASE="${AGENCY_OS_RELAY_BASE:-/var/lib/agency-os}"
TMPFS_BASE="${AGENCY_OS_TMPFS_BASE:-/tmp}"

migrate_one() {
    local callsign="$1"
    local tmp_dir="${TMPFS_BASE}/telegram-relay-${callsign}"
    local durable_dir="${RELAY_BASE}/relay-${callsign}"

    # Already migrated? symlink that resolves to durable_dir — done.
    if [[ -L "$tmp_dir" ]] && [[ "$(readlink -f "$tmp_dir")" == "$durable_dir" ]]; then
        echo "  ${callsign}: already migrated (${tmp_dir} -> ${durable_dir})"
        return 0
    fi

    # Ensure durable target exists with the expected sub-dirs.
    mkdir -p "${durable_dir}"/{inbox,outbox,processed}

    # Copy any existing tmpfs data over before swapping the entry. Use rsync
    # if available (preserves perms + atomic-ish), otherwise cp -a.
    if [[ -d "$tmp_dir" ]] && [[ ! -L "$tmp_dir" ]]; then
        if command -v rsync >/dev/null 2>&1; then
            rsync -a "${tmp_dir}/" "${durable_dir}/"
        else
            cp -a "${tmp_dir}/." "${durable_dir}/"
        fi
        local backup="${tmp_dir}.premigrate.$(date +%s)"
        mv "$tmp_dir" "$backup"
        echo "  ${callsign}: copied data -> ${durable_dir}; tmpfs dir parked at ${backup}"
    fi

    # Atomic-ish symlink replacement: ln -s into a temp name, then mv.
    local tmp_link="${tmp_dir}.linktmp.$$"
    ln -s "$durable_dir" "$tmp_link"
    mv -T "$tmp_link" "$tmp_dir"

    echo "  ${callsign}: ${tmp_dir} -> ${durable_dir} (symlinked)"
}

main() {
    if [[ ! -d "$RELAY_BASE" ]]; then
        echo "FATAL: ${RELAY_BASE} does not exist. See docs/runbooks/relay-tmpfs-migration.md for the one-time setup." >&2
        exit 2
    fi
    if [[ ! -w "$RELAY_BASE" ]]; then
        echo "FATAL: ${RELAY_BASE} is not writable by $(whoami). See runbook." >&2
        exit 2
    fi

    local cmd="${1:-}"
    case "$cmd" in
        --all)
            for cs in "${CALLSIGNS[@]}"; do migrate_one "$cs"; done
            ;;
        "")
            echo "usage: $0 <callsign>|--all" >&2
            exit 1
            ;;
        *)
            migrate_one "$cmd"
            ;;
    esac

    echo "migration: done."
}

main "$@"
