"""Tests for Stage7Haiku — Directive #F6 (BDM JOIN)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
import uuid

from src.pipeline.stage_7_haiku import (
    Stage7Haiku,
    PIPELINE_STAGE_S7,
    HAIKU_MODEL,
    HAIKU_INPUT_COST_PER_TOKEN,
    HAIKU_OUTPUT_COST_PER_TOKEN,
)
from src.pipeline.signal_config import SignalConfig, ServiceSignal


AGENCY_PROFILE = {
    "name": "Acme Digital Agency",
    "services": ["SEO", "Paid Ads", "Marketing Automation"],
    "tone": "professional, direct",
    "founder_name": "Sarah",
    "case_study": "Helped a plumber increase leads 3x in 90 days",
}


def make_config():
    """Returns SignalConfig with enrichment_gates including min_score_to_outreach: 65"""
    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=[ServiceSignal("paid_ads", "Paid Ads", ["Google Ads"], [], {})],
        discovery_config={},
        enrichment_gates={
            "min_score_to_enrich": 30,
            "min_score_to_dm": 50,
            "min_score_to_outreach": 65,
        },
        competitor_config={},
        channel_config={"email": True, "linkedin": True, "voice": True, "sms": False},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_row(**overrides):
    """
    Returns a MagicMock row with BDM JOIN fields.
    Supports: bdm_id, dm_name, dm_title, dm_headline, dm_experience,
    dm_skills, dm_education, vulnerability_report, outreach_channels
    """
    defaults = {
        "id": "bu-uuid-1",
        "domain": "acme-mktg.com.au",
        "display_name": "Acme Marketing",
        "gmb_category": "Marketing Agency",
        "state": "VIC",
        "suburb": "Melbourne",
        "best_match_service": "paid_ads",
        "score_reason": "Best match: Paid Ads. Uses Google Ads but missing HubSpot.",
        "tech_stack": ["Google Ads", "WordPress", "Google Analytics"],
        "tech_gaps": ["HubSpot", "Facebook Pixel"],
        "dfs_paid_keywords": 12,
        "gmb_rating": 3.8,
        "gmb_review_count": 22,
        "outreach_channels": ["email", "linkedin"],
        "vulnerability_report": {
            "vulnerabilities": [
                {"title": "No marketing automation"},
                {"title": "Manual CRM entry"},
            ]
        },
        "bdm_id": "bdm-uuid-1",
        "dm_name": "John Smith",
        "dm_title": "Marketing Director",
        "dm_linkedin_url": "https://linkedin.com/in/jsmith",
        "dm_email": "john@acme.com.au",
        "dm_headline": "Digital Marketing Leader | Melbourne",
        "dm_experience": [
            {"title": "Director", "company": "Acme Marketing"},
            {"title": "Manager", "company": "TechCorp"},
        ],
        "dm_skills": ["Google Ads", "Facebook Ads", "Analytics", "Strategy"],
        "dm_education": [{"degree": "MBA", "institution": "University of Melbourne"}],
    }
    defaults.update(overrides)
    row = MagicMock()
    row.__iter__ = lambda self: iter(defaults.items())
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, d=None: defaults.get(k, d)
    row.keys = lambda: defaults.keys()
    return row


def make_ai_client(content="Test message response", input_tokens=100, output_tokens=50):
    """mock AI client returning content with token counts"""
    client = MagicMock()
    client.complete = AsyncMock(
        return_value={
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    )
    return client


def make_conn(rows=None):
    """conn mock with fetch/execute AsyncMock"""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[make_row()] if rows is None else rows)
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_stage(rows=None, ai_content="Test outreach message", config=None):
    """Factory for Stage7Haiku with defaults"""
    ai = make_ai_client(ai_content)
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=config or make_config())
    conn = make_conn(rows)
    stage = Stage7Haiku(ai, signal_repo, conn)
    return stage, ai, conn


# ─── Core F6 Tests (BDM JOIN) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_query_joins_bdm():
    """Verify SQL query contains LEFT JOIN business_decision_makers"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Verify fetch was called with the correct SQL
    assert conn.fetch.called
    sql = conn.fetch.call_args[0][0]

    # Check for LEFT JOIN business_decision_makers
    assert "LEFT JOIN business_decision_makers" in sql
    assert "bdm.id AS bdm_id" in sql
    assert "bdm.name AS dm_name" in sql
    assert "bdm.headline AS dm_headline" in sql


