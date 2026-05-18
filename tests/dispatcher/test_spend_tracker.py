"""KEI-212 — tests for src/dispatcher/spend_tracker.

External dependencies (Valkey, Supabase, NATS, litellm) are mocked so CI
runs without live services. The acceptance criterion "Cost calc matches
LiteLLM reported cost (within 1%)" is enforced by feeding a known LiteLLM
return through the divergence path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dispatcher import spend_tracker
from src.dispatcher.spend_tracker import (
    SPEND_NAMESPACE_PREFIX,
    _seconds_until_midnight_utc,
    _seconds_until_month_boundary_utc,
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


# ─── _compute_cost ─────────────────────────────────────────────────────────


def test_compute_cost_returns_none_when_litellm_missing(monkeypatch):
    """No litellm → return None so caller falls back to its own cost_usd."""

    def raise_import_error(*_args, **_kw):
        raise ImportError("litellm not installed")

    with patch("builtins.__import__", side_effect=raise_import_error):
        assert spend_tracker._compute_cost("claude-sonnet-4-5", 100, 100) is None


def test_compute_cost_sums_prompt_and_completion():
    """LiteLLM returns (prompt_cost, completion_cost); _compute_cost sums them."""
    fake_litellm = MagicMock()
    fake_litellm.cost_per_token = MagicMock(return_value=(0.001, 0.002))
    with patch.dict("sys.modules", {"litellm": fake_litellm}):
        result = spend_tracker._compute_cost("claude-sonnet-4-5", 100, 100)
    assert result == pytest.approx(0.003)


def test_compute_cost_returns_none_on_litellm_exception():
    """Unknown model → litellm raises → _compute_cost returns None."""
    fake_litellm = MagicMock()
    fake_litellm.cost_per_token = MagicMock(side_effect=ValueError("unknown model"))
    with patch.dict("sys.modules", {"litellm": fake_litellm}):
        assert spend_tracker._compute_cost("made-up-model", 100, 100) is None


# ─── record() — happy path ─────────────────────────────────────────────────


@pytest.fixture
def mock_valkey_client():
    """Fake redis.asyncio.Redis with pipeline + ttl methods stubbed."""
    client = MagicMock()
    pipe = MagicMock()
    pipe.exists = MagicMock()
    pipe.incrbyfloat = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 0.0])  # not exists, new total
    client.pipeline = MagicMock(return_value=pipe)
    client.expire = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.aclose = AsyncMock(return_value=None)
    return client, pipe


@pytest.mark.asyncio
async def test_record_increments_daily_and_monthly(mock_valkey_client, monkeypatch):
    """One record() call → two Valkey INCRBYFLOAT (daily + monthly)."""
    client, pipe = mock_valkey_client
    pipe.execute = AsyncMock(side_effect=[[0, 0.05], [0, 0.05]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))

    result = await record(
        tenant_id=1,
        callsign="max",
        model="claude-sonnet-4-5",
        tokens_in=100,
        tokens_out=200,
        cost_usd=0.05,
    )
    assert result["cost_usd"] == 0.05
    assert result["daily_total_usd"] == 0.05
    assert result["monthly_total_usd"] == 0.05
    assert result["budget_warn_fired"] is False
    # Two pipelines built (one per period)
    assert client.pipeline.call_count == 2


@pytest.mark.asyncio
async def test_record_sets_ttl_only_on_first_write(mock_valkey_client, monkeypatch):
    """existed=0 → EXPIRE called; existed=1 → EXPIRE skipped."""
    client, pipe = mock_valkey_client
    # First period: didn't exist → expire called. Second period: existed → skipped.
    pipe.execute = AsyncMock(side_effect=[[0, 0.05], [1, 0.05]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))

    await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_usd=0.05,
    )
    # First call (daily, didn't exist) → expire fired; second (monthly, existed) → skipped.
    assert client.expire.call_count == 1


# ─── cost match within 1% (acceptance criterion) ───────────────────────────


@pytest.mark.asyncio
async def test_record_uses_litellm_cost_when_within_1pct(mock_valkey_client, monkeypatch):
    """Caller cost 0.0500, LiteLLM 0.0501 → divergence 0.2% → LiteLLM used."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 0.0501], [0, 0.0501]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: 0.0501)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))

    result = await record(
        tenant_id=1,
        callsign="max",
        model="claude-sonnet-4-5",
        tokens_in=100,
        tokens_out=100,
        cost_usd=0.0500,
    )
    assert result["cost_usd"] == pytest.approx(0.0501)


