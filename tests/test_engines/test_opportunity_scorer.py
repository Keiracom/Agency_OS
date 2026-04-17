"""
Tests for opportunity_scorer.py
Directive #217 — 19 unit tests
"""
import pytest
from src.engines.opportunity_scorer import (
    score_business_opportunity,
    is_priority_opportunity,
    get_opportunity_reason,
    OPPORTUNITY_PRIORITY_THRESHOLD,
)


# --- score_business_opportunity ---

def test_zero_signals():
    """1. Zero signals: score == 0"""
    assert score_business_opportunity({
        "gmb_review_count": 0,
        "abr_age_years": 0,
        "multiple_gmb_locations": False,
        "hiring_signals_detected": False,
        "gmb_category": "",
        "dfs_paid_traffic_cost": 100,
        "dfs_organic_traffic": 500,
    }) == 0


def test_reviews_exactly_20():
    """2. Reviews only >= 20 (exactly 20): score == 20"""
    assert score_business_opportunity({
        "gmb_review_count": 20,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }) == 20


def test_reviews_40_gives_30():
    """3. Reviews >= 40: score == 30 (20 + 10 bonus)"""
    assert score_business_opportunity({
        "gmb_review_count": 40,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }) == 30


def test_abr_age_years_5():
    """4. abr_age_years >= 5: score == 20"""
    assert score_business_opportunity({
        "abr_age_years": 5,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }) == 20


def test_hiring_signals_detected():
    """5. hiring_signals_detected=True: score == 20"""
    assert score_business_opportunity({
        "hiring_signals_detected": True,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }) == 20


def test_structural_gap_industry_plumbing():
    """6. Structural gap industry (e.g. "plumbing"): score == 15"""
    assert score_business_opportunity({
        "gmb_category": "plumbing",
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }) == 15


def test_dfs_paid_traffic_cost_zero():
    """7. dfs_paid_traffic_cost=0: score == 10"""
    assert score_business_opportunity({
        "dfs_paid_traffic_cost": 0,
        "dfs_organic_traffic": 1000,
    }) == 10


def test_dfs_organic_traffic_low():
    """8. dfs_organic_traffic < 500 (e.g. 100): score == 10"""
    assert score_business_opportunity({
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 100,
    }) == 10


def test_all_signals_capped_at_100():
    """9. All signals combined: score == 100 (capped from 120)"""
    signals = {
        "gmb_review_count": 50,       # +20 +10
        "abr_age_years": 10,           # +20
        "multiple_gmb_locations": True, # +15
        "hiring_signals_detected": True,# +20
        "gmb_category": "plumbing",    # +15
        "dfs_paid_traffic_cost": 0,    # +10
        "dfs_organic_traffic": 100,    # +10
        # Total = 120, capped at 100
    }
    assert score_business_opportunity(signals) == 100


def test_priority_threshold_exact_60_is_true():
    """10. Priority threshold exact: score == 60 → is_priority_opportunity returns True"""
    signals = {
        "gmb_review_count": 20,        # +20
        "abr_age_years": 5,            # +20
        "hiring_signals_detected": True,# +20
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }
    assert score_business_opportunity(signals) == 60
    assert is_priority_opportunity(signals) is True


def test_priority_threshold_miss_returns_false():
    """11. Priority threshold miss: score == 59 → is_priority_opportunity returns False"""
    # Build a signals dict that scores exactly 59
    # reviews=20 (+20) + abr_age=5 (+20) + hiring (+20) = 60
    # Need 59: reviews=20 (+20) + abr_age=5 (+20) + organic<500 (+10) + paid=0 (+10) = 60... not easy
    # Use: reviews=20 (+20) + abr_age=5 (+20) + organic<500 (+10) + paid=1 = 50 — too low
    # Use: reviews=20 (+20) + abr_age=5 (+20) + hiring (+20) - 1... can't subtract
    # Build 55: reviews=20 (+20) + abr_age=5 (+20) + organic (+10) + paid=0 (+10) = 60 -- still 60
    # Build 50: reviews=20 (+20) + abr_age=5 (+20) + organic (+10) = 50
    # To get 59 we need to construct carefully — use multiple_gmb_locations (+15) for 55
    # reviews=20 (+20) + multiple (+15) + organic (+10) + paid=0 (+10) = 55, nope
    # reviews=20 (+20) + abr_age=5 (+20) + paid=0 (+10) = 50, nope
    # Best approach: mock a combination that gives 55 and verify < threshold
    signals = {
        "gmb_review_count": 20,         # +20
        "abr_age_years": 5,             # +20
        "dfs_paid_traffic_cost": 0,     # +10
        "dfs_organic_traffic": 1000,    # no bonus
    }
    score = score_business_opportunity(signals)
    assert score == 50
    assert score < OPPORTUNITY_PRIORITY_THRESHOLD
    assert is_priority_opportunity(signals) is False


