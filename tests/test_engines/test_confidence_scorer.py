"""Tests for confidence_scorer — Directive #215, amended Directive #219"""
import pytest
from src.engines.confidence_scorer import (
    score_business_confidence,
    meets_enrichment_threshold,
    CONFIDENCE_FLOOR_TO_ENRICH,
)


def test_empty_signals_zero():
    assert score_business_confidence({}) == 0


def test_empty_signals_fails_threshold():
    assert meets_enrichment_threshold({}) is False


def test_gst_only():
    assert score_business_confidence({"gst_registered": True}) == 25


def test_gst_only_fails_threshold():
    # gst=25, threshold=35 → fails
    assert meets_enrichment_threshold({"gst_registered": True}) is False


def test_gst_plus_paid_ads_exactly_50():
    # gst=25 + paid=25 = 50 → passes threshold (35)
    signals = {"gst_registered": True, "dfs_paid_traffic_cost": 100.0}
    assert score_business_confidence(signals) == 50
    assert meets_enrichment_threshold(signals) is True


def test_gst_paid_organic():
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "dfs_organic_traffic": 1000.0,
    }
    assert score_business_confidence(signals) == 65


def test_gst_paid_reviews_10():
    # gst=25 + paid=25 + gmb(10>=5=+15, 10>=15? no) = 65
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "gmb_review_count": 10,
    }
    assert score_business_confidence(signals) == 65


def test_gst_paid_reviews_20_bonus():
    # gst=25 + paid=25 + gmb(20>=5=+15, 20>=15=+10, 20>=30? no) = 75
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "gmb_review_count": 20,
    }
    assert score_business_confidence(signals) == 75


def test_gst_paid_reviews_25_bonus():
    # gst=25 + paid=25 + gmb(25>=5=+15, 25>=15=+10, 25>=30? no) = 75
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "gmb_review_count": 25,
    }
    assert score_business_confidence(signals) == 75


def test_all_signals_capped_at_100():
    # Directive #218: ghost signals removed.
    # Directive #219: new gmb scoring. Max: 25+25+15+15+10+10+10=110 → capped at 100.
    # With gmb=25: 25+25+15+15+10+10 = 100 (25>=5=+15, 25>=15=+10, 25>=30? no)
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 500.0,
        "dfs_organic_traffic": 2000.0,
        "gmb_review_count": 25,
        "linkedin_employee_count": 10,
    }
    result = score_business_confidence(signals)
    assert result == 100  # 25+25+15+15+10+10 = 100, capped at 100


def test_no_gst_but_all_else():
    # Directive #218: ghost signals removed. Directive #219: new gmb scoring.
    # Without GST: paid=25+organic=15+gmb(25>=5=+15, 25>=15=+10)+linkedin=10 = 75
    signals = {
        "gst_registered": False,
        "dfs_paid_traffic_cost": 500.0,
        "dfs_organic_traffic": 2000.0,
        "gmb_review_count": 25,
        "linkedin_employee_count": 10,
    }
    result = score_business_confidence(signals)
    assert result == 75  # 0(no GST)+25+15+15+10+10 = 75


def test_none_values_no_exception():
    signals = {
        "gst_registered": None,
        "dfs_paid_traffic_cost": None,
        "dfs_organic_traffic": None,
        "gmb_review_count": None,
        "linkedin_employee_count": None,
        "domain_age_years": None,
    }
    result = score_business_confidence(signals)
    assert result == 0


def test_zero_values_no_points():
    signals = {
        "gst_registered": False,
        "dfs_paid_traffic_cost": 0,
        "dfs_organic_traffic": 0,
        "gmb_review_count": 0,
        "linkedin_employee_count": 0,
        "domain_age_years": 0,
    }
    assert score_business_confidence(signals) == 0


def test_missing_keys_no_exception():
    result = score_business_confidence({"gst_registered": True})
    assert result == 25


def test_meets_threshold_returns_bool():
    # gst=25+paid=25=50 → passes threshold 35
    result = meets_enrichment_threshold({"gst_registered": True, "dfs_paid_traffic_cost": 100})
    assert isinstance(result, bool)
    assert result is True


def test_threshold_constant():
    # Directive #219: lowered from 50 to 35
    assert CONFIDENCE_FLOOR_TO_ENRICH == 35


def test_reviews_below_5_no_points():
    # Directive #219: new threshold is >=5 reviews
    signals = {"gmb_review_count": 4}
    assert score_business_confidence(signals) == 0


def test_reviews_exactly_5_gets_15():
    # Directive #219: >=5 reviews now awards +15
    signals = {"gmb_review_count": 5}
    assert score_business_confidence(signals) == 15


def test_reviews_exactly_15_gets_25():
    # >=5=+15, >=15=+10 → 25
    signals = {"gmb_review_count": 15}
    assert score_business_confidence(signals) == 25


def test_reviews_exactly_30_gets_35():
    # >=5=+15, >=15=+10, >=30=+10 → 35
    signals = {"gmb_review_count": 30}
    assert score_business_confidence(signals) == 35


def test_employees_below_5_no_points():
    signals = {"linkedin_employee_count": 4}
    assert score_business_confidence(signals) == 0


def test_domain_age_below_2_no_points():
    signals = {"domain_age_years": 1.9}
    assert score_business_confidence(signals) == 0


def test_typical_au_lead_gst_plus_reviews():
    # Typical AU lead: gst=+25, gmb>=5=+15 → 40, passes threshold 35
    signals = {"gst_registered": True, "gmb_review_count": 5}
    score = score_business_confidence(signals)
    assert score == 40
    assert meets_enrichment_threshold(signals) is True
