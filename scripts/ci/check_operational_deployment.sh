#!/usr/bin/env bash
# check_operational_deployment.sh — fail CI when shipped code lacks operational wiring.
#
# Two checks per KEI-108 Part 2:
#   1. New *.service files anywhere in the repo must have a matching install line
#      in a scripts/install*.sh file OR an acceptance test that references the
#      unit. Repo-wide scan — service files have lived in infra/systemd/,
#      infra/cron/, infra/relay/, infra/opa/, infra/observability/, infra/coo/,
#      systemd/, and more; a paths: filter scoped only to a subset would
#      re-introduce the same blind spot KEI-108 was opened to close.
#   2. New FastAPI APIRouter definitions in src/api/webhooks/*.py must have a
#      matching `from src.api.webhooks.X import` in src/api/main.py AND a
#      `include_router(...)` call. The existing-working pattern (linear.py)
#      keeps the `src.` prefix on imports — the check mirrors that exactly.
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

# Check 1 — any new *.service file anywhere must have a matching installer/acceptance reference.
while IFS= read -r svc; do
  [ -z "$svc" ] && continue
  unit="$(basename "$svc" .service)"
  if ! git grep -l "${unit}\.service" -- 'scripts/install*' 'scripts/**/install*.sh' 'scripts/**/*acceptance*.sh' >/dev/null 2>&1; then
    fail "Operational-deployment gap: $svc has no matching scripts/install*.sh entry or acceptance test referencing ${unit}.service. See KEI-108 sweep audit (bd Agency_OS-rom)."
  fi
done < <(added_files '*.service')

# Check 2 — new APIRouter under src/api/webhooks/ needs src. -prefixed import + include_router in main.py.
while IFS= read -r handler; do
  [ -z "$handler" ] && continue
  router_var=$(grep -oE '^[a-zA-Z_][a-zA-Z0-9_]* *= *APIRouter' "$handler" | head -1 | awk '{print $1}')
  [ -z "$router_var" ] && continue
  module="src.${handler#src/}"; module="${module%.py}"; module="${module//\//.}"
  if ! grep -qE "from ${module} import" src/api/main.py 2>/dev/null; then
    fail "Operational-deployment gap: $handler defines '$router_var' but src/api/main.py has no 'from ${module} import …' (router unreachable). See KEI-108 sweep audit (bd Agency_OS-rom)."
  elif ! grep -qE "app\.include_router\(" src/api/main.py 2>/dev/null || ! grep -B1 "app\.include_router" src/api/main.py | grep -q "${module}"; then
    fail "Operational-deployment gap: $handler is imported but never passed to app.include_router(...) in src/api/main.py. See KEI-108 sweep audit (bd Agency_OS-rom)."
  fi
done < <(added_files 'src/api/webhooks/*.py')

exit "$FAILED"
