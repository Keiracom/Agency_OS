"""budget_ceiling unit tests — Cutover-blocker 2 (Agency_OS-6ah2).

Acceptance criteria per dispatch (Dave 2026-05-27):
  (a) pre-spawn check reads current-day spend
  (b) policy table applied per task priority
  (c) Dave direct messages bypass
  (d) alerts channel posts on each fire
  (e) verbatim tests showing budget-cap fires + override works
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from src.relay.budget_ceiling import (
    DEFAULT_DAILY_FLEET_BUDGET_AUD,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    SOURCE_AUTOMATED,
    SOURCE_DAVE_DM,
    SOURCE_FLEET,
    BudgetCeilingError,
    BudgetCeilingGate,
    BudgetDecision,
    fleet_spend_for_day,
)


class _FakeDB:
    """Minimal DB fake — records executes, serves canned fetchone."""

    def __init__(self, spend_request_count: int = 0):
        self.calls: list[tuple[str, tuple]] = []
        self._next_one: Any = (spend_request_count,)

    def execute(self, query: str, *params):
        self.calls.append((query, params))

    def fetchone(self):
        return self._next_one

    def set_request_count(self, count: int) -> None:
        self._next_one = (count,)

    def set_db_error(self) -> None:
        # Will raise on next execute.
        self.calls = []
        self._raise = True

        def _raising_execute(query: str, *params):
            raise RuntimeError("simulated DB error")

        self.execute = _raising_execute  # type: ignore[method-assign]


def _fixed_now() -> datetime:
    return datetime(2026, 5, 27, 14, 0, 0, tzinfo=UTC)


def _gate(
    db: _FakeDB | None = None,
    *,
    daily_budget_aud: float = 25.0,
    alerts_emitter=None,
) -> tuple[BudgetCeilingGate, list[dict]]:
    """Build a gate + return the captured-alerts list for assertion."""
    captured: list[dict] = []

    def emit(payload):
        captured.append(payload)

    return (
        BudgetCeilingGate(
            db=db or _FakeDB(),
            alerts_emitter=alerts_emitter or emit,
            daily_budget_aud=daily_budget_aud,
            now_provider=_fixed_now,
        ),
        captured,
    )


# ────────────────────────────────────────────────────────────────────────────
# Constants + invariants
# ────────────────────────────────────────────────────────────────────────────


def test_default_daily_budget_is_25_aud():
    assert DEFAULT_DAILY_FLEET_BUDGET_AUD == 25.0


def test_gate_rejects_zero_or_negative_budget():
    with pytest.raises(BudgetCeilingError, match="must be > 0"):
        BudgetCeilingGate(db=_FakeDB(), daily_budget_aud=0.0)
    with pytest.raises(BudgetCeilingError, match="must be > 0"):
        BudgetCeilingGate(db=_FakeDB(), daily_budget_aud=-5.0)


def test_check_budget_rejects_invalid_priority():
    gate, _ = _gate()
    with pytest.raises(BudgetCeilingError, match="task_priority"):
        gate.check_budget(task_priority="bogus", source=SOURCE_FLEET)


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (a) — pre-spawn check reads current-day spend
# ────────────────────────────────────────────────────────────────────────────


def test_fleet_spend_for_day_queries_metering_table():
    db = _FakeDB(spend_request_count=10)
    spend = fleet_spend_for_day(db, _fixed_now().date())
    # 10 requests × 0.79 AUD baseline = 7.9 AUD
    assert spend == pytest.approx(7.9)
    query, params = db.calls[0]
    assert "FROM public.keiracom_tenant_metering" in query
    assert "date_utc = %s" in query
    assert params[0] == _fixed_now().date()


def test_fleet_spend_zero_when_no_metering_row():
    """Empty result → 0.0 spend (fresh day, no traffic yet)."""

    class _EmptyDB(_FakeDB):
        def fetchone(self):
            return None

    spend = fleet_spend_for_day(_EmptyDB(), _fixed_now().date())
    assert spend == 0.0


def test_check_budget_under_budget_returns_spawn_ok():
    # 10 requests × 0.79 = 7.9 AUD, well under 25
    gate, alerts = _gate(db=_FakeDB(spend_request_count=10), daily_budget_aud=25.0)
    result = gate.check_budget(task_priority=PRIORITY_NORMAL, source=SOURCE_FLEET)
    assert result.decision == BudgetDecision.SPAWN_OK
    assert result.current_day_spend_aud == pytest.approx(7.9)
    assert result.daily_budget_aud == 25.0
    # No alert when under budget
    assert alerts == []


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (b) — policy table per priority
# ────────────────────────────────────────────────────────────────────────────


def test_priority_high_over_budget_spawns_with_overage_log():
    # 50 requests × 0.79 = 39.5 AUD > 25 budget
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50), daily_budget_aud=25.0)
    result = gate.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_FLEET)
    assert result.decision == BudgetDecision.OVERAGE_LOG_AND_SPAWN
    assert "priority task spawned despite budget overage" in result.reason
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "budget_overage_priority_spawn"
    assert alerts[0]["task_priority"] == PRIORITY_HIGH
    assert alerts[0]["current_day_spend_aud"] == pytest.approx(39.5)


def test_priority_normal_over_budget_deferrable_queues_next_day():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50), daily_budget_aud=25.0)
    result = gate.check_budget(
        task_priority=PRIORITY_NORMAL,
        source=SOURCE_FLEET,
        deferrable=True,
    )
    assert result.decision == BudgetDecision.QUEUE_NEXT_DAY
    assert "non-priority queued until next day" in result.reason
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "budget_overage_queue_next_day"


def test_priority_normal_over_budget_non_deferrable_drops():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50), daily_budget_aud=25.0)
    result = gate.check_budget(
        task_priority=PRIORITY_NORMAL,
        source=SOURCE_FLEET,
        deferrable=False,
    )
    assert result.decision == BudgetDecision.DROP_WITH_LOG
    assert "dropped on overage" in result.reason
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "budget_overage_drop"


def test_priority_low_over_budget_deferrable_queues_next_day():
    """Low priority + deferrable → also queues (same path as normal+deferrable)."""
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50), daily_budget_aud=25.0)
    result = gate.check_budget(
        task_priority=PRIORITY_LOW,
        source=SOURCE_FLEET,
        deferrable=True,
    )
    assert result.decision == BudgetDecision.QUEUE_NEXT_DAY


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (c) — Dave direct messages bypass
# ────────────────────────────────────────────────────────────────────────────


def test_dave_dm_under_budget_is_dave_bypass_with_haiku_tier():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=10), daily_budget_aud=25.0)
    result = gate.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_DAVE_DM)
    assert result.decision == BudgetDecision.DAVE_BYPASS
    assert result.recommended_tier == "haiku"
    assert "CEO never blocked" in result.reason
    # Audit log fired even though it passes
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "budget_dave_bypass"
    assert alerts[0]["over_budget"] is False


def test_dave_dm_over_budget_still_bypasses():
    """CEO NEVER BLOCKED — Dave DM passes even when fleet over budget."""
    gate, alerts = _gate(db=_FakeDB(spend_request_count=100), daily_budget_aud=25.0)
    result = gate.check_budget(task_priority=PRIORITY_LOW, source=SOURCE_DAVE_DM)
    assert result.decision == BudgetDecision.DAVE_BYPASS
    assert result.recommended_tier == "haiku"
    assert alerts[0]["over_budget"] is True


def test_dave_dm_bypass_works_for_any_priority():
    for priority in (PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW):
        gate, _ = _gate(db=_FakeDB(spend_request_count=50), daily_budget_aud=25.0)
        result = gate.check_budget(task_priority=priority, source=SOURCE_DAVE_DM)
        assert result.decision == BudgetDecision.DAVE_BYPASS


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (e) — --force-spawn override
# ────────────────────────────────────────────────────────────────────────────


def test_force_override_requires_justification():
    gate, _ = _gate(db=_FakeDB(spend_request_count=100))
    with pytest.raises(BudgetCeilingError, match="non-empty force_justification"):
        gate.check_budget(
            task_priority=PRIORITY_NORMAL,
            source=SOURCE_FLEET,
            force_override=True,
            force_justification=None,
        )
    with pytest.raises(BudgetCeilingError, match="non-empty force_justification"):
        gate.check_budget(
            task_priority=PRIORITY_NORMAL,
            source=SOURCE_FLEET,
            force_override=True,
            force_justification="",
        )


def test_force_override_fires_regardless_of_budget():
    """Even when way over budget, --force-spawn with justification fires."""
    gate, alerts = _gate(db=_FakeDB(spend_request_count=200), daily_budget_aud=25.0)
    result = gate.check_budget(
        task_priority=PRIORITY_NORMAL,
        source=SOURCE_AUTOMATED,
        force_override=True,
        force_justification="emergency: bd cleanup before billing cutover",
    )
    assert result.decision == BudgetDecision.FORCE_OVERRIDE
    assert "force-spawn override:" in result.reason
    # Justification logged
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "budget_force_override"
    assert alerts[0]["force_justification"] == "emergency: bd cleanup before billing cutover"


def test_force_override_takes_precedence_over_dave_bypass():
    """If both flags fire on the same call, force-override wins (logged path)."""
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50))
    result = gate.check_budget(
        task_priority=PRIORITY_HIGH,
        source=SOURCE_DAVE_DM,
        force_override=True,
        force_justification="explicit operator override",
    )
    assert result.decision == BudgetDecision.FORCE_OVERRIDE
    assert alerts[0]["kind"] == "budget_force_override"


# ────────────────────────────────────────────────────────────────────────────
# Acceptance (d) — alerts channel posts on each fire
# ────────────────────────────────────────────────────────────────────────────


def test_alerts_emitter_called_on_priority_overage():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50))
    gate.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_FLEET)
    assert len(alerts) == 1


def test_alerts_emitter_called_on_dave_bypass_audit():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=10))
    gate.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_DAVE_DM)
    assert len(alerts) == 1


def test_alerts_emitter_called_on_force_override():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=0))
    gate.check_budget(
        task_priority=PRIORITY_NORMAL,
        source=SOURCE_FLEET,
        force_override=True,
        force_justification="x",
    )
    assert len(alerts) == 1


def test_alerts_emitter_not_called_under_budget_no_bypass():
    """SPAWN_OK path doesn't fire alerts — only firings get logged."""
    gate, alerts = _gate(db=_FakeDB(spend_request_count=10))
    gate.check_budget(task_priority=PRIORITY_NORMAL, source=SOURCE_FLEET)
    assert alerts == []


