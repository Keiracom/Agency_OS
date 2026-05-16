"""Unit tests for scripts/orchestrator/kei75_sessions_source_id.

Mocks Weaviate fully. Locks the idempotent re-run guarantee + the
chunk_id-first resolution that backfill writes onto existing rows.
"""

from __future__ import annotations

import importlib
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock

backfill = importlib.import_module("scripts.orchestrator.kei75_sessions_source_id")


def _obj(uuid_str: str, properties: dict) -> SimpleNamespace:
    return SimpleNamespace(uuid=uuid_str, properties=properties)


def _make_client(objects: list[SimpleNamespace]) -> MagicMock:
    client = MagicMock()
    coll = MagicMock()

    def fetch_objects(limit=200, after=None, include_vector=False):
        if after is None:
            start = 0
        else:
            start = next((i + 1 for i, o in enumerate(objects) if o.uuid == after), len(objects))
        return SimpleNamespace(objects=objects[start : start + limit])

    coll.query.fetch_objects.side_effect = fetch_objects
    coll.data.update = MagicMock()
    client.collections.get.return_value = coll
    return client


def test_resolve_uses_chunk_id_when_present():
    obj = _obj("u-1", {"metadata": {"chunk_id": "chunk-A"}})
    assert backfill._resolve_source_id(obj) == "chunk-A"


def test_resolve_falls_back_to_sessions_prefix_uuid():
    obj = _obj("u-2", {"metadata": {}})
    assert backfill._resolve_source_id(obj) == "sessions:u-2"


def test_resolve_skips_when_source_id_already_set():
    obj = _obj("u-3", {"source_id": "already-here", "metadata": {"chunk_id": "ignored"}})
    assert backfill._resolve_source_id(obj) == ""


def test_resolve_handles_string_metadata_blob():
    obj = _obj("u-4", {"metadata": '{"chunk_id": "from-json"}'})
    assert backfill._resolve_source_id(obj) == "from-json"


def test_resolve_treats_blank_existing_source_id_as_unset():
    obj = _obj("u-5", {"source_id": "   ", "metadata": {"chunk_id": "fallback"}})
    assert backfill._resolve_source_id(obj) == "fallback"


def test_run_dry_run_does_not_call_update(monkeypatch):
    objects = [_obj("u-1", {"metadata": {"chunk_id": "c-1"}})]
    client = _make_client(objects)
    monkeypatch.setattr(backfill.weaviate, "connect_to_local", lambda **_: client)
    monkeypatch.setattr(backfill, "_add_property", lambda base_url: "already_present")
    report = backfill.run(host="127.0.0.1", port=8090, apply=False, limit=None)
    assert report["would_update"] == 1
    assert report["applied"] is False
    assert report["sample_updates"] == [("u-1", "c-1")]
    assert client.collections.get(backfill.SESSIONS_CLASS).data.update.call_count == 0


def test_run_apply_writes_updates(monkeypatch):
    objects = [
        _obj("u-1", {"metadata": {"chunk_id": "c-1"}}),
        _obj("u-2", {"metadata": {}}),
        _obj("u-3", {"source_id": "already", "metadata": {"chunk_id": "ignored"}}),
    ]
    client = _make_client(objects)
    monkeypatch.setattr(backfill.weaviate, "connect_to_local", lambda **_: client)
    monkeypatch.setattr(backfill, "_add_property", lambda base_url: "added")
    report = backfill.run(host="127.0.0.1", port=8090, apply=True, limit=None)
    assert report["would_update"] == 2
    assert report["skipped_already_set"] == 1
    update_mock = client.collections.get(backfill.SESSIONS_CLASS).data.update
    assert update_mock.call_count == 2
    call_props = [call.kwargs["properties"]["source_id"] for call in update_mock.call_args_list]
    assert "c-1" in call_props
    assert "sessions:u-2" in call_props


def test_run_limit_caps_iteration(monkeypatch):
    objects = [_obj(f"u-{i}", {"metadata": {"chunk_id": f"c-{i}"}}) for i in range(5)]
    client = _make_client(objects)
    monkeypatch.setattr(backfill.weaviate, "connect_to_local", lambda **_: client)
    monkeypatch.setattr(backfill, "_add_property", lambda base_url: "already_present")
    report = backfill.run(host="127.0.0.1", port=8090, apply=False, limit=2)
    assert report["would_update"] == 2


def test_add_property_treats_422_as_idempotent_success(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url,
            422,
            "Unprocessable Entity",
            {},
            MagicMock(read=lambda: b"property exists"),
        )

    monkeypatch.setattr(backfill.urllib.request, "urlopen", fake_urlopen)
    assert backfill._add_property("http://127.0.0.1:8090") == "already_present"