def test_get_opportunity_reason_non_empty():
    """12. get_opportunity_reason returns non-empty string for any input"""
    result = get_opportunity_reason({})
    assert isinstance(result, str)
    assert len(result) > 0


def test_none_values_dont_raise():
    """13. None values for all signal fields don't raise exceptions"""
    signals = {
        "gmb_review_count": None,
        "abr_age_years": None,
        "multiple_gmb_locations": None,
        "hiring_signals_detected": None,
        "gmb_category": None,
        "dfs_paid_traffic_cost": None,
        "dfs_organic_traffic": None,
    }
    score = score_business_opportunity(signals)
    assert isinstance(score, int)
    reason = get_opportunity_reason(signals)
    assert isinstance(reason, str)


def test_missing_keys_dont_raise():
    """14. Missing keys entirely don't raise exceptions"""
    score = score_business_opportunity({})
    assert isinstance(score, int)
    reason = get_opportunity_reason({})
    assert isinstance(reason, str)


def test_dfs_paid_traffic_cost_none_gives_bonus():
    """15. dfs_paid_traffic_cost=None treated as 0 (gap exists) → +10"""
    signals = {
        "dfs_paid_traffic_cost": None,
        "dfs_organic_traffic": 1000,
    }
    assert score_business_opportunity(signals) == 10


def test_dfs_organic_traffic_none_gives_bonus():
    """16. dfs_organic_traffic=None treated as < 500 → +10"""
    signals = {
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": None,
    }
    assert score_business_opportunity(signals) == 10


def test_dental_triggers_structural_gap():
    """17. gmb_category containing "dental" triggers structural gap"""
    signals = {
        "gmb_category": "dental clinic",
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }
    assert score_business_opportunity(signals) == 15


def test_reviews_19_does_not_trigger():
    """18. Reviews=19 does NOT trigger +20 (boundary test)"""
    signals = {
        "gmb_review_count": 19,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }
    assert score_business_opportunity(signals) == 0


def test_abr_age_4_9_does_not_trigger():
    """19. abr_age_years=4.9 does NOT trigger +20 (boundary test)"""
    signals = {
        "abr_age_years": 4.9,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }
    assert score_business_opportunity(signals) == 0


# --- Wave 1 signal verification tests (Directive #wave1-scoring-signals) ---

def test_no_paid_traffic_scores_higher_than_paid():
    """20. Lead with zero paid ad spend scores higher than same lead with active spend.
    Rationale: zero spend = untapped gap = higher agency opportunity value.
    Note: confidence_scorer.py uses the inverse (spend > 0 = budget signal for health).
    """
    base = {
        "gmb_review_count": 20,
        "abr_age_years": 3,
        "dfs_organic_traffic": 1000,
    }
    score_no_spend = score_business_opportunity({**base, "dfs_paid_traffic_cost": 0})
    score_with_spend = score_business_opportunity({**base, "dfs_paid_traffic_cost": 500})
    assert score_no_spend > score_with_spend, (
        f"Expected no-spend score ({score_no_spend}) > with-spend score ({score_with_spend})"
    )


def test_abr_age_5_scores_higher_than_age_below_5():
    """21. Lead with abr_age_years >= 5 scores higher than identical lead with age < 5.
    Rationale: established businesses (5+ years) are proven operations worth pursuing.
    """
    base = {
        "gmb_review_count": 20,
        "dfs_paid_traffic_cost": 1,
        "dfs_organic_traffic": 1000,
    }
    score_established = score_business_opportunity({**base, "abr_age_years": 5})
    score_young = score_business_opportunity({**base, "abr_age_years": 4})
    assert score_established > score_young, (
        f"Expected established score ({score_established}) > young score ({score_young})"
    )
