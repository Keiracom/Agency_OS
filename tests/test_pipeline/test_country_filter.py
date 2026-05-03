"""Tests for AU country filter — CD Player v1 API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.free_enrichment import FreeEnrichment
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator


def make_fe() -> FreeEnrichment:
    """Instantiate FreeEnrichment without a real DB connection."""
    fe = FreeEnrichment.__new__(FreeEnrichment)
    fe._pool = None
    fe._conn = None
    return fe


# ── _is_au_domain tests ───────────────────────────────────────────────────────


def test_au_domain_passes():
    fe = make_fe()
    assert fe._is_au_domain("dentist.com.au", "") is True


def test_state_in_html_passes():
    fe = make_fe()
    html = "<p>We serve patients across NSW and beyond.</p>"
    assert fe._is_au_domain("dentist.com", html) is True


def test_phone_in_html_passes():
    fe = make_fe()
    # Australian landline: 02 9999 8888 — stripped of spaces = 0299998888
    html = "<p>Call us on 0299998888 today</p>"
    assert fe._is_au_domain("dentist.com", html) is True


def test_foreign_domain_fails():
    fe = make_fe()
    # Turkish dental site with no AU indicators
    html = "<html><head><title>Dentatur Diş Kliniği</title></head><body>İstanbul</body></html>"
    assert fe._is_au_domain("dentatur.com", html) is False


# ── Country filtering in orchestrator (CD Player v1) ─────────────────────────
#
# In CD Player v1, country filtering is enforced by stage mocks that set
# dropped_at="stage5" for non-AU domains. This maps to affordability_rejected
# in the stats path (stage5 drops → affordability_rejected).


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
    domain_data["stage3"] = {
        "business_name": "Test Co",
        "is_enterprise_or_chain": False,
        "dm_candidate": {
            "name": "Jane Smith",
            "role": "Owner",
            "linkedin_url": "https://au.linkedin.com/in/jane",
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


async def _stage5_reject_non_au(domain_data: dict) -> dict:
    """Stage 5 that drops non-AU domains with affordability_rejected."""
    domain_data["stage5"] = {
        "is_viable_prospect": False,
        "composite_score": 0,
        "affordability_band": "LOW",
        "affordability_score": 0,
        "viability_reason": "non_au",
    }
    domain_data["dropped_at"] = "stage5"
    domain_data["drop_reason"] = "non_au"
    return domain_data


async def _stage5_pass(domain_data: dict) -> dict:
    domain_data["stage5"] = {
        "is_viable_prospect": True,
        "composite_score": 55,
        "affordability_band": "MEDIUM",
        "affordability_score": 55,
        "intent_band": "TRYING",
        "intent_score": 55,
    }
    return domain_data


async def _stage6_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage6"] = {}
    return domain_data


async def _stage7_mock(domain_data: dict, gemini) -> dict:
    domain_data["stage7"] = {"evidence": ["Has website"]}
    return domain_data


async def _stage8_mock(domain_data: dict, dfs, bd=None, lm=None) -> dict:
    domain_data["stage8_verify"] = {}
    domain_data["stage8_contacts"] = {
        "email": {"email": "jane@test.com.au", "verified": True, "source": "leadmagic"},
        "mobile": {},
        "linkedin": {"linkedin_url": "https://au.linkedin.com/in/jane"},
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
    domain_data["stage11"] = {
        "company_name": stage3.get("business_name", "Test Co"),
        "location": "Sydney NSW",
        "location_suburb": "Sydney",
        "location_state": "NSW",
        "dm_name": dm.get("name"),
        "dm_title": dm.get("role"),
        "dm_linkedin_url": dm.get("linkedin_url"),
        "dm_confidence": "HIGH",
        "intent_band": stage5.get("intent_band", "TRYING"),
        "services": ["dental"],
        "evidence": ["Has website"],
        "is_running_ads": False,
        "gmb_review_count": 0,
    }
    return domain_data


def _make_orch(domain: str = "example.com"):
    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=[[{"domain": domain}], []])
    return PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=disc,
        on_domain_complete=AsyncMock(return_value=None),
    )


@pytest.mark.asyncio
async def test_non_au_rejected_in_orchestrator():
    """Non-AU domain dropped at stage5 is counted in affordability_rejected."""
    orch = _make_orch("dentatur.com")

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_pass),
        patch("src.pipeline.pipeline_orchestrator._run_stage4", _stage4_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage5", _stage5_reject_non_au),
        patch("src.pipeline.pipeline_orchestrator._run_stage6", _stage6_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage7", _stage7_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage8", _stage8_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage9", _stage9_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage10", _stage10_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage11", _stage11_mock),
    ):
        result = await orch.run_streaming(
            categories=["dental"],
            target_cards=10,
            budget_cap_aud=500.0,
            num_workers=1,
        )

    assert result.stats.affordability_rejected == 1
    assert result.stats.viable_prospects == 0
    assert len(result.prospects) == 0


@pytest.mark.asyncio
async def test_au_domain_not_rejected_in_orchestrator():
    """AU domain passes country filter and produces a prospect card."""
    orch = _make_orch("dentist.com.au")

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
            categories=["dental"],
            target_cards=10,
            budget_cap_aud=500.0,
            num_workers=1,
        )

    # AU domain passes all stages — should produce a card
    assert result.stats.affordability_rejected == 0
    assert len(result.prospects) == 1
