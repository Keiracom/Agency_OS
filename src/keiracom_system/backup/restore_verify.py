"""restore_verify.py — end-to-end Weaviate snapshot restore verification (KEI-242).

HARD GATE before Supabase decommission: a snapshot that cannot be restored is
not a backup. This downloads the latest Weaviate snapshot from R2, extracts it,
launches a throwaway Weaviate instance pointed at the extracted data on a spare
port, and asserts it serves a non-empty schema. Exit 0 = restorable; non-zero +
ceo_memory alert = NOT restorable (block the cutover).

Run: python3 -m src.keiracom_system.backup.restore_verify [--port 8099]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib import request as urlrequest

from src.keiracom_system.backup.alerting import write_backup_alert
from src.keiracom_system.backup.r2 import R2Client

logger = logging.getLogger(__name__)

PREFIX = os.environ.get("WEAVIATE_R2_PREFIX", "weaviate/")
WEAVIATE_BIN = os.environ.get("WEAVIATE_BIN", "/home/elliotbot/clawd/weaviate-bin/weaviate")
READY_TIMEOUT_S = int(os.environ.get("RESTORE_VERIFY_READY_TIMEOUT", "120"))


def _latest_snapshot_key(r2: R2Client) -> str:
    objs = r2.list_objects(PREFIX)
    if not objs:
        raise RuntimeError(f"no snapshots under {PREFIX} to verify")
    return max(objs, key=lambda o: o.last_modified).key


def _wait_ready(port: int, deadline: float) -> None:
    url = f"http://127.0.0.1:{port}/v1/.well-known/ready"
    while time.time() < deadline:
        try:
            with urlrequest.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return
        except OSError:
            pass
        time.sleep(3)
    raise RuntimeError(f"restored Weaviate not ready on :{port} within {READY_TIMEOUT_S}s")


def _assert_non_empty_schema(port: int) -> int:
    url = f"http://127.0.0.1:{port}/v1/schema"
    with urlrequest.urlopen(url, timeout=10) as resp:
        schema = json.loads(resp.read().decode())
    classes = schema.get("classes") or []
    if not classes:
        raise RuntimeError("restored Weaviate served an EMPTY schema — snapshot not usable")
    return len(classes)


def _launch(data_dir: str, port: int) -> subprocess.Popen:
    if not os.path.isfile(WEAVIATE_BIN) or not os.access(WEAVIATE_BIN, os.X_OK):
        raise RuntimeError(f"WEAVIATE_BIN not executable: {WEAVIATE_BIN}")
    env = {**os.environ, "PERSISTENCE_DATA_PATH": data_dir, "DEFAULT_VECTORIZER_MODULE": "none"}
    return subprocess.Popen(
        [WEAVIATE_BIN, "--host", "127.0.0.1", "--port", str(port), "--scheme", "http"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run(*, port: int = 8099) -> int:
    r2 = R2Client()
    key = _latest_snapshot_key(r2)
    logger.info("verifying restore of %s", key)
    with tempfile.TemporaryDirectory() as tmp:
        tarball = os.path.join(tmp, "snapshot.tar.gz")
        r2.download_file(key, tarball)
        data_root = os.path.join(tmp, "restore")
        os.makedirs(data_root, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(data_root)  # noqa: S202 — our own snapshot, trusted source
        proc = _launch(data_root, port)
        try:
            _wait_ready(port, time.time() + READY_TIMEOUT_S)
            n_classes = _assert_non_empty_schema(port)
            logger.info("restore VERIFIED: %s → %d classes served on :%d", key, n_classes, port)
            return n_classes
        finally:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    try:
        run(port=args.port)
    except Exception as exc:  # noqa: BLE001 — failed verification is a P1 gate failure
        write_backup_alert("weaviate_restore_verify", str(exc))
        logger.exception("RESTORE VERIFICATION FAILED — snapshot not restorable")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
