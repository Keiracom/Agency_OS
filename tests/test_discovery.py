"""
Tests for multi-category discovery — Directive #298.
Covers: category_registry, MultiCategoryDiscovery, run_streaming discover_all mode.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Category registry tests ───────────────────────────────────────────────────


def test_get_discovery_categories_seo_returns_ints():
    """get_discovery_categories(['seo']) returns a non-empty list of ints."""
    from src.config.category_registry import get_discovery_categories

    codes = get_discovery_categories(["seo"])
    assert isinstance(codes, list)
    assert len(codes) > 0
    assert all(isinstance(c, int) for c in codes)


def test_get_discovery_categories_multiple_services_union():
    """get_discovery_categories(['seo','google_ads']) returns union of both sets."""
    from src.config.category_registry import SERVICE_CATEGORY_MAP, get_discovery_categories

    seo = set(SERVICE_CATEGORY_MAP["seo"])
    ads = set(SERVICE_CATEGORY_MAP["google_ads"])
    combined = get_discovery_categories(["seo", "google_ads"])
    # Must contain codes from both services
    assert seo.issubset(set(combined) | seo - seo)  # all seo codes present
    assert len(combined) >= len(seo | ads)


def test_get_discovery_categories_preferred_industries_first():
    """Codes matching preferred_industries appear first in returned list."""
    from src.config.category_registry import INDUSTRY_VERTICALS, get_discovery_categories

    dental_codes = set(INDUSTRY_VERTICALS["dental"])
    codes = get_discovery_categories(["seo"], preferred_industries=["dental"])
    # dental codes must appear before non-dental codes
    dental_positions = [i for i, c in enumerate(codes) if c in dental_codes]
    non_dental_positions = [i for i, c in enumerate(codes) if c not in dental_codes]
    if dental_positions and non_dental_positions:
        assert max(dental_positions) < min(non_dental_positions)


def test_get_discovery_categories_unknown_service_returns_all():
    """Unknown service slug falls back to ALL_DISCOVERY_CATEGORIES."""
    from src.config.category_registry import ALL_DISCOVERY_CATEGORIES, get_discovery_categories

    codes = get_discovery_categories(["nonexistent_service"])
    assert set(codes) == set(ALL_DISCOVERY_CATEGORIES)


def test_service_category_map_has_required_services():
    """SERVICE_CATEGORY_MAP contains all four required service slugs."""
    from src.config.category_registry import SERVICE_CATEGORY_MAP

    for svc in ["seo", "google_ads", "social_media", "web_design"]:
        assert svc in SERVICE_CATEGORY_MAP
        assert len(SERVICE_CATEGORY_MAP[svc]) > 0


def test_category_labels_has_dental():
    """CATEGORY_LABELS has the canonical dental code."""
    from src.config.category_registry import CATEGORY_LABELS

    assert 10514 in CATEGORY_LABELS
    assert "dental" in CATEGORY_LABELS[10514].lower() or "dentist" in CATEGORY_LABELS[10514].lower()


# ── MultiCategoryDiscovery tests ──────────────────────────────────────────────


def _make_dfs(domains_per_call=5):
    """Mock DFS client returning N domains per domain_metrics_by_categories call."""
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(
        return_value=[
            {"domain": f"dental{i}.com.au", "organic_etv": 500.0, "paid_etv": 0.0}
            for i in range(domains_per_call)
        ]
    )
    return dfs


@pytest.mark.asyncio
async def test_discover_prospects_returns_domains():
    """discover_prospects returns list of domain dicts."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = _make_dfs(3)
    disc = MultiCategoryDiscovery(dfs)
    results = await disc.discover_prospects(
        category_codes=[10514, 13462],
        location="Australia",
        etv_min=0.0,
        etv_max=999999.0,
    )
    assert len(results) > 0
    assert all("domain" in r for r in results)
    assert all("organic_etv" in r for r in results)


