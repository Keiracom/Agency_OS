#!/usr/bin/env bash
# backup_postgres.sh — KEI-126 nightly Postgres backup to S3-compatible store.
#
# Runs via systemd timer (postgres-backup.timer) at 01:00 UTC daily.
# pg_dump custom-format compressed snapshot → uploads to Vultr Object Store
# (S3-compatible API) → prunes anything older than POSTGRES_BACKUP_RETENTION_DAYS.
#
# Fail-loud: any error exits non-zero so the systemd unit records OnFailure
# and the operator gets paged. NEVER swallow backup failures silently.
#
# Required env (from /home/elliotbot/.config/agency-os/.env):
#   DATABASE_URL or SUPABASE_DB_URL    Postgres DSN. +asyncpg suffix stripped.
#   AWS_S3_BUCKET                       Vultr Object Store bucket name.
#   AWS_S3_ENDPOINT                     Vultr Object Store endpoint URL.
#   AWS_ACCESS_KEY_ID                   S3 key id.
#   AWS_SECRET_ACCESS_KEY               S3 secret.
#
# Optional env:
#   POSTGRES_BACKUP_RETENTION_DAYS      Default 7. Snapshots older than this
#                                       are pruned from the bucket each run.
#   POSTGRES_BACKUP_PREFIX              S3 key prefix. Default 'postgres/'.
#
# Usage (manual):
#   bash scripts/backup_postgres.sh
#
# Usage (systemd):
#   systemctl --user start postgres-backup.service
#
# Anchored unit: postgres-backup.service

set -euo pipefail

# ----- 1. Required env -----
DSN="${DATABASE_URL:-${SUPABASE_DB_URL:-}}"
if [[ -z "${DSN}" ]]; then
    echo "backup_postgres: DATABASE_URL / SUPABASE_DB_URL must be set" >&2
    exit 2
fi
# Strip +asyncpg suffix — pg_dump uses libpq, not asyncpg.
DSN="${DSN/+asyncpg/}"

: "${AWS_S3_BUCKET:?backup_postgres: AWS_S3_BUCKET required}"
: "${AWS_S3_ENDPOINT:?backup_postgres: AWS_S3_ENDPOINT required (Vultr Object Store URL)}"
: "${AWS_ACCESS_KEY_ID:?backup_postgres: AWS_ACCESS_KEY_ID required}"
: "${AWS_SECRET_ACCESS_KEY:?backup_postgres: AWS_SECRET_ACCESS_KEY required}"

retention_days="${POSTGRES_BACKUP_RETENTION_DAYS:-7}"
s3_prefix="${POSTGRES_BACKUP_PREFIX:-postgres/}"

# ----- 2. Build snapshot -----
timestamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
snapshot_path="/tmp/postgres-backup-${timestamp}.dump"
trap 'rm -f "${snapshot_path}"' EXIT

echo "backup_postgres: pg_dump → ${snapshot_path}"
# -Fc = custom format (binary, compressed, parallel-restore capable).
# --no-owner / --no-acl so the dump restores into a fresh DB without
# permission errors against missing roles.
pg_dump -Fc --no-owner --no-acl --file="${snapshot_path}" "${DSN}"

snapshot_bytes="$(stat -c %s "${snapshot_path}" 2>/dev/null || echo 0)"
echo "backup_postgres: snapshot built (${snapshot_bytes} bytes)"

if [[ "${snapshot_bytes}" -lt 1024 ]]; then
    echo "backup_postgres: snapshot suspiciously small (<1KB) — refusing to upload" >&2
    exit 3
fi

# ----- 3. Upload to S3 -----
s3_key="${s3_prefix}${timestamp}.dump"
echo "backup_postgres: aws s3 cp → s3://${AWS_S3_BUCKET}/${s3_key}"
aws s3 cp "${snapshot_path}" "s3://${AWS_S3_BUCKET}/${s3_key}" \
    --endpoint-url "${AWS_S3_ENDPOINT}" \
    --only-show-errors

echo "backup_postgres: upload complete"

# ----- 4. Prune snapshots older than retention_days -----
echo "backup_postgres: pruning snapshots older than ${retention_days} days"
cutoff_unix="$(date -u -d "${retention_days} days ago" +%s)"
pruned=0

# Lists keys + LastModified ISO8601; awk filters lines older than cutoff.
aws s3api list-objects-v2 \
    --endpoint-url "${AWS_S3_ENDPOINT}" \
    --bucket "${AWS_S3_BUCKET}" \
    --prefix "${s3_prefix}" \
    --query 'Contents[].[Key,LastModified]' \
    --output text 2>/dev/null \
    | while read -r key last_modified; do
        [[ -z "${key}" || "${key}" == "None" ]] && continue
        key_unix="$(date -u -d "${last_modified}" +%s 2>/dev/null || echo 0)"
        if [[ "${key_unix}" -lt "${cutoff_unix}" && "${key_unix}" -gt 0 ]]; then
            echo "  prune: ${key} (LastModified=${last_modified})"
            aws s3 rm "s3://${AWS_S3_BUCKET}/${key}" \
                --endpoint-url "${AWS_S3_ENDPOINT}" \
                --only-show-errors
            pruned=$((pruned + 1))
        fi
    done

echo "backup_postgres: done (snapshot=${s3_key}, retention=${retention_days}d)"

# Anchored unit: postgres-backup.service
