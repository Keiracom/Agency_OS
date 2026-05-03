"""Tests for src/pipeline/intelligence.py — Directive #296."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        analyse_reviews,
        classify_intent,
        comprehend_website,
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
    from src.pipeline.intelligence import GLOBAL_SEM_HAIKU, GLOBAL_SEM_SONNET

    assert GLOBAL_SEM_SONNET._value == 55
    assert GLOBAL_SEM_HAIKU._value == 55


# ── Semaphore acquisition test ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_comprehend_website_acquires_sonnet_semaphore():
    """GLOBAL_SEM_SONNET is acquired and released on each comprehend_website call."""
    from src.pipeline.intelligence import GLOBAL_SEM_SONNET

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


# ── Intelligence wiring through orchestrator ──────────────────────────────────


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
    domain_data["stage3"] = {
        "business_name": "Test Dental",
        "is_enterprise_or_chain": False,
        "dm_candidate": {
            "name": "Dr. Jane Smith",
            "role": "Principal Dentist",
            "linkedin_url": "https://au.linkedin.com/in/janesmith",
        },
    }
    return domain_data


async def _stage4_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage4"] = {
        "rank_overview": {"organic_etv": 500, "rank": 50000},
        "backlinks": {"backlinks_num": 120},
    }
    domain_data["cost_usd"] += 0.078
    return domain_data


async def _stage5_pass(domain_data: dict) -> dict:
    domain_data["stage5"] = {
        "is_viable_prospect": True,
        "composite_score": 55,
        "affordability_band": "HIGH",
        "affordability_score": 55,
        "intent_band": "TRYING",
        "intent_score": 55,
    }
    return domain_data


async def _stage6_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage6"] = {}
    return domain_data


async def _stage7_mock(domain_data: dict, gemini) -> dict:
    domain_data["stage7"] = {"evidence": ["Running ads without conversion tracking"]}
    return domain_data


async def _stage8_mock(domain_data: dict, dfs, bd=None, lm=None) -> dict:
    domain_data["stage8_verify"] = {}
    domain_data["stage8_contacts"] = {
        "email": {"email": "jane@dental.com.au", "verified": True, "source": "leadmagic"},
        "mobile": {},
        "linkedin": {"linkedin_url": "https://au.linkedin.com/in/janesmith"},
    }
    domain_data["cost_usd"] += 0.015
    return domain_data


async def _stage9_mock(domain_data: dict, bd) -> dict:
    domain_data["stage9"] = {}
    return domain_data


async def _stage10_mock(domain_data: dict) -> dict:
    domain_data["stage10"] = {}
    return domain_data


async def _stage11_mock(domain_data: dict) -> dict:
    stage3 = domain_data.get("stage3") or {}
    dm = stage3.get("dm_candidate") or {}
    stage5 = domain_data.get("stage5") or {}
    stage7 = domain_data.get("stage7") or {}
    domain_data["stage11"] = {
        "company_name": stage3.get("business_name", "Test Dental"),
        "location": "Sydney NSW",
        "location_suburb": "Sydney",
        "location_state": "NSW",
        "dm_name": dm.get("name"),
        "dm_title": dm.get("role"),
        "dm_linkedin_url": dm.get("linkedin_url"),
        "dm_confidence": "HIGH",
        "intent_band": stage5.get("intent_band", "TRYING"),
        "services": ["dentistry"],
        "evidence": stage7.get("evidence", ["Running ads without conversion tracking"]),
        "is_running_ads": False,
        "gmb_review_count": 0,
    }
    return domain_data


@pytest.mark.asyncio
async def test_run_parallel_with_intelligence_wired():
    """run_streaming with intelligence= wired produces a card with evidence from stage7."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    # Mock discovery: 2 domains then empty
    disc = MagicMock()
    disc.pull_batch = AsyncMock(
        side_effect=[
            [{"domain": "dental.com.au"}, {"domain": "plumber.com.au"}],
            [],
        ]
    )

    # Mock intelligence module (stored on orchestrator, stages call it via mock)
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

    orch = PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=disc,
        intelligence=intel,
        on_domain_complete=AsyncMock(return_value=None),
    )

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_pass),
        patch("src.pipeline.pipeline_orchestrator._run_stage4", _stage4_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage5", _stage5_pass),
        patch("src.pipeline.pipeline_orchestrator._run_stage6", _stage6_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage7", _stage7_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage8", _stage8_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage9", _stage9_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage10", _stage10_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage11", _stage11_mock),
    ):
        result = await orch.run_streaming(
            categories=["10514"],
            target_cards=1,
            budget_cap_aud=500.0,
            num_workers=1,
            batch_size=5,
        )

    assert len(result.prospects) >= 1
    card = result.prospects[0]
    assert card.evidence == ["Running ads without conversion tracking"]
    assert card.intent_band == "TRYING"
    assert card.dm_name == "Dr. Jane Smith"
