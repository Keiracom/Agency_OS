"""Unit tests for the fail-SAFE dispatcher cost circuit breaker (Agency_OS-wdws).

Injects a fake async spend_reader + recording alert_emitter — no Valkey/network.
asyncio.run keeps the suite free of pytest-asyncio mode config.
"""

from __future__ import annotations

import asyncio

import pytest

from src.dispatcher.cost_breaker import (
    BreakerDecision,
    CostBreaker,
    CostBreakerError,
)


def _reader(daily_cents: int, monthly_cents: int, *, raises: Exception | None = None):
    async def read(tenant_id: int, period: str) -> int:
        if raises is not None:
            raise raises
        return {"daily": daily_cents, "monthly": monthly_cents}[period]

    return read


def _breaker(daily_cents, monthly_cents, *, raises=None, now=None):
    alerts: list[dict] = []
    b = CostBreaker(
        fleet_tenant_id=1,
        daily_alert_cents=2000,  # A$20
        daily_halt_cents=3000,  # A$30
        monthly_halt_cents=35000,  # A$350
        alert_emitter=alerts.append,
        spend_reader=_reader(daily_cents, monthly_cents, raises=raises),
        now=now,
    )
    return b, alerts


def _check(b, **kw):
    return asyncio.run(b.check(**kw))


def test_under_all_ceilings_is_ok_no_alert():
    b, alerts = _breaker(1000, 10000)  # A$10 daily, A$100 monthly
    res = _check(b)
    assert res.decision is BreakerDecision.OK
    assert res.daily_spend_aud == 10.0
    assert alerts == []


def test_daily_alert_band_proceeds_and_alerts():
    b, alerts = _breaker(2500, 10000)  # A$25 daily — over alert, under halt
    res = _check(b)
    assert res.decision is BreakerDecision.ALERT
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "cost_breaker_alert"


def test_daily_halt_halts_fleet_spawn():
    b, alerts = _breaker(3000, 10000)  # A$30 daily == halt
    res = _check(b, source="fleet")
    assert res.decision is BreakerDecision.HALT
    assert "ceiling" in res.reason.lower()
    assert alerts[0]["kind"] == "cost_breaker_halt"


def test_monthly_cap_halts_even_when_daily_low():
    b, alerts = _breaker(500, 35000)  # A$5 daily but A$350 monthly == cap
    res = _check(b, source="fleet")
    assert res.decision is BreakerDecision.HALT
    assert len(alerts) == 1


def test_dave_dm_bypasses_halt_but_alerts():
    b, alerts = _breaker(5000, 10000)  # A$50 daily — well over halt
    res = _check(b, source="dave_dm")
    assert res.decision is BreakerDecision.ALERT  # CEO never blocked
    assert res.reason == "over_ceiling_ceo_bypass"
    assert alerts[0]["kind"] == "cost_breaker_halt"  # still pinged


def test_force_override_bypasses_halt():
    b, _ = _breaker(5000, 10000)
    res = _check(b, source="fleet", force_override=True)
    assert res.decision is BreakerDecision.ALERT
    assert res.reason == "over_ceiling_ceo_bypass"


def test_spend_read_failure_fails_safe_to_halt():
    b, alerts = _breaker(0, 0, raises=ConnectionError("valkey down"))
    res = _check(b, source="fleet")
    assert res.decision is BreakerDecision.HALT
    assert "failsafe" in res.reason
    assert alerts[0]["kind"] == "cost_breaker_halt"


def test_alert_deduped_within_cooldown():
    clock = {"t": 1000.0}
    b, alerts = _breaker(2500, 10000, now=lambda: clock["t"])
    _check(b)  # fires alert
    _check(b)  # within cooldown — suppressed
    assert len(alerts) == 1
    clock["t"] += 601  # past NOTIFY_COOLDOWN_SECONDS
    _check(b)
    assert len(alerts) == 2


def test_spend_snapshot_returns_aud():
    b, _ = _breaker(2500, 12345)
    snap = asyncio.run(b.spend_snapshot())
    assert snap == {"daily_spend_aud": 25.0, "monthly_spend_aud": 123.45}


def test_spend_snapshot_failopen_on_error():
    b, _ = _breaker(0, 0, raises=RuntimeError("x"))
    snap = asyncio.run(b.spend_snapshot())
    assert snap["daily_spend_aud"] == -1.0


def test_config_rejects_halt_below_alert():
    with pytest.raises(CostBreakerError):
        CostBreaker(daily_alert_cents=3000, daily_halt_cents=2000, monthly_halt_cents=35000)


def test_config_rejects_nonpositive_ceiling():
    with pytest.raises(CostBreakerError):
        CostBreaker(daily_alert_cents=0, daily_halt_cents=3000, monthly_halt_cents=35000)
