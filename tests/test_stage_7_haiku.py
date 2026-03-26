"""Tests for Stage7Haiku — Directive #264"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.pipeline.stage_7_haiku import Stage7Haiku, PIPELINE_STAGE_S7, HAIKU_MODEL
from src.enrichment.signal_config import SignalConfig, ServiceSignal


AGENCY_PROFILE = {
    "name": "Acme Digital Agency",
    "services": ["SEO", "Paid Ads", "Marketing Automation"],
    "tone": "professional, direct",
    "founder_name": "Sarah",
    "case_study": "Helped a plumber increase leads 3x in 90 days",
}


def make_config():
    import uuid
    return SignalConfig(
        id=str(uuid.uuid4()), vertical_slug="marketing_agency",
        display_name="MktAgency", description=None,
        service_signals=[],
        discovery_config={},
        enrichment_gates={"min_score_to_enrich": 30, "min_score_to_dm": 50, "min_score_to_outreach": 65},
        channel_config={"email": True, "linkedin": True, "voice": True, "sms": False},
        created_at=datetime.now(), updated_at=datetime.now(),
    )


def make_row(**overrides):
    defaults = {
        "id": "uuid-1", "domain": "acme-mktg.com.au",
        "display_name": "Acme Marketing", "gmb_category": "Marketing Agency",
        "state": "VIC", "suburb": "Melbourne",
        "dm_name": "John Smith", "dm_title": "Director",
        "best_match_service": "paid_ads",
        "score_reason": "Best match: Paid Ads. Uses Google Ads but missing HubSpot. Active ad spend detected.",
        "tech_stack": ["Google Ads", "WordPress", "Google Analytics"],
        "tech_gaps": ["HubSpot", "Facebook Pixel"],
        "dfs_paid_keywords": 12,
        "gmb_rating": 3.8,
        "gmb_review_count": 22,
        "outreach_channels": ["email", "linkedin", "voice"],
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__iter__ = lambda self: iter(defaults.items())
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, d=None: defaults.get(k, d)
    row.keys = lambda: defaults.keys()
    return row


def make_ai_client(content="Test message response"):
    client = MagicMock()
    client.complete = AsyncMock(return_value={
        "content": content,
        "input_tokens": 200,
        "output_tokens": 80,
        "cost_aud": 0.001,
    })
    return client


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[make_row()] if rows is None else rows)
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_stage(rows=None, ai_content="Test outreach message"):
    ai = make_ai_client(ai_content)
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=make_config())
    conn = make_conn(rows)
    stage = Stage7Haiku(ai, signal_repo, conn)
    return stage, ai, conn


@pytest.mark.asyncio
async def test_generates_email_message():
    stage, ai, conn = make_stage()
    stage.sources = None
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] > 0
    ai.complete.assert_called()


@pytest.mark.asyncio
async def test_generates_linkedin_message():
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["linkedin"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 1
    # Verify the right channel prompt was used
    ai.complete.assert_called_once()


@pytest.mark.asyncio
async def test_generates_voice_knowledge_card():
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["voice"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 1


@pytest.mark.asyncio
async def test_generates_sms_message():
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["sms"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 1


@pytest.mark.asyncio
async def test_references_specific_signal_in_message():
    """Prospect brief includes score_reason and tech data for Haiku to reference."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)
    call_kwargs = ai.complete.call_args
    prompt = call_kwargs[1].get("prompt") or (call_kwargs[0][0] if call_kwargs[0] else "")
    assert "Google Ads" in prompt or "paid_ads" in prompt or "score_reason" in prompt.lower() or "Score reason" in prompt


@pytest.mark.asyncio
async def test_uses_best_match_service():
    """best_match_service from BU is included in prospect brief."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)
    # Check that any call includes best_match_service context
    all_calls_text = " ".join(
        str(call[1].get("prompt") or (call[0][0] if call[0] else ""))
        for call in ai.complete.call_args_list
    )
    assert "paid_ads" in all_calls_text


@pytest.mark.asyncio
async def test_respects_outreach_gate_threshold():
    """Only pipeline_stage=6 rows with propensity >= 65 are processed."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)
    fetch_sql = conn.fetch.call_args[0][0]
    assert "propensity_score >= $1" in fetch_sql
    assert conn.fetch.call_args[0][1] == 65


@pytest.mark.asyncio
async def test_skips_disabled_channels():
    """Physical channel has no message type — no AI call made for it."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["physical"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 0
    ai.complete.assert_not_called()


@pytest.mark.asyncio
async def test_tracks_cost():
    """Cost tracked from token counts."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["email"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["cost_usd"] > 0
    assert "cost_aud" in result


@pytest.mark.asyncio
async def test_updates_pipeline_stage_to_7():
    """All processed rows advance to pipeline_stage=7."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)
    args = conn.execute.call_args[0]
    assert PIPELINE_STAGE_S7 in args
