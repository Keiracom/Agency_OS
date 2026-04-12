"""Tests for AffordabilityScorer — Directive #288."""
import pytest
from src.pipeline.affordability_scoring import AffordabilityScorer, AffordabilityResult


@pytest.fixture
def scorer():
    return AffordabilityScorer()


def test_sole_trader_always_rejected(scorer):
    enrichment = {
        "entity_type": "Individual/Sole Trader",
        "gst_registered": True,
        "website_cms": "wordpress",
    }
    result = scorer.score(enrichment)
    assert result.passed_gate is False
    assert "sole_trader" in str(result.signals)


def test_gst_false_always_rejected(scorer):
    enrichment = {
        "entity_type": "Company",
        "gst_registered": False,
    }
    result = scorer.score(enrichment)
    assert result.passed_gate is False


def test_high_band_scenario(scorer):
    enrichment = {
        "entity_type": "Company",
        "gst_registered": True,
        "is_running_ads": True,
        "ads_count": 8,
        "gmb_review_count": 55,
        "website_cms": "wordpress",
        "website_tracking_codes": ["ga4"],
        "website_team_names": ["Alice Smith", "Bob Jones", "Carol White"],
        "email_maturity": "PROFESSIONAL",
        "abn_matched": True,
    }
    result = scorer.score(enrichment)
    assert result.band in ("HIGH", "VERY_HIGH")
    assert result.passed_gate is True


def test_low_band_scenario(scorer):
    enrichment = {
        "entity_type": "Partnership",
        "gst_registered": True,
        "is_running_ads": False,
        "gmb_review_count": 2,
        "website_cms": None,
        "website_tracking_codes": [],
        "website_team_names": [],
        "email_maturity": "NONE",
        "abn_matched": True,  # reachable so not hard-gated
    }
    result = scorer.score(enrichment)
    assert result.passed_gate is False
    assert result.band == "LOW"


def test_gaps_populated_from_zero_signals(scorer):
    enrichment = {
        "entity_type": "Company",
        "gst_registered": True,
        "is_running_ads": False,
        "gmb_review_count": 3,
        "website_cms": None,
        "website_tracking_codes": [],
        "email_maturity": "NONE",
        "abn_matched": True,
    }
    result = scorer.score(enrichment)
    assert "Not running Google Ads" in result.gaps
    assert any("Google reviews" in g for g in result.gaps)


def test_no_ads_gap_in_gaps(scorer):
    enrichment = {
        "entity_type": "Company",
        "gst_registered": True,
        "is_running_ads": False,
        "gmb_review_count": 60,
        "website_cms": "wordpress",
        "website_tracking_codes": ["ga4", "gtm"],
        "website_team_names": ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"],
        "email_maturity": "PROFESSIONAL",
        "abn_matched": True,
    }
    result = scorer.score(enrichment)
    assert "Not running Google Ads" in result.gaps


def test_professional_email_adds_point(scorer):
    base = {
        "entity_type": "Company",
        "gst_registered": True,
        "is_running_ads": False,
        "gmb_review_count": 10,
        "website_cms": "wordpress",
        "website_tracking_codes": ["ga4"],
        "website_team_names": ["Alice"],
        "abn_matched": True,
    }
    professional = {**base, "email_maturity": "PROFESSIONAL"}
    none_email = {**base, "email_maturity": "NONE"}

    r_pro = scorer.score(professional)
    r_none = scorer.score(none_email)
    assert r_pro.raw_score == r_none.raw_score + 1


# --- Three-state GST model tests (#328.6) ---

def test_affordability_gst_unknown_not_hard_reject(scorer):
    """GST unknown (None) should NOT hard-reject at affordability gate."""
    enrichment = {
        "gst_registered": None,  # unknown
        "entity_type": "Australian Private Company",
        "website_cms": "wordpress",
        "abn_matched": True,
    }
    result = scorer.score(enrichment)
    assert result.passed_gate is True  # should NOT be rejected


def test_affordability_gst_false_hard_reject(scorer):
    """GST explicitly False = known not registered = hard reject."""
    enrichment = {
        "gst_registered": False,
        "entity_type": "Australian Private Company",
        "website_cms": "wordpress",
        "abn_matched": True,
    }
    result = scorer.score(enrichment)
    assert result.passed_gate is False


def test_affordability_gst_unknown_partial_signal(scorer):
    """GST unknown (None) should contribute 0.5 to signal, not 1 or 0."""
    enrichment = {
        "gst_registered": None,
        "entity_type": "Australian Private Company",
        "website_cms": "wordpress",
        "abn_matched": True,
    }
    result = scorer.score(enrichment)
    assert result.signals.get("gst_registered") == 0.5
