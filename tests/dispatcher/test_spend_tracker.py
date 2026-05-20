"""KEI-212 — tests for src/dispatcher/spend_tracker.

External dependencies (Valkey, Supabase, NATS, litellm) are mocked so CI
runs without live services. The acceptance criterion "Cost calc matches
LiteLLM reported cost (within 1%)" is enforced by feeding a known LiteLLM
return through the divergence path.

All monetary values are integer ``$AUD cents`` per LAW II.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dispatcher import spend_tracker
from src.dispatcher.spend_tracker import (
    SPEND_NAMESPACE_PREFIX,
    USD_TO_AUD_RATE,
    _seconds_until_midnight_utc,
    _seconds_until_month_boundary_utc,
    cost_cents_aud_from_usd,
    get_spend,
    record,
    tenant_spend_key,
)

# ─── tenant_spend_key ──────────────────────────────────────────────────────


def test_tenant_spend_key_daily_format():
    assert tenant_spend_key("1", "daily") == f"{SPEND_NAMESPACE_PREFIX}:1:daily"


def test_tenant_spend_key_monthly_format():
    assert tenant_spend_key("cust-abc", "monthly") == f"{SPEND_NAMESPACE_PREFIX}:cust-abc:monthly"


def test_tenant_spend_key_strips_whitespace():
    assert tenant_spend_key("  7  ", "daily") == f"{SPEND_NAMESPACE_PREFIX}:7:daily"


def test_tenant_spend_key_refuses_empty():
    with pytest.raises(ValueError, match="non-empty"):
        tenant_spend_key("", "daily")
    with pytest.raises(ValueError, match="non-empty"):
        tenant_spend_key("   ", "daily")


def test_tenant_spend_key_refuses_invalid_period():
    with pytest.raises(ValueError, match="period must be"):
        tenant_spend_key("1", "weekly")  # type: ignore[arg-type]


# ─── LAW II conversion ─────────────────────────────────────────────────────


def test_cost_cents_aud_from_usd_uses_documented_rate():
    """1.00 USD → 1.55 AUD → 155 cents (with the documented rate). Use
    math.isclose for the float rate constant — Sonar S1244 forbids `==`
    on floats. Int converter output is asserted directly."""
    import math

    assert math.isclose(USD_TO_AUD_RATE, 1.55, rel_tol=1e-9)
    assert cost_cents_aud_from_usd(1.00) == 155


def test_cost_cents_aud_from_usd_rounds_half_away_from_zero():
    """Small fragments must not silently vanish from billing totals."""
    # 0.001 USD * 1.55 * 100 = 0.155 cents → rounds to 0 (Python banker's rounding hits 0)
    # 0.005 USD * 1.55 * 100 = 0.775 cents → rounds to 1
    assert cost_cents_aud_from_usd(0.005) == 1


def test_cost_cents_aud_from_usd_zero():
    assert cost_cents_aud_from_usd(0.0) == 0


def test_cost_cents_aud_from_usd_refuses_negative():
    with pytest.raises(ValueError, match="non-negative"):
        cost_cents_aud_from_usd(-0.01)


# ─── TTL helpers ───────────────────────────────────────────────────────────


def test_seconds_until_midnight_utc_positive():
    secs = _seconds_until_midnight_utc(datetime(2026, 5, 18, 15, 0, 0, tzinfo=UTC))
    assert secs == 9 * 3600


def test_seconds_until_midnight_utc_just_before_midnight():
    secs = _seconds_until_midnight_utc(datetime(2026, 5, 18, 23, 59, 0, tzinfo=UTC))
    assert secs == 60


def test_seconds_until_month_boundary_handles_month_end():
    """Last day of May → seconds until midnight 1 June."""
    secs = _seconds_until_month_boundary_utc(datetime(2026, 5, 31, 23, 0, 0, tzinfo=UTC))
    assert secs == 3600


def test_seconds_until_month_boundary_handles_mid_month():
    """Mid-May (00:00 UTC on the 15th) → seconds to 00:00 UTC on 1 June.
    May has 31 days, so 17 full days remain: 15→16→…→31→1Jun = 17 * 86400."""
    secs = _seconds_until_month_boundary_utc(datetime(2026, 5, 15, 0, 0, 0, tzinfo=UTC))
    assert secs == 17 * 86400


def test_ttl_never_zero():
    """Edge case: now == midnight exactly. TTL must still be >= 1 so EXPIRE
    is meaningful (Redis EXPIRE 0 deletes the key immediately)."""
    secs = _seconds_until_midnight_utc(datetime(2026, 5, 18, 0, 0, 0, tzinfo=UTC))
    assert secs >= 1


# ─── _compute_cost_cents_aud ───────────────────────────────────────────────


def test_compute_cost_returns_none_when_litellm_missing():
    """No litellm → return None so caller falls back to its own cost_cents_aud."""

    def raise_import_error(*_args, **_kw):
        raise ImportError("litellm not installed")

    with patch("builtins.__import__", side_effect=raise_import_error):
        assert spend_tracker._compute_cost_cents_aud("claude-sonnet-4-5", 100, 100) is None


def test_compute_cost_converts_litellm_usd_to_cents_aud():
    """LiteLLM returns (prompt_usd, completion_usd) tuple → sum × 155 → AUD cents."""
    fake_litellm = MagicMock()
    fake_litellm.cost_per_token = MagicMock(return_value=(0.01, 0.02))  # $0.03 USD
    with patch.dict("sys.modules", {"litellm": fake_litellm}):
        result = spend_tracker._compute_cost_cents_aud("claude-sonnet-4-5", 100, 100)
    # 0.03 USD × 1.55 × 100 = 4.65 cents → rounds to 5 cents
    assert result == 5


def test_compute_cost_returns_none_on_litellm_exception():
    """Unknown model → litellm raises → _compute_cost_cents_aud returns None."""
    fake_litellm = MagicMock()
    fake_litellm.cost_per_token = MagicMock(side_effect=ValueError("unknown model"))
    with patch.dict("sys.modules", {"litellm": fake_litellm}):
        assert spend_tracker._compute_cost_cents_aud("made-up-model", 100, 100) is None


# ─── record() — happy path ─────────────────────────────────────────────────


@pytest.fixture
def mock_valkey_client():
    """Fake redis.asyncio.Redis with pipeline + ttl methods stubbed."""
    client = MagicMock()
    pipe = MagicMock()
    pipe.exists = MagicMock()
    pipe.incrby = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 0])  # not exists, new total cents
    client.pipeline = MagicMock(return_value=pipe)
    client.expire = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.aclose = AsyncMock(return_value=None)
    return client, pipe


@pytest.mark.asyncio
async def test_record_increments_daily_and_monthly(mock_valkey_client, monkeypatch):
    """One record() call → two Valkey INCRBY (daily + monthly), both in cents."""
    client, pipe = mock_valkey_client
    pipe.execute = AsyncMock(side_effect=[[0, 8], [0, 8]])  # 8 cents post-incr each
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))

    result = await record(
        tenant_id=1,
        callsign="max",
        model="claude-sonnet-4-5",
        tokens_in=100,
        tokens_out=200,
        cost_cents_aud=8,
    )
    assert result["cost_cents_aud"] == 8
    assert result["daily_total_cents_aud"] == 8
    assert result["monthly_total_cents_aud"] == 8
    assert result["budget_warn_fired"] is False
    # Two pipelines built (one per period)
    assert client.pipeline.call_count == 2


@pytest.mark.asyncio
async def test_record_sets_ttl_only_on_first_write(mock_valkey_client, monkeypatch):
    """existed=0 → EXPIRE called; existed=1 → EXPIRE skipped."""
    client, pipe = mock_valkey_client
    # First period: didn't exist → expire called. Second period: existed → skipped.
    pipe.execute = AsyncMock(side_effect=[[0, 5], [1, 5]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))

    await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_cents_aud=5,
    )
    # First call (daily, didn't exist) → expire fired; second (monthly, existed) → skipped.
    assert client.expire.call_count == 1


# ─── cost match within 1% (acceptance criterion) ───────────────────────────


@pytest.mark.asyncio
async def test_record_uses_litellm_cost_when_within_1pct(mock_valkey_client, monkeypatch):
    """Caller 1000 cents, LiteLLM 1005 cents → divergence 0.5% → LiteLLM used."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 1005], [0, 1005]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: 1005)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))

    result = await record(
        tenant_id=1,
        callsign="max",
        model="claude-sonnet-4-5",
        tokens_in=100,
        tokens_out=100,
        cost_cents_aud=1000,
    )
    assert result["cost_cents_aud"] == 1005


