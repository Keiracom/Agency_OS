"""tests/scripts/test_auto_label_kei.py — hermetic tests for auto_label_kei.

Stubs LINEAR_API_KEY and monkeypatches `_post` to avoid network IO. Verifies:
- pattern matching per label
- idempotency when labels already present
- no labels matched returns matched_no_change=True with empty applied
- missing label auto-create flow returns id and applies
- bulk match on combined text
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "auto_label_kei.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("auto_label_kei", SCRIPT)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["auto_label_kei"] = m
    spec.loader.exec_module(m)
    return m


def test_infer_labels_audit(mod):
    assert mod.infer_labels("Audit finding in pipeline", "") == ["audit-finding"]


def test_infer_labels_pattern_keyword(mod):
    assert mod.infer_labels("New pattern observed", "") == ["audit-finding"]


def test_infer_labels_incident(mod):
    assert mod.infer_labels("Rate limit outage on Vapi", "") == ["pipeline-incident"]


def test_infer_labels_build(mod):
    # "feature" hits build; "build" alone also fires
    assert mod.infer_labels("Build the new feature wire", "") == ["build"]


def test_infer_labels_docs(mod):
    assert mod.infer_labels("Update runbook", "Docs cleanup") == ["docs"]


def test_infer_labels_research(mod):
    assert mod.infer_labels("Research diagnosis of slow query", "") == ["research"]


def test_infer_labels_none(mod):
    assert mod.infer_labels("Random title", "Random body") == []


def test_infer_labels_multiple(mod):
    # both "audit" and "build" present → both labels in fixed order
    result = mod.infer_labels("Audit-driven build of new feature", "")
    assert result == ["audit-finding", "build"]


def test_label_issue_no_match_short_circuits(mod, monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_post(q, v=None):
        calls.append((q, v or {}))
        return {"data": {}}

    monkeypatch.setattr(mod, "_post", fake_post)
    rep = mod.label_issue("abc-123", "totally unrelated title", "boring body")
    assert rep["matched_no_change"] is True
    assert rep["applied"] == []
    # no Linear calls when nothing matches
    assert calls == []


def test_label_issue_idempotent_when_already_present(mod, monkeypatch):
    """When current labels include all matched names, no mutation runs."""
    calls: list[tuple[str, dict]] = []

    def fake_post(q, v=None):
        calls.append((q, v or {}))
        if "labels { nodes" in q and "issue(id:" in q:
            return {
                "data": {"issue": {"labels": {"nodes": [{"id": "lbl-1", "name": "audit-finding"}]}}}
            }
        return {"data": {}}

    monkeypatch.setattr(mod, "_post", fake_post)
    rep = mod.label_issue("abc-123", "Audit finding here", "")
    assert rep["matched_no_change"] is True
    assert rep["applied"] == []
    assert rep["skipped_already_present"] == ["audit-finding"]
    # only the issue-labels read should have run; no team-label list / no mutate
    assert len(calls) == 1


def test_label_issue_law_locked_suppresses_linear_write(mod, monkeypatch):
    """Linear-read-only LAW (Dave 2026-05-20): a label is matched and absent
    on the issue, but the issueUpdate write is suppressed — applied is empty
    and no issueUpdate is POSTed to Linear."""
    calls: list[tuple[str, dict]] = []
    team_label_map_state = {}  # starts empty (no labels in team)

    def fake_post(q, v=None):
        calls.append((q, v or {}))
        if "issue(id:" in q and "labels { nodes" in q:
            # current labels on issue: empty
            return {"data": {"issue": {"labels": {"nodes": []}}}}
        if "team(id:" in q and "labels { nodes" in q:
            return {
                "data": {
                    "team": {
                        "labels": {
                            "nodes": [
                                {"id": lid, "name": n} for n, lid in team_label_map_state.items()
                            ]
                        }
                    }
                }
            }
        if "issueLabelCreate" in q:
            new_id = f"created-{v.get('name', '?')}"
            team_label_map_state[v["name"]] = new_id
            return {
                "data": {
                    "issueLabelCreate": {
                        "success": True,
                        "issueLabel": {"id": new_id, "name": v["name"]},
                    }
                }
            }
        if "issueUpdate" in q:
            return {"data": {"issueUpdate": {"success": True}}}
        return {"data": {}}

    monkeypatch.setattr(mod, "_post", fake_post)
    rep = mod.label_issue("abc-123", "Build a new feature", "")
    # A label WAS matched + absent → matched_no_change is False, but the
    # write is LAW-locked: applied is empty, no issueUpdate is POSTed.
    assert rep["matched_no_change"] is False
    assert rep["applied"] == []
    assert [c for c in calls if "issueUpdate" in c[0]] == [], "issueUpdate must be suppressed"
