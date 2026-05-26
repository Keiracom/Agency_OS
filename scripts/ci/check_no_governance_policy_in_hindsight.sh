#!/usr/bin/env bash
# boundary-matrix-v1 Guard (d) — governance policy must not be written to
# Cognee/Hindsight memory.
#
# Canonical source: ceo:boundary_matrix_v1 boundary_violations_to_police entry
# "Cognee/Hindsight must NOT store governance policy". Policy-vs-memory test
# (Aiden+Viktor NIT 1): would this content read the same way for ANY tenant?
# Yes → Policy → Supabase ceo_memory keys + governance laws + orchestrator
# runbook. Tenant-specific → Memory → mem.wrap.* per-tenant via Hindsight
# TenantExtension.
#
# Heuristic: governance policy keys carry the `ceo:` prefix (e.g.
# `ceo:boundary_matrix_v1`, `ceo:memory_abstraction_layer_v1`). If a Hindsight
# wrapper or Cognee call-site passes a QUOTED string literal starting with
# `ceo:`, that's a policy write to the memory layer — a boundary violation.
#
# Allowed: citation prose in docstrings/comments referencing `ceo:foo` without
# surrounding quotes — that's documentation about WHAT the wrapper implements
# per the audit-dispatch checklist, not a runtime write.
#
# Scope: src/keiracom_system/memory/ (Hindsight wrappers + their callers)
# Pattern: `"ceo:` or `'ceo:` (a string literal opening) in code lines.
#
# Filed under Agency_OS-9cgr (#10028 follow-up).

set -euo pipefail

SCOPE="src/keiracom_system/memory"

if [ ! -d "$SCOPE" ]; then
  echo "OK (d): $SCOPE not present — guard inactive."
  exit 0
fi

# Match a quote-delimited string literal opening with `ceo:`. Both `"ceo:` and
# `'ceo:` covered. Citation prose like `ceo:memory_abstraction_layer_v1` in a
# docstring (without surrounding quotes) does NOT match — that's policy
# documentation, not a runtime write.
PATTERN='["'"'"']ceo:'

hits=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

if [ -n "$hits" ]; then
  echo "FAIL (d): governance policy key (ceo:*) written as string literal in"
  echo "Hindsight wrapper code. Per ceo:boundary_matrix_v1 policy-vs-memory"
  echo "test, ceo:* keys are policy → Supabase ceo_memory, NOT memory →"
  echo "Hindsight. Move the write to a control-plane / ceo_memory pathway."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (d): no governance policy keys written to Hindsight."
exit 0
