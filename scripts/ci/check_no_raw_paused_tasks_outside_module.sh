#!/usr/bin/env bash
# Phase A8 §7 piece 2 guard — direct SQL on `keiracom_paused_tasks` forbidden
# outside the paused_tasks module. All access MUST go through PausedTaskStore
# so the tenant-prefix invariant + cross-tenant isolation guarantee enforced
# at PausedTaskStore.__init__ + every method holds.
#
# Pattern shape mirrors:
# - A7 CB-10 cache-discipline (PR #1173 scripts/ci/check_no_raw_valkey_outside_client.sh)
# - boundary-matrix-v1 guard (b) (PR #1169 scripts/ci/check_no_direct_db_outside_mal.sh)
# - atomization atom-store discipline (PR #1185 check_no_raw_atom_store_outside_module.sh)
#
# Defence-in-depth: app-layer PausedTaskStore enforces; this PR-linter
# catches at review time + the runtime guard catches at request time.
#
# Scope: src/keiracom_system/ ONLY. Legacy src/pipeline/ + src/orchestration/
# are out of scope until the 3-repo carve-out (Phase 2.0).
#
# Exempt path inside scope:
#   - src/keiracom_system/paused_tasks/  (canonical module)
#
# Pattern: SQL writes/reads against keiracom_paused_tasks. Detection is
# substring-level (not full SQL parsing) — false-positive on prose in
# comments is acceptable per Scout-shape (CB-10) precedent; reviewer
# whitelists prose hits via `# noqa: paused_tasks_guard` if needed.
#
# bd: Agency_OS-70hb

set -euo pipefail

SCOPE="src/keiracom_system"

if [ ! -d "$SCOPE" ]; then
  echo "OK (paused-tasks-discipline): $SCOPE not present — guard inactive."
  exit 0
fi

PATTERN='\b(INSERT[[:space:]]+INTO[[:space:]]+(public\.)?keiracom_paused_tasks|UPDATE[[:space:]]+(public\.)?keiracom_paused_tasks|DELETE[[:space:]]+FROM[[:space:]]+(public\.)?keiracom_paused_tasks|SELECT[[:space:]].+FROM[[:space:]]+(public\.)?keiracom_paused_tasks)'

raw=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^src/keiracom_system/paused_tasks/' \
  | grep -v -E '^[[:space:]]*$' \
  | grep -v -E '#[[:space:]]*noqa:[[:space:]]*paused_tasks_guard' || true)

if [ -n "$hits" ]; then
  echo "FAIL (paused-tasks-discipline): direct SQL on keiracom_paused_tasks"
  echo "found outside src/keiracom_system/paused_tasks/. All access MUST go"
  echo "through PausedTaskStore to preserve the tenant-prefix invariant +"
  echo "cross-tenant isolation guarantee. Route through PausedTaskStore or"
  echo "move the module under src/keiracom_system/paused_tasks/ if it IS"
  echo "a paused-tasks-layer module."
  echo ""
  echo "See PR #1140 §5 + §7 piece 2 + Agency_OS-70hb."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (paused-tasks-discipline): no raw SQL on keiracom_paused_tasks outside module."
exit 0
