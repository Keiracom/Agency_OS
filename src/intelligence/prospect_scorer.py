"""Stage 5 — SCORE: Deterministic formula scoring with category-relative ETV.

Replaces Gemini-guessed scoring. Uses DFS signals + GMB data from Stage 4.
ETV percentile is computed relative to the prospect's category window.

Pipeline F v2.1. Ratified: 2026-04-15.
"""

from __future__ import annotations

import logging

from src.config.category_etv_windows import CATEGORY_ETV_WINDOWS

logger = logging.getLogger(__name__)

# Category code lookup by name (reverse map for signal bundle matching)
_CATEGORY_NAME_TO_CODE: dict[str, int] = {
    w["category_name"].lower(): code for code, w in CATEGORY_ETV_WINDOWS.items()
}


def _find_category_code(category_name: str) -> int | None:
    """Find category code by fuzzy name match."""
    if not category_name:
        return None
    cat_lower = category_name.lower()
    # Exact match
    if cat_lower in _CATEGORY_NAME_TO_CODE:
        return _CATEGORY_NAME_TO_CODE[cat_lower]
    # Substring match
    for name, code in _CATEGORY_NAME_TO_CODE.items():
        if cat_lower in name or name in cat_lower:
            return code
    return None


def _etv_percentile(etv: float, category_code: int | None) -> float:
    """Compute ETV percentile within category window. Returns 0.0-1.0."""
    if category_code is None or category_code not in CATEGORY_ETV_WINDOWS:
        # No calibrated window — use raw heuristic
        if etv > 50000:
            return 0.75
        if etv > 5000:
            return 0.5
        if etv > 500:
            return 0.25
        return 0.1
    w = CATEGORY_ETV_WINDOWS[category_code]
    etv_min = w["etv_min"]
    etv_max = w["etv_max"]
    if etv_max <= etv_min:
        return 0.5
    return max(0.0, min(1.0, (etv - etv_min) / (etv_max - etv_min)))


