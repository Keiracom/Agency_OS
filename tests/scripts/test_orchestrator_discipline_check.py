"""Tests for KEI-34 component 1 — _orchestrator_discipline_check in elliot_polling_loop.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("elliot_polling_loop_d", SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules["elliot_polling_loop_d"] = m
    spec.loader.exec_module(m)
    return m


def _make_signals(mod, *, bd_ready=(), idle_agents=(), orchestrator_idle_agents=()):
    return mod.CycleSignals(
        bd_ready=[{"id": f"Agency_OS-{i}", "title": f"item-{i}", "priority": 1} for i in range(len(bd_ready))],
        linear_stale=[],
        idle_agents=list(idle_agents),
        prefect_failures=[],
        rate_limit_transitions=[],
        orchestrator_idle_agents=list(orchestrator_idle_agents),
    )


def test_excess_ready_beyond_idle_fires(mod):
    """3 ready items + 1 idle agent → 1 paired, 2 excess → fire."""
    signals = _make_signals(
        mod, bd_ready=range(3), idle_agents=["aiden"], orchestrator_idle_agents=["aiden"]
    )
    dispatches = [("inbox:aiden", "dispatch-for-aiden")]
    mod._orchestrator_discipline_check(signals, dispatches)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 1
    assert "orchestrator-discipline gap" in ceo_msgs[0]
    assert "3 unblocked item(s)" in ceo_msgs[0]
    assert "1 agent(s) idle ≥1 cycle" in ceo_msgs[0]


def test_ready_with_zero_idle_fires(mod):
    """2 ready + 0 idle → no dispatch path active → fire (zero loose-idle path)."""
    signals = _make_signals(mod, bd_ready=range(2), idle_agents=[], orchestrator_idle_agents=[])
    dispatches: list = []
    mod._orchestrator_discipline_check(signals, dispatches)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 1
    assert "0 agent(s) idle ≥1 cycle" in ceo_msgs[0]


def test_strict_idle_with_no_dispatch_fires(mod):
    """1 strict-idle agent + 1 ready but 0 paired (compose returned []) → fire on strict-idle path."""
    signals = _make_signals(
        mod, bd_ready=range(1), idle_agents=[], orchestrator_idle_agents=["scout"]
    )
    dispatches: list = []
    mod._orchestrator_discipline_check(signals, dispatches)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 1
    assert "scout" in ceo_msgs[0]


def test_paired_with_no_excess_passes(mod):
    """3 idle + 3 ready → fully paired, no excess, no strict-idle gap → no-op."""
    signals = _make_signals(
        mod, bd_ready=range(3),
        idle_agents=["aiden", "max", "orion"],
        orchestrator_idle_agents=[],
    )
    dispatches: list = [("c", "m"), ("c", "m"), ("c", "m")]
    mod._orchestrator_discipline_check(signals, dispatches)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 0


def test_no_ready_items_is_noop(mod):
    """Empty bd_ready → no-op regardless of idle agents."""
    signals = _make_signals(
        mod, bd_ready=[], idle_agents=["aiden", "max"], orchestrator_idle_agents=["aiden"]
    )
    dispatches: list = []
    mod._orchestrator_discipline_check(signals, dispatches)
    assert dispatches == []


def test_more_loose_idle_than_ready_no_strict_passes(mod):
    """5 loose-idle + 2 ready + 0 strict-idle → fully paired (min=2), no excess, no strict → no-op."""
    signals = _make_signals(
        mod, bd_ready=range(2),
        idle_agents=["a", "b", "c", "d", "e"],
        orchestrator_idle_agents=[],
    )
    dispatches: list = [("c", "m"), ("c", "m")]
    mod._orchestrator_discipline_check(signals, dispatches)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    assert len(ceo_msgs) == 0


def test_cycle_period_seconds_peak_returns_60(mod):
    from datetime import UTC as utc
    from datetime import datetime

    # 22:00 UTC = 08:00 AEST = peak window
    assert mod._cycle_period_seconds(datetime(2026, 5, 12, 22, 0, tzinfo=utc)) == 60


def test_cycle_period_seconds_offpeak_returns_3600(mod):
    from datetime import UTC as utc
    from datetime import datetime

    # 15:00 UTC = 01:00 AEST = off-peak
    assert mod._cycle_period_seconds(datetime(2026, 5, 12, 15, 0, tzinfo=utc)) == 3600
