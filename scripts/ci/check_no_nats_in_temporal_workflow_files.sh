#!/usr/bin/env bash
# boundary-matrix-v1 Guard (a) — NATS forbidden in Temporal workflow files.
#
# Canonical source: ceo:boundary_matrix_v1 layer_ownership_contracts +
# boundary_violations_to_police entry "NATS must NOT carry workflow state".
# Observability fan-out is categorically distinct from workflow state transport
# per Viktor NIT 2 disambiguation — observability code does not live in
# src/keiracom_system/temporal/.
#
# Scope: src/keiracom_system/temporal/ + tests/keiracom_system/temporal/
# Pattern: `import nats` or `from nats` at start-of-line (Python import syntax)
# Exit: 1 on any match, 0 on clean.
#
# Filed under Agency_OS-9cgr (#10028 follow-up).

set -euo pipefail

ROOTS=(
  "src/keiracom_system/temporal"
  "tests/keiracom_system/temporal"
)

EXISTING_ROOTS=()
for root in "${ROOTS[@]}"; do
  if [ -d "$root" ]; then
    EXISTING_ROOTS+=("$root")
  fi
done

if [ ${#EXISTING_ROOTS[@]} -eq 0 ]; then
  echo "OK (a): no Temporal workflow directories present yet — guard inactive."
  exit 0
fi

# Match `import nats` or `from nats[.module] import ...` at line start.
# `-E` extended regex; `^` anchors to start-of-line; `[[:space:]]*` tolerates
# leading whitespace inside conditionally-imported blocks.
PATTERN='^[[:space:]]*(import[[:space:]]+nats|from[[:space:]]+nats(\.|[[:space:]]))'

hits=$(grep -rnE --include='*.py' "$PATTERN" "${EXISTING_ROOTS[@]}" 2>/dev/null || true)

if [ -n "$hits" ]; then
  echo "FAIL (a): NATS imports found in Temporal workflow files."
  echo "Boundary violation per ceo:boundary_matrix_v1 — Temporal workflows must"
  echo "use Temporal Signals for workflow-to-workflow, not NATS. NATS layer is"
  echo "reserved for real-time fan-out (<100ms) + observability heartbeats."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (a): no NATS imports in Temporal workflow files."
exit 0
