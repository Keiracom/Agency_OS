# FILE: tests/test_stage3_propensity.py
# PURPOSE: Tests for Stage3Propensity — scoring, batch, serialization
# DIRECTIVE: #250

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.pipeline.stage3_propensity import Stage3Propensity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stage3():
    db = MagicMock()
    db.fetch = AsyncMock()
    db.execute = AsyncMock()
    return Stage3Propensity(db=db), db


def _high_signal_dict() -> dict:
    return {
        "has_google_ads": True,
        "gmb_rating": 2.8,
        "gmb_review_count": 25,
        "gst_registered": True,
        "has_google_analytics": True,
        "has_facebook_pixel": True,
        "has_conversion_tracking": True,
        "is_mobile_responsive": True,
        "yp_advertiser": True,
        "website": "https://example.com",
        "site_copyright_year": 2020,
        "registration_date": None,
        # Remaining fields
        "id": "test-id",
        "display_name": "Test Biz",
        "state": "NSW",
        "suburb": "Sydney",
        "gmb_category": None,
        "gmb_claimed": True,
        "has_booking_system": False,
        "domain": None,
        "entity_type": None,
        "listed_on_yp": False,
        "yp_years_in_business": 0,
        "abn_status": None,
    }


def _low_signal_dict() -> dict:
    return {
        "has_google_ads": False,
        "gmb_rating": None,
        "gmb_review_count": 0,
        "gst_registered": False,
        "has_google_analytics": False,
        "has_facebook_pixel": False,
        "has_conversion_tracking": False,
        "is_mobile_responsive": False,
        "yp_advertiser": False,
        "website": None,
        "site_copyright_year": None,
        "registration_date": None,
        "id": "test-id-low",
        "display_name": "No Signal Biz",
        "state": None,
        "suburb": None,
        "gmb_category": None,
        "gmb_claimed": False,
        "has_booking_system": False,
        "domain": None,
        "entity_type": None,
        "listed_on_yp": False,
        "yp_years_in_business": 0,
        "abn_status": None,
    }


def _make_db_row(signals: dict):
    """Wrap signals dict as a MagicMock row with key access."""
    row = MagicMock()
    row.__getitem__ = lambda self, k: signals[k]
    row.keys = lambda: signals.keys()
    # Make dict(row) work
    row.__iter__ = lambda self: iter(signals)
    return row


# ---------------------------------------------------------------------------
# Test 1: High-signal business scores above 70
# ---------------------------------------------------------------------------

def test_high_signal_business_scores_above_70():
    stage3, _ = _make_stage3()
    signals = _high_signal_dict()
    score, reasons = stage3._score(signals)
    assert score > 70, f"Expected score > 70, got {score}"


# ---------------------------------------------------------------------------
# Test 2: Low-signal business scores below 30
# ---------------------------------------------------------------------------

def test_low_signal_business_scores_below_30():
    stage3, _ = _make_stage3()
    signals = _low_signal_dict()
    score, reasons = stage3._score(signals)
    assert score < 30, f"Expected score < 30, got {score}"


# ---------------------------------------------------------------------------
# Test 3: Reason dicts have signal + category but NO weight/value/pts/score
# ---------------------------------------------------------------------------

def test_propensity_reasons_no_weights():
    stage3, _ = _make_stage3()
    signals = _high_signal_dict()
    _, reasons = stage3._score(signals)
    assert len(reasons) > 0, "Expected at least 1 reason"
    for r in reasons:
        assert "signal" in r, f"Missing 'signal' key in reason: {r}"
        assert "category" in r, f"Missing 'category' key in reason: {r}"
        assert "weight" not in r, f"Unexpected 'weight' key in reason: {r}"
        assert "value" not in r, f"Unexpected 'value' key in reason: {r}"
        assert "pts" not in r, f"Unexpected 'pts' key in reason: {r}"
        assert "score" not in r, f"Unexpected 'score' key in reason: {r}"


# ---------------------------------------------------------------------------
# Test 4: Batch advances rows to pipeline_stage = 3
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_advances_to_stage_3():
    stage3, db = _make_stage3()

    rows = []
    for i in range(5):
        s = _high_signal_dict()
        s["id"] = f"id-{i}"
        row = MagicMock()
        # Make dict(row) return s by implementing items()
        row.__getitem__ = lambda self, k, _s=s: _s[k]
        row.__iter__ = lambda self, _s=s: iter(_s)
        rows.append(row)

    db.fetch.return_value = rows

    result = await stage3.run(batch_size=5)

    assert result["scored"] == 5, f"Expected 5 scored, got {result['scored']}"
    assert db.execute.call_count == 5

    # Verify pipeline_stage = 3 appears in all SQL calls
    for call in db.execute.call_args_list:
        sql = call.args[0]
        assert "pipeline_stage = 3" in sql, f"Expected 'pipeline_stage = 3' in SQL: {sql}"


# ---------------------------------------------------------------------------
# Test 5: scored_at = NOW() is set in the UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scored_at_set():
    stage3, db = _make_stage3()

    s = _high_signal_dict()
    s["id"] = "id-scored-at"
    row = MagicMock()
    row.__getitem__ = lambda self, k, _s=s: _s[k]
    row.__iter__ = lambda self, _s=s: iter(_s)
    db.fetch.return_value = [row]

    await stage3.run(batch_size=1)

    assert db.execute.call_count == 1
    sql = db.execute.call_args.args[0]
    assert "scored_at" in sql, "Expected 'scored_at' in UPDATE SQL"
    assert "NOW()" in sql, "Expected 'NOW()' in UPDATE SQL"


# ---------------------------------------------------------------------------
# Test 6: Reasons are list[dict] pre-serialization; each serializes to valid JSON
# ---------------------------------------------------------------------------

def test_reasons_serialized_as_json_strings():
    stage3, _ = _make_stage3()
    signals = _high_signal_dict()
    _, reasons = stage3._score(signals)

    assert isinstance(reasons, list), "Expected reasons to be a list"
    assert len(reasons) > 0, "Expected at least 1 reason (high-signal input)"

    for r in reasons:
        assert isinstance(r, dict), f"Expected each reason to be a dict, got {type(r)}"
        serialized = json.dumps(r)
        parsed = json.loads(serialized)
        assert "signal" in parsed, "Parsed JSON must have 'signal' key"
        assert "category" in parsed, "Parsed JSON must have 'category' key"
