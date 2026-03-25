# tests/test_stage6_reachability.py
# PURPOSE: Tests for src/pipeline/stage6_reachability.py — Stage6Reachability
# DIRECTIVE: #251 — all mocks, no live API calls, no live DB

import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.stage6_reachability import (
    Stage6Reachability,
    SIGNAL_MOBILE,
    MOBILE_LOOKUP_COST_AUD,
    MOBILE_SCORE_THRESHOLD,
)
from src.integrations.leadmagic import MobileFinderResult, MobileStatus


# ============================================================
# HELPERS
# ============================================================

def make_db(fetch_rows_pass1=None, fetch_rows_pass2=None, fetchval_return=0):
    """
    Create mock db with two sequential fetch() responses:
      - pass1: rows for stage 5 scoring
      - pass2: high_reach_rows for mobile enrichment
    """
    db = MagicMock()
    pass1 = fetch_rows_pass1 or []
    pass2 = fetch_rows_pass2 or []

    # fetch is called twice: first for pass 1 rows, then for high_reach_rows
    db.fetch = AsyncMock(side_effect=[pass1, pass2])
    db.execute = AsyncMock(return_value=None)
    db.fetchval = AsyncMock(return_value=fetchval_return)
    return db


def make_row(**kwargs):
    """Build a minimal row dict for Stage6."""
    defaults = {
        "id": uuid.uuid4(),
        "dm_email": None,
        "dm_email_verified": False,
        "dm_email_confidence": 0,
        "dm_linkedin_url": None,
        "dm_mobile": None,
        "dm_name": None,
        "dm_title": None,
        "dm_confidence": None,
        "website": None,
        "domain": None,
        "phone": None,
        "reachability_score": None,
    }
    defaults.update(kwargs)
    return defaults


# ============================================================
# TEST 1: _score — high reachability
# ============================================================

def test_high_reachability_score():
    """Row with verified email, linkedin URL, website, phone, high confidence → score > 70."""
    row = make_row(
        dm_email="x@y.com",
        dm_email_verified=True,
        dm_email_confidence=90,
        dm_linkedin_url="https://linkedin.com/in/john",
        website="https://x.com",
        phone="0400000000",
        dm_confidence=Decimal("0.90"),
        dm_name="John",
        dm_title="CEO",
        dm_mobile=None,
    )
    client = MagicMock()
    db = MagicMock()
    stage6 = Stage6Reachability(leadmagic_client=client, db=db)

    score = stage6._score(row, include_mobile=False)
    assert score > 70


# ============================================================
# TEST 2: _score — low reachability (all None/False/0)
# ============================================================

def test_low_reachability_score():
    """Row with all None/False/0 signals → score == 0."""
    row = make_row()
    client = MagicMock()
    db = MagicMock()
    stage6 = Stage6Reachability(leadmagic_client=client, db=db)

    score = stage6._score(row, include_mobile=False)
    assert score == 0


# ============================================================
# TEST 3: mobile gate triggers above threshold
# ============================================================

@pytest.mark.asyncio
async def test_mobile_gate_triggers_above_threshold():
    """High-score row with dm_linkedin_url: mobile enrichment is attempted and found."""
    high_score_row = make_row(
        dm_email="x@y.com",
        dm_email_verified=True,
        dm_email_confidence=90,
        dm_linkedin_url="https://linkedin.com/in/john",
        website="https://x.com",
        phone="0400000000",
        dm_confidence=Decimal("0.90"),
        dm_name="John",
        dm_title="CEO",
        dm_mobile=None,
        reachability_score=85,
    )

    db = make_db(
        fetch_rows_pass1=[high_score_row],
        fetch_rows_pass2=[high_score_row],
        fetchval_return=1,
    )

    mock_mobile_result = MobileFinderResult(
        found=True,
        mobile_number="+61400000000",
        mobile_confidence=88,
        status=MobileStatus.VERIFIED,
    )
    client = MagicMock()
    client.find_mobile = AsyncMock(return_value=mock_mobile_result)

    stage6 = Stage6Reachability(leadmagic_client=client, db=db)
    result = await stage6.run(mobile_threshold=70, batch_size=1, mobile_spend_cap_aud=5.0)

    assert result["mobile_attempted"] == 1
    assert result["mobile_found"] == 1