def test_alert_payload_includes_required_fields():
    gate, alerts = _gate(db=_FakeDB(spend_request_count=50))
    gate.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_FLEET)
    payload = alerts[0]
    assert "kind" in payload
    assert "task_priority" in payload
    assert "source" in payload
    assert "current_day_spend_aud" in payload
    assert "daily_budget_aud" in payload
    assert "ts" in payload
    # ISO-8601 with TZ
    assert "T" in payload["ts"]


# ────────────────────────────────────────────────────────────────────────────
# Fail-open — DB / alerts failures must not block dispatch logic
# ────────────────────────────────────────────────────────────────────────────


def test_db_read_failure_treats_as_under_budget():
    """Transient DB blip → SPAWN_OK (better one extra spawn than silent block)."""
    db = _FakeDB()

    def _raising(query, *params):
        raise RuntimeError("simulated DB error")

    db.execute = _raising  # type: ignore[method-assign]
    gate, _ = _gate(db=db, daily_budget_aud=25.0)
    result = gate.check_budget(task_priority=PRIORITY_NORMAL, source=SOURCE_FLEET)
    assert result.decision == BudgetDecision.SPAWN_OK
    assert result.current_day_spend_aud == 0.0


def test_alerts_emitter_failure_does_not_block_decision():
    """Alerts emit raises → decision still returned (caller never sees the throw)."""

    def _raising_emit(payload):
        raise RuntimeError("simulated alerts channel down")

    gate, _ = _gate(
        db=_FakeDB(spend_request_count=50),
        daily_budget_aud=25.0,
        alerts_emitter=_raising_emit,
    )
    result = gate.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_FLEET)
    # Decision still computed — alerts failure swallowed
    assert result.decision == BudgetDecision.OVERAGE_LOG_AND_SPAWN


