#!/usr/bin/env bash
# CI guard: verify all wiring points named in dispatcher_wiring_inventory_kei213.md
# exist. Mirrors PR #1221 but targets the CANONICAL KEI-213 dispatcher per Dave +
# Aiden + Viktor ratify 2026-05-27.
#
# bd: cutover-step-4.5-dispatcher-wiring-pr-E (KEI-213 mirror of PR #1221)

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

echo "=== KEI-213 Dispatcher wiring inventory verification ==="

# Canonical KEI-213 dispatcher entry-points.
assert_exists "src/dispatcher/main.py"               "KEI-213 canonical dispatcher entry (Dave/Aiden/Viktor ratify 2026-05-27)"
assert_exists "src/dispatcher/interceptor_proxy.py"  "KEI-213 LLM-call interceptor"
assert_exists "src/dispatcher/governance_proxy.py"   "KEI-213 governance proxy"

# Lib modules from PRs #1202-#1211 (wiring preconditions).
assert_exists "src/dispatcher/idempotency.py"                       "PR #1204 idempotency module (cutover-blocker 5)"
assert_exists "src/relay/budget_ceiling.py"                         "PR #1203 budget ceiling module (cutover-blocker 2)"
assert_exists "src/relay/context_budget.py"                         "PR #1210 context_budget module (cutover-blocker 3)"
assert_exists "src/keiracom_system/attribution/logger.py"           "PR #1207 spawn-attribution module (cutover-blocker 6)"
assert_exists "scripts/agency_cost_rollup.py"                       "PR #1202 cost rollup script (cutover-blocker 1)"
assert_exists "scripts/cache_hit_rate_ingest.py"                    "PR #1208 cache hit-rate ingest (cutover-blocker 9)"
assert_exists "scripts/cache_hit_rate_alert.py"                     "PR #1208 cache hit-rate alert (cutover-blocker 9)"
assert_exists "scripts/install_cache_hit_rate.sh"                   "PR #1208 cache hit-rate installer (cutover-blocker 9)"
assert_exists "docs/architecture/ephemeral_persistence_boundary.md" "PR #1206 persistence boundary spec (cutover-blocker 8)"

# Systemd units from PR #1208 cache hit-rate observability.
assert_exists "systemd/cache_hit_rate_ingest.service"               "PR #1208 ingest systemd service"
assert_exists "systemd/cache_hit_rate_ingest.timer"                 "PR #1208 ingest systemd timer"
assert_exists "systemd/cache_hit_rate_alert.service"                "PR #1208 alert systemd service"
assert_exists "systemd/cache_hit_rate_alert.timer"                  "PR #1208 alert systemd timer"

# CI guard from PR #1205 cache write TTL.
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

# KEI-213 wiring inventory doc itself.
assert_exists "docs/architecture/dispatcher_wiring_inventory_kei213.md"  "KEI-213 wiring inventory doc (this PR)"

echo ""
if [[ $errors -eq 0 ]]; then
    echo "OK — all KEI-213 wiring preconditions present (canonical entry + 9 launch-blocker libs + inventory doc)"
    exit 0
else
    echo "FAIL — $errors wiring point(s) missing"
    exit 1
fi