# ============================================================
# TEST 4: mobile gate skips when high_reach_rows is empty
# ============================================================

@pytest.mark.asyncio
async def test_mobile_gate_skips_below_threshold():
    """When pass2 returns no high-reach rows, mobile_attempted == 0."""
    # Some row for pass 1
    row = make_row(
        dm_email="low@example.com",
        dm_email_verified=False,
        dm_linkedin_url="https://linkedin.com/in/low",
    )

    db = make_db(
        fetch_rows_pass1=[row],
        fetch_rows_pass2=[],  # No rows above threshold
        fetchval_return=1,
    )
    client = MagicMock()
    client.find_mobile = AsyncMock()

    stage6 = Stage6Reachability(leadmagic_client=client, db=db)
    result = await stage6.run(mobile_threshold=70, batch_size=1, mobile_spend_cap_aud=5.0)

    assert result["mobile_attempted"] == 0
    client.find_mobile.assert_not_called()


# ============================================================
# TEST 5: mobile spend cap blocks enrichment
# ============================================================

@pytest.mark.asyncio
async def test_mobile_spend_cap():
    """mobile_spend_cap_aud=0.01 (< $0.077): no mobile attempts even with 2 high-reach rows."""
    row1 = make_row(
        dm_linkedin_url="https://linkedin.com/in/person1",
        dm_email="a@b.com", dm_email_verified=True, dm_email_confidence=90,
        reachability_score=85,
    )
    row2 = make_row(
        dm_linkedin_url="https://linkedin.com/in/person2",
        dm_email="c@d.com", dm_email_verified=True, dm_email_confidence=90,
        reachability_score=85,
    )

    db = make_db(
        fetch_rows_pass1=[row1, row2],
        fetch_rows_pass2=[row1, row2],
        fetchval_return=2,
    )
    client = MagicMock()
    client.find_mobile = AsyncMock()

    stage6 = Stage6Reachability(leadmagic_client=client, db=db)
    result = await stage6.run(
        mobile_threshold=70,
        batch_size=2,
        mobile_spend_cap_aud=0.01,  # less than $0.077
    )

    assert result["mobile_attempted"] == 0
    client.find_mobile.assert_not_called()


# ============================================================
# TEST 6: pipeline_complete status set in final UPDATE
# ============================================================

@pytest.mark.asyncio
async def test_pipeline_complete_status_set():
    """run() calls db.execute with SQL containing 'pipeline_complete'."""
    row = make_row(
        dm_email="x@y.com",
        dm_email_verified=True,
        dm_linkedin_url="https://linkedin.com/in/john",
    )

    db = make_db(
        fetch_rows_pass1=[row],
        fetch_rows_pass2=[],  # No mobile enrichment
        fetchval_return=1,
    )
    client = MagicMock()

    stage6 = Stage6Reachability(leadmagic_client=client, db=db)
    await stage6.run(mobile_threshold=70, batch_size=1, mobile_spend_cap_aud=5.0)

    # Check that at least one db.execute call contained 'pipeline_complete'
    call_args_list = db.execute.call_args_list
    sql_calls = [str(call) for call in call_args_list]
    assert any("pipeline_complete" in s for s in sql_calls), (
        f"Expected 'pipeline_complete' in db.execute calls, got: {sql_calls}"
    )


# ============================================================
# TEST 7: score increases after mobile added
# ============================================================

def test_score_increases_after_mobile():
    """Score with dm_mobile set is higher than without by exactly SIGNAL_MOBILE."""
    base_row = make_row(
        dm_email="x@y.com",
        dm_email_verified=True,
        dm_email_confidence=80,
        dm_linkedin_url="https://linkedin.com/in/john",
    )

    client = MagicMock()
    db = MagicMock()
    stage6 = Stage6Reachability(leadmagic_client=client, db=db)

    score_without = stage6._score(base_row, include_mobile=False)

    row_with_mobile = dict(base_row)
    row_with_mobile["dm_mobile"] = "+61400000000"
    score_with = stage6._score(row_with_mobile, include_mobile=True)

    assert score_with > score_without
    assert score_with - score_without == SIGNAL_MOBILE
