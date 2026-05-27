#!/usr/bin/env bash
# Cache-write-TTL-5-min-default CI guard.
#
# Enforces the Cutover Readiness Gate INFRASTRUCTURE-SIDE criterion:
#   "cache write TTL 5-minute"
# (RATIFIED-CEO Cat 21 lever 29, Dave directive 2026-05-27.)
#
# WHY:
# Anthropic prompt caching defaults to 5-minute TTL when cache_control is
# `{"type": "ephemeral"}` (no "ttl" key). Adding `{"ttl": "1h"}` switches
# to the 1-hour write path — Opus 4.x cache_write_1h ~$30/M vs cache_write_5m
# ~$18.75/M published rates → 37% delta on the cache-write cost line per
# Atlas empirical measurement 2026-05-27. The Cutover Gate locks the 5-min
# default; ad-hoc 1h adds slip cost discipline silently.
#
# DETECTION:
# Greps for `"ttl"` literal-string adjacent to a `"1h"` value within
# src/ + scripts/. Pattern catches both single-line dict literals + multi-
# line dict assignments via a per-file-collapsed line scan.
#
# EXEMPT:
# - Documentation paths under docs/ (allowed to describe the trade-off).
# - This guard's own script + the cost-rollup script (PR #1202) which lists
#   1h pricing as REFERENCE not a CACHE_CONTROL setting.
#
# COMPLEMENTS:
# - tests/keiracom_system/cache/test_litellm_helpers.py
#   ::test_ephemeral_cache_control_is_5min_default_no_ttl_key — type-level
#   lock on the canonical default constant.
# - This guard — cross-codebase enforcement on ad-hoc cache_control dicts.
#
# Pattern shape mirrors PR #1169 boundary-matrix-v1 + PR #1173 cache-
# discipline + PR #1185 atom-store-discipline + PR #1198 composer-isolation.

set -euo pipefail

SCOPE_SRC="src"
SCOPE_SCRIPTS="scripts"

# Pattern: any cache_control-style "ttl" key with "1h" string value, allowing
# whitespace + the python dict-literal punctuation. Matches both:
#   {"type": "ephemeral", "ttl": "1h"}
#   "ttl":"1h"
#   "ttl": "1h",
PATTERN='"ttl"[[:space:]]*:[[:space:]]*"1h"'

raw=""
if [ -d "$SCOPE_SRC" ]; then
  raw="$raw
$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE_SRC" 2>/dev/null || true)"
fi
if [ -d "$SCOPE_SCRIPTS" ]; then
  raw="$raw
$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE_SCRIPTS" 2>/dev/null || true)"
fi

# Strip:
#  - Python comment lines (text starting with `#`). The pattern is allowed
#    to appear in DOCUMENTATION describing the anti-pattern; only RUNTIME
#    code adds count as violations.
#  - exempt paths: cost-rollup script lists 1h pricing as REFERENCE not a
#    cache_control SETTING (PR #1202 ships those rates as cost-calc inputs);
#    this guard's own self-test offender (synthetic test fixture).
hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^[^:]+\.py:[0-9]+:[[:space:]]*#' \
  | grep -v -E '^scripts/agency_cost_rollup\.py:' \
  | grep -v -E '^scripts/ci/check_no_1h_cache_ttl\.sh' \
  | grep -v -E '^[[:space:]]*$' || true)

if [ -n "$hits" ]; then
  echo "FAIL (cache-write-ttl-5min): cache_control 'ttl: 1h' literal found"
  echo "in src/ or scripts/. This violates the Cutover Readiness Gate"
  echo "INFRASTRUCTURE-SIDE criterion 'cache write TTL 5-minute' (RATIFIED-CEO"
  echo "Cat 21 lever 29, Dave directive 2026-05-27)."
  echo ""
  echo "Anthropic cache_write_1h ~\$30/M (Opus 4.x) vs cache_write_5m ~\$18.75/M"
  echo "→ 37% delta on the cache-write cost line per Atlas empirical 2026-05-27."
  echo ""
  echo "Fix: drop the 'ttl' key from the cache_control dict — bare"
  echo "{\"type\": \"ephemeral\"} = 5-minute Anthropic default."
  echo ""
  echo "If a SPECIFIC caller has a justified need for 1h (slow-changing prompt"
  echo "that survives long idle windows): exempt that one line via comment +"
  echo "extend this guard's exempt list with the file path + document the cost"
  echo "justification in the PR body."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (cache-write-ttl-5min): no 1h cache_control ttl literals outside exempt paths."
exit 0
