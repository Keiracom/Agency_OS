#!/bin/bash
# FILE: scripts/backup_offsite.sh
# PURPOSE: Offsite backup of Supabase DB via pg_dump + upload to cloud storage.
#          Complements Supabase Pro's native 7-day PITR; intended for recovery
#          scenarios where the Supabase project itself is suspended/deleted.
# AUTHOR: [AIDEN] — Wave 1 item #4 (offsite backup + recovery runbook)
#
# Env required:
#   SUPABASE_DB_URL     — postgres connection string (from Supabase Settings → Database)
#   BACKUP_DESTINATION  — one of: s3://bucket/path, b2://bucket/path, gs://bucket/path
#
# Optional env:
#   BACKUP_KEEP_LOCAL=1 — don't delete the local dump after upload
#   BACKUP_PREFIX        — filename prefix (default: agency-os-backup)
#
# Cloud creds (provide based on destination scheme):
#   S3  → AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (or instance role)
#   B2  → rclone remote "b2-remote" configured with application key
#   GCS → GOOGLE_APPLICATION_CREDENTIALS path

set -euo pipefail

: "${SUPABASE_DB_URL:?SUPABASE_DB_URL is required}"
: "${BACKUP_DESTINATION:?BACKUP_DESTINATION is required (s3://, b2://, or gs://)}"

PREFIX="${BACKUP_PREFIX:-agency-os-backup}"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP_FILE="/tmp/${PREFIX}-${TIMESTAMP}.sql.gz"

echo "[backup] dumping Supabase DB → ${DUMP_FILE}"
pg_dump "${SUPABASE_DB_URL}" --no-owner --no-acl --clean --if-exists | gzip > "${DUMP_FILE}"

SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
echo "[backup] dump complete: ${SIZE}"

echo "[backup] uploading to ${BACKUP_DESTINATION}"
case "${BACKUP_DESTINATION}" in
    s3://*)
        aws s3 cp "${DUMP_FILE}" "${BACKUP_DESTINATION}/"
        ;;
    b2://*)
        # Requires rclone remote "b2-remote:" preconfigured with B2 application key
        rclone copy "${DUMP_FILE}" "${BACKUP_DESTINATION}"
        ;;
    gs://*)
        gsutil cp "${DUMP_FILE}" "${BACKUP_DESTINATION}/"
        ;;
    *)
        echo "[backup] ERROR: unsupported destination scheme: ${BACKUP_DESTINATION}" >&2
        echo "[backup] supported: s3://, b2://, gs://" >&2
        exit 2
        ;;
esac

echo "[backup] uploaded OK"

if [ "${BACKUP_KEEP_LOCAL:-0}" != "1" ]; then
    rm -f "${DUMP_FILE}"
    echo "[backup] local dump removed (set BACKUP_KEEP_LOCAL=1 to keep)"
else
    echo "[backup] local dump kept at ${DUMP_FILE}"
fi

echo "[backup] done"
