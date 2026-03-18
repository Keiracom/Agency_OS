"""Tests for confidence_scorer — Directive #215"""
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
    assert meets_enrichment_threshold({"gst_registered": True}) is False


def test_gst_plus_paid_ads_exactly_50():
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
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "gmb_review_count": 10,
    }
    assert score_business_confidence(signals) == 60


def test_gst_paid_reviews_20_bonus():
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "gmb_review_count": 20,
    }
    assert score_business_confidence(signals) == 65


def test_gst_paid_reviews_25_bonus():
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 100.0,
        "gmb_review_count": 25,
    }
    assert score_business_confidence(signals) == 65


def test_all_signals_capped_at_100():
    # Directive #218: job_listings_active (+15) and domain_age_years (+10) removed as ghost signals.
    # Max score is now 90 (25+25+15+10+5+10). Cap at 100 still applies but max is 90.
    signals = {
        "gst_registered": True,
        "dfs_paid_traffic_cost": 500.0,
        "dfs_organic_traffic": 2000.0,
        "gmb_review_count": 25,
        "linkedin_employee_count": 10,
    }
    result = score_business_confidence(signals)
    assert result == 90  # 25+25+15+10+5+10 = 90 (capped at 100; new max is 90)


def test_no_gst_but_all_else():
    # Directive #218: ghost signals removed. Without GST: 25+15+10+5+10 = 65
    signals = {
        "gst_registered": False,
        "dfs_paid_traffic_cost": 500.0,
        "dfs_organic_traffic": 2000.0,
        "gmb_review_count": 25,
        "linkedin_employee_count": 10,
    }
    result = score_business_confidence(signals)
    assert result == 65  # 0(no GST)+25+15+10+5+10 = 65


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
    result = meets_enrichment_threshold({"gst_registered": True, "dfs_paid_traffic_cost": 100})
    assert isinstance(result, bool)
    assert result is True


def test_threshold_constant():
    assert CONFIDENCE_FLOOR_TO_ENRICH == 50


def test_reviews_below_10_no_points():
    signals = {"gmb_review_count": 9}
    assert score_business_confidence(signals) == 0


def test_employees_below_5_no_points():
    signals = {"linkedin_employee_count": 4}
    assert score_business_confidence(signals) == 0


def test_domain_age_below_2_no_points():
    signals = {"domain_age_years": 1.9}
    assert score_business_confidence(signals) == 0