@pytest.mark.asyncio
async def test_discover_prospects_deduplicates_against_exclude():
    """discover_prospects skips domains in exclude_domains."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(
        return_value=[
            {"domain": "claimed.com.au", "organic_etv": 500.0, "paid_etv": 0.0},
            {"domain": "fresh.com.au", "organic_etv": 500.0, "paid_etv": 0.0},
        ]
    )
    disc = MultiCategoryDiscovery(dfs)
    results = await disc.discover_prospects(
        category_codes=[10514],
        exclude_domains={"claimed.com.au"},
        etv_min=0.0,
        etv_max=999999.0,
    )
    domains = [r["domain"] for r in results]
    assert "claimed.com.au" not in domains
    assert "fresh.com.au" in domains


@pytest.mark.asyncio
async def test_discover_prospects_empty_category_list():
    """discover_prospects with empty category list returns [] gracefully."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = _make_dfs()
    disc = MultiCategoryDiscovery(dfs)
    results = await disc.discover_prospects(category_codes=[], etv_min=0.0, etv_max=999999.0)
    assert results == []
    dfs.domain_metrics_by_categories.assert_not_called()


@pytest.mark.asyncio
async def test_discover_prospects_batch_callback_fires():
    """batch_callback fires once per pagination call (one call per category code)."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = _make_dfs(2)
    disc = MultiCategoryDiscovery(dfs)
    callback_calls = []

    await disc.discover_prospects(
        category_codes=[10514, 13462, 11295],
        batch_callback=lambda b: callback_calls.append(b),
        etv_min=0.0,
        etv_max=999999.0,
    )
    # 3 codes → 3 DFS calls (one per code) → up to 3 callbacks
    # Each returns 2 domains with etv=500 (in range) → callback fires per batch
    assert len(callback_calls) >= 1


@pytest.mark.asyncio
async def test_discover_prospects_batches_at_max_codes():
    """Each category code gets its own DFS call (pagination architecture)."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = _make_dfs(1)  # returns 1 domain per call, etv=500 → in range, then pagination stops
    disc = MultiCategoryDiscovery(dfs)
    # 5 codes → at least 5 DFS calls (one per code, possibly more if paginating)
    codes = list(range(10000, 10005))
    await disc.discover_prospects(category_codes=codes, etv_min=0.0, etv_max=999999.0)
    # Each code gets at least 1 call; since mock returns only 1 item (< batch_size=100),
    # pagination stops after 1 call per code → exactly 5 calls
    assert dfs.domain_metrics_by_categories.call_count == len(codes)


@pytest.mark.asyncio
async def test_discover_prospects_deduplicates_across_batches():
    """Same domain from two category batches appears only once."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    call_n = {"n": 0}

    async def mock_dfs(*args, **kwargs):
        call_n["n"] += 1
        # Both batches return the same domain + one unique
        return [
            {"domain": "shared.com.au", "organic_etv": 500.0, "paid_etv": 0.0},
            {"domain": f"unique{call_n['n']}.com.au", "organic_etv": 500.0, "paid_etv": 0.0},
        ]

    dfs = MagicMock()
    dfs.domain_metrics_by_categories = mock_dfs
    disc = MultiCategoryDiscovery(dfs)

    # 25 codes → 2 batches
    codes = list(range(10000, 10025))
    results = await disc.discover_prospects(category_codes=codes, etv_min=0.0, etv_max=999999.0)
    domains = [r["domain"] for r in results]
    assert domains.count("shared.com.au") == 1  # not duplicated


# ── run_streaming discover_all integration ────────────────────────────────────

# Stage mock helpers for CD Player v1


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


@pytest.mark.asyncio
async def test_run_parallel_discover_all_feeds_worker_pool():
    """run_streaming processes domains from discovery pull_batch."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    call_count = {"n": 0}

    async def pull_batch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return [
                {"domain": f"dental{i}.com.au", "organic_etv": 500.0, "category_codes": [10514]}
                for i in range(5)
            ]
        return []

    disc = MagicMock()
    disc.pull_batch = pull_batch

    orch = PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=disc,
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
            categories=["10514", "13462"],
            target_cards=2,
            budget_cap_aud=500.0,
            num_workers=2,
            batch_size=5,
        )

    # pull_batch was called — workers fetched domains
    assert call_count["n"] >= 1
    # Got prospects from the discovery pool
    assert len(result.prospects) >= 1


