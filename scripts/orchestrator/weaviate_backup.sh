#!/usr/bin/env bash
# weaviate_backup.sh — daily snapshot of the Weaviate data directory.
#
# KEI-60 — Weaviate persistent storage governance: volume mount + backup.
#
# Snapshots /home/elliotbot/clawd/weaviate-data to a dated tar.gz under
# /home/elliotbot/clawd/backups/weaviate/ and prunes archives older than
# AGENCY_OS_BACKUP_RETENTION_DAYS (default 7). Intended to run from a
# systemd --user timer once per day; safe to run ad-hoc for restore tests.
#
# Why tar.gz of the host data directory:
#   Weaviate native binary persists every collection + index as files under
#   WEAVIATE_DATA_DIR. Stopping the service before tar makes the snapshot
#   consistent; running tar against a live data dir risks capturing a
#   half-written WAL (acceptable for pre-revenue cost model, fragile for
#   prod-scale). This script does NOT stop the service — operators wanting
#   a strictly consistent snapshot stop weaviate.service manually first.
#
# Why not encrypted-at-rest / S3 / cross-region:
#   Pre-revenue right-sizing per Dave directive. Host-local tar.gz +
#   7-day retention is the floor; harder backups added when revenue funds
#   the storage cost.
#
# Usage:
#   scripts/orchestrator/weaviate_backup.sh             # snapshot + prune
#   scripts/orchestrator/weaviate_backup.sh --dry-run   # print actions, no I/O
#
# Env overrides:
#   WEAVIATE_DATA_DIR             default /home/elliotbot/clawd/weaviate-data
#   AGENCY_OS_BACKUP_DIR          default /home/elliotbot/clawd/backups/weaviate
#   AGENCY_OS_BACKUP_RETENTION_DAYS  default 7
#   AGENCY_OS_BACKUP_DATE         override date stamp (testing; default $(date -u +%Y-%m-%d))
#
# Exit codes:
#   0  snapshot + prune succeeded
#   2  data dir missing or unreadable
#   3  backup dir creation failed
#   4  tar fatal error (rc>=2) or archive missing/empty after tar

set -euo pipefail

WEAVIATE_DATA_DIR="${WEAVIATE_DATA_DIR:-/home/elliotbot/clawd/weaviate-data}"
BACKUP_DIR="${AGENCY_OS_BACKUP_DIR:-/home/elliotbot/clawd/backups/weaviate}"
RETENTION_DAYS="${AGENCY_OS_BACKUP_RETENTION_DAYS:-7}"
STAMP="${AGENCY_OS_BACKUP_DATE:-$(date -u +%Y-%m-%d)}"
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
fi

ARCHIVE="$BACKUP_DIR/weaviate-${STAMP}.tar.gz"

if [[ ! -d "$WEAVIATE_DATA_DIR" ]]; then
    echo "ERROR: WEAVIATE_DATA_DIR not found: $WEAVIATE_DATA_DIR" >&2
    exit 2
fi
if ! [[ -r "$WEAVIATE_DATA_DIR" ]]; then
    echo "ERROR: WEAVIATE_DATA_DIR not readable: $WEAVIATE_DATA_DIR" >&2
    exit 2
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY_RUN snapshot $WEAVIATE_DATA_DIR -> $ARCHIVE"
    echo "DRY_RUN prune $BACKUP_DIR archives older than ${RETENTION_DAYS} days"
    exit 0
fi

if ! mkdir -p "$BACKUP_DIR"; then
    echo "ERROR: could not create $BACKUP_DIR" >&2
    exit 3
fi

# Snapshot (tar from data dir parent so paths are relative to the dir itself).
# Live Weaviate compacts its LSM segments mid-backup, so tar may exit rc=1
# ("file changed as we read it") while still writing a valid archive. Treat
# rc<=1 with a non-empty archive as success; only a fatal tar error (rc>=2)
# or a missing/empty archive is a real failure.
set +e
tar -czf "$ARCHIVE" -C "$(dirname "$WEAVIATE_DATA_DIR")" "$(basename "$WEAVIATE_DATA_DIR")"
TAR_RC=$?
set -e
if [[ "$TAR_RC" -gt 1 ]] || [[ ! -s "$ARCHIVE" ]]; then
    echo "ERROR: tar failed (rc=$TAR_RC) — fatal error or archive missing/empty" >&2
    exit 4
fi
if [[ "$TAR_RC" -eq 1 ]]; then
    echo "WARNING: tar rc=1 (files changed during live backup); archive produced, treating as success" >&2
fi

# Prune archives older than RETENTION_DAYS days (best-effort).
find "$BACKUP_DIR" -name "weaviate-*.tar.gz" -type f \
    -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

SIZE=$(stat -c%s "$ARCHIVE" 2>/dev/null || echo "?")
echo "snapshot OK $ARCHIVE (${SIZE} bytes); pruned anything older than ${RETENTION_DAYS}d"
