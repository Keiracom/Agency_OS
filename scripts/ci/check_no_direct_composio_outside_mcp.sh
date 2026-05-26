#!/usr/bin/env bash
# boundary-matrix-v1 Guard (c) — Composio imports forbidden outside MCP layer.
#
# Canonical source: ceo:boundary_matrix_v1 boundary_violations_to_police entry
# "Agents must NEVER bypass MCP for convenience tool calls". Composio is a
# tool-aggregation library; tool authorization + per-tenant allowed-set is
# MCP's responsibility per layer_ownership_contracts.mcp. Direct Composio
# imports anywhere outside src/keiracom_system/mcp/ route around the MCP
# permission boundary.
#
# Scope: src/keiracom_system/ ONLY. Same rationale as guard (b): legacy
# Agency_OS BDR surface is out of scope until 3-repo split (per
# ceo:agency_os_keiracom_separation_v1) hands enforcement to the Keiracom
# repo.
#
# Exempt path: src/keiracom_system/mcp/
# Pattern: `import composio` / `from composio` at start-of-line.
#
# Filed under Agency_OS-9cgr (#10028 follow-up).

set -euo pipefail

SCOPE="src/keiracom_system"

if [ ! -d "$SCOPE" ]; then
  echo "OK (c): $SCOPE not present — guard inactive."
  exit 0
fi

PATTERN='^[[:space:]]*(import[[:space:]]+composio|from[[:space:]]+composio(\.|[[:space:]]))'

raw=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^src/keiracom_system/mcp/' \
  | grep -v -E '^[[:space:]]*$' || true)

if [ -n "$hits" ]; then
  echo "FAIL (c): direct Composio imports found outside MCP layer."
  echo "Tool authorization + per-tenant allowed set is MCP's responsibility"
  echo "(ceo:boundary_matrix_v1 layer_ownership_contracts.mcp). Route all"
  echo "Composio calls through src/keiracom_system/mcp/."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (c): no Composio imports outside MCP layer."
exit 0
