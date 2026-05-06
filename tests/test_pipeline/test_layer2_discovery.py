"""Tests for Layer2Discovery exception handling — Directive #285 additions."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.enrichment.signal_config import ServiceSignal, SignalConfig
from src.pipeline.layer_2_discovery import Layer2Discovery


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def make_signal_config(discovery_config: dict | None = None) -> SignalConfig:
    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=[
            ServiceSignal(
                service_name="paid_ads",
                label="Paid Ads",
                dfs_technologies=["Google Ads"],
                gmb_categories=["marketing_agency"],
                scoring_weights={},
            )
        ],
        discovery_config=discovery_config or {},
        enrichment_gates={},
        competitor_config={},
        channel_config={"email": True},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="UPDATE 0")
    return conn


# ─── Task E: ValueError on DFS 4xx propagates ─────────────────────────────────


@pytest.mark.asyncio
async def test_layer2_raises_on_dfs_value_error():
    """
    ValueError raised by DFS client (e.g. on 4xx response) must propagate
    out of run() — it must NOT be swallowed as a source_error.
    """
    cfg = {"category_codes": [10233]}
    conn = make_conn()
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(
        side_effect=ValueError("DFS returned 40501: invalid category")
    )
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        with pytest.raises(ValueError, match="DFS returned 40501"):
            await engine.run("marketing_agency", daily_budget_usd=10.0)


@pytest.mark.asyncio
async def test_layer2_raises_on_http_status_error():
    """
    httpx.HTTPStatusError (e.g. 500) must propagate — not swallowed.
    """
    cfg = {"category_codes": [10233]}
    conn = make_conn()
    dfs = MagicMock()

    mock_request = MagicMock(spec=httpx.Request)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500

    dfs.domain_metrics_by_categories = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server error", request=mock_request, response=mock_response
        )
    )
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        with pytest.raises(httpx.HTTPStatusError):
            await engine.run("marketing_agency", daily_budget_usd=10.0)


@pytest.mark.asyncio
async def test_layer2_swallows_timeout_error():
    """
    httpx.TimeoutException is expected and non-fatal — run() should complete
    and record it as a source_error without raising.
    """
    cfg = {"category_codes": [10233, 10234]}
    conn = make_conn()
    conn.fetchval = AsyncMock(return_value=0)
    dfs = MagicMock()
    # First category times out, second succeeds with empty
    dfs.domain_metrics_by_categories = AsyncMock(
        side_effect=[httpx.TimeoutException("read timeout"), []]
    )
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    # Must complete without raising
    assert len(stats.source_errors) == 1
    assert "timeout" in stats.source_errors[0].lower()
