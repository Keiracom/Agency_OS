#!/usr/bin/env bash
# check_operational_deployment.sh — fail CI when shipped code lacks operational wiring.
#
# Two checks per KEI-108 Part 2:
#   1. New *.service files (under infra/systemd/ or systemd/) must have a matching
#      install line in a scripts/install*.sh file OR an acceptance test that calls
#      `systemctl --user is-active` against the unit.
#   2. New FastAPI APIRouter definitions in src/api/webhooks/*.py must have a
#      matching app.include_router(...) call in src/api/main.py.
#
# Runs against the PR diff vs origin/<BASE_REF>. Exits 0 on pass, 1 on fail.

set -euo pipefail

BASE_REF="${BASE_REF:-main}"
git fetch --no-tags --depth=1 origin "$BASE_REF" >/dev/null 2>&1 || true

added_files() {
  git diff --name-only --diff-filter=A "origin/${BASE_REF}...HEAD" -- "$@"
}

fail() {
  echo "::error::$*"
  FAILED=1
}

FAILED=0

# Check 1 — new *.service files need an install line.
for svc in $(added_files 'infra/systemd/**/*.service' 'systemd/**/*.service'); do
  unit="$(basename "$svc" .service)"
  install_hits=$(git grep -l --untracked "${unit}\\.service" -- 'scripts/install*' 'scripts/**/install*.sh' 'scripts/**/*acceptance*.sh' 2>/dev/null || true)
  if [ -z "$install_hits" ]; then
    fail "Operational-deployment gap: $svc has no matching scripts/install*.sh entry or acceptance test referencing ${unit}.service. See KEI-108 sweep audit (Agency_OS-rom)."
  fi
done

# Check 2 — new APIRouter in src/api/webhooks/ needs include_router in src/api/main.py.
for handler in $(added_files 'src/api/webhooks/*.py'); do
  router_name=$(grep -oE '^[a-zA-Z_][a-zA-Z0-9_]* *= *APIRouter' "$handler" | head -1 | awk '{print $1}')
  if [ -z "$router_name" ]; then
    continue
  fi
  module_path=$(echo "$handler" | sed 's|/|.|g; s|\.py$||; s|^src\.||')
  if ! grep -qE "from ${module_path} import|import ${module_path}" src/api/main.py 2>/dev/null; then
    fail "Operational-deployment gap: $handler defines '$router_name' but src/api/main.py does not import from ${module_path}. See KEI-108 sweep audit (Agency_OS-rom)."
  elif ! grep -qE "app\\.include_router\\([^)]*${router_name}" src/api/main.py 2>/dev/null; then
    fail "Operational-deployment gap: $handler defines '$router_name' but src/api/main.py does not include_router(${router_name}). See KEI-108 sweep audit (Agency_OS-rom)."
  fi
done

exit "$FAILED"