@pytest.mark.asyncio
async def test_skips_rows_without_bdm():
    """Row with bdm_id=None is skipped, no execute called for messages"""
    row_no_bdm = make_row(bdm_id=None)
    stage, ai, conn = make_stage(rows=[row_no_bdm])

    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    # No messages should be generated
    assert result["messages_generated"] == 0
    # execute should not be called (no inserts)
    assert not conn.execute.called


@pytest.mark.asyncio
async def test_writes_to_dm_messages():
    """Verify INSERT INTO dm_messages is called per channel"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Should be called twice: once per channel (email, linkedin) + once for UPDATE
    # Specifically: 2 INSERTs (email, linkedin) + 1 UPDATE
    assert conn.execute.call_count == 3

    # Check that INSERTs target dm_messages
    insert_calls = [
        call for call in conn.execute.call_args_list if "INSERT INTO dm_messages" in call[0][0]
    ]
    assert len(insert_calls) == 2


@pytest.mark.asyncio
async def test_advances_pipeline_stage():
    """Verify UPDATE business_universe pipeline_stage = 7"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    # Find the UPDATE call
    update_calls = [
        call for call in conn.execute.call_args_list if "UPDATE business_universe" in call[0][0]
    ]
    assert len(update_calls) == 1

    # Verify pipeline_stage argument is PIPELINE_STAGE_S7
    update_args = update_calls[0][0]
    assert PIPELINE_STAGE_S7 in update_args


@pytest.mark.asyncio
async def test_prospect_brief_includes_bdm_context():
    """Call _build_prospect_brief with BDM data, verify output contains headline/experience/skills"""
    stage, ai, conn = make_stage()

    business = dict(make_row())
    brief = stage._build_prospect_brief(business)

    # Verify BDM headline appears
    assert business["dm_headline"] in brief

    # Verify experience title and company appear
    assert "Director" in brief
    assert "Acme Marketing" in brief

    # Verify skills appear
    assert "Google Ads" in brief
    assert "Strategy" in brief

    # Verify education appears
    assert "MBA" in brief
    assert "University of Melbourne" in brief


@pytest.mark.asyncio
async def test_prospect_brief_handles_missing_bdm_fields():
    """All BDM fields None, brief still works"""
    stage, ai, conn = make_stage()

    business = dict(
        make_row(
            dm_headline=None,
            dm_experience=None,
            dm_skills=None,
            dm_education=None,
        )
    )
    brief = stage._build_prospect_brief(business)

    # Should not raise, should include base business info
    assert "Acme Marketing" in brief
    assert "acme-mktg.com.au" in brief
    assert "Marketing Agency" in brief


@pytest.mark.asyncio
async def test_per_channel_cost_tracking():
    """Verify channel_costs dict has per-channel token counts"""
    stage, ai, conn = make_stage()

    business = dict(make_row())
    messages, channel_costs = await stage._generate_messages(
        business, AGENCY_PROFILE, ["email", "linkedin"]
    )

    # Should have entries for email and linkedin
    assert "email" in channel_costs
    assert "linkedin" in channel_costs

    # Each should have input_tokens and output_tokens
    assert "input_tokens" in channel_costs["email"]
    assert "output_tokens" in channel_costs["email"]
    assert channel_costs["email"]["input_tokens"] == 100
    assert channel_costs["email"]["output_tokens"] == 50


@pytest.mark.asyncio
async def test_vulnerability_report_in_brief():
    """VR data appears in prospect brief"""
    stage, ai, conn = make_stage()

    business = dict(
        make_row(
            vulnerability_report={
                "vulnerabilities": [
                    {"title": "No marketing automation"},
                    {"title": "Manual CRM entry"},
                    {"title": "Poor email infrastructure"},
                ]
            }
        )
    )
    brief = stage._build_prospect_brief(business)

    # Top 3 vulnerabilities should appear
    assert "No marketing automation" in brief
    assert "Manual CRM entry" in brief
    assert "Poor email infrastructure" in brief


