"""Tests for the shared upload+prune pipeline step (mock R2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.keiracom_system.backup import pipeline
from src.keiracom_system.backup.r2 import R2Object

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


class FakeR2:
    def __init__(self, existing: list[R2Object]) -> None:
        self.bucket = "bk"
        self._existing = existing
        self.uploaded: list[tuple] = []
        self.deleted: list[str] = []

    def upload_file(self, local: str, key: str) -> None:
        self.uploaded.append((local, key))

    def list_objects(self, prefix: str) -> list[R2Object]:
        return [o for o in self._existing if o.key.startswith(prefix)]

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)


def _big_file(tmp_path) -> str:
    p = tmp_path / "snap.tar.gz"
    p.write_bytes(b"x" * 4096)
    return str(p)


def test_upload_and_prune_uploads_and_prunes(tmp_path):
    existing = [R2Object(f"weaviate/old-{i}", NOW - timedelta(days=i + 1), 4096) for i in range(9)]
    r2 = FakeR2(existing)
    key = pipeline.upload_and_prune(
        r2, _big_file(tmp_path), prefix="weaviate/", key_name="new.tar.gz", keep_recent=7
    )
    assert key == "weaviate/new.tar.gz"
    assert r2.uploaded and r2.uploaded[0][1] == "weaviate/new.tar.gz"
    # 9 existing, keep_recent=7 → 2 oldest pruned (new upload isn't in the list yet)
    assert len(r2.deleted) == 2


def test_small_file_refused(tmp_path):
    p = tmp_path / "tiny.dump"
    p.write_bytes(b"too small")
    r2 = FakeR2([])
    with pytest.raises(RuntimeError, match="refusing upload"):
        pipeline.upload_and_prune(r2, str(p), prefix="postgres/", key_name="x.dump", keep_recent=24)
    assert r2.uploaded == []


def test_missing_file_refused(tmp_path):
    r2 = FakeR2([])
    with pytest.raises(RuntimeError):
        pipeline.upload_and_prune(
            r2, str(tmp_path / "nope"), prefix="p/", key_name="x", keep_recent=7
        )


def test_dry_run_no_io(tmp_path):
    r2 = FakeR2([R2Object("weaviate/old", NOW - timedelta(days=99), 4096)])
    key = pipeline.upload_and_prune(
        r2,
        _big_file(tmp_path),
        prefix="weaviate/",
        key_name="n.tar.gz",
        keep_recent=7,
        dry_run=True,
    )
    assert key == "weaviate/new.tar.gz".replace("new", "n")
    assert r2.uploaded == []
    assert r2.deleted == []


def test_timestamp_format():
    ts = pipeline.timestamp()
    # YYYY-MM-DDTHH-MM-SSZ — colon-free so it is a safe S3 key segment
    datetime.strptime(ts, "%Y-%m-%dT%H-%M-%SZ")
    assert ":" not in ts
