"""Tests for SignalConfigRepository — Directive #256"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.enrichment.signal_config import (
    SignalConfigRepository,
    SignalConfig,
    ServiceSignal,
    VerticalNotFoundError,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def make_mock_row(**overrides):
    import uuid, datetime

    defaults = {
        "id": uuid.uuid4(),
        "vertical_slug": "marketing_agency",
        "display_name": "Marketing Agency",
        "description": "Test config",
        "service_signals": [
            {
                "service_name": "paid_ads",
                "label": "Paid Ads Management",
                "dfs_technologies": ["Google Ads", "Facebook Pixel"],
                "gmb_categories": ["marketing_agency"],
                "scoring_weights": {"budget": 30, "pain": 30, "gap": 25, "fit": 15},
                "must_not_have_technologies": ["HubSpot"],
            }
        ],
        "discovery_config": {"dfs_depth": 100, "gmb_zoom": "14z"},
        "enrichment_gates": {
            "min_score_to_enrich": 30,
            "min_score_to_dm": 50,
            "min_score_to_outreach": 65,
        },
        "channel_config": {"email": True, "linkedin": True, "voice": True, "sms": False},
        "created_at": datetime.datetime.now(),
        "updated_at": datetime.datetime.now(),
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, default=None: defaults.get(k, default)
    return row


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_config_returns_valid_structure():
    conn = AsyncMock()
    conn.fetchrow.return_value = make_mock_row()
    repo = SignalConfigRepository(conn)
    config = await repo.get_config("marketing_agency")
    assert isinstance(config, SignalConfig)
    assert config.vertical_slug == "marketing_agency"
    assert config.vertical == "marketing_agency"
    assert len(config.service_signals) == 1
    assert isinstance(config.service_signals[0], ServiceSignal)


@pytest.mark.asyncio
async def test_get_config_missing_vertical_raises():
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    repo = SignalConfigRepository(conn)
    with pytest.raises(VerticalNotFoundError, match="marketing_agency"):
        await repo.get_config("marketing_agency")


@pytest.mark.asyncio
async def test_list_verticals_includes_marketing_agency():
    conn = AsyncMock()
    row = MagicMock()
    row.__getitem__ = lambda self, k: "marketing_agency" if k == "vertical" else None
    conn.fetch.return_value = [row]
    repo = SignalConfigRepository(conn)
    verticals = await repo.list_verticals()
    assert "marketing_agency" in verticals


@pytest.mark.asyncio
async def test_get_services_for_vertical():
    conn = AsyncMock()
    conn.fetchrow.return_value = make_mock_row()
    repo = SignalConfigRepository(conn)
    services = await repo.get_services_for_vertical("marketing_agency")
    assert len(services) == 1
    assert services[0].service_name == "paid_ads"
    assert "Google Ads" in services[0].dfs_technologies
    assert "HubSpot" in services[0].must_not_have_technologies


@pytest.mark.asyncio
async def test_all_dfs_technologies_deduped():
    conn = AsyncMock()
    row = make_mock_row(
        service_signals=[
            {
                "service_name": "svc1",
                "label": "S1",
                "dfs_technologies": ["Google Ads", "Facebook Pixel"],
                "gmb_categories": [],
                "scoring_weights": {},
                "must_not_have_technologies": [],
            },
            {
                "service_name": "svc2",
                "label": "S2",
                "dfs_technologies": ["Google Ads", "HubSpot"],
                "gmb_categories": [],
                "scoring_weights": {},
                "must_not_have_technologies": [],
            },
        ]
    )
    conn.fetchrow.return_value = row
    repo = SignalConfigRepository(conn)
    config = await repo.get_config("marketing_agency")
    techs = config.all_dfs_technologies
    assert techs.count("Google Ads") == 1  # deduped
    assert set(techs) == {"Google Ads", "Facebook Pixel", "HubSpot"}


def test_enrichment_gate_defaults():
    """SignalConfig gate properties return correct values from enrichment_gates."""
    import uuid, datetime

    config = SignalConfig(
        id=str(uuid.uuid4()),
        vertical="test",
        services=[],
        discovery_config={},
        enrichment_gates={
            "min_score_to_enrich": 30,
            "min_score_to_dm": 50,
            "min_score_to_outreach": 65,
        },
        competitor_config={},
        channel_config={},
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    assert config.min_score_to_enrich == 30
    assert config.min_score_to_dm == 50
    assert config.min_score_to_outreach == 65
