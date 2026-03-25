# FILE: tests/test_stage7_personalisation.py
# PURPOSE: Unit tests for Stage7Personalisation
# DIRECTIVE: #252

from __future__ import annotations

import json
import math
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.pipeline.stage7_personalisation import (
    Stage7Personalisation,
    HAIKU_INPUT_COST_PER_TOKEN,
    HAIKU_OUTPUT_COST_PER_TOKEN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CAMPAIGN_ID = uuid.uuid4()
CLIENT_ID = uuid.uuid4()
CL_ID = uuid.uuid4()
BU_ID = uuid.uuid4()


def make_ai_response(
    outreach_angle: str = "Business needs digital marketing help",
    include_email: bool = True,
    include_linkedin: bool = True,
    input_tokens: int = 500,
    output_tokens: int = 150,
) -> dict:
    content_dict: dict = {"outreach_angle": outreach_angle}
    if include_email:
        content_dict["email"] = {"subject": "Grow your business", "body": "Hi John, I noticed..."}
    if include_linkedin:
        content_dict["linkedin"] = {"note": "Hi John, I work with businesses like yours..."}
    return {
        "content": json.dumps(content_dict),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_aud": 0.003,
        "model": "claude-3-5-haiku-20241022",
        "cached_tokens": 0,
        "stop_reason": "end_turn",
    }


def make_lead_row(
    dm_email: str | None = "john@co.com",
    dm_linkedin_url: str | None = "https://linkedin.com/in/john",
    dm_mobile: str | None = None,
    phone: str | None = None,
    propensity_reasons=None,
) -> dict:
    return {
        "cl_id": CL_ID,
        "campaign_id": CAMPAIGN_ID,
        "client_id": CLIENT_ID,
        "bu_id": BU_ID,
        "display_name": "John's Plumbing",
        "gmb_category": "Plumber",
        "suburb": "Melbourne",
        "state": "VIC",
        "gmb_rating": 4.5,
        "gmb_review_count": 20,
        "website": "https://johnsplumbing.com.au",
        "domain": "johnsplumbing.com.au",
        "phone": phone,
        "dm_name": "John Smith",
        "dm_title": "Owner",
        "dm_email": dm_email,
        "dm_linkedin_url": dm_linkedin_url,
        "dm_mobile": dm_mobile,
        "has_google_ads": False,
        "has_facebook_pixel": False,
        "listed_on_yp": True,
        "yp_advertiser": False,
        "site_copyright_year": 2019,
        "is_mobile_responsive": True,
        "propensity_score": 75,
        "reachability_score": 60,
        "propensity_reasons": propensity_reasons or [],
    }


AGENCY_ROW = {
    "name": "Test Agency",
    "value_proposition": "We help SMBs grow",
    "services_offered": ["SEO", "PPC"],
    "company_description": "An Australian digital marketing agency.",
    "website_url": "https://agency.com.au",
}


def make_db(lead_rows=None, agency_row=None):
    db = MagicMock()
    db.fetch = AsyncMock(return_value=lead_rows if lead_rows is not None else [make_lead_row()])
    db.fetchrow = AsyncMock(return_value=agency_row if agency_row is not None else AGENCY_ROW)
    db.execute = AsyncMock(return_value=None)
    return db


def make_ai(response=None, side_effect=None):
    ai = MagicMock()
    if side_effect is not None:
        ai.complete = AsyncMock(side_effect=side_effect)
    else:
        ai.complete = AsyncMock(return_value=response or make_ai_response())
    return ai


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_flow_email_linkedin():
    """1 lead with email + linkedin channels → 2 messages, 1 personalised."""
    db = make_db()
    ai = make_ai(response=make_ai_response(include_email=True, include_linkedin=True))

    stage7 = Stage7Personalisation(ai, db)
    result = await stage7.run(CAMPAIGN_ID, batch_size=1)

    assert result["personalised"] == 1
    assert result["messages_generated"] == 2
    assert result["errors"] == []

    # Verify INSERT into campaign_lead_messages called twice (email + linkedin)
    insert_calls = [
        c for c in db.execute.call_args_list
        if "campaign_lead_messages" in c[0][0]
    ]
    assert len(insert_calls) == 2, f"Expected 2 inserts, got {len(insert_calls)}"

    # Verify UPDATE campaign_leads with status='personalised'
    update_calls = [
        c for c in db.execute.call_args_list
        if "status = 'personalised'" in c[0][0]
    ]
    assert len(update_calls) == 1, f"Expected 1 personalised update, got {len(update_calls)}"


@pytest.mark.asyncio
async def test_email_only_no_linkedin():
    """Lead with email only (no linkedin) → 1 message generated."""
    row = make_lead_row(dm_linkedin_url=None)
    db = make_db(lead_rows=[row])
    ai = make_ai(response=make_ai_response(include_email=True, include_linkedin=False))

    stage7 = Stage7Personalisation(ai, db)
    result = await stage7.run(CAMPAIGN_ID, batch_size=1)

    assert result["messages_generated"] == 1


@pytest.mark.asyncio
async def test_haiku_api_failure_retry_success():
    """First call raises Exception, second call succeeds → personalised == 1."""
    db = make_db()
    responses = [Exception("API timeout"), make_ai_response()]
    ai = make_ai(side_effect=responses)

    stage7 = Stage7Personalisation(ai, db)
    result = await stage7.run(CAMPAIGN_ID, batch_size=1)

    assert result["personalised"] == 1
    assert result["errors"] == []
    assert ai.complete.call_count == 2


@pytest.mark.asyncio
async def test_haiku_both_attempts_fail():
    """Both Haiku attempts fail → personalised == 0, errors has 1 entry."""
    db = make_db()
    ai = make_ai(side_effect=Exception("Always fails"))

    stage7 = Stage7Personalisation(ai, db)
    result = await stage7.run(CAMPAIGN_ID, batch_size=1)

    assert result["personalised"] == 0
    assert len(result["errors"]) == 1

    # Verify UPDATE with status='personalisation_failed'
    fail_updates = [
        c for c in db.execute.call_args_list
        if "personalisation_failed" in c[0][0]
    ]
    assert len(fail_updates) == 1, f"Expected 1 fail update, got {len(fail_updates)}"


@pytest.mark.asyncio
async def test_cost_tracking():
    """cost_aud should equal 500 * INPUT_COST + 150 * OUTPUT_COST."""
    db = make_db()
    ai = make_ai(response=make_ai_response(input_tokens=500, output_tokens=150))

    stage7 = Stage7Personalisation(ai, db)
    result = await stage7.run(CAMPAIGN_ID, batch_size=1)

    expected = float(
        Decimal("500") * HAIKU_INPUT_COST_PER_TOKEN
        + Decimal("150") * HAIKU_OUTPUT_COST_PER_TOKEN
    )
    assert math.isclose(result["cost_aud"], expected, rel_tol=1e-9), (
        f"Expected cost {expected}, got {result['cost_aud']}"
    )


@pytest.mark.asyncio
async def test_outreach_angle_stored():
    """outreach_angle in AI response is written to campaign_leads UPDATE."""
    db = make_db()
    angle = "Business needs SEO help"
    ai = make_ai(response=make_ai_response(outreach_angle=angle))

    stage7 = Stage7Personalisation(ai, db)
    await stage7.run(CAMPAIGN_ID, batch_size=1)

    # Find the UPDATE campaign_leads call and verify outreach_angle is passed
    update_calls = [
        c for c in db.execute.call_args_list
        if "outreach_angle" in c[0][0]
    ]
    assert len(update_calls) == 1
    # The angle is the first positional param after the SQL
    assert update_calls[0][0][1] == angle, (
        f"Expected outreach_angle='{angle}', got {update_calls[0][0][1]}"
    )


@pytest.mark.asyncio
async def test_no_channels_marks_failed():
    """Lead with no contact channels → personalised == 0, error='no_channels_available'."""
    row = make_lead_row(dm_email=None, dm_linkedin_url=None, dm_mobile=None, phone=None)
    db = make_db(lead_rows=[row])
    ai = make_ai()

    stage7 = Stage7Personalisation(ai, db)
    result = await stage7.run(CAMPAIGN_ID, batch_size=1)

    assert result["personalised"] == 0
    assert len(result["errors"]) == 1
    assert result["errors"][0]["error"] == "no_channels_available"

    # No Haiku call should have been made
    ai.complete.assert_not_called()

    # Verify UPDATE with personalisation_failed
    fail_updates = [
        c for c in db.execute.call_args_list
        if "personalisation_failed" in c[0][0]
    ]
    assert len(fail_updates) == 1


@pytest.mark.asyncio
async def test_batch_size_respects_limit():
    """batch_size=2 must be passed as $2 in the SELECT query."""
    db = make_db(lead_rows=[])
    ai = make_ai()

    stage7 = Stage7Personalisation(ai, db)
    await stage7.run(CAMPAIGN_ID, batch_size=2)

    assert db.fetch.called
    fetch_call_args = db.fetch.call_args[0]
    # $1 = campaign_id, $2 = batch_size
    # params are positional after the SQL string
    assert fetch_call_args[2] == 2, (
        f"Expected batch_size=2 as 3rd positional arg, got {fetch_call_args[2]}"
    )