# ── On-demand next_batch tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_next_batch_returns_domains():
    """next_batch returns domains from first page."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = _make_dfs(5)
    disc = MultiCategoryDiscovery(dfs)
    disc.reset([10514])
    batch = await disc.next_batch(
        category_codes=[10514],
        location="Australia",
        batch_size=100,
        etv_min=0.0,
        etv_max=99999.0,
    )
    assert len(batch) == 5
    assert all("domain" in d for d in batch)


@pytest.mark.asyncio
async def test_next_batch_advances_offset():
    """Successive next_batch calls advance offset — each call uses a higher offset."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    call_offsets = []

    async def mock_dfs(
        category_codes,
        location_name="Australia",
        paid_etv_min=0.0,
        limit=100,
        offset=0,
        **kwargs,
    ):
        call_offsets.append(offset)
        # Return exactly limit items so pagination doesn't stop (not a last page)
        return [
            {
                "domain": f"d{offset}x{i}.com.au",
                "organic_etv": 500.0,
                "paid_etv": 0.0,
                "_total_count": 1000,
            }
            for i in range(limit)
        ]

    dfs = MagicMock()
    dfs.domain_metrics_by_categories = mock_dfs
    disc = MultiCategoryDiscovery(dfs)
    disc.reset([10514])

    await disc.next_batch(category_codes=[10514], batch_size=100, etv_min=0.0, etv_max=99999.0)
    await disc.next_batch(category_codes=[10514], batch_size=100, etv_min=0.0, etv_max=99999.0)

    assert len(call_offsets) == 2
    assert call_offsets[0] == 0
    assert call_offsets[1] == 100  # advanced by len(raw) = limit = 100


@pytest.mark.asyncio
async def test_next_batch_exhausts_when_min_etv_drops():
    """Category marked exhausted when min_etv in batch drops below etv_min."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    async def mock_dfs(*args, **kwargs):
        # Return low-ETV items that are below the 100 floor
        return [
            {"domain": f"low{i}.com.au", "organic_etv": 50.0, "paid_etv": 0.0} for i in range(5)
        ]

    dfs = MagicMock()
    dfs.domain_metrics_by_categories = mock_dfs
    disc = MultiCategoryDiscovery(dfs)
    disc.reset([10514])

    batch = await disc.next_batch(
        category_codes=[10514], batch_size=100, etv_min=100.0, etv_max=99999.0
    )
    # Items below etv_min are filtered out
    assert len(batch) == 0
    # Category should be exhausted
    assert disc.all_exhausted


@pytest.mark.asyncio
async def test_all_exhausted_returns_empty():
    """next_batch returns [] when all categories exhausted."""
    from src.pipeline.discovery import MultiCategoryDiscovery

    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=[])
    disc = MultiCategoryDiscovery(dfs)
    disc.reset([10514])

    result = await disc.next_batch(
        category_codes=[10514], batch_size=100, etv_min=0.0, etv_max=99999.0
    )
    assert result == []
    assert disc.all_exhausted


@pytest.mark.asyncio
async def test_run_parallel_on_demand_stops_refill_at_target():
    """run_streaming stops accepting new domains after target_cards reached."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    pull_calls = {"n": 0}

    async def pull_batch(**kwargs):
        pull_calls["n"] += 1
        return [
            {
                "domain": f"d{pull_calls['n']}x{i}.com.au",
                "organic_etv": 500.0,
                "category_codes": [10514],
            }
            for i in range(20)
        ]

    disc = MagicMock()
    disc.pull_batch = pull_batch

    orch = PipelineOrchestrator(
        dfs_client=MagicMock(),
        gemini_client=MagicMock(),
        bd_client=MagicMock(),
        lm_client=MagicMock(),
        discovery=disc,
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

    assert len(result.prospects) == 1
    # pull_batch was called (worker fetched domains)
    assert pull_calls["n"] >= 1
