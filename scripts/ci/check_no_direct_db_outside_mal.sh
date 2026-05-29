#!/usr/bin/env bash
# boundary-matrix-v1 Guard (b) — direct DB drivers forbidden outside MAL +
# control_plane wrappers.
#
# Canonical source: ceo:boundary_matrix_v1 boundary_violations_to_police entry
# "Memory writes that bypass MAL wrappers must fail in CI". MAL owns memory
# reads/writes; control_plane (when built) owns supabase-layer durable-state
# writes (ceo_memory, governance audit). Anywhere else hitting asyncpg/psycopg
# raw is a boundary violation.
#
# Scope: src/keiracom_system/ ONLY. Legacy Agency_OS BDR pipeline code in
# src/pipeline/ + src/orchestration/flows/ is out of scope — that surface
# separates out per the 3-repo split (ceo:agency_os_keiracom_separation_v1).
# When that split lands, the Keiracom-side repo inherits this guard against
# its full src/.
#
# Exempt paths inside scope:
#   - src/keiracom_system/memory/        (MAL — canonical owner per layer matrix)
#   - src/keiracom_system/control_plane/ (supabase-layer interface, to be built)
#   - src/keiracom_system/vault/agent_cold_start.py (bootstrap entrypoint: runs
#     in a scrubbed env BEFORE the MAL is available; psycopg is the only path
#     to the task row before Vault credentials are resolved. Tracked under
#     Agency_OS-zr7e.5 for future migration to control_plane once built.)
#   - src/keiracom_system/atomization/decisions_backfill.py (CLI entrypoint for
#     the one-time ceo_memory→Hindsight backfill — NOT in the agent hot path.
#     psycopg is imported only inside the CLI main()'s _connect_cursor(); the
#     library functions (run_direct/build_atom_from_source) take an injected db.
#     Same rationale as vault/agent_cold_start.py. Agency_OS-c66k.)
#
# Pattern: `import asyncpg` / `from asyncpg` / `import psycopg` / `from psycopg`
# at start-of-line.
#
# Filed under Agency_OS-9cgr (#10028 follow-up).

set -euo pipefail

SCOPE="src/keiracom_system"

if [ ! -d "$SCOPE" ]; then
  echo "OK (b): $SCOPE not present — guard inactive."
  exit 0
fi

PATTERN='^[[:space:]]*(import[[:space:]]+(asyncpg|psycopg)|from[[:space:]]+(asyncpg|psycopg)(\.|[[:space:]]|_))'

# Collect hits, then filter out exempt paths.
raw=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^src/keiracom_system/memory/' \
  | grep -v -E '^src/keiracom_system/control_plane/' \
  | grep -v -E '^src/keiracom_system/vault/agent_cold_start\.py' \
  | grep -v -E '^src/keiracom_system/atomization/decisions_backfill\.py' \
  | grep -v -E '^[[:space:]]*$' || true)

if [ -n "$hits" ]; then
  echo "FAIL (b): direct asyncpg/psycopg imports found outside MAL +"
  echo "control_plane wrappers. All memory reads/writes route through"
  echo "src/keiracom_system/memory/; all supabase-layer durable-state writes"
  echo "route through src/keiracom_system/control_plane/. See"
  echo "ceo:boundary_matrix_v1 and docs/governance/boundary_matrix_v1.md."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (b): no direct DB drivers outside MAL + control_plane."
exit 0
