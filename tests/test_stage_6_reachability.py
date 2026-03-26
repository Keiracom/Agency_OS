"""Tests for Stage6Reachability — Directive #264"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.pipeline.stage_6_reachability import (
    Stage6Reachability, PIPELINE_STAGE_S6,
    validate_email, validate_au_phone, validate_linkedin_url, calculate_reachability,
)
from src.enrichment.signal_config import SignalConfig, ServiceSignal


def make_config(channel_config=None):
    import uuid
    return SignalConfig(
        id=str(uuid.uuid4()), vertical="marketing_agency",
        services=[],
        discovery_config={},
        enrichment_gates={"min_score_to_enrich": 30, "min_score_to_dm": 50, "min_score_to_outreach": 65},
        competitor_config={},
        channel_config=channel_config or {"email": True, "linkedin": True, "voice": True, "sms": False},
        created_at=datetime.now(), updated_at=datetime.now(),
    )


def make_row(**overrides):
    defaults = {
        "id": "uuid-1",
        "dm_email": "john@acme.com.au",
        "dm_phone": "+61412345678",
        "dm_linkedin_url": "https://linkedin.com/in/john-smith",
        "address": "123 Main St",
        "state": "VIC",
        "suburb": "Melbourne",
        "gmb_place_id": "ChIJ123",
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__iter__ = lambda self: iter(defaults.items())
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, d=None: defaults.get(k, d)
    row.keys = lambda: defaults.keys()
    return row


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[make_row()] if rows is None else rows)
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_stage(channel_config=None, rows=None):
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=make_config(channel_config))
    conn = make_conn(rows)
    stage = Stage6Reachability(signal_repo, conn)
    return stage, conn


# ─── Unit tests ──────────────────────────────────────────────────────────────

def test_validates_email_format():
    assert validate_email("john@acme.com.au") is True
    assert validate_email("info@example.com") is True
    assert validate_email("not-an-email") is False
    assert validate_email(None) is False
    assert validate_email("@nodomain") is False


def test_validates_au_phone_format():
    assert validate_au_phone("+61412345678") is True
    assert validate_au_phone("0412345678") is True
    assert validate_au_phone("0312345678") is True
    assert validate_au_phone("1234567890") is False
    assert validate_au_phone(None) is False


def test_validates_linkedin_url():
    assert validate_linkedin_url("https://linkedin.com/in/john-smith") is True
    assert validate_linkedin_url("https://www.linkedin.com/in/jsmith123") is True
    assert validate_linkedin_url("https://linkedin.com/company/acme") is False
    assert validate_linkedin_url(None) is False
    assert validate_linkedin_url("https://example.com") is False


def test_calculates_final_reachability_score():
    assert calculate_reachability(["email", "linkedin", "voice", "physical"]) == 100
    assert calculate_reachability(["email"]) == 40  # 30 + 10 base
    assert calculate_reachability([]) == 0


@pytest.mark.asyncio
async def test_determines_outreach_channels():
    stage, conn = make_stage()
    result = await stage.run("marketing_agency")
    assert result["validated"] == 1
    args = conn.execute.call_args[0]
    channels = args[1]  # outreach_channels positional arg
    assert "email" in channels
    assert "linkedin" in channels
    assert "voice" in channels


@pytest.mark.asyncio
async def test_respects_channel_config():
    """SMS disabled in config → not in confirmed channels."""
    stage, conn = make_stage(channel_config={"email": True, "linkedin": False, "voice": False, "sms": False})
    result = await stage.run("marketing_agency")
    args = conn.execute.call_args[0]
    channels = args[1]
    assert "linkedin" not in channels
    assert "voice" not in channels
    assert "email" in channels


@pytest.mark.asyncio
async def test_updates_pipeline_stage_to_6():
    stage, conn = make_stage()
    await stage.run("marketing_agency")
    args = conn.execute.call_args[0]
    assert PIPELINE_STAGE_S6 in args


@pytest.mark.asyncio
async def test_returns_channel_breakdown():
    stage, conn = make_stage()
    result = await stage.run("marketing_agency")
    assert "channels_confirmed" in result
    assert isinstance(result["channels_confirmed"], dict)
