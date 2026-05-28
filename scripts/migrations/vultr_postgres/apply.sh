#!/usr/bin/env bash
# =============================================================================
# KEI-241  Vultr Postgres Migration — apply.sh
# Author:  [AIDEN]
# Date:    2026-05-28
# Branch:  aiden/vultr-postgres-migration
#
# Applies schema + triggers + column migrations against the Vultr Postgres
# instance, then dumps data from Supabase and restores it to Vultr.
#
# DO NOT RUN until Atlas has provisioned the Vultr Postgres instance AND
# VULTR_POSTGRES_DSN is set in the environment.
#
# Hard gate: DECOMMISSION_SUPABASE=true is refused — Supabase stays as
# fallback until KEI-242 (Hindsight backup/restore) completes.
#
# Usage:
#   VULTR_POSTGRES_DSN="postgres://..." \
#   SUPABASE_DATABASE_URL="postgres://..." \
#   bash apply.sh
#
#   Optional:
#     SKIP_DATA_DUMP=true   — run DDL only, skip pg_dump/restore
#     DRY_RUN=true          — print commands, do not execute psql/pg_dump
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Helper: log with timestamp prefix.
# ---------------------------------------------------------------------------
log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

# ---------------------------------------------------------------------------
# Hard gate: refuse if Supabase decommission flag is set.
# Supabase must remain the fallback until KEI-242 completes.
# ---------------------------------------------------------------------------
if [[ "${DECOMMISSION_SUPABASE:-false}" == "true" ]]; then
    echo "ERROR: DECOMMISSION_SUPABASE=true is set. Refusing to run." >&2
    echo "Supabase stays as fallback until KEI-242 (Hindsight backup/restore) completes." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Require env vars.
# ---------------------------------------------------------------------------
if [[ -z "${VULTR_POSTGRES_DSN:-}" ]]; then
    echo "ERROR: VULTR_POSTGRES_DSN is not set." >&2
    echo "Atlas must provision the Vultr Postgres instance before apply.sh can run." >&2
    exit 1
fi

if [[ -z "${SUPABASE_DATABASE_URL:-}" ]]; then
    echo "ERROR: SUPABASE_DATABASE_URL is not set." >&2
    echo "Required to pg_dump operational data from Supabase for restore to Vultr." >&2
    exit 1
fi

DRY_RUN="${DRY_RUN:-false}"
SKIP_DATA_DUMP="${SKIP_DATA_DUMP:-false}"

# Wrapper: honour DRY_RUN for all side-effecting commands.
run() {
    if [[ "${DRY_RUN}" == "true" ]]; then
        echo "[DRY_RUN] $*"
    else
        "$@"
    fi
}

log "KEI-241 Vultr Postgres migration starting."
log "DRY_RUN=${DRY_RUN}  SKIP_DATA_DUMP=${SKIP_DATA_DUMP}"

# ---------------------------------------------------------------------------
# Step 1: Apply DDL migrations (001, 002, 003) against Vultr.
# ---------------------------------------------------------------------------
for migration_file in \
    "${SCRIPT_DIR}/001_schema.sql" \
    "${SCRIPT_DIR}/002_triggers.sql" \
    "${SCRIPT_DIR}/003_add_max_concurrent_tasks.sql"
do
    log "Applying ${migration_file} ..."
    run psql "${VULTR_POSTGRES_DSN}" \
        --set ON_ERROR_STOP=1 \
        --file "${migration_file}"
    log "  done."
done

# ---------------------------------------------------------------------------
# Step 2: Dump data from Supabase and restore to Vultr.
#
# Tables are listed in FK-safe order (parents before children):
#   1. ceo_memory               — no FKs
#   2. tasks                    — no FKs into other migrated tables
#   3. task_verifications       — FK → tasks.id
#   4. completion_sync_queue    — FK → tasks.id
#   5. keiracom_tenants         — no FKs
#   6. keiracom_spawn_attribution — no FKs
#   7. keiracom_paused_tasks    — no FKs
#
# pg_dump flags:
#   --data-only          — schema already applied; only rows needed
#   --disable-triggers   — suppress trigger fire during restore (avoids
#                          write-guard + verify-before-done false positives
#                          on data that was already valid in Supabase)
#   --no-owner           — Vultr role hierarchy may differ
#   --no-privileges      — GRANTs re-applied separately if needed
#   --column-inserts     — portable INSERT statements (safer across versions)
# ---------------------------------------------------------------------------

if [[ "${SKIP_DATA_DUMP}" == "true" ]]; then
    log "SKIP_DATA_DUMP=true — skipping pg_dump/restore step."
else
    TABLES=(
        "public.ceo_memory"
        "public.tasks"
        "public.task_verifications"
        "public.completion_sync_queue"
        "public.keiracom_tenants"
        "public.keiracom_spawn_attribution"
        "public.keiracom_paused_tasks"
    )

    # Build --table flags list.
    TABLE_FLAGS=()
    for tbl in "${TABLES[@]}"; do
        TABLE_FLAGS+=("--table=${tbl}")
    done

    log "Dumping data from Supabase (${#TABLES[@]} tables) ..."
    DUMP_FILE="$(mktemp /tmp/kei241_dump.XXXXXX.sql)"
    # shellcheck disable=SC2064
    trap "rm -f '${DUMP_FILE}'" EXIT

    run pg_dump \
        "${SUPABASE_DATABASE_URL}" \
        --data-only \
        --disable-triggers \
        --no-owner \
        --no-privileges \
        --column-inserts \
        "${TABLE_FLAGS[@]}" \
        --file "${DUMP_FILE}"

    log "Dump written to ${DUMP_FILE}."

    log "Restoring data to Vultr ..."
    run psql "${VULTR_POSTGRES_DSN}" \
        --set ON_ERROR_STOP=1 \
        --file "${DUMP_FILE}"
    log "Restore complete."
fi

# ---------------------------------------------------------------------------
# Step 3: Run validation script.
# ---------------------------------------------------------------------------
VALIDATE_SCRIPT="${SCRIPT_DIR}/../../vultr_validate.py"

if [[ -f "${VALIDATE_SCRIPT}" ]]; then
    log "Running validation: ${VALIDATE_SCRIPT} ..."
    run python3 "${VALIDATE_SCRIPT}"
    log "Validation passed."
else
    log "WARNING: Validation script not found at ${VALIDATE_SCRIPT} — skipping."
fi

log "KEI-241 apply.sh complete."