def score_prospect(
    signal_bundle: dict,
    f3a_output: dict,
    category_name: str | None = None,
) -> dict:
    """Score a prospect using deterministic formula with category-relative ETV.

    Args:
        signal_bundle: Stage 4 SIGNAL output (rank_overview, gmb, backlinks, ads, etc.)
        f3a_output: Stage 3 IDENTIFY output (business identity, DM, enterprise flag).
            NOTE: param name retained for caller compatibility. Rename deferred to Directive C when filenames change.
        category_name: Discovery category for ETV window lookup.

    Returns:
        {
            "budget_score": 0-25,
            "pain_score": 0-25,
            "reachability_score": 0-25,
            "fit_score": 0-25,
            "composite_score": 0-100,
            "etv_percentile": 0.0-1.0,
            "passed_gate": bool (composite >= 30),
            "is_viable_prospect": bool,
            "viability_reason": str | None,
            "score_breakdown": dict,
        }
    """
    ro = signal_bundle.get("rank_overview") or {}
    gmb = signal_bundle.get("gmb") or {}
    ads_domain = signal_bundle.get("ads_domain") or {}
    indexed = signal_bundle.get("indexed_pages") or 0

    organic_etv = ro.get("dfs_organic_etv") or 0
    organic_kw = ro.get("dfs_organic_keywords") or 0
    paid_kw = ro.get("dfs_paid_keywords") or 0
    gmb_rating = gmb.get("gmb_rating") or 0
    gmb_reviews = gmb.get("gmb_review_count") or 0
    is_running_ads = ads_domain.get("is_running_ads") or False
    cat_code = _find_category_code(category_name or "")
    etv_pct = _etv_percentile(organic_etv, cat_code)

    breakdown = {}

    # ── BUDGET SCORE (0-25) — real affordability signals ───────────
    budget = 0
    tech = signal_bundle.get("technologies") or []
    tech_lower = {t.lower() for t in tech}
    staff = f3a_output.get("staff_estimate_band") or ""
    entity_type = (f3a_output.get("entity_type_hint") or "").lower()

    # GST registered (from ABN → ABR, proves >$75K annual revenue)
    serp_abn = f3a_output.get("abn") or f3a_output.get("serp_abn")
    # If ABN was found, business is registered = minimum viability signal
    if serp_abn:
        budget += 3
        breakdown["abn_registered"] = 3

    # Entity type — structured business = more likely to have budget
    if any(t in entity_type for t in ("company", "trust", "pty", "ltd")):
        budget += 3
        breakdown["structured_entity"] = 3

    # Professional CMS (investing in web presence)
    pro_cms = {"shopify", "wordpress", "webflow", "squarespace", "wix", "magento", "bigcommerce"}
    if pro_cms & tech_lower:
        budget += 2
        breakdown["professional_cms"] = 2

    # Tracking installed (investing in measurement = marketing-aware)
    tracking = {"google analytics", "google tag manager", "facebook pixel", "hotjar", "crazy egg"}
    if tracking & tech_lower:
        budget += 2
        breakdown["tracking_installed"] = 2

    # Booking/scheduling system (structured revenue flow)
    booking = {"calendly", "acuity", "mindbody", "timely", "fresha", "bookeo", "cliniko"}
    if booking & tech_lower:
        budget += 2
        breakdown["booking_system"] = 2

    # Customer volume (GMB reviews as revenue proxy)
    if gmb_reviews > 100:
        budget += 3
        breakdown["high_review_volume"] = 3
    elif gmb_reviews > 30:
        budget += 2
        breakdown["moderate_review_volume"] = 2

    # Staff band (paying wages = has revenue)
    if staff in ("medium(6-20)", "large(20+)"):
        budget += 2
        breakdown["employs_staff"] = 2

    # Already spending on marketing (strongest affordability signal)
    if paid_kw > 0 or is_running_ads:
        budget += 5
        breakdown["active_ad_spend"] = 5

    # ETV percentile — category-relative online presence (weak signal, low weight)
    if 0.25 <= etv_pct <= 0.75:
        budget += 3
        breakdown["etv_sweet_spot"] = 3
    elif etv_pct > 0.75:
        budget += 1
        breakdown["etv_top_quarter"] = 1
    elif etv_pct > 0:
        budget += 2
        breakdown["etv_present"] = 2

    budget = min(budget, 25)

    # ── PAIN SCORE (0-25) ───────────────────────────────────────────
    pain = 0
    if 0 < gmb_rating < 4.0:
        pain += 10
        breakdown["low_gmb_rating"] = 10
    elif 4.0 <= gmb_rating < 4.5:
        pain += 5
        breakdown["mediocre_gmb_rating"] = 5

    if indexed > 0 and indexed < 50:
        pain += 5
        breakdown["thin_content"] = 5

    if not is_running_ads and organic_etv > 0:
        pain += 5
        breakdown["zero_paid_ads"] = 5

    # Lost keywords (position 11-20 = page 2)
    pos_11_20 = ro.get("dfs_organic_pos_11_20") or 0
    if pos_11_20 > 100:
        pain += 5
        breakdown["many_page2_keywords"] = 5
    elif pos_11_20 > 30:
        pain += 3
        breakdown["some_page2_keywords"] = 3
    pain = min(pain, 25)

    # ── REACHABILITY SCORE (0-25) ───────────────────────────────────
    reach = 0
    if f3a_output.get("primary_phone"):
        reach += 5
        breakdown["has_phone"] = 5
    if f3a_output.get("primary_email"):
        reach += 5
        breakdown["has_email"] = 5
    if signal_bundle.get("gmb"):
        reach += 5
        breakdown["has_gmb"] = 5
    dm = f3a_output.get("dm_candidate") or {}
    if dm.get("name"):
        reach += 5
        breakdown["has_dm"] = 5
    social = f3a_output.get("social_urls") or {}
    if any(social.get(k) for k in ("linkedin", "facebook", "instagram")):
        reach += 5
        breakdown["has_social"] = 5
    reach = min(reach, 25)

    # ── FIT SCORE (0-25) — ICP alignment ──────────────────────────
    fit = 0
    is_enterprise = f3a_output.get("is_enterprise_or_chain", False)
    if not is_enterprise:
        fit += 10
        breakdown["not_enterprise"] = 10

    # SMB sweet spot — small/medium is ideal ICP
    if staff in ("small(2-5)", "medium(6-20)"):
        fit += 5
        breakdown["smb_staff_band"] = 5
    elif staff == "solo":
        fit += 3
        breakdown["solo_operator"] = 3

    # Has meaningful organic presence (potential for agency to improve)
    if organic_kw > 500:
        fit += 5
        breakdown["strong_organic_base"] = 5
    elif organic_kw > 100:
        fit += 3
        breakdown["moderate_organic_base"] = 3

    if organic_kw > 100:
        fit += 5
        breakdown["meaningful_organic"] = 5
    fit = min(fit, 25)

    composite = budget + pain + reach + fit
    passed_gate = composite >= 30

    # ── VIABILITY FILTER ────────────────────────────────────────────
    is_viable = True
    viability_reason = None
    industry = (f3a_output.get("industry_category") or "").lower()

    media_keywords = [
        "media",
        "magazine",
        "newspaper",
        "news",
        "broadcast",
        "publisher",
        "publishing",
    ]
    directory_keywords = [
        "directory",
        "aggregator",
        "listing",
        "marketplace",
        "platform",
        "comparison",
    ]

    if any(k in industry for k in media_keywords):
        is_viable = False
        viability_reason = f"media/publishing company: {industry}"
    elif any(k in industry for k in directory_keywords):
        is_viable = False
        viability_reason = f"directory/aggregator: {industry}"

    return {
        "budget_score": budget,
        "pain_score": pain,
        "reachability_score": reach,
        "fit_score": fit,
        "composite_score": composite,
        "etv_percentile": round(etv_pct, 3),
        "passed_gate": passed_gate,
        "is_viable_prospect": is_viable,
        "viability_reason": viability_reason,
        "score_breakdown": breakdown,
    }
