"""Tests for ProspectScorer — Directive #291."""
import pytest
from src.pipeline.prospect_scorer import ProspectScorer, AffordabilityResult, IntentResult


def _scorer():
    return ProspectScorer()


class TestAffordabilityGates:
    def test_sole_trader_rejected(self):
        s = _scorer()
        r = s.score_affordability({"entity_type": "Individual/Sole Trader",
                                   "gst_registered": True, "website_cms": "wordpress"})
        assert r.passed_gate is False
        assert r.reject_reason == "sole_trader"

    def test_no_gst_rejected(self):
        s = _scorer()
        r = s.score_affordability({"entity_type": "Australian Private Company",
                                   "gst_registered": False, "website_cms": "wordpress"})
        assert r.passed_gate is False
        assert r.reject_reason == "no_gst"

    def test_unreachable_rejected(self):
        s = _scorer()
        r = s.score_affordability({"entity_type": "Australian Private Company",
                                   "gst_registered": True, "website_cms": None,
                                   "abn_matched": False})
        assert r.passed_gate is False
        assert r.reject_reason == "unreachable"

    def test_company_gst_professional_email_good_website_passes(self):
        s = _scorer()
        r = s.score_affordability({
            "entity_type": "Australian Private Company",
            "gst_registered": True,
            "website_cms": "wordpress",
            "email_maturity": "professional",
        })
        assert r.passed_gate is True
        assert r.band in ("MEDIUM", "HIGH", "VERY_HIGH")

    def test_trust_higher_score_than_company(self):
        s = _scorer()
        r_trust = s.score_affordability({"entity_type": "Trust", "gst_registered": True,
                                         "website_cms": "wordpress"})
        r_co    = s.score_affordability({"entity_type": "Australian Private Company",
                                         "gst_registered": True, "website_cms": "wordpress"})
        assert r_trust.raw_score > r_co.raw_score


class TestIntentFree:
    def test_zero_signals_not_trying(self):
        s = _scorer()
        r = s.score_intent_free({})
        assert r.band == "NOT_TRYING"
        assert r.passed_free_gate is False

    def test_website_no_analytics_gets_signal(self):
        s = _scorer()
        r = s.score_intent_free({
            "website_cms": "wordpress",
            "website_tracking_codes": [],
        })
        assert r.signals.get("website_no_analytics", 0) > 0
        assert any("analytics" in e.lower() for e in r.evidence)

    def test_ads_tag_no_conversion_high_signal(self):
        s = _scorer()
        r = s.score_intent_free({
            "has_google_ads_tag": True,
            "website_tracking_codes": [],
        })
        assert r.signals.get("ads_tag_no_conversion", 0) > 0
        assert any("conversion" in e.lower() for e in r.evidence)

    def test_meta_pixel_detected(self):
        s = _scorer()
        r = s.score_intent_free({"has_meta_pixel": True})
        assert r.signals.get("meta_pixel", 0) > 0

    def test_trying_band_passes_free_gate(self):
        s = _scorer()
        r = s.score_intent_free({
            "website_cms": "wordpress",
            "website_tracking_codes": [],
            "has_google_ads_tag": True,
        })
        assert r.passed_free_gate is True
        assert r.band in ("TRYING", "STRUGGLING", "DABBLING")

    def test_evidence_pairs_effort_with_gap(self):
        s = _scorer()
        r = s.score_intent_free({
            "website_cms": "wordpress",
            "website_tracking_codes": [],
            "has_google_ads_tag": True,
        })
        assert len(r.evidence) >= 1
        for ev in r.evidence:
            assert isinstance(ev, str) and len(ev) > 10


class TestIntentFull:
    def test_adds_gads_signal_when_running(self):
        s = _scorer()
        r = s.score_intent_full(
            enrichment={"website_cms": "wordpress", "website_tracking_codes": []},
            ads_data={"is_running_ads": True, "ad_count": 5},
        )
        assert r.signals.get("running_gads", 0) > 0

    def test_no_ads_data_does_not_crash(self):
        s = _scorer()
        r = s.score_intent_full(enrichment={"website_cms": "wordpress"}, ads_data=None)
        assert isinstance(r.raw_score, int)

    def test_gmb_established_signal(self):
        s = _scorer()
        r = s.score_intent_full(
            enrichment={},
            gmb_data={"gmb_review_count": 25, "gmb_rating": 4.5},
        )
        assert r.signals.get("gmb_established", 0) > 0
