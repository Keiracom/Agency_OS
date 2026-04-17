"""
Contract: src/pipeline/affordability_scoring.py
Purpose: Composite affordability scorer — combines weak signals into a revenue band estimate.
Layer: 2 - pipeline
Imports: src.pipeline.free_enrichment (EmailMaturity enum)
Consumers: src/pipeline/pipeline_orchestrator.py
Directive #288.
"""
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
BAND_LOW       = (0,  4)   # reject
BAND_MEDIUM    = (5,  8)   # pass — small but viable
BAND_HIGH      = (9,  13)  # pass — strong prospect
BAND_VERY_HIGH = (14, 20)  # pass — premium prospect

# ---------------------------------------------------------------------------
# Gap messages (for Haiku outreach context)
# ---------------------------------------------------------------------------
GAP_MESSAGES = {
    "no_ads":       "Not running Google Ads",
    "low_reviews":  "Only {count} Google reviews",  # format with actual count
    "basic_cms":    "Basic website platform",
    "no_tracking":  "No analytics installed",
    "no_booking":   "No online booking system",
    "webmail":      "Using Gmail/Outlook, not professional email",
    "no_website":   "No website found",
    "sole_trader":  "Sole trader — too small",
    "no_gst":       "Not GST registered",
    "public_or_govt": "Public company or government entity",
}


@dataclass
class AffordabilityResult:
    raw_score: int
    band: str           # LOW | MEDIUM | HIGH | VERY_HIGH
    signals: dict       # signal_name -> points awarded
    gaps: list          # plain English gap strings for Haiku
    passed_gate: bool


class AffordabilityScorer:
    """
    Scores a domain on composite affordability using free enrichment signals.
    Returns AffordabilityResult with band, score, signals dict, and gaps list.
    """

    def score(self, enrichment: dict) -> AffordabilityResult:
        signals = {}
        gaps = []

        # --- Hard gates ---
        entity_type = (enrichment.get("entity_type") or "").lower()
        gst = enrichment.get("gst_registered")
        reachable = enrichment.get("website_cms") is not None or enrichment.get("abn_matched")

        if "sole trader" in entity_type or "individual" in entity_type:
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "sole_trader"},
                gaps=[GAP_MESSAGES["sole_trader"]], passed_gate=False
            )

        # Public companies and government entities — never Agency OS clients
        # Substring match (consistent with sole_trader gate above) — ABN returns
        # title-case like "Australian Public Company" which .lower() → "australian public company"
        _NON_SMB_TYPES = ("public company", "state government", "commonwealth government", "local government")
        if any(t in entity_type for t in _NON_SMB_TYPES):
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "public_or_govt"},
                gaps=[GAP_MESSAGES["public_or_govt"]], passed_gate=False
            )

        # GST gate: only reject when explicitly NOT registered.
        # GST unknown (None) is a soft flag, not a hard reject. (#328.6)
        if gst is False:  # explicitly False = known not registered
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "no_gst"},
                gaps=[GAP_MESSAGES["no_gst"]], passed_gate=False
            )
        # gst is None = unknown, continue to scoring (soft flag below)

        if not reachable:
            return AffordabilityResult(
                raw_score=0, band="LOW", signals={"hard_gate": "unreachable"},
                gaps=[GAP_MESSAGES["no_website"]], passed_gate=False
            )

        # --- Entity type ---
        et = (enrichment.get("entity_type") or "").lower()
        if "trust" in et:
            signals["entity_type"] = 3
        elif "company" in et or "pty" in et or "ltd" in et:
            signals["entity_type"] = 2
        elif "partner" in et:
            signals["entity_type"] = 1
        else:
            signals["entity_type"] = 0

        # --- GST registered — three-state scoring (#328.6) ---
        if gst is True:
            signals["gst_registered"] = 1
        elif gst is None:
            signals["gst_registered"] = 0.5  # unknown — partial credit
        else:
            signals["gst_registered"] = 0

        # --- Google Ads active ---
        ads_active = enrichment.get("is_running_ads") or False
        ads_count = enrichment.get("ads_count") or 0
        if ads_active and ads_count > 5:
            signals["google_ads"] = 3
        elif ads_active:
            signals["google_ads"] = 2
        else:
            signals["google_ads"] = 0
            gaps.append(GAP_MESSAGES["no_ads"])

        # --- Review count ---
        review_count = enrichment.get("gmb_review_count") or 0
        if review_count >= 101:
            signals["review_count"] = 4
        elif review_count >= 51:
            signals["review_count"] = 3
        elif review_count >= 21:
            signals["review_count"] = 2
        elif review_count >= 6:
            signals["review_count"] = 1
        else:
            signals["review_count"] = 0
            gaps.append(GAP_MESSAGES["low_reviews"].format(count=review_count))

        # --- Website sophistication (max 5) ---
        website_score = 0
        cms = (enrichment.get("website_cms") or "").lower()
        professional_cms = ["wordpress", "squarespace", "shopify", "webflow", "wix",
                            "custom", "react", "next", "nuxt", "gatsby"]
        if any(c in cms for c in professional_cms):
            website_score += 1
        else:
            gaps.append(GAP_MESSAGES["basic_cms"])

        tracking = enrichment.get("website_tracking_codes") or []
        if tracking:
            website_score += 1
        else:
            gaps.append(GAP_MESSAGES["no_tracking"])

        # Booking system — look for booking signals in tech stack or tracking
        tech = enrichment.get("website_tech_stack") or []
        booking_signals = ["calendly", "acuity", "mindbody", "timely", "bookeo",
                           "appointy", "fresha", "shortcuts", "booking"]
        has_booking = any(
            b in (enrichment.get("website_cms") or "").lower() or
            any(b in t.lower() for t in tech) or
            any(b in t.lower() for t in tracking)
            for b in booking_signals
        )
        if has_booking:
            website_score += 1
        else:
            gaps.append(GAP_MESSAGES["no_booking"])

        # SSL — if we scraped it, it had SSL (spider follows https)
        if enrichment.get("website_ssl") or enrichment.get("website_cms"):
            website_score += 1

        # Multiple pages
        pages = enrichment.get("website_page_links") or []
        if len(pages) > 1 or enrichment.get("website_cms"):
            website_score += 1

        signals["website"] = min(website_score, 5)

        # --- Employee signals ---
        team_names = enrichment.get("website_team_names") or []
        n = len(team_names)
        if n >= 6:
            signals["employees"] = 3
        elif n >= 3:
            signals["employees"] = 2
        elif n >= 1:
            signals["employees"] = 1
        else:
            signals["employees"] = 0

        # --- Email maturity ---
        from src.pipeline.free_enrichment import EmailMaturity
        em = enrichment.get("email_maturity")
        if em == EmailMaturity.PROFESSIONAL or em == "PROFESSIONAL":
            signals["email_maturity"] = 1
        else:
            signals["email_maturity"] = 0
            if em == EmailMaturity.WEBMAIL or em == "WEBMAIL":
                gaps.append(GAP_MESSAGES["webmail"])

        # --- Total ---
        raw_score = sum(signals.values())

        # Band
        if raw_score >= 14:
            band = "VERY_HIGH"
        elif raw_score >= 9:
            band = "HIGH"
        elif raw_score >= 5:
            band = "MEDIUM"
        else:
            band = "LOW"

        passed_gate = band != "LOW"

        logger.info(
            "affordability_scored domain_score=%d band=%s passed=%s",
            raw_score, band, passed_gate,
        )

        return AffordabilityResult(
            raw_score=raw_score,
            band=band,
            signals=signals,
            gaps=gaps,
            passed_gate=passed_gate,
        )