# ────────────────────────────────────────────────────────────────────────────
# Env-var override
# ────────────────────────────────────────────────────────────────────────────


def test_env_var_overrides_default_budget(monkeypatch):
    monkeypatch.setenv("KEIRACOM_DAILY_FLEET_BUDGET_AUD", "50.0")
    gate = BudgetCeilingGate(db=_FakeDB(), now_provider=_fixed_now)
    assert gate.daily_budget_aud == 50.0


def test_env_var_invalid_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("KEIRACOM_DAILY_FLEET_BUDGET_AUD", "not-a-number")
    gate = BudgetCeilingGate(db=_FakeDB(), now_provider=_fixed_now)
    assert gate.daily_budget_aud == DEFAULT_DAILY_FLEET_BUDGET_AUD


def test_env_var_unset_uses_default(monkeypatch):
    monkeypatch.delenv("KEIRACOM_DAILY_FLEET_BUDGET_AUD", raising=False)
    gate = BudgetCeilingGate(db=_FakeDB(), now_provider=_fixed_now)
    assert gate.daily_budget_aud == DEFAULT_DAILY_FLEET_BUDGET_AUD


# ────────────────────────────────────────────────────────────────────────────
# End-to-end smoke: full pre-spawn sequence
# ────────────────────────────────────────────────────────────────────────────


