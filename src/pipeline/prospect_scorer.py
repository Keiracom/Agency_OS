"""
Contract: src/pipeline/prospect_scorer.py
Purpose: Two-dimension prospect scoring — Affordability (can they pay) +
         Intent (will they buy). Replaces AffordabilityScorer as the primary
         scorer in PipelineOrchestrator.
Layer: pipeline
Directive: #291

PROPRIETARY: Signal weights are defined as constants only. Do not add
inline comments explaining what scores mean. The algorithm is not for
public disclosure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Affordability constants ──────────────────────────────────────────────────
_A_GATE_MIN = 3          # min score to pass affordability gate
_A_BAND_MEDIUM = 3
_A_BAND_HIGH = 6
_A_BAND_VERY_HIGH = 9

# Affordability signal weights
_AW_ENTITY_TRUST    = 3
_AW_ENTITY_COMPANY  = 2
_AW_ENTITY_PARTNER  = 1
_AW_GST             = 1
_AW_PROF_EMAIL      = 1
_AW_CMS             = 1
_AW_SSL             = 1
_AW_PAGES           = 1

# ── Intent constants ─────────────────────────────────────────────────────────
_I_GATE_FREE = "NOT_TRYING"   # band that skips paid enrichment
_I_BAND_DABBLING    = 3
_I_BAND_TRYING      = 5
_I_BAND_STRUGGLING  = 8

# Intent free-pass signal weights
_IW_WEBSITE_NO_ANALYTICS   = 2
_IW_ADS_TAG_NO_CONVERSION  = 3
_IW_SOCIAL_LINKS           = 1
_IW_BOOKING_NO_ANALYTICS   = 2
_IW_STALE_CMS              = 1
_IW_META_PIXEL             = 1

# Intent paid-supplement signal weights
_IW_RUNNING_GADS           = 2
_IW_RUNNING_META_ADS       = 1
_IW_GMB_LOW_RESPONSE       = 2
_IW_GMB_ESTABLISHED        = 1


@dataclass
class AffordabilityResult:
    raw_score: int
    band: str          # LOW | MEDIUM | HIGH | VERY_HIGH
    signals: dict
    gaps: list
    passed_gate: bool
    reject_reason: str | None = None


@dataclass
class IntentResult:
    raw_score: int
    band: str          # NOT_TRYING | DABBLING | TRYING | STRUGGLING
    signals: dict
    evidence: list     # plain-English paired statements for Haiku
    passed_free_gate: bool  # False if NOT_TRYING → skip paid enrichment


@dataclass
class ProspectScore:
    affordability: AffordabilityResult
    intent: IntentResult
    is_running_ads: bool = False
    gmb_review_count: int = 0
    gmb_rating: float | None = None


class ProspectScorer:
    """
    Two-dimension prospect scoring: Affordability + Intent.

    Usage:
        scorer = ProspectScorer()

        # Gate 1 — affordability (hard gates: sole trader, no GST, unreachable)
        afford = scorer.score_affordability(enrichment)
        if not afford.passed_gate:
            continue

        # Gate 2 — intent free (free signals from Spider HTML)
        intent_free = scorer.score_intent_free(enrichment)
        if not intent_free.passed_free_gate:
            continue   # skip paid enrichment

        # After paid enrichment:
        intent_full = scorer.score_intent_full(enrichment, ads_data, gmb_data)
    """

    def score_affordability(self, enrichment: dict) -> AffordabilityResult:
        """
        Score affordability from free enrichment signals.
        Hard gates reject immediately (sole trader, no GST, unreachable).
        """
        signals: dict[str, int] = {}
        gaps: list[str] = []

        entity_type = (enrichment.get("entity_type") or "").lower()
        gst = enrichment.get("gst_registered")
        has_web = (
            enrichment.get("website_cms") is not None
            or enrichment.get("abn_matched")
        )

        # Hard gates
        if "sole trader" in entity_type or "individual" in entity_type:
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "sole_trader"},
                gaps=["Business is a sole trader — not a viable agency prospect"],
                passed_gate=False, reject_reason="sole_trader",
            )

        if gst is False:
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "no_gst"},
                gaps=["Not GST registered — revenue likely below $75k threshold"],
                passed_gate=False, reject_reason="no_gst",
            )

        if not has_web:
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "unreachable"},
                gaps=["No website or ABN match — business not contactable"],
                passed_gate=False, reject_reason="unreachable",
            )

        # Entity type
        et = entity_type
        if "trust" in et:
            signals["entity_type"] = _AW_ENTITY_TRUST
        elif "company" in et or "pty" in et or "ltd" in et:
            signals["entity_type"] = _AW_ENTITY_COMPANY
        elif "partner" in et:
            signals["entity_type"] = _AW_ENTITY_PARTNER
        else:
            signals["entity_type"] = 0
            gaps.append("Entity type unclear — cannot confirm business structure")

        # GST
        signals["gst_registered"] = _AW_GST if gst else 0

        # Professional email
        email_maturity = (enrichment.get("email_maturity") or enrichment.get("dns_email_maturity") or "").lower()
        if email_maturity == "professional":
            signals["professional_email"] = _AW_PROF_EMAIL
        else:
            signals["professional_email"] = 0
            gaps.append("No professional email setup detected")

        # Website investment
        cms = (enrichment.get("website_cms") or "").lower()
        professional_cms = ["wordpress", "squarespace", "shopify", "webflow", "wix",
                            "custom", "react", "next", "nuxt", "gatsby"]
        if any(c in cms for c in professional_cms):
            signals["website_cms"] = _AW_CMS
        else:
            signals["website_cms"] = 0

        if enrichment.get("website_cms"):  # if we scraped it, SSL likely present
            signals["website_ssl"] = _AW_SSL
        else:
            signals["website_ssl"] = 0

        pages = enrichment.get("website_page_links") or []
        signals["website_pages"] = _AW_PAGES if (len(pages) > 1 or enrichment.get("website_cms")) else 0

        raw = sum(signals.values())

        if raw >= _A_BAND_VERY_HIGH:
            band = "VERY_HIGH"
        elif raw >= _A_BAND_HIGH:
            band = "HIGH"
        elif raw >= _A_BAND_MEDIUM:
            band = "MEDIUM"
        else:
            band = "LOW"

        return AffordabilityResult(
            raw_score=raw,
            band=band,
            signals=signals,
            gaps=gaps,
            passed_gate=raw >= _A_GATE_MIN,
        )

    def score_intent_free(self, enrichment: dict) -> IntentResult:
        """
        Score intent from free Spider-scraped signals only.
        NOT_TRYING band → skip paid enrichment.
        """
        signals: dict[str, int] = {}
        evidence: list[str] = []

        tracking = enrichment.get("website_tracking_codes") or []
        tech     = enrichment.get("website_tech_stack") or []
        cms      = (enrichment.get("website_cms") or "").lower()

        tracking_lower = [t.lower() for t in tracking]
        tech_lower     = [t.lower() for t in tech]

        has_analytics = any(
            k in t for t in tracking_lower + tech_lower
            for k in ("ga4", "gtm", "google-analytics", "analytics", "hotjar", "clarity")
        )
        has_ads_tag     = enrichment.get("has_google_ads_tag") or False
        has_meta_pixel  = enrichment.get("has_meta_pixel") or False
        has_conversion  = any("aw-" in t or "conversion" in t for t in tracking_lower)
        has_booking     = any(
            b in cms or any(b in t for t in tech_lower + tracking_lower)
            for b in ("calendly", "acuity", "mindbody", "timely", "bookeo",
                      "appointy", "fresha", "shortcuts", "booking")
        )
        has_website = bool(enrichment.get("website_cms") or enrichment.get("title"))
        has_social  = bool(enrichment.get("website_team_names"))  # proxy for social links

        # Website with no analytics
        if has_website and not has_analytics:
            signals["website_no_analytics"] = _IW_WEBSITE_NO_ANALYTICS
            evidence.append(
                f"Has a {'professional ' + cms if cms else 'website'} but no analytics installed"
            )

        # Ads tag without conversion tracking
        if has_ads_tag and not has_conversion:
            signals["ads_tag_no_conversion"] = _IW_ADS_TAG_NO_CONVERSION
            evidence.append(
                "Running Google Ads but missing conversion tracking — wasting budget"
            )
        elif has_ads_tag and has_conversion:
            signals["ads_tag_no_conversion"] = 0

        # Meta Pixel present (marketing effort signal)
        if has_meta_pixel:
            signals["meta_pixel"] = _IW_META_PIXEL
            evidence.append("Has Meta Pixel installed — running social media marketing")

        # Social links (effort signal)
        if has_social:
            signals["social_links"] = _IW_SOCIAL_LINKS

        # Booking system without analytics
        if has_booking and not has_analytics:
            signals["booking_no_analytics"] = _IW_BOOKING_NO_ANALYTICS
            evidence.append(
                "Has online booking but can't measure which channels drive bookings"
            )

        # Professional CMS with stale/thin content signal
        if cms in ("wordpress", "squarespace", "webflow", "wix"):
            signals["stale_cms"] = _IW_STALE_CMS

        raw = sum(signals.values())

        if raw >= _I_BAND_STRUGGLING:
            band = "STRUGGLING"
        elif raw >= _I_BAND_TRYING:
            band = "TRYING"
        elif raw >= _I_BAND_DABBLING:
            band = "DABBLING"
        else:
            band = "NOT_TRYING"

        return IntentResult(
            raw_score=raw,
            band=band,
            signals=signals,
            evidence=evidence,
            passed_free_gate=(band != _I_GATE_FREE),
        )

    def score_intent_full(
        self,
        enrichment: dict,
        ads_data: dict | None = None,
        gmb_data: dict | None = None,
    ) -> IntentResult:
        """
        Full intent score: free signals + paid enrichment (DFS Ads Search + GMB).
        Call after score_intent_free passes.
        """
        # Start from free score
        base = self.score_intent_free(enrichment)
        signals = dict(base.signals)
        evidence = list(base.evidence)

        # Paid: Google Ads (from DFS Ads Search)
        if ads_data:
            if ads_data.get("is_running_ads"):
                ad_count = ads_data.get("ad_count", 0)
                signals["running_gads"] = _IW_RUNNING_GADS
                evidence.append(
                    f"Currently running {ad_count} Google Ads but no conversion tracking in place"
                    if not enrichment.get("has_google_ads_tag")
                    else f"Active on Google Ads with {ad_count} creatives"
                )

        # Paid: GMB reviews
        if gmb_data:
            review_count = gmb_data.get("gmb_review_count") or 0
            if review_count > 20:
                signals["gmb_established"] = _IW_GMB_ESTABLISHED
                evidence.append(
                    f"Has {review_count} Google reviews — established local presence"
                )

        raw = sum(signals.values())

        if raw >= _I_BAND_STRUGGLING:
            band = "STRUGGLING"
        elif raw >= _I_BAND_TRYING:
            band = "TRYING"
        elif raw >= _I_BAND_DABBLING:
            band = "DABBLING"
        else:
            band = "NOT_TRYING"

        return IntentResult(
            raw_score=raw,
            band=band,
            signals=signals,
            evidence=evidence,
            passed_free_gate=(band != _I_GATE_FREE),
        )