@pytest.mark.asyncio
async def test_record_uses_litellm_cost_even_when_divergent_logs_warning(
    mock_valkey_client, monkeypatch, caplog
):
    """Caller 0.05, LiteLLM 0.10 → 100% divergence → warning logged, LiteLLM still used."""
    import logging

    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 0.10], [0, 0.10]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: 0.10)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))

    with caplog.at_level(logging.WARNING):
        result = await record(
            tenant_id=1,
            callsign="max",
            model="m",
            tokens_in=100,
            tokens_out=100,
            cost_usd=0.05,
        )
    assert result["cost_usd"] == pytest.approx(0.10)
    assert any("cost divergence" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_record_falls_back_to_caller_cost_when_litellm_unavailable(
    mock_valkey_client, monkeypatch
):
    """LiteLLM unavailable → caller cost_usd used verbatim."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 0.05], [0, 0.05]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=100,
        tokens_out=100,
        cost_usd=0.05,
    )
    assert result["cost_usd"] == 0.05


# ─── budget warn path ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_warns_when_daily_spend_exceeds_budget(mock_valkey_client, monkeypatch):
    client, _ = mock_valkey_client
    # daily total post-incr = 15.00 vs budget 10.00 → exceeded
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 15.0], [0, 15.0]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=10.0))
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
        cost_usd=15.0,
    )
    assert result["budget_warn_fired"] is True
    nats_mock.assert_awaited_once()
    audit_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_does_not_warn_when_under_budget(mock_valkey_client, monkeypatch):
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 5.0], [0, 5.0]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=10.0))
    nats_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", nats_mock)

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_usd=5.0,
    )
    assert result["budget_warn_fired"] is False
    nats_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_skips_budget_check_when_budget_is_null(mock_valkey_client, monkeypatch):
    """budget=None means no enforcement (unlimited tenant). No NATS, no audit."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 99999.0], [0, 99999.0]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))
    nats_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", nats_mock)

    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_usd=99999.0,
    )
    assert result["budget_warn_fired"] is False
    nats_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_warn_only_does_not_kill_session(mock_valkey_client, monkeypatch):
    """Spec contract: warn-only stage — record() returns normally even when
    budget is exceeded; no exception, no return signal indicating kill."""
    client, _ = mock_valkey_client
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 1000.0], [0, 1000.0]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=1.0))
    monkeypatch.setattr(spend_tracker, "_publish_nats_warn", AsyncMock(return_value=True))
    monkeypatch.setattr(spend_tracker, "_write_budget_warn_audit", AsyncMock())

    # Must return without raising, no "kill" / "abort" key in result.
    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_usd=1000.0,
    )
    assert "kill" not in result
    assert "abort" not in result
    assert result["budget_warn_fired"] is True


# ─── get_spend ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_spend_returns_valkey_value(monkeypatch):
    client = MagicMock()
    client.get = AsyncMock(return_value="42.5")
    client.aclose = AsyncMock()
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    assert await get_spend(1, "daily") == 42.5


@pytest.mark.asyncio
async def test_get_spend_returns_zero_when_key_absent(monkeypatch):
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.aclose = AsyncMock()
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    assert await get_spend(99, "daily") == 0.0


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
    client.pipeline.return_value.execute = AsyncMock(side_effect=[[0, 0.05], [0, 0.05]])
    monkeypatch.setattr(spend_tracker, "get_valkey_client", lambda: client)
    monkeypatch.setattr(spend_tracker, "_compute_cost", lambda *_a, **_kw: None)
    monkeypatch.setattr(spend_tracker, "_write_spend_row", AsyncMock(return_value=False))
    monkeypatch.setattr(spend_tracker, "_read_daily_budget", AsyncMock(return_value=None))
    result = await record(
        tenant_id=1,
        callsign="max",
        model="m",
        tokens_in=10,
        tokens_out=10,
        cost_usd=0.05,
    )
    assert result["daily_total_usd"] == 0.05
