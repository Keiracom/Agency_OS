"""Tests for src/pipeline/intelligence.py — Directive #296."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_anthropic_response(payload: dict) -> MagicMock:
    """Return a mock httpx response that mimics Anthropic API."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"text": json.dumps(payload)}],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    return mock_resp


def _patch_httpx(payload: dict):
    """Context manager: patch httpx.AsyncClient.post to return payload."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=_mock_anthropic_response(payload))
    return patch("src.pipeline.intelligence.httpx.AsyncClient", return_value=mock_client)


# ── comprehend_website ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_comprehend_website_returns_structured_dict():
    expected = {
        "services": ["dental implants", "teeth whitening"],
        "team_size_indicator": "small(2-5)",
        "technology_signals": {
            "has_analytics": False,
            "has_ads_tag": True,
            "has_meta_pixel": False,
            "has_booking_system": True,
            "has_conversion_tracking": False,
            "cms": "wordpress",
            "analytics_tools": [],
        },
        "contact_methods": ["phone", "email"],
        "content_freshness": "current",
        "business_maturity": "established",
        "location_signals": ["Sydney", "NSW"],
        "pain_indicators": ["no conversion tracking on ads"],
    }
    with _patch_httpx(expected):
        from src.pipeline.intelligence import comprehend_website

        result = await comprehend_website(
            "dentist.com.au", "<html>test</html>", "https://dentist.com.au"
        )
    assert result["services"] == ["dental implants", "teeth whitening"]
    assert result["technology_signals"]["has_ads_tag"] is True
    assert result["location_signals"] == ["Sydney", "NSW"]


@pytest.mark.asyncio
async def test_comprehend_website_returns_fallback_on_api_error():
    with patch("src.pipeline.intelligence.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("API down"))
        mock_cls.return_value = mock_client
        from src.pipeline.intelligence import comprehend_website

        result = await comprehend_website(
            "dentist.com.au", "<html>test</html>", "https://dentist.com.au"
        )
    assert result["services"] == []
    assert result["team_size_indicator"] == "unknown"


@pytest.mark.asyncio
async def test_comprehend_website_returns_fallback_on_bad_json():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"text": "not valid json at all!"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    with patch("src.pipeline.intelligence.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_client
        from src.pipeline.intelligence import comprehend_website

        result = await comprehend_website(
            "dentist.com.au", "<html>test</html>", "https://dentist.com.au"
        )
    assert "services" in result  # fallback has services key


# ── classify_intent ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classify_intent_returns_band_and_evidence():
    expected = {
        "band": "TRYING",
        "score": 7,
        "confidence": "HIGH",
        "evidence": [{"effort": "Running Google Ads", "gap": "No conversion tracking"}],
        "primary_signal": "Active ads spend without measurement",
        "recommended_entry_point": "We noticed your Google Ads are running without conversion tracking",
    }
    with _patch_httpx(expected):
        from src.pipeline.intelligence import classify_intent

        result = await classify_intent(
            "dentist.com.au",
            website_data={"technology_signals": {"has_ads_tag": True}},
            gmb_data={"gmb_review_count": 45},
            ads_data={"is_running_ads": True, "ad_count": 3},
        )
    assert result["band"] == "TRYING"
    assert result["score"] == 7
    assert len(result["evidence"]) == 1


@pytest.mark.asyncio
async def test_classify_intent_fallback_on_error():
    with patch("src.pipeline.intelligence.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_cls.return_value = mock_client
        from src.pipeline.intelligence import classify_intent

        result = await classify_intent("dentist.com.au", {}, None, None)
    assert result["band"] == "NOT_TRYING"
    assert result["evidence"] == []


# ── analyse_reviews ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyse_reviews_returns_sentiment():
    expected = {
        "sentiment_trend": "improving",
        "average_rating": 4.5,
        "pain_themes": ["long wait times"],
        "strength_themes": ["friendly staff", "clean rooms"],
        "owner_responsiveness": "always",
        "owner_tone": "professional",
        "staff_mentions": ["Dr. Smith"],
        "decision_maker_signals": ["owner replies personally"],
        "marketing_opportunity": "Highlight 5-star reviews in Google Ads",
    }
    reviews = [{"text": "Great service!", "rating": 5}]
    with _patch_httpx(expected):
        from src.pipeline.intelligence import analyse_reviews

        result = await analyse_reviews("dentist.com.au", reviews)
    assert result["sentiment_trend"] == "improving"
    assert "Dr. Smith" in result["staff_mentions"]


@pytest.mark.asyncio
async def test_analyse_reviews_returns_fallback_for_empty_list():
    from src.pipeline.intelligence import analyse_reviews

    result = await analyse_reviews("dentist.com.au", [])
    assert result["sentiment_trend"] == "insufficient_data"
    assert result["pain_themes"] == []


# ── judge_affordability ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_judge_affordability_passes_company():
    expected = {
        "score": 8,
        "hard_gate": False,
        "gate_reason": "none",
        "band": "HIGH",
        "judgment": "Established company, GST registered, professional website",
        "confidence": "HIGH",
    }
    abn = {"entity_type": "Company", "gst_registered": True, "abn_matched": True}
    website = {"technology_signals": {"cms": "wordpress"}, "team_size_indicator": "small(2-5)"}
    with _patch_httpx(expected):
        from src.pipeline.intelligence import judge_affordability

        result = await judge_affordability("dentist.com.au", abn, website)
    assert result["hard_gate"] is False
    assert result["band"] == "HIGH"
    assert result["score"] == 8


@pytest.mark.asyncio
async def test_judge_affordability_hard_gate_sole_trader():
    expected = {
        "score": 0,
        "hard_gate": True,
        "gate_reason": "sole_trader",
        "band": "LOW",
        "judgment": "Individual sole trader — below affordability threshold",
        "confidence": "HIGH",
    }
    abn = {"entity_type": "Individual", "gst_registered": False}
    with _patch_httpx(expected):
        from src.pipeline.intelligence import judge_affordability

        result = await judge_affordability("tradie.com.au", abn, {})
    assert result["hard_gate"] is True
    assert result["gate_reason"] == "sole_trader"


# ── refine_evidence ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refine_evidence_returns_card_copy():
    expected = {
        "evidence_statements": [
            "Running Google Ads without conversion tracking — spending blind",
            "WordPress site with no analytics — can't measure ROI",
        ],
        "headline_signal": "Active ad spend with zero measurement",
        "recommended_service": "Google Ads audit + conversion tracking setup",
        "outreach_angle": "You're spending money on ads but can't tell if they're working",
    }
    intent_data = {
        "band": "TRYING",
        "score": 7,
        "evidence": [],
        "primary_signal": "ads no tracking",
    }
    with _patch_httpx(expected):
        from src.pipeline.intelligence import refine_evidence

        result = await refine_evidence("dentist.com.au", intent_data, {}, {})
    assert len(result["evidence_statements"]) == 2
    assert "headline_signal" in result
    assert "outreach_angle" in result


@pytest.mark.asyncio
async def test_refine_evidence_fallback_on_error():
    with patch("src.pipeline.intelligence.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))
        mock_cls.return_value = mock_client
        from src.pipeline.intelligence import refine_evidence

        result = await refine_evidence("dentist.com.au", {}, {}, {})
    assert result["evidence_statements"] == []
    assert result["headline_signal"] == ""


# ── Orchestrator wiring ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_accepts_intelligence_kwarg():
    """PipelineOrchestrator accepts intelligence= without error."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    intel_mock = MagicMock()
    orch = PipelineOrchestrator(
        discovery=MagicMock(),
        free_enrichment=MagicMock(),
        scorer=MagicMock(),
        dm_identification=MagicMock(),
        intelligence=intel_mock,
    )
    assert orch._intelligence is intel_mock


