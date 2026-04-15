"""Verify cost constants match documented provider rates.
When DFS/provider pricing changes, this test fails until constants updated."""

from src.orchestration.cohort_runner import (
    STAGE4_COST_PER_DOMAIN,
    STAGE6_COST_PER_DOMAIN,
    STAGE8_SERP_FALLBACK,
    STAGE8_WATERFALL_COST,
    STAGE9_COST_PER_DOMAIN,
)


def test_stage4_cost_matches_documented():
    """Stage 4 SIGNAL: 10 DFS endpoints — constant must match independent endpoint sum."""
    from decimal import Decimal

    # Independent calculation from provider rates in dfs_labs_client.py
    endpoints = {
        "domain_rank_overview": Decimal("0.010"),
        "competitors_domain": Decimal("0.011"),
        "keywords_for_site": Decimal("0.011"),
        "domain_technologies": Decimal("0.010"),
        "maps_search_gmb": Decimal("0.0035"),
        "backlinks_summary": Decimal("0.020"),
        "brand_serp": Decimal("0.002"),
        "indexed_pages": Decimal("0.002"),
        "ads_search_by_domain": Decimal("0.002"),
        "google_ads_advertisers": Decimal("0.006"),
    }
    endpoints_sum = float(sum(endpoints.values()))
    assert abs(STAGE4_COST_PER_DOMAIN - endpoints_sum) < 0.005, (
        f"Stage 4 cost drift: constant={STAGE4_COST_PER_DOMAIN} vs endpoints={endpoints_sum}"
    )


def test_stage6_cost_matches_documented():
    """Stage 6 ENRICH: historical_rank_overview endpoint."""
    # historical_rank_overview from dfs_labs_client.py
    assert abs(STAGE6_COST_PER_DOMAIN - 0.106) < 0.001, (
        f"Stage 6 cost drift: constant={STAGE6_COST_PER_DOMAIN}"
    )


def test_stage8_cost_matches_documented():
    """Stage 8 CONTACT: SERP fallback + waterfall must match historical total ~$0.023."""
    # verify_fills SERP fallback ($0.008) + scraper ($0.004) + ContactOut (~$0.011) = $0.023
    total = STAGE8_SERP_FALLBACK + STAGE8_WATERFALL_COST
    assert abs(total - 0.023) < 0.002, (
        f"Stage 8 cost drift: serp_fallback={STAGE8_SERP_FALLBACK} + waterfall={STAGE8_WATERFALL_COST} = {total}"
    )


def test_stage9_cost_matches_documented():
    """Stage 9 SOCIAL: BD LinkedIn DM + company profiles."""
    # ~$0.002 DM profile + $0.025 company profile = $0.027
    assert abs(STAGE9_COST_PER_DOMAIN - 0.027) < 0.001, (
        f"Stage 9 cost drift: constant={STAGE9_COST_PER_DOMAIN}"
    )
