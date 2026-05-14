"""Tests for KEI-60 weaviate_backup.sh — snapshot + prune behavior."""

from __future__ import annotations

import os
import subprocess
import tarfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "weaviate_backup.sh"


@pytest.fixture
def fake_data_dir(tmp_path):
    data = tmp_path / "weaviate-data"
    data.mkdir()
    (data / "collection-a.bin").write_text("fake row data row data row data")
    (data / "index").mkdir()
    (data / "index" / "lance.shard.0").write_text("lance shard payload")
    return data


@pytest.fixture
def backup_dir(tmp_path):
    return tmp_path / "backups" / "weaviate"


def _run(env_extra: dict, args=None):
    env = os.environ.copy()
    env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *(args or [])],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_backup_creates_archive(fake_data_dir, backup_dir):
    result = _run(
        {
            "WEAVIATE_DATA_DIR": str(fake_data_dir),
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
            "AGENCY_OS_BACKUP_DATE": "2026-05-14",
        }
    )
    assert result.returncode == 0, result.stderr
    archive = backup_dir / "weaviate-2026-05-14.tar.gz"
    assert archive.exists()
    assert archive.stat().st_size > 0


def test_backup_archive_contains_data_files(fake_data_dir, backup_dir):
    _run(
        {
            "WEAVIATE_DATA_DIR": str(fake_data_dir),
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
            "AGENCY_OS_BACKUP_DATE": "2026-05-14",
        }
    )
    archive = backup_dir / "weaviate-2026-05-14.tar.gz"
    with tarfile.open(archive, "r:gz") as tf:
        names = tf.getnames()
    assert any(n.endswith("collection-a.bin") for n in names)
    assert any(n.endswith("lance.shard.0") for n in names)


def test_backup_dry_run_skips_io(fake_data_dir, backup_dir):
    result = _run(
        {
            "WEAVIATE_DATA_DIR": str(fake_data_dir),
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
        },
        args=["--dry-run"],
    )
    assert result.returncode == 0
    assert "DRY_RUN snapshot" in result.stdout
    assert not backup_dir.exists()


def test_backup_missing_data_dir_returns_2(tmp_path, backup_dir):
    result = _run(
        {
            "WEAVIATE_DATA_DIR": str(tmp_path / "does-not-exist"),
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
        }
    )
    assert result.returncode == 2
    assert "WEAVIATE_DATA_DIR not found" in result.stderr


def test_backup_prunes_old_archives(fake_data_dir, backup_dir):
    backup_dir.mkdir(parents=True)
    old = backup_dir / "weaviate-2020-01-01.tar.gz"
    old.write_text("ancient")
    # Touch it to be ~30 days old via mtime.
    old_time = time.time() - (30 * 86400)
    os.utime(old, (old_time, old_time))
    assert old.exists()

    _run(
        {
            "WEAVIATE_DATA_DIR": str(fake_data_dir),
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
            "AGENCY_OS_BACKUP_DATE": "2026-05-14",
            "AGENCY_OS_BACKUP_RETENTION_DAYS": "7",
        }
    )

    new_archive = backup_dir / "weaviate-2026-05-14.tar.gz"
    assert new_archive.exists()
    assert not old.exists(), "old archive should have been pruned (mtime > 7 days)"


def test_backup_keeps_recent_archives(fake_data_dir, backup_dir):
    backup_dir.mkdir(parents=True)
    recent = backup_dir / "weaviate-yesterday.tar.gz"
    recent.write_text("fresh")
    # Recent mtime — within retention window.
    recent_time = time.time() - (2 * 86400)
    os.utime(recent, (recent_time, recent_time))

    _run(
        {
            "WEAVIATE_DATA_DIR": str(fake_data_dir),
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
            "AGENCY_OS_BACKUP_DATE": "2026-05-14",
            "AGENCY_OS_BACKUP_RETENTION_DAYS": "7",
        }
    )

    assert recent.exists(), "archive within retention window should be kept"


def test_backup_default_data_dir_unreachable_returns_2(tmp_path, backup_dir):
    result = _run(
        {
            "WEAVIATE_DATA_DIR": "/this/path/should/never/exist/weaviate",
            "AGENCY_OS_BACKUP_DIR": str(backup_dir),
        }
    )
    assert result.returncode == 2
