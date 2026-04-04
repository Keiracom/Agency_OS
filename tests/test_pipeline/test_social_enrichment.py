"""Tests for src/pipeline/social_enrichment.py — Directive #300-FIX Issues 13-14."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.pipeline.social_enrichment import (
    GLOBAL_SEM_BRIGHTDATA,
    _activity_level,
    scrape_linkedin_company,
    scrape_linkedin_dm,
)


# ── _activity_level ────────────────────────────────────────────────────────────

def test_activity_level_active():
    assert _activity_level(10) == "active"

def test_activity_level_moderate():
    assert _activity_level(4) == "moderate"

def test_activity_level_lurker():
    assert _activity_level(1) == "lurker"

def test_activity_level_zero():
    assert _activity_level(0) == "lurker"

def test_activity_level_none():
    assert _activity_level(None) == "unknown"


# ── scrape_linkedin_company ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_company_null_url_returns_none():
    result = await scrape_linkedin_company("", "example.com.au")
    assert result is None


@pytest.mark.asyncio
async def test_company_empty_records_returns_none():
    with patch("src.pipeline.social_enrichment.BrightDataLinkedInClient") as MockBD:
        instance = MockBD.return_value
        instance._scraper_request = AsyncMock(return_value=[])
        result = await scrape_linkedin_company(
            "https://linkedin.com/company/test", "test.com.au"
        )
    assert result is None


@pytest.mark.asyncio
async def test_company_returns_structured_dict():
    fake_record = {
        "employee_count": 20,
        "followers": 850,
        "specialties": ["Dentistry", "Cosmetic Dentistry"],
        "description": "A leading dental practice.",
        "posts": [
            {"date": "2026-03-01", "text": "New treatment available!"},
            {"date": "2026-02-15", "text": "Award winner 2026."},
            {"date": "2026-01-10", "text": "Happy New Year!"},
            {"date": "2025-12-20", "text": "Older post."},
        ],
        "job_openings": 2,
    }
    with patch("src.pipeline.social_enrichment.BrightDataLinkedInClient") as MockBD:
        instance = MockBD.return_value
        instance._scraper_request = AsyncMock(return_value=[fake_record])
        result = await scrape_linkedin_company(
            "https://linkedin.com/company/smile-dental", "smiledental.com.au"
        )
    assert result is not None
    assert result["employee_count"] == 20
    assert result["follower_count"] == 850
    assert len(result["recent_posts"]) == 3      # capped at 3
    assert result["last_post_date"] == "2026-03-01"
    assert result["job_postings"] == 2
    assert result["activity_level"] == "moderate"  # 4 posts → moderate (>=8 active, >=2 moderate)
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_company_api_failure_returns_none():
    with patch("src.pipeline.social_enrichment.BrightDataLinkedInClient") as MockBD:
        instance = MockBD.return_value
        instance._scraper_request = AsyncMock(side_effect=RuntimeError("BD down"))
        result = await scrape_linkedin_company(
            "https://linkedin.com/company/error-co", "errorco.com.au"
        )
    assert result is None


# ── scrape_linkedin_dm ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dm_null_url_returns_none():
    result = await scrape_linkedin_dm("", "example.com.au")
    assert result is None


@pytest.mark.asyncio
async def test_dm_empty_records_returns_none():
    with patch("src.pipeline.social_enrichment.BrightDataLinkedInClient") as MockBD:
        instance = MockBD.return_value
        instance._scraper_request = AsyncMock(return_value=[])
        result = await scrape_linkedin_dm(
            "https://au.linkedin.com/in/jane-smith", "janesmith.com.au"
        )
    assert result is None


@pytest.mark.asyncio
async def test_dm_returns_structured_dict():
    fake_record = {
        "headline": "Principal Dentist & Owner at Smile Dental",
        "summary": "15 years of dental experience.",
        "connections": 412,
        "skills": ["Dentistry", "Implants", "Leadership"],
        "posts": [
            {"date": "2026-03-20", "text": "Excited about new technology!"},
        ],
        "experience": [
            {"company": "Smile Dental", "title": "Owner", "start_date": "2015-01", "end_date": None},
            {"company": "City Dental", "title": "Dentist", "start_date": "2010-01", "end_date": "2015-01"},
        ],
    }
    with patch("src.pipeline.social_enrichment.BrightDataLinkedInClient") as MockBD:
        instance = MockBD.return_value
        instance._scraper_request = AsyncMock(return_value=[fake_record])
        result = await scrape_linkedin_dm(
            "https://au.linkedin.com/in/jane-smith-123", "smiledental.com.au"
        )
    assert result is not None
    assert result["headline"] == "Principal Dentist & Owner at Smile Dental"
    assert result["connections_count"] == 412
    assert len(result["skills"]) == 3
    assert len(result["recent_posts"]) == 1
    assert len(result["career_history"]) == 2
    assert result["career_history"][0]["current"] is True   # no end_date
    assert result["career_history"][1]["current"] is False  # has end_date
    assert result["activity_level"] == "lurker"  # 1 post


@pytest.mark.asyncio
async def test_dm_api_failure_returns_none():
    with patch("src.pipeline.social_enrichment.BrightDataLinkedInClient") as MockBD:
        instance = MockBD.return_value
        instance._scraper_request = AsyncMock(side_effect=ValueError("timeout"))
        result = await scrape_linkedin_dm(
            "https://linkedin.com/in/error-person", "error.com.au"
        )
    assert result is None


# ── semaphore ──────────────────────────────────────────────────────────────────

def test_global_sem_brightdata_is_semaphore():
    assert isinstance(GLOBAL_SEM_BRIGHTDATA, asyncio.Semaphore)
