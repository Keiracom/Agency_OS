"""weaviate_snapshot.py — daily Weaviate snapshot → Cloudflare R2 (KEI-242).

tar.gz the Weaviate data dir → upload to R2 under weaviate/ → prune to the 7
most-recent snapshots. Any failure writes ceo:backup_alert:{date} and exits
non-zero so the systemd unit records the incident.

Run: python3 -m src.keiracom_system.backup.weaviate_snapshot [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import tempfile

from src.keiracom_system.backup.alerting import write_backup_alert
from src.keiracom_system.backup.pipeline import timestamp, upload_and_prune
from src.keiracom_system.backup.r2 import R2Client

logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get("WEAVIATE_DATA_DIR", "/home/elliotbot/clawd/weaviate-data")
PREFIX = os.environ.get("WEAVIATE_R2_PREFIX", "weaviate/")
KEEP_RECENT = int(os.environ.get("WEAVIATE_R2_KEEP", "7"))


def _build_tarball(data_dir: str, dest: str) -> None:
    """tar.gz the Weaviate data dir. Live-dir tar is acceptable pre-revenue; a
    strictly-consistent snapshot requires stopping weaviate.service first."""
    parent = os.path.dirname(data_dir.rstrip("/")) or "."
    base = os.path.basename(data_dir.rstrip("/"))
    subprocess.run(["tar", "-czf", dest, "-C", parent, base], check=True)


def run(*, dry_run: bool = False) -> str:
    if not os.path.isdir(DATA_DIR):
        raise RuntimeError(f"WEAVIATE_DATA_DIR not found: {DATA_DIR}")
    ts = timestamp()
    with tempfile.TemporaryDirectory() as tmp:
        tarball = os.path.join(tmp, f"weaviate-snapshot-{ts}.tar.gz")
        _build_tarball(DATA_DIR, tarball)
        r2 = R2Client()
        return upload_and_prune(
            r2,
            tarball,
            prefix=PREFIX,
            key_name=f"weaviate-snapshot-{ts}.tar.gz",
            keep_recent=KEEP_RECENT,
            dry_run=dry_run,
        )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        key = run(dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001 — convert any failure into an alert + non-zero exit
        write_backup_alert("weaviate_snapshot", str(exc))
        logger.exception("weaviate snapshot failed")
        return 1
    logger.info("weaviate snapshot complete: %s", key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