# ─── Integration & Legacy Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generates_email_message():
    """Email message generation works end-to-end"""
    stage, ai, conn = make_stage()
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] > 0
    ai.complete.assert_called()


@pytest.mark.asyncio
async def test_generates_linkedin_message():
    """LinkedIn message generation works"""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["linkedin"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 1
    ai.complete.assert_called_once()


@pytest.mark.asyncio
async def test_generates_voice_knowledge_card():
    """Voice knowledge card generation works"""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["voice"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 1


@pytest.mark.asyncio
async def test_generates_sms_message():
    """SMS message generation works"""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["sms"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 1


@pytest.mark.asyncio
async def test_respects_outreach_gate_threshold():
    """Only pipeline_stage=6 rows with propensity >= 65 are processed"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)
    fetch_sql = conn.fetch.call_args[0][0]
    assert "propensity_score >= $1" in fetch_sql
    assert conn.fetch.call_args[0][1] == 65


@pytest.mark.asyncio
async def test_skips_disabled_channels():
    """Physical channel has no message type — no AI call made for it"""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["physical"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["messages_generated"] == 0
    ai.complete.assert_not_called()


@pytest.mark.asyncio
async def test_skips_rows_without_channels():
    """Row with no outreach_channels is skipped"""
    row_no_channels = make_row(outreach_channels=[])
    stage, ai, conn = make_stage(rows=[row_no_channels])

    result = await stage.run("marketing_agency", AGENCY_PROFILE)

    # No messages should be generated
    assert result["messages_generated"] == 0


@pytest.mark.asyncio
async def test_tracks_cost_usd_and_aud():
    """run() returns dict with cost_usd and cost_aud"""
    stage, ai, conn = make_stage(rows=[make_row(outreach_channels=["email"])])
    result = await stage.run("marketing_agency", AGENCY_PROFILE)
    assert result["cost_usd"] > 0
    assert "cost_aud" in result
    # cost_aud should be cost_usd * 1.55
    assert result["cost_aud"] == round(result["cost_usd"] * 1.55, 4)


@pytest.mark.asyncio
async def test_haiku_model_used():
    """Verify HAIKU_MODEL constant is used in AI calls"""
    ai = make_ai_client()
    stage, _, conn = make_stage(ai_content="Test")
    stage.ai = ai

    business = dict(make_row())
    await stage._generate_messages(business, AGENCY_PROFILE, ["email"])

    # Check that the model parameter was passed
    call_kwargs = ai.complete.call_args[1]
    assert call_kwargs["model"] == HAIKU_MODEL


@pytest.mark.asyncio
async def test_dm_messages_insert_has_status_draft():
    """Inserted dm_messages have status='draft'"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    insert_calls = [
        call for call in conn.execute.call_args_list if "INSERT INTO dm_messages" in call[0][0]
    ]
    assert len(insert_calls) == 2

    for call in insert_calls:
        sql = call[0][0]
        # status is passed as 'draft'
        assert "'draft'" in sql


@pytest.mark.asyncio
async def test_batch_size_respected():
    """run() passes batch_size to DB query LIMIT"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE, batch_size=50)

    # LIMIT $2 should be batch_size
    assert conn.fetch.call_args[0][2] == 50


@pytest.mark.asyncio
async def test_handles_ai_exception_gracefully():
    """AI client exception is caught, warning logged, message skipped"""
    ai = make_ai_client()
    ai.complete = AsyncMock(side_effect=Exception("API error"))
    stage, _, conn = make_stage()
    stage.ai = ai

    business = dict(make_row())
    messages, channel_costs = await stage._generate_messages(business, AGENCY_PROFILE, ["email"])

    # Should return empty messages dict (exception caught)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_message_generation_rate_limiting():
    """_generate_messages includes 0.5s sleep between channel calls"""
    stage, ai, conn = make_stage()

    business = dict(make_row())

    # Mock asyncio.sleep to verify it's called
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        messages, _ = await stage._generate_messages(
            business, AGENCY_PROFILE, ["email", "linkedin"]
        )

        # Should sleep once between calls (2 channels = 1 sleep)
        assert mock_sleep.called


@pytest.mark.asyncio
async def test_total_cost_usd_calculation():
    """total_cost_usd property correctly sums input+output token costs"""
    ai = make_ai_client(input_tokens=100, output_tokens=50)
    stage, _, conn = make_stage()
    stage.ai = ai

    business = dict(make_row())
    # Generate 2 messages (email, linkedin), each with 100 input, 50 output tokens
    await stage._generate_messages(business, AGENCY_PROFILE, ["email", "linkedin"])

    # 2 channels * (100 input * 0.0000008 + 50 output * 0.000004)
    # = 2 * (0.00008 + 0.0002) = 2 * 0.00028 = 0.00056
    expected_cost = 2 * (100 * HAIKU_INPUT_COST_PER_TOKEN + 50 * HAIKU_OUTPUT_COST_PER_TOKEN)
    assert abs(stage.total_cost_usd - expected_cost) < 0.00001


@pytest.mark.asyncio
async def test_dm_experience_list_format():
    """dm_experience is list of dicts with title/company"""
    stage, ai, conn = make_stage()

    business = dict(
        make_row(
            dm_experience=[
                {"title": "CEO", "company": "StartupCo"},
                {"title": "Director", "company": "BigCorp"},
            ]
        )
    )
    brief = stage._build_prospect_brief(business)

    # Should include recent experience entries
    assert "CEO" in brief
    assert "StartupCo" in brief
    assert "Director" in brief
    assert "BigCorp" in brief


@pytest.mark.asyncio
async def test_dm_skills_list_format():
    """dm_skills is list of strings, top 5 included"""
    stage, ai, conn = make_stage()

    business = dict(
        make_row(
            dm_skills=[
                "Google Ads",
                "Facebook Ads",
                "Analytics",
                "Strategy",
                "Copywriting",
                "Design",
            ]
        )
    )
    brief = stage._build_prospect_brief(business)

    # Top 5 should appear
    assert "Google Ads" in brief
    assert "Strategy" in brief
    assert "Copywriting" in brief


@pytest.mark.asyncio
async def test_dm_education_format():
    """dm_education is list of dicts with degree/institution"""
    stage, ai, conn = make_stage()

    business = dict(
        make_row(dm_education=[{"degree": "Bachelor of Commerce", "institution": "UNSW"}])
    )
    brief = stage._build_prospect_brief(business)

    assert "Bachelor of Commerce" in brief
    assert "UNSW" in brief


@pytest.mark.asyncio
async def test_message_returned_stripped():
    """Messages returned from AI are stripped of whitespace"""
    ai = make_ai_client("  Test message with whitespace  \n")
    stage, _, conn = make_stage()
    stage.ai = ai

    business = dict(make_row())
    messages, _ = await stage._generate_messages(business, AGENCY_PROFILE, ["email"])

    # Message should be stripped
    assert messages["email"] == "Test message with whitespace"


@pytest.mark.asyncio
async def test_dm_messages_insert_includes_all_fields():
    """dm_messages INSERT includes business_universe_id, bdm_id, channel, body, model, cost_usd, generated_at"""
    stage, ai, conn = make_stage()
    await stage.run("marketing_agency", AGENCY_PROFILE)

    insert_calls = [
        call for call in conn.execute.call_args_list if "INSERT INTO dm_messages" in call[0][0]
    ]

    for call in insert_calls:
        sql = call[0][0]
        # Verify all expected columns are mentioned
        assert "business_universe_id" in sql
        assert "business_decision_makers_id" in sql
        assert "channel" in sql
        assert "body" in sql
        assert "model" in sql
        assert "cost_usd" in sql
        assert "generated_at" in sql
