"""Unit tests for scripts/orchestrator/heartbeat_monitor.py (KEI-91 Gate 4).

No DB / no Slack. Pure-function tests for evaluate() — the alert-rule logic.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import heartbeat_monitor as hm  # noqa: E402


def _ts(hour: int = 12, minute: int = 0) -> _dt.datetime:
    return _dt.datetime(2026, 5, 17, hour, minute, 0, tzinfo=_dt.UTC)


def _state(
    *,
    last_tick_minutes_ago: float = 1.0,
    counter: int = 5,
    status: str = "ok",
    error: str | None = None,
    period_start_minutes_ago: float = 1.0,
    now: _dt.datetime | None = None,
) -> dict:
    now = now or _ts()
    return {
        "last_tick_ts": (now - _dt.timedelta(minutes=last_tick_minutes_ago)).isoformat(),
        "last_period_start": (now - _dt.timedelta(minutes=period_start_minutes_ago)).isoformat(),
        "last_outcome_counter_period_seconds": 300,
        "last_outcome_counter_value": counter,
        "last_status": status,
        "last_error_message": error,
    }


# ACCEPTANCE TEST 1 — kill-service => stale tick alert fires.
def test_kill_service_triggers_stale_tick_alert():
    now = _ts()
    state = _state(last_tick_minutes_ago=15.0, now=now)
    alerts = hm.evaluate("completion-sync-worker", state, now=now, threshold=hm.ServiceThreshold())
    reasons = {a.reason for a in alerts}
    assert "stale_tick" in reasons


def test_recent_tick_no_stale_alert():
    now = _ts()
    state = _state(last_tick_minutes_ago=2.0, now=now)
    alerts = hm.evaluate("completion-sync-worker", state, now=now, threshold=hm.ServiceThreshold())
    reasons = {a.reason for a in alerts}
    assert "stale_tick" not in reasons


# ACCEPTANCE TEST 2 — zero-outcome window during business hours fires.
def test_zero_outcome_in_business_hours_triggers_alert():
    now = _ts(hour=14)  # 14 UTC, default business hours 00-24 covers it
    state = _state(
        last_tick_minutes_ago=1.0,
        counter=0,
        period_start_minutes_ago=45.0,
        now=now,
    )
    alerts = hm.evaluate(
        "linear-webhook-handler",
        state,
        now=now,
        threshold=hm.ServiceThreshold(zero_outcome_window_minutes=30),
    )
    reasons = {a.reason for a in alerts}
    assert "zero_outcome_window" in reasons


def test_zero_outcome_inside_window_does_not_alert():
    now = _ts(hour=14)
    state = _state(
        last_tick_minutes_ago=1.0,
        counter=0,
        period_start_minutes_ago=10.0,
        now=now,
    )
    alerts = hm.evaluate(
        "linear-webhook-handler",
        state,
        now=now,
        threshold=hm.ServiceThreshold(zero_outcome_window_minutes=30),
    )
    reasons = {a.reason for a in alerts}
    assert "zero_outcome_window" not in reasons


def test_nonzero_counter_never_zero_outcome_alert():
    now = _ts(hour=14)
    state = _state(
        last_tick_minutes_ago=1.0,
        counter=42,
        period_start_minutes_ago=45.0,
        now=now,
    )
    alerts = hm.evaluate("completion-sync-worker", state, now=now, threshold=hm.ServiceThreshold())
    reasons = {a.reason for a in alerts}
    assert "zero_outcome_window" not in reasons


# ACCEPTANCE TEST 3 — silent-regression simulation (webhook-HMAC-fail equivalent).
def test_simulated_hmac_fail_pattern_caught():
    """Models today's webhook incident: process alive (recent tick) but
    outcome counter staying at 0 for a substantial window during business
    hours. Without the outcome counter, aliveness alone would have missed
    this. The monitor must catch it.
    """
    now = _ts(hour=10)
    state = _state(
        last_tick_minutes_ago=0.5,  # alive — just ticked
        counter=0,  # but doing nothing meaningful
        period_start_minutes_ago=35.0,
        now=now,
    )
    alerts = hm.evaluate(
        "linear-webhook-handler",
        state,
        now=now,
        threshold=hm.ServiceThreshold(zero_outcome_window_minutes=30),
    )
    reasons = {a.reason for a in alerts}
    # Stale-tick must NOT fire (process is alive).
    assert "stale_tick" not in reasons
    # Zero-outcome MUST fire — this is the load-bearing detection.
    assert "zero_outcome_window" in reasons


# Status=error path.
def test_self_reported_error_status_alerts():
    now = _ts()
    state = _state(status="error", error="HMAC verification failed", now=now)
    alerts = hm.evaluate("any", state, now=now, threshold=hm.ServiceThreshold())
    reasons = {a.reason for a in alerts}
    assert "self_reported_error" in reasons
    err_alert = next(a for a in alerts if a.reason == "self_reported_error")
    assert "HMAC" in err_alert.detail


# Edge cases — malformed state.
def test_missing_last_tick_ts_alerts():
    now = _ts()
    state = {"last_outcome_counter_value": 5, "last_status": "ok"}
    alerts = hm.evaluate("svc", state, now=now, threshold=hm.ServiceThreshold())
    reasons = {a.reason for a in alerts}
    assert "missing_last_tick_ts" in reasons


def test_outside_business_hours_skips_zero_outcome_when_bh_only():
    # Force business-hours window to 09-17 UTC so 03:00 is outside.
    monkeypatch_target = hm
    original_bh_start = monkeypatch_target.BUSINESS_HOURS_START
    original_bh_end = monkeypatch_target.BUSINESS_HOURS_END
    try:
        monkeypatch_target.BUSINESS_HOURS_START = 9
        monkeypatch_target.BUSINESS_HOURS_END = 17
        now = _ts(hour=3)
        state = _state(
            last_tick_minutes_ago=1.0,
            counter=0,
            period_start_minutes_ago=45.0,
            now=now,
        )
        alerts = hm.evaluate(
            "completion-sync-worker",
            state,
            now=now,
            threshold=hm.ServiceThreshold(business_hours_only=True),
        )
        reasons = {a.reason for a in alerts}
        assert "zero_outcome_window" not in reasons
    finally:
        monkeypatch_target.BUSINESS_HOURS_START = original_bh_start
        monkeypatch_target.BUSINESS_HOURS_END = original_bh_end