@pytest.mark.asyncio
async def test_orchestrator_intelligence_none_by_default():
    """intelligence= defaults to None — existing runs unaffected."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    orch = PipelineOrchestrator(
        discovery=MagicMock(),
        free_enrichment=MagicMock(),
        scorer=MagicMock(),
        dm_identification=MagicMock(),
    )
    assert orch._intelligence is None


def test_intelligence_module_imports():
    """All five functions importable from intelligence module."""
    from src.pipeline.intelligence import (
        comprehend_website,
        classify_intent,
        analyse_reviews,
        judge_affordability,
        refine_evidence,
    )

    assert callable(comprehend_website)
    assert callable(classify_intent)
    assert callable(analyse_reviews)
    assert callable(judge_affordability)
    assert callable(refine_evidence)


def test_global_semaphores_used():
    """Intelligence module imports GLOBAL_SEM_SONNET and GLOBAL_SEM_HAIKU."""
    from src.pipeline.intelligence import GLOBAL_SEM_SONNET, GLOBAL_SEM_HAIKU

    assert GLOBAL_SEM_SONNET._value == 55
    assert GLOBAL_SEM_HAIKU._value == 55


# ── Semaphore acquisition test ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_comprehend_website_acquires_sonnet_semaphore():
    """GLOBAL_SEM_SONNET is acquired and released on each comprehend_website call."""
    import asyncio
    from src.pipeline.intelligence import GLOBAL_SEM_SONNET

    acquire_calls = []
    release_calls = []

    original_acquire = GLOBAL_SEM_SONNET.__class__.__aenter__
    original_release = GLOBAL_SEM_SONNET.__class__.__aexit__

    expected = {
        "services": [],
        "team_size_indicator": "unknown",
        "technology_signals": {
            "has_analytics": False,
            "has_ads_tag": False,
            "has_meta_pixel": False,
            "has_booking_system": False,
            "has_conversion_tracking": False,
            "cms": "unknown",
            "analytics_tools": [],
        },
        "contact_methods": [],
        "content_freshness": "unknown",
        "business_maturity": "unknown",
        "location_signals": [],
        "pain_indicators": [],
    }

    semaphore_acquired = []

    async def patched_aenter(self):
        semaphore_acquired.append(True)
        return self

    async def patched_aexit(self, *args):
        semaphore_acquired.append(False)

    with (
        patch.object(GLOBAL_SEM_SONNET.__class__, "__aenter__", patched_aenter),
        patch.object(GLOBAL_SEM_SONNET.__class__, "__aexit__", patched_aexit),
        _patch_httpx(expected),
    ):
        from src.pipeline.intelligence import comprehend_website

        await comprehend_website("test.com.au", "<html>test</html>", "https://test.com.au")

    # Semaphore was both acquired (True) and released (False)
    assert True in semaphore_acquired
    assert False in semaphore_acquired


@pytest.mark.asyncio
async def test_token_usage_logged(caplog):
    """comprehend_website logs input/output token counts for cost tracking."""
    import logging

    expected = {
        "services": ["plumbing"],
        "team_size_indicator": "small(2-5)",
        "technology_signals": {
            "has_analytics": True,
            "has_ads_tag": False,
            "has_meta_pixel": False,
            "has_booking_system": False,
            "has_conversion_tracking": False,
            "cms": "wordpress",
            "analytics_tools": ["ga4"],
        },
        "contact_methods": ["phone"],
        "content_freshness": "current",
        "business_maturity": "established",
        "location_signals": ["Melbourne", "VIC"],
        "pain_indicators": [],
    }
    with _patch_httpx(expected), caplog.at_level(logging.INFO, logger="src.pipeline.intelligence"):
        from src.pipeline.intelligence import comprehend_website

        await comprehend_website(
            "plumber.com.au", "<html>plumbing</html>", "https://plumber.com.au"
        )

    # Log should contain domain and token counts (100 input, 50 output from mock)
    assert any("plumber.com.au" in r.message and "100" in r.message for r in caplog.records)


@pytest.mark.xfail(reason="Legacy orchestrator API — CD Player v1 rewrite pending")
@pytest.mark.asyncio
async def test_run_parallel_with_intelligence_wired():
    """run_parallel uses intelligence flow when self._intelligence is set."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    # Mock discovery: 2 domains then empty
    disc = MagicMock()
    disc.pull_batch = AsyncMock(
        side_effect=[
            [{"domain": "dental.com.au"}, {"domain": "plumber.com.au"}],
            [],
        ]
    )

    # Mock free enrichment
    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "Test", "html": "<html>Test</html>"})
    fe.enrich_from_spider = AsyncMock(
        return_value={
            "domain": "dental.com.au",
            "company_name": "Test Dental",
            "entity_type": "Company",
            "gst_registered": True,
            "non_au": False,
            "website_contact_emails": ["info@dental.com.au"],
            "html": "<html>Test</html>",
        }
    )

    # Mock intelligence module
    intel = MagicMock()
    intel.comprehend_website = AsyncMock(
        return_value={"services": ["dentistry"], "technology_signals": {"has_ads_tag": True}}
    )
    intel.judge_affordability = AsyncMock(
        return_value={"hard_gate": False, "band": "HIGH", "score": 8}
    )
    intel.classify_intent = AsyncMock(
        return_value={
            "band": "TRYING",
            "score": 6,
            "evidence": [{"effort": "Ads", "gap": "No tracking"}],
        }
    )
    intel.analyse_reviews = AsyncMock(return_value={"sentiment_trend": "stable", "pain_themes": []})
    intel.refine_evidence = AsyncMock(
        return_value={
            "evidence_statements": ["Running ads without conversion tracking"],
            "headline_signal": "Active ad spend, no measurement",
            "recommended_service": "Google Ads audit",
            "outreach_angle": "You're spending blind",
        }
    )

    # Mock DM
    dm_id = MagicMock()
    dm_result = MagicMock()
    dm_result.name = "Dr. Jane Smith"
    dm_result.title = "Principal Dentist"
    dm_result.linkedin_url = "https://au.linkedin.com/in/janesmith"
    dm_result.confidence = "HIGH"
    dm_id.identify = AsyncMock(return_value=dm_result)

    # Minimal scorer (fallback path, shouldn't be called with intel wired)
    scorer = MagicMock()
    scorer.score_affordability = MagicMock(
        side_effect=AssertionError("scorer should not be called with intel wired")
    )

    orch = PipelineOrchestrator(
        discovery=disc,
        free_enrichment=fe,
        scorer=scorer,
        dm_identification=dm_id,
        intelligence=intel,
    )

    result = await orch.run_parallel(
        category_codes=["10514"],
        location="Australia",
        target_count=1,
        num_workers=1,
        batch_size=5,
    )

    assert len(result.prospects) >= 1
    card = result.prospects[0]
    assert card.evidence == ["Running ads without conversion tracking"]
    assert card.intent_band == "TRYING"
    assert card.dm_name == "Dr. Jane Smith"
    # Verify intelligence functions were called
    intel.comprehend_website.assert_called()
    intel.judge_affordability.assert_called()
    intel.classify_intent.assert_called()
    intel.refine_evidence.assert_called()
