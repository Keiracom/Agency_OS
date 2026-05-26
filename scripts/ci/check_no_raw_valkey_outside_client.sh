#!/usr/bin/env bash
# Phase A7 CB-10 guard — direct redis/valkey imports forbidden outside the
# cache layer. All Valkey access MUST go through ValkeyClient — importing
# redis/valkey directly elsewhere in src/keiracom_system/ creates a parallel
# path that bypasses the tenant-prefix invariant + cross-tenant isolation
# guarantee enforced at ValkeyClient.canonical_cache_key() + _enforce_tenant_prefix().
#
# Canonical source: docs/architecture/design/a7_cache_architecture.md §13 CB-10
# Complements: src/keiracom_system/cache/valkey_client.py _enforce_tenant_prefix()
# (defence-in-depth — linter catches at PR-review time; runtime guard catches
# at read/write boundary at request time)
#
# Pattern shape mirrors boundary-matrix-v1 guard (b) (PR #1169 import-detection).
# Detecting calls (e.g. `client.set(...)`) would require flow analysis; the
# import barrier is the chokepoint — no import = no call.
#
# Scope: src/keiracom_system/ ONLY. Legacy Agency_OS BDR surface in
# src/pipeline/ uses redis for KEI-117 rate limiting + KV state, which is
# out-of-scope for this cache-layer rule (separate concern; would be caught
# by the boundary-matrix-v1 expansion at 3-repo carve-out per Phase 2.0).
#
# Exempt paths inside scope:
#   - src/keiracom_system/cache/  (the canonical cache module)
#
# Pattern: `import redis` / `from redis` / `import valkey` / `from valkey`
# at start-of-line.

set -euo pipefail

SCOPE="src/keiracom_system"

if [ ! -d "$SCOPE" ]; then
  echo "OK (cache-discipline): $SCOPE not present — guard inactive."
  exit 0
fi

PATTERN='^[[:space:]]*(import[[:space:]]+(redis|valkey)|from[[:space:]]+(redis|valkey)(\.|[[:space:]]))'

raw=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

# Exempt the cache module — ValkeyClient lives there and legitimately imports redis.
hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^src/keiracom_system/cache/' \
  | grep -v -E '^[[:space:]]*$' || true)

if [ -n "$hits" ]; then
  echo "FAIL (cache-discipline): direct redis/valkey imports found outside"
  echo "src/keiracom_system/cache/. All Valkey access MUST go through"
  echo "ValkeyClient to preserve the tenant-prefix invariant + cross-tenant"
  echo "isolation guarantee. Route the call through ValkeyClient or move the"
  echo "module under src/keiracom_system/cache/ if it IS a cache-layer module."
  echo ""
  echo "See docs/architecture/design/a7_cache_architecture.md §13 CB-10."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (cache-discipline): no raw redis/valkey imports outside cache module."
exit 0
