"""Tests for gated PipelineOrchestrator flow — CD Player v1 API.

These tests patch the cohort_runner stage functions imported into
pipeline_orchestrator so the real orchestrator logic runs but without
live API calls. Stages return controlled domain_data dicts that trigger
specific gate conditions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.pipeline.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStats,
    ProspectCard,
)


# ── Shared stage mock helpers ─────────────────────────────────────────────────

def _stage_pass(domain_data: dict) -> dict:
    """Return domain_data unchanged (stage succeeded, no drop)."""
    return domain_data


async def _async_stage_pass(domain_data: dict, *args, **kwargs) -> dict:
    return domain_data


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
    """Stage 3 that passes: returns a valid DM candidate."""
    domain_data["stage3"] = {
        "business_name": "Test Dental",
        "is_enterprise_or_chain": False,
        "dm_candidate": {
            "name": "Jane Smith",
            "role": "Owner",
            "linkedin_url": "https://au.linkedin.com/in/janesmith",
        },
    }
    return domain_data


async def _stage3_no_dm(domain_data: dict, gemini) -> dict:
    """Stage 3 that drops: no DM found (mirrors real cohort_runner gate)."""
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
    """Stage 5 that passes the affordability gate (composite_score >= 30)."""
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
    """Stage 5 that fails the affordability gate (mirrors real cohort_runner gate)."""
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
        "email": {"email": "jane@testdental.com.au", "verified": True, "source": "leadmagic"},
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


# ── Discovery mock factory ────────────────────────────────────────────────────

def _make_discovery(domains: list[str]):
    """Return a discovery mock whose pull_batch returns the domains once then empty."""
    disc = MagicMock()
    batch = [{"domain": d} for d in domains]
    disc.pull_batch = AsyncMock(side_effect=[batch, []])
    return disc


# ── Patch context for all stage functions ────────────────────────────────────

STAGE_PATCHES_PASS = {
    "src.pipeline.pipeline_orchestrator._run_stage2": _stage2_mock,
    "src.pipeline.pipeline_orchestrator._run_stage3": _stage3_pass,
    "src.pipeline.pipeline_orchestrator._run_stage4": _stage4_mock,
    "src.pipeline.pipeline_orchestrator._run_stage5": _stage5_pass,
    "src.pipeline.pipeline_orchestrator._run_stage6": _stage6_mock,
    "src.pipeline.pipeline_orchestrator._run_stage7": _stage7_mock,
    "src.pipeline.pipeline_orchestrator._run_stage8": _stage8_mock,
    "src.pipeline.pipeline_orchestrator._run_stage9": _stage9_mock,
    "src.pipeline.pipeline_orchestrator._run_stage10": _stage10_mock,
    "src.pipeline.pipeline_orchestrator._run_stage11": _stage11_mock,
    "src.pipeline.pipeline_orchestrator._default_on_domain_complete": AsyncMock(return_value=None),
}


def _patch_stages(overrides: dict | None = None):
    """Return a list of patch objects. overrides replaces specific stage mocks."""
    patches = dict(STAGE_PATCHES_PASS)
    if overrides:
        patches.update(overrides)
    return patches


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


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_affordability_rejected_counted():
    """Stage 5 drop (score < gate) must increment stats.affordability_rejected."""
    disc = _make_discovery(["dental.com.au"])
    orch = _make_orch(disc)

    stage_mocks = _patch_stages(overrides={
        "src.pipeline.pipeline_orchestrator._run_stage5": _stage5_reject,
    })
    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_pass),
        patch("src.pipeline.pipeline_orchestrator._run_stage4", _stage4_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage5", _stage5_reject),
        patch("src.pipeline.pipeline_orchestrator._run_stage6", _stage6_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage7", _stage7_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage8", _stage8_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage9", _stage9_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage10", _stage10_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage11", _stage11_mock),
    ):
        result = await orch.run_streaming(
            categories=["dental"], target_cards=5, budget_cap_aud=50.0, num_workers=1
        )

    assert result.stats.affordability_rejected == 1
    assert result.stats.viable_prospects == 0


@pytest.mark.asyncio
async def test_intent_not_trying_skips_paid_enrichment():
    """Stage 3 drop with no_dm_found must count as enrichment_failed (not a card).
    Paid stages (8, 9) must not be called for that domain.
    """
    disc = _make_discovery(["dental.com.au"])
    orch = _make_orch(disc)

    stage8_spy = AsyncMock(side_effect=_stage8_mock)

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_no_dm),
        patch("src.pipeline.pipeline_orchestrator._run_stage4", _stage4_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage5", _stage5_pass),
        patch("src.pipeline.pipeline_orchestrator._run_stage6", _stage6_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage7", _stage7_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage8", stage8_spy),
        patch("src.pipeline.pipeline_orchestrator._run_stage9", _stage9_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage10", _stage10_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage11", _stage11_mock),
    ):
        result = await orch.run_streaming(
            categories=["dental"], target_cards=5, budget_cap_aud=50.0, num_workers=1
        )

    # Domain dropped at stage3 — no card produced, stage 8 never called
    assert result.stats.viable_prospects == 0
    assert result.stats.enrichment_failed == 1
    stage8_spy.assert_not_called()


@pytest.mark.asyncio
async def test_full_prospect_card_with_evidence():
    """A domain that passes all gates must produce a ProspectCard with dm_name and intent_band."""
    disc = _make_discovery(["dental.com.au"])
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
            categories=["dental"], target_cards=1, budget_cap_aud=50.0, num_workers=1
        )

    assert len(result.prospects) == 1
    card = result.prospects[0]
    assert card.dm_name == "Jane Smith"
    assert card.intent_band in ("NOT_TRYING", "DABBLING", "TRYING", "STRUGGLING", "UNKNOWN")


@pytest.mark.asyncio
async def test_dm_not_found_counted():
    """Stage 3 gate (no DM candidate) must drop the domain; no card produced."""
    disc = _make_discovery(["x.com.au"])
    orch = _make_orch(disc)

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_no_dm),
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
            categories=["dental"], target_cards=5, budget_cap_aud=50.0, num_workers=1
        )

    # No card produced; enrichment_failed incremented for stage3 drop
    assert result.stats.viable_prospects == 0
    assert result.stats.enrichment_failed == 1


@pytest.mark.asyncio
async def test_stops_at_target_count():
    """Pipeline must stop emitting cards once target_cards is reached."""
    domains = [f"d{i}.com.au" for i in range(20)]
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
            categories=["dental"],
            target_cards=3,
            budget_cap_aud=500.0,
            num_workers=1,
            batch_size=20,
        )

    assert len(result.prospects) == 3
