"""Stage 11 — CARD: Card assembly and binary lead pool classification.

Binary: complete card -> lead pool. Incomplete -> BU only.
No Ready/Near-ready/Watchlist classification. 4-dimension scores handle prioritisation.

Pipeline F v2.1. Ratified: 2026-04-15.
"""
from __future__ import annotations


def assemble_card(
    domain: str,
    stage2_verify: dict,
    stage3_identity: dict,
    stage4_signals: dict,
    stage5_scores: dict,
    stage7_analyse: dict,
    stage8_contacts: dict,
    stage9_social: dict | None = None,
    stage10_vr_msg: dict | None = None,
    stage6_enrich: dict | None = None,
) -> dict:
    """Assemble final customer card from all pipeline stage outputs.

    Returns:
        {
            "domain": str,
            "lead_pool_eligible": bool,
            "missing_fields": list[str],
            "card": {all accumulated data},
        }
    """
    dm = stage3_identity.get("dm_candidate") or {}
    contacts = stage8_contacts or {}
    email_data = contacts.get("email", {})

    # Check completeness
    missing = []
    if not dm.get("name"):
        missing.append("dm_name")
    if not email_data.get("email"):
        missing.append("email")
    if not stage5_scores:
        missing.append("scores")
    if not stage7_analyse:
        missing.append("vr_report")

    lead_pool_eligible = len(missing) == 0

    card = {
        "domain": domain,
        "lead_pool_eligible": lead_pool_eligible,
        "missing_fields": missing,
        # Business identity (Stage 3)
        "business_name": stage3_identity.get("business_name"),
        "location": stage3_identity.get("location"),
        "industry_category": stage3_identity.get("industry_category"),
        "entity_type_hint": stage3_identity.get("entity_type_hint"),
        "staff_estimate_band": stage3_identity.get("staff_estimate_band"),
        "primary_phone": stage3_identity.get("primary_phone"),
        "primary_email": stage3_identity.get("primary_email"),
        # DM (Stage 3 + verification)
        "dm_candidate": dm,
        "dm_verified": stage3_identity.get("_dm_verified", False),
        # Verification data (Stage 2)
        "abn": stage2_verify.get("serp_abn"),
        "company_linkedin_url": stage2_verify.get("serp_company_linkedin"),
        "facebook_url": stage2_verify.get("serp_facebook_url"),
        # Scores (Stage 5)
        "scores": stage5_scores,
        # Contacts (Stage 8)
        "contacts": contacts,
        # Signals summary (Stage 4 — key metrics only, not full bundle)
        "signals_summary": _extract_signal_summary(stage4_signals),
        # VR + Outreach (Stage 7 + 10)
        "vulnerability_report": (stage10_vr_msg or {}).get("vr_report")
        or stage7_analyse.get("vulnerability_report"),
        "outreach": (stage10_vr_msg or {}).get("outreach"),
        "intent_band": stage7_analyse.get("intent_band_final"),
        # Social (Stage 9)
        "social": stage9_social,
        # Enrichment (Stage 6)
        "historical_rank": (stage6_enrich or {}).get("historical_rank"),
    }

    return card


def _extract_signal_summary(stage4_signals: dict) -> dict:
    """Extract key metrics from full signal bundle for card display."""
    ro = stage4_signals.get("rank_overview") or {}
    gmb = stage4_signals.get("gmb") or {}
    ads = stage4_signals.get("ads_domain") or {}
    return {
        "organic_etv": ro.get("dfs_organic_etv"),
        "organic_keywords": ro.get("dfs_organic_keywords"),
        "paid_keywords": ro.get("dfs_paid_keywords"),
        "page2_keywords": ro.get("dfs_organic_pos_11_20"),
        "gmb_rating": gmb.get("gmb_rating"),
        "gmb_reviews": gmb.get("gmb_review_count"),
        "is_running_ads": ads.get("is_running_ads"),
        "indexed_pages": stage4_signals.get("indexed_pages"),
        "technologies": stage4_signals.get("technologies", [])[:5],
    }
