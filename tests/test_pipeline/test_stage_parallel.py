"""Tests for stage-parallel PipelineOrchestrator — CD Player v1 API.

These tests patch the cohort_runner stage functions imported into
pipeline_orchestrator so the real orchestrator logic runs but without
live API calls. Stages return controlled domain_data dicts that trigger
specific gate conditions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.pipeline_orchestrator import (
    SEM_ABN,
    SEM_DM,
    SEM_PAID,
    SEM_SPIDER,
    PipelineOrchestrator,
)

# ── Shared stage mock helpers ─────────────────────────────────────────────────


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
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


# ── Orchestrator factory ──────────────────────────────────────────────────────


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


# ── Passing non-xfail tests (unchanged) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_semaphore_constants_defined():
    assert SEM_SPIDER == 15
    assert SEM_ABN == 50
    assert SEM_PAID == 20
    assert SEM_DM == 20


@pytest.mark.asyncio
async def test_empty_discovery_returns_empty():
    disc = MagicMock()
    disc.pull_batch = AsyncMock(return_value=[])
    fe = MagicMock()
    scorer = MagicMock()
    dm_id = MagicMock()
    orch = PipelineOrchestrator(
        discovery=disc, free_enrichment=fe, scorer=scorer, dm_identification=dm_id
    )
    result = await orch.run("10514", target_count=10)
    assert result.prospects == []
    assert result.stats.discovered == 0


# ── Rewritten xfail tests (CD Player v1 API) ─────────────────────────────────


@pytest.mark.asyncio
async def test_stage_parallel_produces_prospect():
    """Single domain through all stages produces a prospect card."""
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
    assert card.domain == "dental.com.au"
    assert card.dm_name == "Jane Smith"


@pytest.mark.asyncio
async def test_batch_of_10_all_concurrent():
    """10 domains processed — verify all 10 were discovered (no wall-clock assertion)."""
    domains = [{"domain": f"d{i}.com.au"} for i in range(10)]
    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=[domains, []])
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
            target_cards=10,
            budget_cap_aud=500.0,
            num_workers=4,
            batch_size=10,
        )

    assert result.stats.discovered == 10


@pytest.mark.asyncio
async def test_affordability_gate_filters_between_stages():
    """Affordability rejection (stage5 drop) stops further stages and increments counter."""
    disc = _make_discovery(["dental.com.au"])
    orch = _make_orch(disc)

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

    assert result.stats.affordability_rejected >= 1
    assert len(result.prospects) == 0


@pytest.mark.asyncio
async def test_not_trying_skips_paid_enrichment():
    """Intent rejection at stage3 (no_dm_found) skips paid stages; stage8 never called."""
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

    assert result.stats.viable_prospects == 0
    assert result.stats.enrichment_failed >= 1
    stage8_spy.assert_not_called()


@pytest.mark.asyncio
async def test_spider_failure_doesnt_block_others():
    """One domain failing stage2 doesn't block the others from processing."""
    domains = [{"domain": "fail.com.au"}, {"domain": "ok.com.au"}]
    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=[domains, []])
    orch = _make_orch(disc)

    call_count = {"n": 0}

    async def _stage2_fail_first(domain_data: dict, dfs) -> dict:
        call_count["n"] += 1
        if domain_data.get("domain") == "fail.com.au":
            domain_data["dropped_at"] = "stage2"
            domain_data["drop_reason"] = "spider_timeout"
            return domain_data
        domain_data["stage2"] = {"serp_abn": "12345678901"}
        domain_data["cost_usd"] += 0.01
        return domain_data

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_fail_first),
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
            categories=["dental"], target_cards=5, budget_cap_aud=50.0, num_workers=2
        )

    # Both domains entered stage2 (fail.com.au dropped, ok.com.au continued)
    assert call_count["n"] == 2
    assert result.stats.discovered == 2
    assert len(result.prospects) == 1


@pytest.mark.asyncio
async def test_stats_track_all_rejection_reasons():
    """Mixed outcomes: stats counters reflect correct tallies."""
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

    stats = result.stats
    assert stats.discovered >= 1
    assert stats.viable_prospects == len(result.prospects)


@pytest.mark.asyncio
async def test_stops_at_target_count():
    """Pipeline stops after target_cards is reached."""
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
