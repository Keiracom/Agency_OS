"""
FILE: tests/scripts/test_re_embed_corpus.py
PURPOSE: Unit tests for scripts/re_embed_corpus.py

Uses a fake Weaviate client and fake embedder — no live Weaviate required.

Covers:
- Dry-run leaves corpus unchanged
- Live run re-embeds N=5 fake objects, calls embedder N times, writes back N times
- Partial failure (one object embed throws): script exits 4, logs failed IDs
- Spot-check verifier: 10 queries return results
- Audit log dict has required fields
- CLI parsing: missing required args exits 2; default dry-run is True

KEI: KEI-60 (Linear: https://linear.app/keiracom/issue/KEI-62)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Ensure scripts/ directory is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from re_embed_corpus import (
    _parse_args,
    _re_embed_collection,
    _verify_spot_check,
    _write_audit_log,
    main,
)

# ---------------------------------------------------------------------------
# Fake embedder — deterministic, no network
# ---------------------------------------------------------------------------

_FAKE_DIM = 8  # small vector dimension for tests


def _fake_embed(text: str, model: str) -> list[float]:
    """Deterministic fake embedder: returns a vector based on text hash."""
    h = hash(text) % (10**6)
    return [(h + i) / 1e6 for i in range(_FAKE_DIM)]


# ---------------------------------------------------------------------------
# Fake Weaviate client
# ---------------------------------------------------------------------------


class FakeWeaviateClient:
    """In-memory Weaviate client stub that satisfies _WeaviateClient."""

    def __init__(self, objects_by_collection: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._objects: dict[str, list[dict[str, Any]]] = objects_by_collection or {}
        self._vectors: dict[str, dict[str, list[float]]] = {}  # collection -> id -> vector
        self.update_calls: list[tuple[str, str, list[float]]] = []
        self.query_calls: list[tuple[str, list[float], int]] = []

    def get_all_objects(self, collection: str) -> list[dict[str, Any]]:
        return self._objects.get(collection, [])

    def update_vector(self, collection: str, object_id: str, vector: list[float]) -> None:
        self._vectors.setdefault(collection, {})[object_id] = vector
        self.update_calls.append((collection, object_id, vector))

    def query_objects(self, collection: str, query_vector: list[float], limit: int) -> list[dict[str, Any]]:
        self.query_calls.append((collection, query_vector, limit))
        objects = self._objects.get(collection, [])
        return objects[:limit]


def _make_objects(n: int, collection: str = "TestCollection") -> list[dict[str, Any]]:
    return [
        {"id": f"obj-{i:04d}", "properties": {"raw_text": f"document content number {i}"}}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests: dry-run leaves corpus unchanged
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_does_not_call_update_vector(self):
        objects = _make_objects(5)
        client = FakeWeaviateClient({"Col": objects})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            succeeded, failed = _re_embed_collection(
                client, "Col", "gemini-embedding-002", dry_run=True, batch_size=10
            )

        assert len(client.update_calls) == 0, "update_vector must NOT be called during dry-run"
        assert succeeded == 5
        assert failed == []

    def test_dry_run_exit_0(self):
        objects = _make_objects(3)
        client = FakeWeaviateClient({"Col": objects})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            code = main(
                ["--old-model", "gemini-embedding-001", "--new-model", "gemini-embedding-002",
                 "--collections", "Col", "--dry-run", "True"],
                client=client,
            )

        assert code == 0
        assert len(client.update_calls) == 0


# ---------------------------------------------------------------------------
# Tests: live run re-embeds correctly
# ---------------------------------------------------------------------------


class TestLiveRun:
    def test_live_run_calls_embedder_once_per_object(self):
        n = 5
        objects = _make_objects(n)
        client = FakeWeaviateClient({"Col": objects})
        embed_calls: list[tuple[str, str]] = []

        def counting_embed(text: str, model: str) -> list[float]:
            embed_calls.append((text, model))
            return _fake_embed(text, model)

        with patch("re_embed_corpus.embed", side_effect=counting_embed):
            succeeded, failed = _re_embed_collection(
                client, "Col", "gemini-embedding-002", dry_run=False, batch_size=10
            )

        assert len(embed_calls) == n
        assert succeeded == n
        assert failed == []

    def test_live_run_calls_update_vector_once_per_object(self):
        n = 5
        objects = _make_objects(n)
        client = FakeWeaviateClient({"Col": objects})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            _re_embed_collection(client, "Col", "gemini-embedding-002", dry_run=False, batch_size=10)

        assert len(client.update_calls) == n
        obj_ids_updated = {call[1] for call in client.update_calls}
        expected_ids = {f"obj-{i:04d}" for i in range(n)}
        assert obj_ids_updated == expected_ids

    def test_live_run_exits_0(self):
        objects = _make_objects(3)
        client = FakeWeaviateClient({"Col": objects})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            code = main(
                ["--old-model", "gemini-embedding-001", "--new-model", "gemini-embedding-002",
                 "--collections", "Col", "--dry-run", "False"],
                client=client,
            )

        assert code == 0


# ---------------------------------------------------------------------------
# Tests: partial failure exits 4
# ---------------------------------------------------------------------------


class TestPartialFailure:
    def test_partial_failure_exits_4(self):
        objects = _make_objects(5)
        client = FakeWeaviateClient({"Col": objects})
        call_count = [0]

        def failing_embed(text: str, model: str) -> list[float]:
            call_count[0] += 1
            if call_count[0] == 3:
                raise RuntimeError("provider error")
            return _fake_embed(text, model)

        with patch("re_embed_corpus.embed", side_effect=failing_embed):
            code = main(
                ["--old-model", "gemini-embedding-001", "--new-model", "gemini-embedding-002",
                 "--collections", "Col", "--dry-run", "False"],
                client=client,
            )

        assert code == 4

    def test_partial_failure_records_failed_ids(self):
        objects = _make_objects(5)
        client = FakeWeaviateClient({"Col": objects})
        call_count = [0]

        def failing_on_third(text: str, model: str) -> list[float]:
            call_count[0] += 1
            if call_count[0] == 3:
                raise RuntimeError("embed error")
            return _fake_embed(text, model)

        with patch("re_embed_corpus.embed", side_effect=failing_on_third):
            succeeded, failed = _re_embed_collection(
                client, "Col", "gemini-embedding-002", dry_run=False, batch_size=10
            )

        assert len(failed) == 1
        assert succeeded == 4

    def test_objects_missing_raw_text_counted_as_failed(self):
        objects = [
            {"id": "no-text-obj", "properties": {}},  # no raw_text
            {"id": "good-obj", "properties": {"raw_text": "some content"}},
        ]
        client = FakeWeaviateClient({"Col": objects})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            succeeded, failed = _re_embed_collection(
                client, "Col", "gemini-embedding-002", dry_run=False, batch_size=10
            )

        assert "no-text-obj" in failed
        assert succeeded == 1


# ---------------------------------------------------------------------------
# Tests: spot-check verifier
# ---------------------------------------------------------------------------


class TestSpotCheck:
    def test_spot_check_passes_when_queries_return_results(self):
        objects = _make_objects(5)
        client = FakeWeaviateClient({"Col": objects})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            result = _verify_spot_check(client, "Col", "gemini-embedding-002", n_queries=10)

        assert result is True
        assert len(client.query_calls) == 10

    def test_spot_check_fails_when_collection_empty(self):
        client = FakeWeaviateClient({"Col": []})

        with patch("re_embed_corpus.embed", side_effect=_fake_embed):
            result = _verify_spot_check(client, "Col", "gemini-embedding-002", n_queries=10)

        assert result is False


# ---------------------------------------------------------------------------
# Tests: audit log dict has required fields
# ---------------------------------------------------------------------------


class TestAuditLog:
    REQUIRED_FIELDS = {
        "event", "source", "agent", "kei",
        "model_from", "model_to", "n_objects", "timestamp", "dry_run",
    }

    def test_audit_log_has_required_fields(self):
        record = _write_audit_log(
            old_model="gemini-embedding-001",
            new_model="gemini-embedding-002",
            collections=["Col"],
            n_objects=42,
            failed_ids=[],
            dry_run=True,
        )
        missing = self.REQUIRED_FIELDS - record.keys()
        assert not missing, f"Audit log missing fields: {missing}"

    def test_audit_log_values_correct(self):
        record = _write_audit_log(
            old_model="old-model",
            new_model="new-model",
            collections=["C1", "C2"],
            n_objects=10,
            failed_ids=["x"],
            dry_run=False,
        )
        assert record["model_from"] == "old-model"
        assert record["model_to"] == "new-model"
        assert record["n_objects"] == 10
        assert record["dry_run"] is False
        assert record["event"] == "re_embed_complete"
        assert record["kei"] == "KEI-60"
        assert record["agent"] == "elliot"

    def test_audit_log_timestamp_is_iso8601(self):
        import re

        record = _write_audit_log(
            old_model="a", new_model="b", collections=[], n_objects=0, failed_ids=[], dry_run=True
        )
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", record["timestamp"])


# ---------------------------------------------------------------------------
# Tests: CLI parsing
# ---------------------------------------------------------------------------


class TestCLIParsing:
    def test_default_dry_run_is_true(self):
        args = _parse_args([
            "--old-model", "a", "--new-model", "b", "--collections", "Col"
        ])
        assert args.dry_run is True

    def test_dry_run_false_when_explicit(self):
        args = _parse_args([
            "--old-model", "a", "--new-model", "b", "--collections", "Col",
            "--dry-run", "False"
        ])
        assert args.dry_run is False

    def test_missing_old_model_exits_2(self):
        code = main(["--new-model", "b", "--collections", "Col"])
        assert code == 2

    def test_missing_new_model_exits_2(self):
        code = main(["--old-model", "a", "--collections", "Col"])
        assert code == 2

    def test_missing_collections_exits_2(self):
        code = main(["--old-model", "a", "--new-model", "b"])
        assert code == 2

    def test_empty_collections_string_exits_2(self):
        objects = _make_objects(1)
        client = FakeWeaviateClient({"Col": objects})
        code = main(
            ["--old-model", "a", "--new-model", "b", "--collections", ""],
            client=client,
        )
        assert code == 2

    def test_batch_size_default_100(self):
        args = _parse_args([
            "--old-model", "a", "--new-model", "b", "--collections", "Col"
        ])
        assert args.batch_size == 100

    def test_multiple_collections_parsed(self):
        args = _parse_args([
            "--old-model", "a", "--new-model", "b",
            "--collections", "Col1,Col2,Col3"
        ])
        # collections are split in main(), not parse_args — check raw string
        assert "Col1" in args.collections
        assert "Col2" in args.collections