@pytest.mark.asyncio
async def test_record_uses_litellm_cost_even_when_divergent_logs_warning(
    mock_valkey_client, monkeypatch, caplog
):
    """Caller 500 cents, LiteLLM 1000 cents → 100% divergence → warning logged, LiteLLM used."""
    import logging

    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 1000], [0, 1000]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: 1000)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))

    with caplog.at_level(logging.WARNING):
        result = await record(
            tenant_id=1,
            callsign="max",
            model="m",
            tokens_in=100,
            tokens_out=100,
            cost_cents_aud=500,
        )
    assert result["cost_cents_aud"] == 1000
    assert any("cost divergence" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_record_falls_back_to_caller_cost_when_litellm_unavailable(
    mock_valkey_client, monkeypatch
):
    """LiteLLM unavailable → caller cost_cents_aud used verbatim."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 8], [0, 8]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=100,
        tokens_out=100,
        cost_cents_aud=8,
    )
    assert result["cost_cents_aud"] == 8


# ─── budget warn path ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_warns_when_daily_spend_exceeds_budget(mock_valkey_client, monkeypatch):
    client, _ = mock_valkey_client
    # daily total post-incr = 1500 cents vs budget 1000 cents → exceeded
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 1500], [0, 1500]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=1000))
    nats_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", nats_mock)
    audit_mock = AsyncMock()
    monkeypatch.setattr(spend_tracker, "_write_budget_warn_audit", audit_mock)

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_cents_aud=1500,
    )
    assert result["budget_warn_fired"] is True
    nats_mock.assert_awaited_once()
    audit_mock.assert_awaited_once()
    # Verify NATS payload field names are AUD-cents
    call_args = nats_mock.call_args
    assert call_args.args[1] == 1500  # daily_spend_cents_aud
    assert call_args.args[2] == 1000  # budget_cents_aud


@pytest.mark.asyncio
async def test_record_does_not_warn_when_under_budget(mock_valkey_client, monkeypatch):
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 500], [0, 500]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=1000))
    nats_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", nats_mock)

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_cents_aud=500,
    )
    assert result["budget_warn_fired"] is False
    nats_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_skips_budget_check_when_budget_is_null(mock_valkey_client, monkeypatch):
    """budget=None means no enforcement (unlimited tenant). No NATS, no audit."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 9_999_999], [0, 9_999_999]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))
    nats_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", nats_mock)

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_cents_aud=9_999_999,
    )
    assert result["budget_warn_fired"] is False
    nats_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_warn_only_does_not_kill_session(mock_valkey_client, monkeypatch):
    """Spec contract: warn-only stage — record() returns normally even when
    budget is exceeded; no exception, no return signal indicating kill."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 100_000], [0, 100_000]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=100))
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_write_budget_warn_audit", AsyncMock())

    # Must return without raising, no "kill" / "abort" key in result.
    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_cents_aud=100_000,
    )
    assert "kill" not in result
    assert "abort" not in result
    assert result["budget_warn_fired"] is True


# ─── get_spend ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_spend_returns_valkey_value_as_int(monkeypatch):
    client = MagicMock()
    client.get = AsyncMock(return_value="425")  # 425 cents = $4.25 AUD
    client.aclose = AsyncMock()
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    result = await get_spend(1, "daily")
    assert result == 425
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_get_spend_returns_zero_when_key_absent(monkeypatch):
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.aclose = AsyncMock()
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    assert await get_spend(99, "daily") == 0


@pytest.mark.asyncio
async def test_get_spend_validates_period(monkeypatch):
    """Invalid period → ValueError from tenant_spend_key, never touches Valkey."""
    with pytest.raises(ValueError, match="period must be"):
        await get_spend(1, "yearly")  # type: ignore[arg-type]


# ─── fail-open guarantees ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_continues_when_supabase_write_fails(mock_valkey_client, monkeypatch):
    """Supabase down → Valkey counters still increment, no exception bubbles up."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 8], [0, 8]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost_cents_aud", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=False))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget_cents_aud", AsyncMock(return_value=None))
    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_cents_aud=8,
    )
    assert result["daily_total_cents_aud"] == 8
