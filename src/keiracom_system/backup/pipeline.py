"""pipeline.py — shared upload+prune step for the R2 backup entrypoints."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from src.keiracom_system.backup.r2 import R2Client
from src.keiracom_system.backup.retention import select_prunable

logger = logging.getLogger(__name__)

MIN_SNAPSHOT_BYTES = 1024  # guard against uploading an empty/half-written dump


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def _too_small(path: str) -> bool:
    try:
        return os.path.getsize(path) < MIN_SNAPSHOT_BYTES
    except OSError:
        return True


def upload_and_prune(
    r2: R2Client,
    local_path: str,
    *,
    prefix: str,
    key_name: str,
    keep_recent: int,
    keep_daily: int = 0,
    dry_run: bool = False,
) -> str:
    """Upload `local_path` to `{prefix}{key_name}`, then prune per retention.

    Raises on a suspiciously-small snapshot (refuse to overwrite good backups
    with a broken one) or any R2 error — the caller turns that into an alert.
    """
    if _too_small(local_path):
        raise RuntimeError(f"snapshot {local_path} < {MIN_SNAPSHOT_BYTES} bytes — refusing upload")
    key = f"{prefix}{key_name}"
    if dry_run:
        logger.info("[dry-run] would upload %s → %s/%s", local_path, r2.bucket, key)
        return key
    r2.upload_file(local_path, key)
    logger.info("uploaded %s → %s/%s", local_path, r2.bucket, key)

    existing = r2.list_objects(prefix)
    for obj in select_prunable(existing, keep_recent=keep_recent, keep_daily=keep_daily):
        r2.delete_object(obj.key)
        logger.info("pruned %s (last_modified=%s)", obj.key, obj.last_modified)
    return key
