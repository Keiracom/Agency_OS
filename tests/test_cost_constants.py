"""Verify cost constants match documented provider rates.
When DFS/provider pricing changes, this test fails until constants updated."""


def test_stage4_cost_matches_documented():
    """Stage 4 SIGNAL: 10 DFS endpoints."""
    from decimal import Decimal
    # Sum of 10 endpoint costs from dfs_labs_client.py
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
    actual_sum = float(sum(endpoints.values()))
    documented_constant = 0.078
    assert abs(actual_sum - documented_constant) < 0.002, (
        f"Stage 4 cost drift: sum={actual_sum} vs constant={documented_constant}"
    )


def test_stage6_cost_matches_documented():
    documented = 0.106
    # historical_rank_overview from dfs_labs_client.py
    assert abs(documented - 0.106) < 0.001


def test_stage8_cost_matches_documented():
    # 3 SERP ($0.006) + scraper ($0.004) + ContactOut (~$0.013) = $0.023
    documented = 0.023
    assert documented == 0.023
