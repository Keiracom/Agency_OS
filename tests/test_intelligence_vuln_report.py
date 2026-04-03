"""
Tests for generate_vulnerability_report() — Directive #306.
Tests the Stage 7c Sonnet synthesis function and ProspectCard field.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import fields
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.pipeline.intelligence as intel_module
from src.pipeline.intelligence import (
    _VULN_FALLBACK,
    _VULN_SYSTEM_BLOCK,
    generate_vulnerability_report,
)
from src.pipeline.pipeline_orchestrator import ProspectCard

# ── Shared mock data ────────────────────────────────────────────────────────

_FULL_MOCK_RESULT = {
    "overall_grade": "D+",
    "sections": {
        "search_visibility": {
            "grade": "D",
            "findings": ["Brand ranks at position 8 — below the fold"],
            "data": {"brand_position": 8},
        },
        "technical_seo": {
            "grade": "C",
            "findings": ["94 pages indexed — reasonable for site size"],
            "data": {"indexed_pages": 94, "cms": "WordPress"},
        },
        "backlink_profile": {
            "grade": "D",
            "findings": ["Domain rank 18 — below average for this category"],
            "data": {"domain_rank": 18, "trend": "declining"},
        },
        "paid_advertising": {
            "grade": "F",
            "findings": ["13 campaigns running but no conversion tracking installed"],
            "data": {"campaigns": 13, "tracking": False},
        },
        "reputation": {
            "grade": "B-",
            "findings": ["4.2 stars from 265 reviews — strong social proof"],
            "data": {"rating": 4.2, "reviews": 265},
        },
        "competitive_position": {
            "grade": "D",
            "findings": ["3 competitors outranking on brand SERP"],
            "competitors": [{"domain": "rival.com.au", "dr": 34}],
        },
    },
    "priority_action": "Install conversion tracking on all 13 Google Ads campaigns immediately.",
    "three_month_roadmap": [
        "Month 1: Fix conversion tracking and audit 13 campaigns for waste",
        "Month 2: Build backlinks to push domain rank above 25",
        "Month 3: Claim brand SERP position 1 via review response strategy",
    ],
}

_MOCK_ENRICHMENT = {
    "gmb_rating": 4.2,
    "gmb_review_count": 265,
    "is_running_ads": True,
    "google_ads_active": True,
}

_MOCK_INTELLIGENCE = {
    "intent_band": "ACTIVE_SPENDER",
    "intent_score": 72,
}


# ── test_1: full data returns all 6 sections ─────────────────────────────────

@pytest.mark.asyncio
async def test_1_full_data_returns_all_sections():
    with patch.object(intel_module, "_call_anthropic", new=AsyncMock(
        return_value=(json.dumps(_FULL_MOCK_RESULT), 800, 300)
    )):
        result = await generate_vulnerability_report(
            domain="example.com.au",
            company_name="Example Pty Ltd",
            enrichment=_MOCK_ENRICHMENT,
            intelligence=_MOCK_INTELLIGENCE,
            competitors_data={"top3": [{"domain": "rival.com.au"}], "count": 3},
            backlinks_data={"referring_domains": 45, "domain_rank": 18, "trend": "declining"},
            brand_serp_data={"position": 8, "gmb_showing": True, "competitors_bidding": True},
            indexed_pages=94,
        )

    assert "sections" in result
    expected_sections = {
        "search_visibility",
        "technical_seo",
        "backlink_profile",
        "paid_advertising",
        "reputation",
        "competitive_position",
    }
    assert set(result["sections"].keys()) == expected_sections


# ── test_2: missing competitors gives "Insufficient Data" grade ──────────────

@pytest.mark.asyncio
async def test_2_missing_competitors_gives_insufficient():
    partial_result = dict(_FULL_MOCK_RESULT)
    partial_result["sections"] = dict(_FULL_MOCK_RESULT["sections"])
    partial_result["sections"]["competitive_position"] = {
        "grade": "Insufficient Data",
        "findings": [],
        "competitors": [],
    }
    with patch.object(intel_module, "_call_anthropic", new=AsyncMock(
        return_value=(json.dumps(partial_result), 700, 250)
    )):
        result = await generate_vulnerability_report(
            domain="nocomp.com.au",
            company_name="No Comp Co",
            enrichment={},
            intelligence={},
            competitors_data=None,
        )

    assert result["sections"]["competitive_position"]["grade"] == "Insufficient Data"


# ── test_3: missing ads data does not crash ───────────────────────────────────

@pytest.mark.asyncio
async def test_3_missing_ads_gives_appropriate_grade():
    no_ads_result = dict(_FULL_MOCK_RESULT)
    no_ads_result["sections"] = dict(_FULL_MOCK_RESULT["sections"])
    no_ads_result["sections"]["paid_advertising"] = {
        "grade": "Insufficient Data",
        "findings": ["No advertising data available"],
        "data": {},
    }
    with patch.object(intel_module, "_call_anthropic", new=AsyncMock(
        return_value=(json.dumps(no_ads_result), 600, 200)
    )):
        result = await generate_vulnerability_report(
            domain="noads.com.au",
            company_name="No Ads Ltd",
            enrichment={"google_ads_active": False},
            intelligence={},
        )

    assert "paid_advertising" in result["sections"]
    assert result["sections"]["paid_advertising"]["grade"] is not None


# ── test_4: result has all top-level required keys ────────────────────────────

@pytest.mark.asyncio
async def test_4_result_json_has_required_keys():
    with patch.object(intel_module, "_call_anthropic", new=AsyncMock(
        return_value=(json.dumps(_FULL_MOCK_RESULT), 800, 300)
    )):
        result = await generate_vulnerability_report(
            domain="keys-check.com.au",
            company_name="Keys Check Co",
            enrichment=_MOCK_ENRICHMENT,
            intelligence=_MOCK_INTELLIGENCE,
        )

    for key in ("overall_grade", "sections", "priority_action", "three_month_roadmap"):
        assert key in result, f"Missing top-level key: {key}"


# ── test_5: ProspectCard has vulnerability_report field ──────────────────────

def test_5_vulnerability_report_on_prospect_card():
    card = ProspectCard(domain="x.com.au", company_name="X", location="Sydney")
    assert hasattr(card, "vulnerability_report")
    assert isinstance(card.vulnerability_report, dict)


# ── test_6: GLOBAL_SEM_SONNET semaphore is acquired ──────────────────────────

@pytest.mark.asyncio
async def test_6_sonnet_semaphore_acquired():
    real_sem = asyncio.Semaphore(1)
    acquired_events: list[bool] = []

    original_acquire = real_sem.acquire

    async def tracking_acquire():
        acquired_events.append(True)
        return await original_acquire()

    real_sem.acquire = tracking_acquire  # type: ignore[method-assign]

    with patch.object(intel_module, "GLOBAL_SEM_SONNET", real_sem):
        with patch.object(intel_module, "_call_anthropic", new=AsyncMock(
            return_value=(json.dumps(_FULL_MOCK_RESULT), 800, 300)
        )):
            await generate_vulnerability_report(
                domain="sem-test.com.au",
                company_name="Sem Test",
                enrichment={},
                intelligence={},
            )

    assert len(acquired_events) >= 1, "Semaphore was never acquired"


# ── test_7: _VULN_SYSTEM_BLOCK has prompt caching header ─────────────────────

def test_7_prompt_caching_block_present():
    assert "cache_control" in _VULN_SYSTEM_BLOCK
    assert _VULN_SYSTEM_BLOCK["cache_control"] == {"type": "ephemeral"}


# ── test_8: API error returns fallback dict ───────────────────────────────────

@pytest.mark.asyncio
async def test_8_api_error_returns_fallback():
    with patch.object(intel_module, "_call_anthropic", new=AsyncMock(
        side_effect=Exception("API error")
    )):
        result = await generate_vulnerability_report(
            domain="error.com.au",
            company_name="Error Co",
            enrichment={},
            intelligence={},
        )

    assert result["overall_grade"] == "Insufficient Data"
    assert result == _VULN_FALLBACK
