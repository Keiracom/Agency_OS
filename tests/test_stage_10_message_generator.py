"""Tests for Stage 10 Message Generator — Directive #339.1"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.pipeline.stage_10_message_generator import (
    Stage10MessageGenerator,
    SONNET_MODEL,
    HAIKU_MODEL,
    PIPELINE_STAGE_S10,
)
from src.enrichment.signal_config import SignalConfig


AGENCY_PROFILE = {
    "name": "Acme Digital Agency",
    "services": ["SEO", "Paid Ads", "Marketing Automation"],
    "tone": "professional, direct, results-focused",
    "founder_name": "Sarah",
    "case_study": "Helped a plumber increase leads 3x in 90 days",
}


def make_config():
    import uuid

    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=[],
        discovery_config={},
        enrichment_gates={"min_score_to_outreach": 65},
        competitor_config={},
        channel_config={"email": True, "linkedin": True, "voice": True, "sms": True},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_row(**overrides):
    defaults = {
        "id": "uuid-1",
        "domain": "acme-mktg.com.au",
        "display_name": "Acme Marketing",
        "gmb_category": "Marketing Agency",
        "state": "VIC",
        "suburb": "Melbourne",
        "dm_name": "John Smith",
        "dm_title": "Director",
        "best_match_service": "paid_ads",
        "score_reason": "Best match: Paid Ads. Uses Google Ads but missing HubSpot.",
        "tech_stack": ["Google Ads", "WordPress", "Google Analytics"],
        "tech_gaps": ["HubSpot", "Facebook Pixel"],
        "dfs_paid_keywords": 12,
        "gmb_rating": 3.8,
        "gmb_review_count": 22,
        "outreach_channels": ["email", "linkedin", "sms", "voice"],
        "vulnerability_report": {
            "marketing_automation": {"grade": "D"},
            "analytics": {"grade": "C"},
        },
        "bdm_id": "bdm-uuid-1",
        "bdm_headline": "Digital Marketing Strategist",
        "bdm_experience": [
            {"title": "Senior Manager", "company": "Tech Corp"},
            {"title": "Specialist", "company": "Agency X"},
        ],
        "bdm_skills": ["SEO", "Analytics", "Paid Ads"],
        "bdm_education": [],
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__iter__ = lambda self: iter(defaults.items())
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, d=None: defaults.get(k, d)
    row.keys = lambda: defaults.keys()
    return row


def make_ai_response(
    content="Test message", input_tokens=500, output_tokens=100, cached_tokens=400
):
    return {
        "content": content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "cost_aud": 0.01,
    }


def make_ai_client(
    content="Test message response", input_tokens=500, output_tokens=100, cached_tokens=400
):
    client = MagicMock()
    client.complete = AsyncMock(
        return_value=make_ai_response(content, input_tokens, output_tokens, cached_tokens)
    )
    return client


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[make_row()] if rows is None else rows)
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_stage(
    rows=None,
    ai_content="Test message",
    ai_input_tokens=500,
    ai_output_tokens=100,
    ai_cached_tokens=400,
):
    ai = make_ai_client(ai_content, ai_input_tokens, ai_output_tokens, ai_cached_tokens)
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=make_config())
    conn = make_conn(rows)
    stage = Stage10MessageGenerator(ai, signal_repo, conn)
    return stage, ai, conn


@pytest.mark.asyncio
async def test_uses_sonnet_for_email():
    """Email channel should call ai.complete with Sonnet model."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["email"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Check that ai.complete was called with Sonnet model
    ai.complete.assert_called()
    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs.get("model") == SONNET_MODEL


@pytest.mark.asyncio
async def test_uses_haiku_for_linkedin():
    """LinkedIn channel should call ai.complete with Haiku model."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["linkedin"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    ai.complete.assert_called()
    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs.get("model") == HAIKU_MODEL


@pytest.mark.asyncio
async def test_uses_haiku_for_sms():
    """SMS channel should call ai.complete with Haiku model."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["sms"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    ai.complete.assert_called()
    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs.get("model") == HAIKU_MODEL


