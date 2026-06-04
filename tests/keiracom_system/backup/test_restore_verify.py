"""Unit tests for restore_verify structural recoverability (KEI-242, orion).

The live round-trip is proven in scripts/proof_bar/weaviate_offsite_backup_
live_proof.sh; these guard the pure structural assertions against synthetic
Weaviate data dirs (no R2, no boot).
"""

from __future__ import annotations

import os

import pytest

from src.keiracom_system.backup import restore_verify as rv


def _make_collection(root: str, name: str, *, object_bytes: int) -> None:
    """Create a synthetic collection dir with an LSM objects segment."""
    objects = os.path.join(root, name, "shard1", "lsm", "objects")
    os.makedirs(objects, exist_ok=True)
    if object_bytes:
        with open(os.path.join(objects, "segment-1.db"), "wb") as fh:
            fh.write(b"x" * object_bytes)


def _make_store(root: str, *, collections: int, bytes_each: int, schema: bool = True) -> None:
    os.makedirs(os.path.join(root, "raft", "snapshots"), exist_ok=True)
    if schema:
        with open(os.path.join(root, "schema.db"), "wb") as fh:
            fh.write(b"schema")
    for i in range(collections):
        _make_collection(root, f"collection{i}", object_bytes=bytes_each)


def test_verify_structural_passes_on_complete_store(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "MIN_COLLECTIONS_WITH_OBJECTS", 5)
    monkeypatch.setattr(rv, "MIN_OBJECT_BYTES", 1024)
    root = str(tmp_path / "data")
    _make_store(root, collections=6, bytes_each=2048)
    collections, with_objects, obj_bytes = rv._verify_structural(root)
    assert collections == 6
    assert with_objects == 6
    assert obj_bytes >= 6 * 2048


def test_verify_structural_fails_when_too_few_collections(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "MIN_COLLECTIONS_WITH_OBJECTS", 5)
    monkeypatch.setattr(rv, "MIN_OBJECT_BYTES", 1024)
    root = str(tmp_path / "data")
    _make_store(root, collections=3, bytes_each=2048)  # only 3 < 5
    with pytest.raises(RuntimeError, match="object segments"):
        rv._verify_structural(root)


def test_verify_structural_fails_when_object_data_too_small(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "MIN_COLLECTIONS_WITH_OBJECTS", 2)
    monkeypatch.setattr(rv, "MIN_OBJECT_BYTES", 10 * 1024 * 1024)
    root = str(tmp_path / "data")
    _make_store(root, collections=5, bytes_each=8)  # tiny — total well under 10MB
    with pytest.raises(RuntimeError, match="empty"):
        rv._verify_structural(root)


def test_verify_structural_fails_without_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "MIN_COLLECTIONS_WITH_OBJECTS", 2)
    monkeypatch.setattr(rv, "MIN_OBJECT_BYTES", 1024)
    root = str(tmp_path / "data")
    os.makedirs(root)
    for i in range(3):
        _make_collection(root, f"collection{i}", object_bytes=2048)
    # No schema.db and no raft/snapshots → schema metadata missing.
    with pytest.raises(RuntimeError, match="schema metadata"):
        rv._verify_structural(root)


def test_locate_data_root_finds_raft_dir(tmp_path):
    nested = tmp_path / "weaviate-data"
    os.makedirs(nested / "raft")
    assert rv._locate_data_root(str(tmp_path)) == str(nested)


def test_locate_data_root_raises_without_raft(tmp_path):
    os.makedirs(tmp_path / "nothing")
    with pytest.raises(RuntimeError, match="raft"):
        rv._locate_data_root(str(tmp_path))
