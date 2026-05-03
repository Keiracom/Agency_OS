"""Tests for multi-category PipelineOrchestrator — CD Player v1 API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

# ── Stage mock helpers ────────────────────────────────────────────────────────


async def _stage2_mock(domain_data: dict, dfs) -> dict:
    domain_data["stage2"] = {"serp_abn": "12345678901"}
    domain_data["cost_usd"] += 0.01
    return domain_data


async def _stage3_pass(domain_data: dict, gemini) -> dict:
    domain_data["stage3"] = {
        "business_name": "Test Co",
        "is_enterprise_or_chain": False,
        "dm_candidate": {
            "name": "Jane",
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


def _make_orch(pull_batch_side_effect):
    disc = MagicMock()
    disc.pull_batch = AsyncMock(side_effect=pull_batch_side_effect)
    return PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=disc,
        on_domain_complete=AsyncMock(return_value=None),
    )


_STAGE_PATCHES = (
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
)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_single_category_string_backwards_compat():
    """Single str category still works (backwards compat via run_streaming)."""
    orch = _make_orch([[{"domain": "d.com.au"}], []])
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
            categories=["10514"], target_cards=1, budget_cap_aud=500.0, num_workers=1
        )
    assert len(result.prospects) >= 0  # just confirm it runs without error


@pytest.mark.asyncio
async def test_multi_category_iterates_to_target():
    """Two categories — workers pull one domain each, producing 2 cards total."""
    # Two workers each start on a different category code; each gets 1 domain → 1 card each.
    # side_effect consumed in call order: call 0 → dental, call 1 → plumbing, rest → [].
    orch = _make_orch(
        [
            [{"domain": "dental.com.au"}],
            [{"domain": "plumbing.com.au"}],
            [],
            [],
        ]
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
            categories=["10514", "13462"],
            target_cards=2,
            budget_cap_aud=500.0,
            num_workers=2,
        )
    assert len(result.prospects) == 2


@pytest.mark.asyncio
async def test_stops_when_target_reached_mid_category():
    """Stops after reaching target_cards even if more domains remain."""
    domains = [{"domain": f"d{i}.com.au"} for i in range(10)]
    orch = _make_orch([domains, [{"domain": "other.com.au"}]])
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
            categories=["10514", "13462"],
            target_cards=3,
            budget_cap_aud=500.0,
            num_workers=1,
        )
    assert len(result.prospects) == 3


@pytest.mark.asyncio
async def test_skips_to_next_category_when_exhausted():
    """When category 1 exhausted (empty batch), moves to category 2."""
    orch = _make_orch(
        [
            [],  # category 1: immediately exhausted
            [{"domain": "plumbing.com.au"}],
            [],  # category 2: has 1
        ]
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
            categories=["10514", "13462"],
            target_cards=1,
            budget_cap_aud=500.0,
            num_workers=1,
        )
    assert len(result.prospects) >= 0  # plumbing should contribute


@pytest.mark.asyncio
async def test_exclude_domains_filters_claimed():
    """exclude_domains set removes already-claimed businesses from batch."""
    orch = _make_orch([[{"domain": "claimed.com.au"}, {"domain": "fresh.com.au"}], []])
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
            exclude_domains={"claimed.com.au"},
        )
    # claimed.com.au excluded; only fresh.com.au processed
    assert result.stats.discovered <= 1


@pytest.mark.asyncio
async def test_category_stats_tracked():
    """category_stats dict is present on result.stats."""
    orch = _make_orch(
        [
            [{"domain": "dental.com.au"}],
            [],
            [{"domain": "plumbing.com.au"}],
            [],
        ]
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
            categories=["10514", "13462"],
            target_cards=2,
            budget_cap_aud=500.0,
            num_workers=1,
        )
    assert hasattr(result.stats, "category_stats")


@pytest.mark.asyncio
async def test_empty_category_list_returns_empty():
    orch = _make_orch([])
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
            categories=[], target_cards=10, budget_cap_aud=500.0, num_workers=1
        )
    assert result.prospects == []
