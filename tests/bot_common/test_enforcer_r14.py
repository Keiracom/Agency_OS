"""Tests for KEI-34 component 2 — R14 ORCHESTRATOR-DISPATCH-DISCIPLINE."""

from __future__ import annotations

from src.bot_common.enforcer_deterministic import check_r14

EXECUTION_CH = "C0B3QB0K1GQ"
CEO_CH = "C0B2PM3TV0B"


def test_r14_idle_with_dispatch_token_passes():
    """Elliot acknowledges idle agents AND pairs with dispatch token → pass."""
    msg = (
        "idle agents: aiden, max. [DISPATCH-PROPOSAL:aiden] KEI-26 P1 — pick up "
        "Better Stack incident webhook now."
    )
    assert check_r14(msg, channel=EXECUTION_CH, callsign="elliot") is None


def test_r14_idle_without_dispatch_fires():
    """Elliot enumerates idle without dispatch → fire."""
    msg = "Standing on idle agents: aiden, max — awaiting Max's evidence post."
    out = check_r14(msg, channel=EXECUTION_CH, callsign="elliot")
    assert out is not None
    assert out["rule_number"] == 14
    assert out["rule_name"] == "ORCHESTRATOR-DISPATCH-DISCIPLINE"
    assert "without an inline dispatch token" in out["detail"]


def test_r14_ready_marker_without_dispatch_fires():
    """Elliot acknowledges [READY:aiden] without dispatch → fire."""
    msg = "[READY:aiden] noted. Standing by on Track 1 evidence."
    out = check_r14(msg, channel=EXECUTION_CH, callsign="elliot")
    assert out is not None
    assert out["rule_number"] == 14


def test_r14_in_ceo_channel_is_noop():
    """Same trigger content in #ceo (not #execution) → no-op."""
    msg = "Standing on idle agents: aiden — awaiting evidence."
    assert check_r14(msg, channel=CEO_CH, callsign="elliot") is None


def test_r14_non_elliot_callsign_is_noop():
    """Aiden/Max/clones posting same content in #execution → no-op (not orchestrator)."""
    msg = "Standing on idle agents: aiden, max — awaiting evidence."
    assert check_r14(msg, channel=EXECUTION_CH, callsign="aiden") is None
    assert check_r14(msg, channel=EXECUTION_CH, callsign="max") is None
    assert check_r14(msg, channel=EXECUTION_CH, callsign="atlas") is None


def test_r14_non_idle_content_in_execution_is_noop():
    """Elliot non-idle messages in #execution → no-op."""
    msg = "[CONCUR:aiden] FINAL on PR #815 — KEI-26 Better Stack incident webhook."
    assert check_r14(msg, channel=EXECUTION_CH, callsign="elliot") is None


def test_r14_explicit_dispatch_token_passes():
    """The 'EXPLICIT DISPATCH' marker also counts as dispatch token."""
    msg = "idle agents: aiden, max — EXPLICIT DISPATCH on KEI-34 Step 0 RESTATE NOW"
    assert check_r14(msg, channel=EXECUTION_CH, callsign="elliot") is None


def test_r14_dispatching_verb_passes():
    """'Dispatching X' counts as dispatch token."""
    msg = "idle agents: aiden — dispatching aiden to KEI-26 webhook build"
    assert check_r14(msg, channel=EXECUTION_CH, callsign="elliot") is None


def test_r14_picks_up_kei_passes():
    """'picks up KEI-N' inline reference counts as dispatch token."""
    msg = "idle agents: aiden — Aiden picks up KEI-26 immediately"
    assert check_r14(msg, channel=EXECUTION_CH, callsign="elliot") is None


def test_r14_no_callsign_is_noop():
    """No callsign provided → no-op (can't verify orchestrator)."""
    msg = "idle agents: aiden — no dispatch"
    assert check_r14(msg, channel=EXECUTION_CH, callsign=None) is None
