"""Tests for scripts/orchestrator/weekly_cycle_from_bd.py — KEI-29.

bd CLI + Linear GraphQL + datetime.now are stubbed at the module level.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "weekly_cycle_from_bd.py"


@pytest.fixture(scope="module")
def wc_mod():
    spec = importlib.util.spec_from_file_location("weekly_cycle_from_bd", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["weekly_cycle_from_bd"] = mod
    spec.loader.exec_module(mod)
    return mod


# _extract_kei_number ────────────────────────────────────────────────────────


def test_extract_kei_number_canonical_url(wc_mod):
    assert wc_mod._extract_kei_number("https://linear.app/keiracom/issue/KEI-29") == 29


def test_extract_kei_number_handles_other_workspaces(wc_mod):
    assert wc_mod._extract_kei_number("https://linear.app/other-team/issue/KEI-7") == 7


def test_extract_kei_number_returns_none_on_empty(wc_mod):
    assert wc_mod._extract_kei_number("") is None


def test_extract_kei_number_returns_none_on_non_linear_url(wc_mod):
    assert wc_mod._extract_kei_number("https://github.com/Keiracom/Agency_OS/issues/19") is None


# filter_eligible ────────────────────────────────────────────────────────────


def test_filter_eligible_keeps_p0_p1_with_external_ref(wc_mod):
    items = [
        {"id": "a", "priority": 0, "external_ref": "https://linear.app/keiracom/issue/KEI-1"},
        {"id": "b", "priority": 1, "external_ref": "https://linear.app/keiracom/issue/KEI-2"},
        {"id": "c", "priority": 2, "external_ref": "https://linear.app/keiracom/issue/KEI-3"},
        {"id": "d", "priority": 0, "external_ref": ""},
    ]
    out = wc_mod.filter_eligible(items)
    assert [(it["id"], kei) for it, kei in out] == [("a", 1), ("b", 2)]


def test_filter_eligible_handles_missing_priority(wc_mod):
    # priority absent → not in {0,1} → filtered out (defensive).
    assert wc_mod.filter_eligible([{"id": "x", "external_ref": "KEI-1"}]) == []


# compute_target_window ──────────────────────────────────────────────────────


def test_compute_target_window_from_monday_before_7am_aest(wc_mod):
    # Monday 2026-05-18 02:00 AEST = Sunday 2026-05-17 16:00 UTC. Should target SAME Monday.
    starts, ends = wc_mod.compute_target_window(datetime(2026, 5, 17, 16, 0, tzinfo=UTC))
    # Target Monday 2026-05-18 07:00 AEST = Mon 2026-05-17 21:00 UTC.
    assert starts == datetime(2026, 5, 17, 21, 0, tzinfo=UTC)
    assert ends == datetime(2026, 5, 24, 21, 0, tzinfo=UTC)


def test_compute_target_window_from_monday_after_7am_aest_uses_next_week(wc_mod):
    # Mon 2026-05-18 10:00 AEST = Mon 2026-05-18 00:00 UTC. Past 07:00 AEST → next Mon.
    starts, _ = wc_mod.compute_target_window(datetime(2026, 5, 18, 0, 0, tzinfo=UTC))
    # Next Monday is 2026-05-25.
    assert starts == datetime(2026, 5, 24, 21, 0, tzinfo=UTC)


def test_compute_target_window_from_wednesday(wc_mod):
    # Wed 2026-05-20 → next Monday is 2026-05-25.
    starts, _ = wc_mod.compute_target_window(datetime(2026, 5, 20, 12, 0, tzinfo=UTC))
    assert starts == datetime(2026, 5, 24, 21, 0, tzinfo=UTC)


# _cycle_name ────────────────────────────────────────────────────────────────


def test_cycle_name_uses_aest_date(wc_mod):
    # startsAt UTC Sun 21:00 → AEST Mon 07:00.
    name = wc_mod._cycle_name(datetime(2026, 5, 17, 21, 0, tzinfo=UTC))
    assert name == "KEI Week of 2026-05-18"


# run() integration ──────────────────────────────────────────────────────────


def _install_graphql_stub(wc_mod, monkeypatch, responses: list):
    """Each GraphQL call pops the next dict from `responses`."""
    calls: list[tuple[str, dict]] = []

    def fake_gql(api_key, query, variables=None):
        calls.append((query, variables or {}))
        return responses.pop(0) if responses else None

    monkeypatch.setattr(wc_mod, "_linear_graphql", fake_gql)
    return calls


def test_run_no_api_key_returns_2(wc_mod, monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    assert wc_mod.run() == 2


def test_run_empty_bd_ready_is_noop(wc_mod, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "x")
    monkeypatch.setattr(wc_mod, "_bd_ready", lambda: [])
    _install_graphql_stub(wc_mod, monkeypatch, [])  # No GraphQL calls expected
    assert wc_mod.run() == 0


def test_run_no_eligible_items_is_noop(wc_mod, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "x")
    monkeypatch.setattr(
        wc_mod,
        "_bd_ready",
        lambda: [
            {"id": "a", "priority": 2, "external_ref": "https://linear.app/keiracom/issue/KEI-9"},
            {"id": "b", "priority": 0, "external_ref": ""},
        ],
    )
    calls = _install_graphql_stub(wc_mod, monkeypatch, [])
    assert wc_mod.run() == 0
    assert calls == [], "no Linear calls expected when nothing is eligible"


def test_run_idempotent_skip_on_existing_cycle(wc_mod, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "x")
    monkeypatch.setattr(
        wc_mod,
        "_bd_ready",
        lambda: [
            {"id": "a", "priority": 0, "external_ref": "https://linear.app/keiracom/issue/KEI-9"},
        ],
    )
    # Response 1: _find_existing_cycle returns an existing UUID
    # Response 2: _resolve_kei_to_uuid returns the issue UUID
    # Response 3: _add_issue_to_cycle success
    existing_cycle_id = "cycle-already-here"
    issue_uuid = "issue-uuid-9"
    _install_graphql_stub(
        wc_mod,
        monkeypatch,
        [
            {"data": {"team": {"cycles": {"nodes": [{"id": existing_cycle_id}]}}}},
            {"data": {"issues": {"nodes": [{"id": issue_uuid}]}}},
            {"data": {"issueUpdate": {"success": True}}},
        ],
    )
    # Pin time to a Tuesday so target is next Monday — deterministic.
    monkeypatch.setattr(wc_mod, "datetime", _frozen_datetime(2026, 5, 19, 12, 0))
    assert wc_mod.run() == 0


def test_run_happy_path_creates_cycle_and_adds_issue(wc_mod, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "x")
    monkeypatch.setattr(
        wc_mod,
        "_bd_ready",
        lambda: [
            {"id": "a", "priority": 1, "external_ref": "https://linear.app/keiracom/issue/KEI-19"},
        ],
    )
    new_cycle_id = "freshly-created-cycle"
    issue_uuid = "issue-uuid-19"
    _install_graphql_stub(
        wc_mod,
        monkeypatch,
        [
            {"data": {"team": {"cycles": {"nodes": []}}}},  # _find_existing_cycle: none
            {"data": {"cycleCreate": {"success": True, "cycle": {"id": new_cycle_id}}}},
            {"data": {"issues": {"nodes": [{"id": issue_uuid}]}}},  # resolve KEI-19
            {"data": {"issueUpdate": {"success": True}}},  # add to cycle
        ],
    )
    monkeypatch.setattr(wc_mod, "datetime", _frozen_datetime(2026, 5, 19, 12, 0))
    assert wc_mod.run() == 0


def test_run_continues_when_one_resolve_fails(wc_mod, monkeypatch):
    """Linear UUID lookup miss for one item should not block the cycle."""
    monkeypatch.setenv("LINEAR_API_KEY", "x")
    monkeypatch.setattr(
        wc_mod,
        "_bd_ready",
        lambda: [
            {"id": "a", "priority": 0, "external_ref": "https://linear.app/keiracom/issue/KEI-1"},
            {"id": "b", "priority": 1, "external_ref": "https://linear.app/keiracom/issue/KEI-2"},
        ],
    )
    _install_graphql_stub(
        wc_mod,
        monkeypatch,
        [
            {"data": {"team": {"cycles": {"nodes": []}}}},
            {"data": {"cycleCreate": {"success": True, "cycle": {"id": "cyc"}}}},
            {"data": {"issues": {"nodes": []}}},  # KEI-1 not found
            {"data": {"issues": {"nodes": [{"id": "uuid2"}]}}},  # KEI-2 found
            {"data": {"issueUpdate": {"success": True}}},  # add KEI-2
        ],
    )
    monkeypatch.setattr(wc_mod, "datetime", _frozen_datetime(2026, 5, 19, 12, 0))
    assert wc_mod.run() == 0


# Helper: freezes datetime.now(UTC) at the given instant for compute_target_window.


def _frozen_datetime(year, month, day, hour, minute):
    real_datetime = datetime

    class _Frozen(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(year, month, day, hour, minute, tzinfo=tz or UTC)

    return _Frozen