def test_e2e_dispatcher_flow_under_budget(monkeypatch):
    """Pre-spawn sequence at 0 AUD spend → SPAWN_OK for any non-Dave task."""
    monkeypatch.setenv("KEIRACOM_DAILY_FLEET_BUDGET_AUD", "25.0")
    gate, alerts = _gate(db=_FakeDB(spend_request_count=0))
    for priority in (PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW):
        result = gate.check_budget(task_priority=priority, source=SOURCE_FLEET)
        assert result.decision == BudgetDecision.SPAWN_OK
    # No alerts under budget
    assert alerts == []


def test_e2e_dispatcher_flow_over_budget_full_policy():
    """31+ spawns × 0.79 = >24.49 AUD; verify each policy branch fires correctly."""
    # 32 requests × 0.79 = 25.28 AUD > 25 budget
    db_over = _FakeDB(spend_request_count=32)

    # Priority HIGH → OVERAGE_LOG_AND_SPAWN
    gate_h, alerts_h = _gate(db=db_over, daily_budget_aud=25.0)
    r_h = gate_h.check_budget(task_priority=PRIORITY_HIGH, source=SOURCE_FLEET)
    assert r_h.decision == BudgetDecision.OVERAGE_LOG_AND_SPAWN

    # Priority NORMAL + deferrable → QUEUE_NEXT_DAY
    db_over2 = _FakeDB(spend_request_count=32)
    gate_n, _ = _gate(db=db_over2, daily_budget_aud=25.0)
    r_n = gate_n.check_budget(task_priority=PRIORITY_NORMAL, source=SOURCE_FLEET, deferrable=True)
    assert r_n.decision == BudgetDecision.QUEUE_NEXT_DAY

    # Priority LOW + non-deferrable → DROP_WITH_LOG
    db_over3 = _FakeDB(spend_request_count=32)
    gate_l, _ = _gate(db=db_over3, daily_budget_aud=25.0)
    r_l = gate_l.check_budget(task_priority=PRIORITY_LOW, source=SOURCE_FLEET, deferrable=False)
    assert r_l.decision == BudgetDecision.DROP_WITH_LOG

    # Dave DM → DAVE_BYPASS regardless of overage
    db_over4 = _FakeDB(spend_request_count=32)
    gate_d, _ = _gate(db=db_over4, daily_budget_aud=25.0)
    r_d = gate_d.check_budget(task_priority=PRIORITY_LOW, source=SOURCE_DAVE_DM)
    assert r_d.decision == BudgetDecision.DAVE_BYPASS
    assert r_d.recommended_tier == "haiku"

    # --force-spawn → FORCE_OVERRIDE
    db_over5 = _FakeDB(spend_request_count=32)
    gate_f, _ = _gate(db=db_over5, daily_budget_aud=25.0)
    r_f = gate_f.check_budget(
        task_priority=PRIORITY_NORMAL,
        source=SOURCE_FLEET,
        force_override=True,
        force_justification="emergency",
    )
    assert r_f.decision == BudgetDecision.FORCE_OVERRIDE
