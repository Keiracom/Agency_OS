"""
Tests for multi-category discovery — Directive #298.
Covers: category_registry, MultiCategoryDiscovery, run_parallel discover_all mode.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, call


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
    from src.config.category_registry import get_discovery_categories, SERVICE_CATEGORY_MAP
    seo = set(SERVICE_CATEGORY_MAP["seo"])
    ads = set(SERVICE_CATEGORY_MAP["google_ads"])
    combined = get_discovery_categories(["seo", "google_ads"])
    # Must contain codes from both services
    assert seo.issubset(set(combined) | seo - seo)  # all seo codes present
    assert len(combined) >= len(seo | ads)


def test_get_discovery_categories_preferred_industries_first():
    """Codes matching preferred_industries appear first in returned list."""
    from src.config.category_registry import get_discovery_categories, INDUSTRY_VERTICALS
    dental_codes = set(INDUSTRY_VERTICALS["dental"])
    codes = get_discovery_categories(["seo"], preferred_industries=["dental"])
    # dental codes must appear before non-dental codes
    dental_positions = [i for i, c in enumerate(codes) if c in dental_codes]
    non_dental_positions = [i for i, c in enumerate(codes) if c not in dental_codes]
    if dental_positions and non_dental_positions:
        assert max(dental_positions) < min(non_dental_positions)


def test_get_discovery_categories_unknown_service_returns_all():
    """Unknown service slug falls back to ALL_DISCOVERY_CATEGORIES."""
    from src.config.category_registry import get_discovery_categories, ALL_DISCOVERY_CATEGORIES
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
    dfs.domain_metrics_by_categories = AsyncMock(return_value=[
        {"domain": f"dental{i}.com.au", "organic_etv": 500.0, "paid_etv": 0.0}
        for i in range(domains_per_call)
    ])
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
    )
    assert len(results) > 0
    assert all("domain" in r for r in results)
    assert all("organic_etv" in r for r in results)


@pytest.mark.asyncio
async def test_discover_prospects_deduplicates_against_exclude():
    """discover_prospects skips domains in exclude_domains."""
    from src.pipeline.discovery import MultiCategoryDiscovery
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=[
        {"domain": "claimed.com.au", "organic_etv": 500.0, "paid_etv": 0.0},
        {"domain": "fresh.com.au", "organic_etv": 500.0, "paid_etv": 0.0},
    ])
    disc = MultiCategoryDiscovery(dfs)
    results = await disc.discover_prospects(
        category_codes=[10514],
        exclude_domains={"claimed.com.au"},
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
    results = await disc.discover_prospects(category_codes=[])
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
    await disc.discover_prospects(category_codes=codes)
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
    results = await disc.discover_prospects(category_codes=codes)
    domains = [r["domain"] for r in results]
    assert domains.count("shared.com.au") == 1  # not duplicated


# ── run_parallel discover_all integration ────────────────────────────────────

@pytest.mark.asyncio
async def test_run_parallel_discover_all_feeds_worker_pool():
    """run_parallel with discover_all=True pre-fetches domains and workers process them."""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    # Discovery mock with discover_prospects
    disc = MagicMock()
    disc.discover_prospects = AsyncMock(return_value=[
        {"domain": f"dental{i}.com.au", "organic_etv": 500.0, "category_codes": [10514]}
        for i in range(5)
    ])

    fe = MagicMock()
    fe.scrape_website = AsyncMock(return_value={"title": "Test", "_raw_html": "<html>NSW</html>"})
    fe.enrich_from_spider = AsyncMock(return_value={
        "domain": "dental.com.au", "company_name": "Test Dental",
        "entity_type": "Company", "gst_registered": True,
        "non_au": False, "website_contact_emails": ["info@test.com.au"],
        "html": "<html>NSW</html>",
    })

    scorer = MagicMock()
    scorer.score_affordability = MagicMock(
        return_value=MagicMock(passed_gate=True, band="HIGH", raw_score=9, gaps=[])
    )
    scorer.score_intent_free = MagicMock(
        return_value=MagicMock(band="TRYING", passed_free_gate=True, raw_score=5, evidence=[])
    )
    scorer.score_intent_full = MagicMock(
        return_value=MagicMock(band="TRYING", raw_score=6, evidence=["Signal A"])
    )

    dm_result = MagicMock()
    dm_result.name = "Dr. Jane Smith"
    dm_result.title = "Principal Dentist"
    dm_result.linkedin_url = "https://au.linkedin.com/in/jane"
    dm_result.confidence = "HIGH"
    dm_id = MagicMock()
    dm_id.identify = AsyncMock(return_value=dm_result)

    orch = PipelineOrchestrator(
        discovery=disc,
        free_enrichment=fe,
        scorer=scorer,
        dm_identification=dm_id,
    )

    result = await orch.run_parallel(
        category_codes=["10514", "13462"],
        location="Australia",
        target_count=2,
        num_workers=2,
        batch_size=5,
        discover_all=True,
    )

    # discover_prospects must have been called (not pull_batch)
    disc.discover_prospects.assert_called_once()
    assert "discover_prospects" in str(disc.method_calls)
    # Got prospects from the pre-fetched pool
    assert len(result.prospects) >= 1
