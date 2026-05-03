"""Tests for PipelineOrchestrator parallel/streaming — CD Player v1 API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.pipeline_orchestrator import (
    GLOBAL_SEM_DFS,
    GLOBAL_SEM_SCRAPE,
    PipelineOrchestrator,
)

# ── Shared stage mock helpers (copied from test_orchestrator_gates.py) ────────


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
    domain_data["stage3"] = {
        "business_name": "Test Co",
        "is_enterprise_or_chain": False,
        "dm_candidate": {
            "name": "Jane Owner",
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


async def _stage5_non_au_reject(domain_data: dict) -> dict:
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


# ── Discovery mock factory ────────────────────────────────────────────────────


def _make_discovery(domains: list[str]):
    disc = MagicMock()
    batch = [{"domain": d} for d in domains]
    disc.pull_batch = AsyncMock(side_effect=[batch, []])
    return disc


def _make_orch(discovery, domains_per_batch=5, target=3):
    """Build a CD Player v1 orchestrator with mocked clients."""
    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 3:
            return []
        return [{"domain": f"d{call_count['n']}x{i}.com.au"} for i in range(domains_per_batch)]

    if discovery is None:
        discovery = MagicMock()
        discovery.pull_batch = pull_batch

    return PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=discovery,
        on_domain_complete=AsyncMock(return_value=None),
    )


_ALL_STAGE_PATCHES = {
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
}


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_parallel_reaches_target():
    """With ample domains, run_streaming stops at target_cards."""
    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 5:
            return []
        return [{"domain": f"d{call_count['n']}x{i}.com.au"} for i in range(10)]

    disc = MagicMock()
    disc.pull_batch = pull_batch
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
            num_workers=2,
            batch_size=10,
        )

    assert len(result.prospects) == 3
    assert result.stats.viable_prospects == 3


@pytest.mark.asyncio
async def test_run_parallel_deduplicates_domains():
    """Same domain appearing in multiple batches is processed only once."""
    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return [{"domain": "shared.com.au"}]
        if call_count["n"] == 2:
            return [{"domain": "shared.com.au"}]  # duplicate
        return []

    disc = MagicMock()
    disc.pull_batch = pull_batch
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
            num_workers=2,
            batch_size=1,
        )

    # shared.com.au should only be counted once
    assert result.stats.discovered == 1


@pytest.mark.asyncio
async def test_run_parallel_stops_on_exhaustion():
    """When all batches are empty, workers stop and empty result is returned."""
    disc = MagicMock()
    disc.pull_batch = AsyncMock(return_value=[])
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
            target_cards=100,
            budget_cap_aud=500.0,
            num_workers=2,
            batch_size=10,
        )

    assert len(result.prospects) == 0
    assert result.stats.discovered == 0


@pytest.mark.asyncio
async def test_run_parallel_non_au_rejected():
    """Domains that fail stage5 with non_au are counted in affordability_rejected."""
    disc = _make_discovery(["dentatur.com"])
    orch = _make_orch(disc)

    with (
        patch("src.pipeline.pipeline_orchestrator._run_stage2", _stage2_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage3", _stage3_pass),
        patch("src.pipeline.pipeline_orchestrator._run_stage4", _stage4_mock),
        patch("src.pipeline.pipeline_orchestrator._run_stage5", _stage5_non_au_reject),
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
            batch_size=5,
        )

    assert result.stats.affordability_rejected == 1
    assert len(result.prospects) == 0


@pytest.mark.asyncio
async def test_run_parallel_on_prospect_found_callback():
    """on_card callback is invoked for each prospect found."""
    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] > 3:
            return []
        return [{"domain": f"d{call_count['n']}x{i}.com.au"} for i in range(5)]

    disc = MagicMock()
    disc.pull_batch = pull_batch

    found = []

    def capture(card):
        found.append(card.domain)

    orch = PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=disc,
        on_card=capture,
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
            categories=["dental"],
            target_cards=2,
            budget_cap_aud=500.0,
            num_workers=1,
            batch_size=5,
        )

    assert len(found) == 2
    assert len(result.prospects) == 2


@pytest.mark.asyncio
async def test_parallel_stops_at_target_count():
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


@pytest.mark.asyncio
async def test_global_semaphores_exist():
    """Global semaphore pool is module-level and accessible."""
    assert GLOBAL_SEM_DFS._value == 28
    assert GLOBAL_SEM_SCRAPE._value == 80