@pytest.mark.asyncio
async def test_uses_haiku_for_voice():
    """Voice channel should call ai.complete with Haiku model."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["voice"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    ai.complete.assert_called()
    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs.get("model") == HAIKU_MODEL


@pytest.mark.asyncio
async def test_query_reads_stage_9():
    """Fetch query should filter for pipeline_stage = 9."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    fetch_sql = conn.fetch.call_args[0][0]
    assert "pipeline_stage = 9" in fetch_sql


@pytest.mark.asyncio
async def test_query_joins_bdm_with_is_current():
    """Fetch query should LEFT JOIN bdm with is_current = TRUE."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    fetch_sql = conn.fetch.call_args[0][0]
    assert "LEFT JOIN business_decision_makers" in fetch_sql
    assert "is_current = TRUE" in fetch_sql


@pytest.mark.asyncio
async def test_skips_no_bdm():
    """Rows without bdm_id should be skipped."""
    stage, ai, conn = make_stage(rows=[make_row(bdm_id=None)])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    assert result["skipped_no_bdm"] == 1
    assert result["messages_generated"] == 0
    ai.complete.assert_not_called()


@pytest.mark.asyncio
async def test_writes_dm_messages_per_channel():
    """Each channel should write one dm_messages row."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["email", "linkedin", "sms"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Should have 3 INSERT calls (one per channel) + 1 UPDATE
    inserts = [
        call for call in conn.execute.call_args_list if "INSERT INTO dm_messages" in call[0][0]
    ]
    assert len(inserts) == 3


@pytest.mark.asyncio
async def test_advances_pipeline_to_10():
    """After processing, pipeline_stage should be set to 10."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Find the UPDATE call
    update_calls = [
        call for call in conn.execute.call_args_list if "UPDATE business_universe" in call[0][0]
    ]
    assert len(update_calls) > 0
    update_sql = update_calls[0][0][0]
    assert "pipeline_stage = $1" in update_sql
    # The value should be PIPELINE_STAGE_S10
    assert update_calls[0][0][1] == PIPELINE_STAGE_S10


@pytest.mark.asyncio
async def test_email_subject_extraction():
    """Email subject should be extracted from 'SUBJECT: ...' line."""
    email_content = (
        "SUBJECT: Check out your tech stack\n\nHey John,\n\nI noticed you're using Ads..."
    )
    stage, ai, conn = make_stage(
        rows=[make_row(outreach_channels=["email"])],
        ai_content=email_content,
    )
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    # Check that the INSERT call includes the subject
    inserts = [
        call for call in conn.execute.call_args_list if "INSERT INTO dm_messages" in call[0][0]
    ]
    assert len(inserts) == 1
    insert_call = inserts[0]
    # Args to INSERT: bu_id, bdm_id, channel, subject, body, model, cost, now
    # subject is at position 3 (0-indexed)
    subject_arg = insert_call[0][4]  # $4 = subject
    assert subject_arg == "Check out your tech stack"


@pytest.mark.asyncio
async def test_concurrent_haiku_channels():
    """LinkedIn + SMS + Voice should run concurrently via gather."""
    stage, ai, conn = make_stage(
        rows=[make_row(outreach_channels=["email", "linkedin", "sms", "voice"])]
    )
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    # All 4 channels should be called
    assert ai.complete.call_count == 4
    # Should have 4 messages generated
    assert result["messages_generated"] == 4


@pytest.mark.asyncio
async def test_cost_tracking_per_channel():
    """Cost should be tracked separately per channel."""
    # Email: 500 input + 100 output
    # Haiku: 200 input + 50 output each (for 3 channels)
    stage, ai, conn = make_stage(
        rows=[make_row(outreach_channels=["email", "linkedin", "sms"])],
        ai_input_tokens=500,
        ai_output_tokens=100,
    )
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    per_channel = result["per_channel"]
    assert per_channel["email"]["count"] == 1
    assert per_channel["linkedin"]["count"] == 1
    assert per_channel["sms"]["count"] == 1
    assert per_channel["email"]["cost_usd"] > 0
    assert per_channel["linkedin"]["cost_usd"] > 0
    assert per_channel["sms"]["cost_usd"] > 0


@pytest.mark.asyncio
async def test_cache_hit_rate_calculation():
    """Cache hit rate should be cached_tokens / (cached + non_cached)."""
    # 400 cached out of 500 input = 80% cache hit
    stage, ai, conn = make_stage(
        ai_input_tokens=500,
        ai_output_tokens=100,
        ai_cached_tokens=400,
    )
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    cache_hit = result["cache_hit_rate"]
    # Single call: 400 cached / 500 total = 0.8
    assert cache_hit == 0.8


@pytest.mark.asyncio
async def test_prospect_brief_includes_bdm_context():
    """Prospect brief should include BDM headline, experience, and skills."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Extract prompt from AI call
    call_kwargs = ai.complete.call_args[1]
    prompt = call_kwargs.get("prompt", "")

    assert "Digital Marketing Strategist" in prompt  # bdm_headline
    assert "Senior Manager" in prompt  # top role title
    assert "SEO" in prompt  # bdm_skills


