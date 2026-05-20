#!/usr/bin/env bash
# Test for scripts/migrate_relay_tmpfs_to_durable.sh — KEI-142.
#
# Verifies the four behaviours the runbook + acceptance criteria depend on:
#   1. Fresh migration: tmpfs dir -> symlink, data preserved.
#   2. Idempotent: re-running on already-migrated callsign exits 0 with the
#      "already migrated" message and does NOT re-rsync.
#   3. --all migrates every known callsign.
#   4. Missing RELAY_BASE produces a clear fatal exit 2.
#
# Uses temp dirs via AGENCY_OS_RELAY_BASE + AGENCY_OS_TMPFS_BASE so the test
# never touches the real /var/lib or /tmp.

set -euo pipefail

SCRIPT="$(dirname "$0")/../../scripts/migrate_relay_tmpfs_to_durable.sh"
[[ -f "$SCRIPT" ]] || { echo "FAIL: cannot find $SCRIPT" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

TMPFS="${WORK}/tmp"
DURABLE="${WORK}/var-lib-agency-os"
mkdir -p "$TMPFS" "$DURABLE"

pass() { local msg="$1"; echo "  ✓ $msg"; }
fail() { local msg="$1"; echo "  ✗ $msg" >&2; exit 1; }

# -----------------------------------------------------------------------------
# Case 1 — fresh migration preserves data + creates symlink
# -----------------------------------------------------------------------------
echo "Case 1: fresh migration"
mkdir -p "${TMPFS}/telegram-relay-orion/inbox"
echo "sentinel-1" > "${TMPFS}/telegram-relay-orion/inbox/msg1.json"

AGENCY_OS_RELAY_BASE="$DURABLE" \
AGENCY_OS_TMPFS_BASE="$TMPFS" \
    bash "$SCRIPT" orion > /tmp/migrate_test_case1.log

[[ -L "${TMPFS}/telegram-relay-orion" ]] || fail "tmpfs path is not a symlink"
[[ "$(readlink -f "${TMPFS}/telegram-relay-orion")" == "${DURABLE}/relay-orion" ]] \
    || fail "symlink does not resolve to durable target"
[[ -f "${DURABLE}/relay-orion/inbox/msg1.json" ]] || fail "data not migrated"
grep -q "sentinel-1" "${DURABLE}/relay-orion/inbox/msg1.json" || fail "data content lost"
pass "fresh migration: symlink + data integrity"

# -----------------------------------------------------------------------------
# Case 2 — idempotent (re-running is a no-op)
# -----------------------------------------------------------------------------
echo "Case 2: idempotent re-run"
AGENCY_OS_RELAY_BASE="$DURABLE" \
AGENCY_OS_TMPFS_BASE="$TMPFS" \
    bash "$SCRIPT" orion > /tmp/migrate_test_case2.log
grep -q "already migrated" /tmp/migrate_test_case2.log \
    || fail "second run did not detect already-migrated state"
[[ -L "${TMPFS}/telegram-relay-orion" ]] || fail "symlink clobbered on re-run"
pass "idempotent re-run: 'already migrated' detected, symlink intact"

# -----------------------------------------------------------------------------
# Case 3 — --all migrates every callsign that has a tmpfs dir
# -----------------------------------------------------------------------------
echo "Case 3: --all"
# Seed two more callsigns with content; leave others to be created empty.
mkdir -p "${TMPFS}/telegram-relay-atlas/outbox" "${TMPFS}/telegram-relay-scout/processed"
echo "from-atlas" > "${TMPFS}/telegram-relay-atlas/outbox/o1.json"
echo "from-scout" > "${TMPFS}/telegram-relay-scout/processed/p1.json"

AGENCY_OS_RELAY_BASE="$DURABLE" \
AGENCY_OS_TMPFS_BASE="$TMPFS" \
    bash "$SCRIPT" --all > /tmp/migrate_test_case3.log

for cs in elliot aiden max orion atlas scout nova; do
    [[ -L "${TMPFS}/telegram-relay-${cs}" ]] || fail "${cs}: symlink missing after --all"
    [[ -d "${DURABLE}/relay-${cs}/inbox" ]] || fail "${cs}: durable inbox missing"
done
[[ -f "${DURABLE}/relay-atlas/outbox/o1.json" ]] || fail "atlas outbox content lost"
[[ -f "${DURABLE}/relay-scout/processed/p1.json" ]] || fail "scout processed content lost"
pass "--all: all 7 callsigns migrated, seeded content preserved"

# -----------------------------------------------------------------------------
# Case 4 — missing RELAY_BASE -> fatal exit 2
# -----------------------------------------------------------------------------
echo "Case 4: missing relay base"
set +e
AGENCY_OS_RELAY_BASE="${WORK}/does-not-exist" \
AGENCY_OS_TMPFS_BASE="$TMPFS" \
    bash "$SCRIPT" orion 2> /tmp/migrate_test_case4.err
rc=$?
set -e
[[ "$rc" == "2" ]] || fail "expected exit 2 on missing relay base; got ${rc}"
grep -q "does not exist" /tmp/migrate_test_case4.err \
    || fail "missing-relay-base error message not surfaced"
pass "missing relay base: clear fatal exit 2"

echo ""
echo "All 4 cases passed."
