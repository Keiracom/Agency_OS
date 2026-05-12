"""Tests for scripts/bd_to_linear.py — PR-2 Beads→Linear outbound sync.

Mocks the Linear GraphQL urllib endpoint + state-file/beads-export reads.
Covers:
  - _linear_id_from_external_ref: extract KEI-NN from Linear URL; None on
    non-Linear strings
  - _resolve_assignee_id: env primary, GraphQL fallback by name
  - compute_deltas: status change / assignee change / both / no change
  - sync_once: end-to-end happy path PATCHes Linear + writes state file
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bd_to_linear.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bd_to_linear", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bd_to_linear"] = m
    spec.loader.exec_module(m)
    return m


# _linear_id_from_external_ref ────────────────────────────────────────────────


def test_linear_id_extraction_canonical_url(mod):
    url = "https://linear.app/keiracom/issue/KEI-77/build-sync-receiver"
    assert mod._linear_id_from_external_ref(url) == "KEI-77"


def test_linear_id_extraction_missing_returns_none(mod):
    assert mod._linear_id_from_external_ref("https://github.com/x/y/issues/1") is None
    assert mod._linear_id_from_external_ref("") is None


# _resolve_assignee_id ────────────────────────────────────────────────────────


def test_resolve_assignee_env_primary(mod, monkeypatch):
    monkeypatch.setenv("AGENCY_OS_LINEAR_USER_AIDEN", "uuid-aiden-from-env")

    def _no_graphql(*args, **kwargs):
        raise AssertionError("env hit should short-circuit GraphQL")

    monkeypatch.setattr(mod, "_linear_graphql", _no_graphql)
    assert mod._resolve_assignee_id("key", "aiden") == "uuid-aiden-from-env"


def test_resolve_assignee_graphql_fallback(mod, monkeypatch):
    monkeypatch.delenv("AGENCY_OS_LINEAR_USER_AIDEN", raising=False)

    def _fake(api_key, query, variables=None):
        return {"data": {"users": {"nodes": [{"id": "uuid-fallback", "name": "aiden"}]}}}

    monkeypatch.setattr(mod, "_linear_graphql", _fake)
    assert mod._resolve_assignee_id("key", "aiden") == "uuid-fallback"


def test_resolve_assignee_empty_returns_none(mod, monkeypatch):
    monkeypatch.delenv("AGENCY_OS_LINEAR_USER_AIDEN", raising=False)
    monkeypatch.setattr(
        mod, "_linear_graphql", lambda *a, **k: {"data": {"users": {"nodes": []}}}
    )
    assert mod._resolve_assignee_id("key", "aiden") is None


# compute_deltas ──────────────────────────────────────────────────────────────


def test_compute_deltas_status_change(mod):
    prior = {"Agency_OS-abc": {"status": "open", "assignee": ""}}
    current = [
        {
            "id": "Agency_OS-abc",
            "status": "active",
            "assignee": "",
            "external_ref": "https://linear.app/keiracom/issue/KEI-77/x",
        },
    ]
    deltas = mod.compute_deltas(prior, current)
    assert len(deltas) == 1
    assert deltas[0]["status_changed"] is True
    assert deltas[0]["assignee_changed"] is False
    assert deltas[0]["linear_id"] == "KEI-77"


def test_compute_deltas_assignee_change(mod):
    prior = {"Agency_OS-def": {"status": "open", "assignee": ""}}
    current = [
        {
            "id": "Agency_OS-def",
            "status": "open",
            "assignee": "aiden",
            "external_ref": "https://linear.app/keiracom/issue/KEI-88",
        },
    ]
    deltas = mod.compute_deltas(prior, current)
    assert len(deltas) == 1
    assert deltas[0]["assignee_changed"] is True
    assert deltas[0]["status_changed"] is False


def test_compute_deltas_no_change_returns_empty(mod):
    prior = {
        "Agency_OS-x": {"status": "active", "assignee": "aiden", "linear_id": "KEI-99"}
    }
    current = [
        {
            "id": "Agency_OS-x",
            "status": "active",
            "assignee": "aiden",
            "external_ref": "https://linear.app/keiracom/issue/KEI-99",
        },
    ]
    assert mod.compute_deltas(prior, current) == []


def test_compute_deltas_skip_no_external_ref(mod):
    """bd issue without external_ref doesn't have a Linear counterpart — skip."""
    current = [{"id": "Agency_OS-y", "status": "active", "assignee": "aiden"}]
    assert mod.compute_deltas({}, current) == []


def test_compute_deltas_skip_non_linear_ref(mod):
    """external_ref that isn't a Linear URL — skip."""
    current = [
        {
            "id": "Agency_OS-z",
            "status": "active",
            "external_ref": "https://github.com/x/y/issues/1",
        }
    ]
    assert mod.compute_deltas({}, current) == []


# sync_once end-to-end ────────────────────────────────────────────────────────


def test_sync_once_no_api_key_no_op(mod, monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    assert mod.sync_once() == 0


def test_sync_once_patches_changed_issue(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    state_path = tmp_path / "state.json"
    beads_path = tmp_path / "issues.jsonl"
    monkeypatch.setenv("AGENCY_OS_BD_TO_LINEAR_STATE", str(state_path))
    monkeypatch.setenv("AGENCY_OS_BEADS_EXPORT", str(beads_path))
    monkeypatch.setenv("AGENCY_OS_LINEAR_USER_AIDEN", "uuid-aiden")

    state_path.write_text(json.dumps({"Agency_OS-abc": {"status": "open", "assignee": ""}}))
    beads_path.write_text(
        json.dumps(
            {
                "id": "Agency_OS-abc",
                "status": "closed",
                "assignee": "aiden",
                "external_ref": "https://linear.app/keiracom/issue/KEI-77/build",
            }
        )
        + "\n"
    )

    captured: list[tuple] = []

    def _fake(api_key, query, variables=None):
        captured.append((query, variables))
        if "team{states" in query:
            return {
                "data": {
                    "issue": {
                        "team": {
                            "states": {
                                "nodes": [{"id": "state-uuid", "name": "Done", "type": "completed"}]
                            }
                        }
                    }
                }
            }
        if "issueUpdate" in query:
            return {"data": {"issueUpdate": {"success": True}}}
        return {"data": {"users": {"nodes": []}}}

    monkeypatch.setattr(mod, "_linear_graphql", _fake)
    n = mod.sync_once()
    assert n == 1
    # State should now reflect the new snapshot
    after = json.loads(state_path.read_text())
    assert after["Agency_OS-abc"]["status"] == "closed"
    assert after["Agency_OS-abc"]["assignee"] == "aiden"
    # Linear update mutation must have been called
    assert any("issueUpdate" in c[0] for c in captured)
