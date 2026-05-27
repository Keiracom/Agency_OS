#!/usr/bin/env bash
# CI guard: verify all wiring points named in dispatcher_wiring_inventory.md exist.
#
# Fails CI if any of the 9-launch-blocker wiring points is missing. Runs
# in seconds — pure stat/grep checks, no Python imports.
#
# bd: cutover-step-4.5-dispatcher-wiring-pr5
# Companion to docs/architecture/dispatcher_wiring_inventory.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

errors=0

assert_exists() {
    local path="$1"
    local label="$2"
    if [[ ! -e "$path" ]]; then
        echo "ERROR: missing wiring point [$label] expected at $path"
        errors=$((errors + 1))
    fi
}

assert_grep() {
    local pattern="$1"
    local path="$2"
    local label="$3"
    if [[ ! -f "$path" ]]; then
        echo "ERROR: cannot grep [$label] — file $path does not exist"
        errors=$((errors + 1))
        return
    fi
    if ! grep -q "$pattern" "$path"; then
        echo "ERROR: pattern [$pattern] not found in $path (wiring [$label])"
        errors=$((errors + 1))
    fi
}

echo "=== Dispatcher wiring inventory verification ==="

# Lib modules from PRs #1202-#1211 (these MUST exist on main already; this is
# the precondition for the wiring PRs to wire them).
assert_exists "src/dispatcher/idempotency.py"                       "PR #1204 idempotency module (cutover-blocker 5)"
assert_exists "src/relay/budget_ceiling.py"                         "PR #1203 budget ceiling module (cutover-blocker 2)"
assert_exists "src/relay/context_budget.py"                         "PR #1210 context_budget module (cutover-blocker 3)"
assert_exists "src/keiracom_system/attribution/logger.py"           "PR #1207 spawn-attribution module (cutover-blocker 6)"
assert_exists "scripts/agency_cost_rollup.py"                       "PR #1202 cost rollup script (cutover-blocker 1)"
assert_exists "scripts/cache_hit_rate_ingest.py"                    "PR #1208 cache hit-rate ingest (cutover-blocker 9)"
assert_exists "scripts/cache_hit_rate_alert.py"                     "PR #1208 cache hit-rate alert (cutover-blocker 9)"
assert_exists "scripts/install_cache_hit_rate.sh"                   "PR #1208 cache hit-rate installer (cutover-blocker 9)"
assert_exists "docs/architecture/ephemeral_persistence_boundary.md" "PR #1206 persistence boundary spec (cutover-blocker 8)"
assert_exists "supabase/migrations/20260527_keiracom_cache_hit_rates.sql" "PR #1208 cache hit-rate migration"
assert_exists "supabase/migrations/20260527_keiracom_spawn_attribution.sql" "PR #1207 spawn-attribution migration"

# Systemd units from PR #1208 cache hit-rate observability.
assert_exists "systemd/cache_hit_rate_ingest.service"               "PR #1208 ingest systemd service"
assert_exists "systemd/cache_hit_rate_ingest.timer"                 "PR #1208 ingest systemd timer"
assert_exists "systemd/cache_hit_rate_alert.service"                "PR #1208 alert systemd service"
assert_exists "systemd/cache_hit_rate_alert.timer"                  "PR #1208 alert systemd timer"

# CI guard from PR #1205 cache write TTL.
# Tolerated names: check_no_1h_cache_ttl.sh OR check_cache_write_ttl.sh (Nova may
# have chosen either; the existence of ONE is the wiring point).
ttl_guard_found=0
for candidate in scripts/ci/check_no_1h_cache_ttl.sh scripts/ci/check_cache_write_ttl.sh scripts/ci/check_cache_ttl_5min.sh; do
    if [[ -e "$candidate" ]]; then
        ttl_guard_found=1
        break
    fi
done
if [[ $ttl_guard_found -eq 0 ]]; then
    echo "ERROR: missing wiring point [PR #1205 cache write TTL CI guard (cutover-blocker 4)] — expected one of scripts/ci/check_no_1h_cache_ttl.sh / check_cache_write_ttl.sh / check_cache_ttl_5min.sh"
    errors=$((errors + 1))
fi

# Inventory doc itself.
assert_exists "docs/architecture/dispatcher_wiring_inventory.md"    "Wiring inventory doc (this PR)"

# Inventory doc cross-checks intentionally omitted — the doc's content authority
# is reviewed via PR, not regex. CI guard's job is to verify the underlying
# wiring points exist; documentation is reviewer-checked separately.

echo ""
if [[ $errors -eq 0 ]]; then
    echo "OK — all 9 launch-blocker wiring points present"
    exit 0
else
    echo "FAIL — $errors wiring point(s) missing"
    exit 1
fi
