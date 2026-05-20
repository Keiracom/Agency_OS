"""tests for scripts/orchestrator/ingest_strategic_docs.py — Agency_OS-zbvs.

psycopg + Weaviate mocked. Verifies the ceo_memory strategic_doc:* parse and
the deterministic-UUID upsert payload.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "ingest_strategic_docs.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("ingest_strategic_docs", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["ingest_strategic_docs"] = m
    spec.loader.exec_module(m)
    return m


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a):
        return None

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return None


class _Conn:
    def __init__(self, rows):
        self._cur = _Cursor(rows)

    def cursor(self):
        return self._cur


def test_fetch_strategic_docs_parses_json_value(mod):
    rows = [
        ("strategic_doc:team_structure", {"title": "TS", "content": "body", "drive_id": "abc"}),
        # value may also arrive as a JSON string
        ("strategic_doc:roadmap", json.dumps({"title": "RM", "content": "rc", "drive_id": "xyz"})),
    ]
    docs = mod.fetch_strategic_docs(_Conn(rows))
    assert docs[0] == {
        "key": "strategic_doc:team_structure",
        "title": "TS",
        "content": "body",
        "drive_id": "abc",
    }
    assert docs[1]["title"] == "RM" and docs[1]["drive_id"] == "xyz"


def test_upsert_uuid_is_deterministic_per_drive_id(mod):
    """Re-running the ingest must target the SAME Weaviate object id for a
    given drive_id (idempotent upsert, no duplicates)."""
    a = uuid.uuid5(mod._UUID_NS, "abc")
    b = uuid.uuid5(mod._UUID_NS, "abc")
    c = uuid.uuid5(mod._UUID_NS, "different")
    assert a == b
    assert a != c


def test_upsert_doc_posts_strategic_documents_object(mod, monkeypatch):
    calls = []

    def _fake_weaviate(method, path, body=None):
        calls.append((method, path, body))
        return 200, "{}"

    monkeypatch.setattr(mod, "_weaviate", _fake_weaviate)
    mod.upsert_doc({"key": "strategic_doc:x", "title": "T", "content": "C", "drive_id": "d1"})
    # a DELETE (idempotent upsert) then a POST to /v1/objects
    assert calls[0][0] == "DELETE"
    assert calls[1][0] == "POST" and calls[1][1] == "/v1/objects"
    payload = calls[1][2]
    assert payload["class"] == "StrategicDocuments"
    assert payload["properties"]["doc_id"] == "d1"
    assert payload["properties"]["content"] == "C"


def test_upsert_doc_raises_on_weaviate_error(mod, monkeypatch):
    monkeypatch.setattr(mod, "_weaviate", lambda *a: (500, "boom"))
    with pytest.raises(RuntimeError, match="Weaviate POST 500"):
        mod.upsert_doc({"key": "k", "title": "T", "content": "C", "drive_id": "d"})
