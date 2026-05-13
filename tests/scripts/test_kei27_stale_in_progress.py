"""Tests for KEI-27 stale-in-progress alert (24h no activity → #ceo)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("elliot_polling_loop_kei27", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["elliot_polling_loop_kei27"] = m
    spec.loader.exec_module(m)
    return m


def test_poll_kei_stale_no_api_key_returns_empty(mod, monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    assert mod.poll_kei_stale() == []


def test_query_linear_stale_used_by_both_polls(mod, monkeypatch):
    """Shared _query_linear_stale helper invoked by both poll_linear_stale + poll_kei_stale."""
    calls: list[tuple[int, object]] = []

    def _fake(hours, now):
        calls.append((hours, now))
        return []

    monkeypatch.setattr(mod, "_query_linear_stale", _fake)
    mod.poll_linear_stale()
    mod.poll_kei_stale()
    assert len(calls) == 2
    hours_called = [c[0] for c in calls]
    assert mod.STALE_LINEAR_HOURS in hours_called
    assert mod.STALE_KEI_HOURS in hours_called
    # Distinct hours values
    assert mod.STALE_LINEAR_HOURS != mod.STALE_KEI_HOURS


def test_compose_dispatches_kei_stale_emits_to_ceo(mod):
    sig = mod.CycleSignals(
        bd_ready=[],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[],
        kei_stale=[
            {
                "identifier": "KEI-99",
                "title": "Silently died",
                "updatedAt": "2026-05-11T00:00:00Z",
                "assignee": {"name": "elliot"},
            },
        ],
    )
    dispatches = mod.compose_dispatches(sig)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 1
    assert "KEI silently-died sweep" in ceo_msgs[0]
    assert "KEI-99" in ceo_msgs[0]
    assert "Silently died" in ceo_msgs[0]
    assert "elliot" in ceo_msgs[0]


def test_compose_dispatches_kei_stale_deduped_against_linear_stale(mod):
    """KEI-27 must not double-post issues already in linear_stale (12h subset)."""
    common = {
        "identifier": "KEI-100",
        "title": "Already in both",
        "updatedAt": "2026-05-11T00:00:00Z",
        "assignee": {"name": "aiden"},
    }
    sig = mod.CycleSignals(
        bd_ready=[],
        linear_stale=[common],
        idle_agents=[],
        prefect_failures=[],
        kei_stale=[common],
    )
    dispatches = mod.compose_dispatches(sig)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    # Only one #ceo post (linear_stale) — kei_stale dedup'd out.
    sweep_messages = [m for m in ceo_msgs if "silently-died" in m]
    assert sweep_messages == [], "KEI-27 should not double-post issues already in linear_stale"
    linear_messages = [m for m in ceo_msgs if "Linear stale-In-Progress" in m]
    assert len(linear_messages) == 1


def test_compose_dispatches_kei_stale_empty_is_noop(mod):
    sig = mod.CycleSignals(
        bd_ready=[],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[],
        kei_stale=[],
    )
    dispatches = mod.compose_dispatches(sig)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    sweep_messages = [m for m in ceo_msgs if "silently-died" in m]
    assert sweep_messages == []


def test_compose_dispatches_kei_stale_handles_null_assignee(mod):
    """Same null-assignee defensiveness as PR #794 fix."""
    sig = mod.CycleSignals(
        bd_ready=[],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[],
        kei_stale=[
            {
                "identifier": "KEI-101",
                "title": "Unassigned silently-died",
                "updatedAt": "2026-05-11T00:00:00Z",
                "assignee": None,
            },
        ],
    )
    dispatches = mod.compose_dispatches(sig)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 1
    assert "KEI-101" in ceo_msgs[0]


def test_stale_hours_constants_distinct(mod):
    assert mod.STALE_LINEAR_HOURS == 12
    assert mod.STALE_KEI_HOURS == 24
