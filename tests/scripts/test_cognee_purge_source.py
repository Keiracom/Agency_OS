"""tests for scripts/orchestrator/cognee_purge_source.py — Agency_OS-zbvs.

Cognee API mocked. Verifies exact-name match (team_structure must NOT also
purge team_structure_brief_v2), dry-run safety, and not-found handling.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "cognee_purge_source.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("cognee_purge_source", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cognee_purge_source"] = m
    spec.loader.exec_module(m)
    return m


_ITEMS = [
    {"id": "id-arch", "name": "strategic_doc_strategic_doc%3Aarchitecture_final"},
    {"id": "id-team", "name": "strategic_doc_strategic_doc%3Ateam_structure"},
    {"id": "id-brief", "name": "strategic_doc_strategic_doc%3Ateam_structure_brief_v2"},
    {"id": "id-road", "name": "strategic_doc_strategic_doc%3Aroadmap"},
]


def _wire(mod, monkeypatch, deletes: list):
    """Patch the Cognee API surface: token, dataset lookup, data list, delete-capture."""
    monkeypatch.setattr(mod, "get_token", lambda: "tok")
    monkeypatch.setattr(mod, "_dataset_id", lambda _t: "gov-id")
    monkeypatch.setattr(mod, "list_data", lambda _t, _d: list(_ITEMS))

    def _api(_token, method, path):
        if method == "DELETE":
            deletes.append(path)
            return 204, ""
        return 200, "[]"

    monkeypatch.setattr(mod, "_api", _api)


def test_exact_name_match_does_not_purge_brief(mod, monkeypatch):
    """Purging 'team_structure' must NOT also delete 'team_structure_brief_v2'
    — exact-name match, not substring."""
    deletes: list = []
    _wire(mod, monkeypatch, deletes)
    rc = mod.purge(["strategic_doc_strategic_doc%3Ateam_structure"], apply=True)
    assert rc == 0
    assert len(deletes) == 1
    assert "id-team" in deletes[0]
    assert "id-brief" not in deletes[0]


def test_dry_run_deletes_nothing(mod, monkeypatch):
    deletes: list = []
    _wire(mod, monkeypatch, deletes)
    rc = mod.purge(["strategic_doc_strategic_doc%3Aarchitecture_final"], apply=False)
    assert rc == 0
    assert deletes == []


def test_unknown_source_is_a_failure(mod, monkeypatch):
    deletes: list = []
    _wire(mod, monkeypatch, deletes)
    rc = mod.purge(["strategic_doc_strategic_doc%3Anonexistent"], apply=True)
    assert rc == 1
    assert deletes == []


def test_purge_three_stale_docs(mod, monkeypatch):
    deletes: list = []
    _wire(mod, monkeypatch, deletes)
    rc = mod.purge(
        [
            "strategic_doc_strategic_doc%3Aarchitecture_final",
            "strategic_doc_strategic_doc%3Ateam_structure",
            "strategic_doc_strategic_doc%3Ateam_structure_brief_v2",
        ],
        apply=True,
    )
    assert rc == 0
    assert len(deletes) == 3
