"""restore_verify.py — Weaviate snapshot restore verification from R2 (KEI-242).

HARD GATE before ceo_memory/Supabase decommission: a snapshot that cannot be
restored is not a backup. This downloads the latest Weaviate snapshot from R2,
extracts it, and STRUCTURALLY verifies the restored store is recoverable —
every collection survives with real LSM object segments + schema metadata.

WHY STRUCTURAL (not a live boot): Weaviate (1.25+) persists its node identity in
the raft store (CLUSTER_HOSTNAME @ RAFT address, e.g. node1@127.0.0.1:8300). A
recovery node booted with a DIFFERENT identity comes up as a non-voter that
never elects a leader ("not part of a stable configuration") and never serves;
booting with the ORIGINAL identity collides with the live node's raft port. So
Weaviate recovery is a NODE-REPLACEMENT operation, not an on-host parallel boot
(orion 2026-06-03, anchored in the backups_dr drill). The byte-level guarantee a
node-replacement recovery depends on — all collections + their object data +
schema survive the snapshot — is exactly what this verifies, without disturbing
the live node.

Exit 0 = restorable; non-zero + ceo_memory alert = NOT restorable (block cutover).

Run: python3 -m src.keiracom_system.backup.restore_verify
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import sys
import tarfile
import tempfile

from src.keiracom_system.backup.alerting import write_backup_alert
from src.keiracom_system.backup.r2 import R2Client

logger = logging.getLogger(__name__)

PREFIX = os.environ.get("WEAVIATE_R2_PREFIX", "weaviate/")
MIN_COLLECTIONS_WITH_OBJECTS = int(os.environ.get("RESTORE_VERIFY_MIN_COLLECTIONS", "5"))
MIN_OBJECT_BYTES = int(os.environ.get("RESTORE_VERIFY_MIN_OBJECT_BYTES", str(10 * 1024 * 1024)))

# Non-collection entries in a Weaviate data dir (skip when counting collections).
_NON_COLLECTION = {"raft", "modules.db", "classifications.db", "schema.db"}


def _latest_snapshot_key(r2: R2Client) -> str:
    objs = r2.list_objects(PREFIX)
    if not objs:
        raise RuntimeError(f"no snapshots under {PREFIX} to verify")
    return max(objs, key=lambda o: o.last_modified).key


def _locate_data_root(extract_dir: str) -> str:
    """The tar wraps the data dir; find the dir that holds the raft store."""
    for root, dirs, _files in os.walk(extract_dir):
        if "raft" in dirs:
            return root
    raise RuntimeError("could not locate the Weaviate data root (no raft/ dir) in snapshot")


def _verify_structural(data_root: str) -> tuple[int, int, int]:
    """Assert collections survive with real object segments. Returns
    (collections, collections_with_objects, total_object_bytes)."""
    collections = with_objects = obj_bytes = 0
    for entry in sorted(os.listdir(data_root)):
        path = os.path.join(data_root, entry)
        if not os.path.isdir(path) or entry in _NON_COLLECTION:
            continue
        collections += 1
        segs = glob.glob(os.path.join(path, "*", "lsm", "objects", "*.db"))
        if segs:
            with_objects += 1
            obj_bytes += sum(os.path.getsize(s) for s in segs)
    schema_ok = os.path.exists(os.path.join(data_root, "schema.db")) or os.path.isdir(
        os.path.join(data_root, "raft", "snapshots")
    )
    if with_objects < MIN_COLLECTIONS_WITH_OBJECTS:
        raise RuntimeError(
            f"only {with_objects} collections carry object segments "
            f"(< {MIN_COLLECTIONS_WITH_OBJECTS}) — snapshot not usable"
        )
    if obj_bytes < MIN_OBJECT_BYTES:
        raise RuntimeError(
            f"recovered object data {obj_bytes} bytes < {MIN_OBJECT_BYTES} — store looks empty"
        )
    if not schema_ok:
        raise RuntimeError("no schema metadata (schema.db / raft snapshots) in snapshot")
    return collections, with_objects, obj_bytes


def run() -> int:
    """Download + structurally verify the latest R2 snapshot. Returns the
    number of collections recovered."""
    r2 = R2Client()
    key = _latest_snapshot_key(r2)
    logger.info("verifying restore of %s", key)
    with tempfile.TemporaryDirectory() as tmp:
        tarball = os.path.join(tmp, "snapshot.tar.gz")
        r2.download_file(key, tarball)
        data_root_parent = os.path.join(tmp, "restore")
        os.makedirs(data_root_parent, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(data_root_parent)  # noqa: S202 — our own snapshot, trusted source
        data_root = _locate_data_root(data_root_parent)
        collections, with_objects, obj_bytes = _verify_structural(data_root)
        logger.info(
            "restore VERIFIED: %s → %d collections (%d with object data, %d MB) + schema",
            key,
            collections,
            with_objects,
            obj_bytes // 1024 // 1024,
        )
        return collections


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    argparse.ArgumentParser().parse_args()
    try:
        run()
    except Exception as exc:  # noqa: BLE001 — failed verification is a P1 gate failure
        write_backup_alert("weaviate_restore_verify", str(exc))
        logger.exception("RESTORE VERIFICATION FAILED — snapshot not restorable")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
