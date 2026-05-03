"""Tests for PipelineOrchestrator — CD Player v1 API.

Rewrites the legacy xfail mock tests to use the proven stage-patch pattern
from test_orchestrator_gates.py: real orchestrator logic runs, all _run_stage*
functions are patched at module level.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

# ── Shared stage mock helpers ─────────────────────────────────────────────────


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
    domain_data["stage3"] = {
        "business_name": "Test Co Pty Ltd",
        "is_enterprise_or_chain": False,
        "dm_candidate": {
            "name": "Alice Owner",
            "role": "Owner",
            "linkedin_url": "https://au.linkedin.com/in/aliceowner",
        },
    }
    return domain_data


async def _stage3_no_dm(domain_data: dict, gemini) -> dict:
    domain_data["stage3"] = {
        "business_name": "Test Co",
        "is_enterprise_or_chain": False,
        "dm_candidate": {},
    }
    domain_data["dropped_at"] = "stage3"
    domain_data["drop_reason"] = "no_dm_found"
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
        "affordability_band": "MEDIUM",
        "affordability_score": 55,
        "intent_band": "TRYING",
        "intent_score": 55,
    }
    return domain_data


async def _stage5_reject(domain_data: dict) -> dict:
    domain_data["stage5"] = {
        "is_viable_prospect": False,
        "composite_score": 10,
        "affordability_band": "LOW",
        "affordability_score": 10,
        "viability_reason": "sole_trader",
    }
    domain_data["dropped_at"] = "stage5"
    domain_data["drop_reason"] = "viability: sole_trader"
    return domain_data


async def _stage6_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage6"] = {}
    return domain_data


async def _stage7_mock(domain_data: dict, gemini) -> dict:
    domain_data["stage7"] = {"evidence": ["Has website", "No analytics"]}
    return domain_data


async def _stage8_mock(domain_data: dict, dfs, bd=None, lm=None) -> dict:
    domain_data["stage8_verify"] = {}
    domain_data["stage8_contacts"] = {
        "email": {"email": "alice@testco.com.au", "verified": True, "source": "leadmagic"},
        "mobile": {},
        "linkedin": {"linkedin_url": "https://au.linkedin.com/in/aliceowner"},
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
        "services": ["beauty_salon"],
        "evidence": ["Has website", "No analytics"],
        "is_running_ads": False,
        "gmb_review_count": 12,
    }
    return domain_data


# ── Factory helpers ────────────────────────────────────────────────────────────


def _make_discovery(domains: list[str]):
    """Discovery mock whose pull_batch returns domains once then empty."""
    disc = MagicMock()
    batch = [{"domain": d} for d in domains]
    disc.pull_batch = AsyncMock(side_effect=[batch, []])
    return disc


def _make_orch(discovery):
    """Build an orchestrator with null clients (stages are fully mocked)."""
    return PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=discovery,
        on_domain_complete=AsyncMock(return_value=None),
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_stops_at_target():
    """Pipeline must stop emitting cards once target_cards is reached."""
    domains = [f"domain{i}.com.au" for i in range(10)]
    disc = MagicMock()
    disc.pull_batch = AsyncMock(return_value=[{"domain": d} for d in domains])
    orch = _make_orch(disc)

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
            categories=["beauty_salon"],
            target_cards=5,
            budget_cap_aud=500.0,
            num_workers=1,
            batch_size=10,
        )

    assert len(result.prospects) == 5


@pytest.mark.asyncio
async def test_orchestrator_stops_on_category_exhausted():
    """Pipeline must return all prospects when discovery is exhausted before target."""
    disc = _make_discovery([f"domain{i}.com.au" for i in range(3)])
    orch = _make_orch(disc)

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
            categories=["beauty_salon"],
            target_cards=100,
            budget_cap_aud=500.0,
            num_workers=1,
        )

    assert len(result.prospects) == 3


@pytest.mark.asyncio
async def test_orchestrator_tracks_stats():
    """
    5 domains with different outcomes:
      domain0 — stage2 raises → enrichment_failed
      domain1 — stage5 rejects → affordability_rejected
      domain2 — stage5 rejects → affordability_rejected
      domain3 — stage3 no DM → enrichment_failed (dm_not_found counted via enrichment_failed)
      domain4 — success → viable_prospects
    """
    domains = [{"domain": f"domain{i}.com.au"} for i in range(5)]
    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=[domains, []])
    orch = _make_orch(disc)

    call_counts = {"stage2": 0, "stage3": 0, "stage5": 0}

    async def _stage2_side_effect(domain_data: dict, dfs) -> dict:
        idx = call_counts["stage2"]
        call_counts["stage2"] += 1
        if idx == 0:
            # domain0: fail enrichment
            domain_data["dropped_at"] = "stage2"
            domain_data["drop_reason"] = "enrichment_failed"
            return domain_data
        return await _stage2_mock(domain_data, dfs)

    async def _stage3_side_effect(domain_data: dict, gemini) -> dict:
        idx = call_counts["stage3"]
        call_counts["stage3"] += 1
        if idx == 2:
            # domain3 (3rd call to stage3): no DM
            return await _stage3_no_dm(domain_data, gemini)
        return await _stage3_pass(domain_data, gemini)

    async def _stage5_side_effect(domain_data: dict) -> dict:
        idx = call_counts["stage5"]
        call_counts["stage5"] += 1
        if idx < 2:
            # domain1 and domain2: rejected
            return await _stage5_reject(domain_data)
        return await _stage5_pass(domain_data)

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_side_effect),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_side_effect),
        patch("src.pipeline.pipeline_orchestrator._run_stage4", _stage4_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage5", _stage5_side_effect),
        patch("src.pipeline.pipeline_orchestrator._run_stage6", _stage6_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage7", _stage7_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage8", _stage8_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage9", _stage9_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage10", _stage10_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage11", _stage11_mock),
    ):
        result = await orch.run_streaming(
            categories=["beauty_salon"],
            target_cards=10,
            budget_cap_aud=500.0,
            num_workers=1,
        )

    assert result.stats.discovered == 5
    assert result.stats.enrichment_failed >= 1
    assert result.stats.affordability_rejected == 2
    assert result.stats.viable_prospects == 1


@pytest.mark.asyncio
async def test_prospect_card_fields():
    """A domain passing all stages must produce a ProspectCard with expected fields."""
    disc = _make_discovery(["example.com.au"])
    orch = _make_orch(disc)

    async def _stage11_full(domain_data: dict) -> dict:
        stage3 = domain_data.get("stage3") or {}
        dm = stage3.get("dm_candidate") or {}
        stage5 = domain_data.get("stage5") or {}
        domain_data["stage11"] = {
            "company_name": "Example Pty Ltd",
            "location": "Melbourne VIC",
            "location_suburb": "Melbourne",
            "location_state": "VIC",
            "dm_name": dm.get("name", "Alice Owner"),
            "dm_title": dm.get("role", "Owner"),
            "dm_linkedin_url": dm.get("linkedin_url", "https://au.linkedin.com/in/aliceowner"),
            "dm_confidence": "HIGH",
            "intent_band": stage5.get("intent_band", "TRYING"),
            "services": ["beauty_salon"],
            "evidence": ["Has website", "No analytics", "Signal A"],
            "is_running_ads": True,
            "gmb_review_count": 45,
        }
        return domain_data

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
        patch("src.pipeline.pipeline_orchestrator._run_stage11", _stage11_full),
    ):
        result = await orch.run_streaming(
            categories=["beauty_salon"],
            target_cards=1,
            budget_cap_aud=50.0,
            num_workers=1,
        )

    assert len(result.prospects) == 1
    card = result.prospects[0]

    assert card.domain == "example.com.au"
    assert isinstance(card.company_name, str) and card.company_name
    assert isinstance(card.location, str)
    assert isinstance(card.evidence, list)
    assert isinstance(card.affordability_band, str)
    assert isinstance(card.affordability_score, int)
    assert card.dm_name is not None and isinstance(card.dm_name, str)
    assert hasattr(card, "dm_title")
    assert hasattr(card, "dm_linkedin_url")
    assert hasattr(card, "dm_confidence")