@pytest.mark.asyncio
async def test_vulnerability_grades_in_brief():
    """Vulnerability grades should appear in prospect brief."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    call_kwargs = ai.complete.call_args[1]
    prompt = call_kwargs.get("prompt", "")

    # Should mention vulnerability grades
    assert "Vulnerability grades:" in prompt
    assert "marketing_automation:D" in prompt
    assert "analytics:C" in prompt


@pytest.mark.asyncio
async def test_returns_cost_aud():
    """Cost should be converted to AUD using 1 USD = 1.55 AUD."""
    # With mock returning cost_aud, verify it's used
    stage, ai, conn = make_stage()
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    assert "cost_aud" in result
    assert result["cost_aud"] > 0
    # cost_usd * 1.55 should equal cost_aud
    assert result["cost_aud"] == round(result["cost_usd"] * 1.55, 4)


@pytest.mark.asyncio
async def test_enables_caching():
    """All ai.complete calls should pass enable_caching=True."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Check all calls have enable_caching=True
    for call in ai.complete.call_args_list:
        call_kwargs = call[1]
        assert call_kwargs.get("enable_caching") is True


@pytest.mark.asyncio
async def test_respects_outreach_gate():
    """Only rows with propensity_score >= min_score_to_outreach should be processed."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    fetch_sql = conn.fetch.call_args[0][0]
    assert "propensity_score >= $1" in fetch_sql
    # Gate value should be passed as second arg (index 1)
    assert conn.fetch.call_args[0][1] == 65


@pytest.mark.asyncio
async def test_system_prompt_passed_to_ai():
    """System prompt should be passed to every ai.complete call."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    call_kwargs = ai.complete.call_args[1]
    system = call_kwargs.get("system", "")
    assert "senior business development consultant" in system.lower()
    assert "never use" in system.lower()


@pytest.mark.asyncio
async def test_no_messages_when_no_active_channels():
    """Rows with no active outreach_channels should be skipped."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=[])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    assert result["messages_generated"] == 0
    assert result["skipped_no_bdm"] == 1
    ai.complete.assert_not_called()


@pytest.mark.asyncio
async def test_dms_processed_incremented():
    """dms_processed should increment for each successfully processed DM."""
    # 3 rows with valid BDM and channels
    rows = [
        make_row(id=f"uuid-{i}", bdm_id=f"bdm-{i}", outreach_channels=["email"]) for i in range(3)
    ]
    stage, ai, conn = make_stage(rows=rows)
    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    assert result["dms_processed"] == 3
    assert result["messages_generated"] == 3


@pytest.mark.asyncio
async def test_email_max_tokens_500():
    """Email generation should request max_tokens=500."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["email"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs.get("max_tokens") == 500


@pytest.mark.asyncio
async def test_haiku_max_tokens_300():
    """Non-email channels should request max_tokens=300."""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["linkedin"])])
    await stage.run("marketing_agency", AGENCY_PROFILE)

    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs.get("max_tokens") == 300


@pytest.mark.asyncio
async def test_temperature_set_to_0_7():
    """All calls should use temperature=0.7."""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    for call in ai.complete.call_args_list:
        call_kwargs = call[1]
        assert call_kwargs.get("temperature") == 0.7
