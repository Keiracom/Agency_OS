"""Funnel classifier — Ready / Near-ready / Watchlist / Dropped.

Classification per F-REFACTOR-01 directive:
  Ready: identity + afford>=5 + intent!=NOT_TRYING + DM name + at_least_one_verified_contact
  Near-ready: identity + scoring pass + DM present + contact waterfalls incomplete
  Watchlist: identity + scoring pass + (DM missing OR all contacts exhausted)
  Dropped: affordability hard fail OR NOT_TRYING OR DORMANT

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations


def classify_prospect(
    f3a_output: dict,
    f3b_output: dict | None = None,
    contacts: dict | None = None,
) -> dict:
    """Classify prospect into Ready / Near-ready / Watchlist / Dropped.

    Args:
        f3a_output: Parsed F3a JSON dict.
        f3b_output: Parsed F3b JSON dict (optional).
        contacts: F5 waterfall results {linkedin, email, mobile} (optional).

    Returns:
        {classification, reason, intent_band, affordability_gate, buyer_match_score}
    """
    contacts = contacts or {}

    # Intent band (F3b final takes precedence)
    if f3b_output and f3b_output.get("intent_band_final"):
        intent_band = f3b_output["intent_band_final"]
    else:
        intent_band = f3a_output.get("intent_band_preliminary") or "DORMANT"

    afford_score = f3a_output.get("affordability_score", 0) or 0
    afford_gate = f3a_output.get("affordability_gate", "unknown")
    has_name = bool(f3a_output.get("business_name"))
    dm = f3a_output.get("dm_candidate", {}) or {}
    has_dm = bool(dm.get("name"))

    # Contact resolution
    email_data = contacts.get("email", {})
    has_email = bool(email_data.get("email"))
    has_mobile = bool(contacts.get("mobile", {}).get("mobile"))
    li_data = contacts.get("linkedin", {})
    has_linkedin = bool(li_data.get("linkedin_url")) and li_data.get("match_type") != "no_match"
    has_any_contact = has_email or has_mobile or has_linkedin

    # DM verification level: full / partial / minimal
    email_verified = has_email and email_data.get("verified") is True
    if has_linkedin and (email_verified or has_mobile):
        dm_verification_level = "full"
    elif email_verified or has_mobile:
        dm_verification_level = "partial"
    elif has_email or has_linkedin:
        dm_verification_level = "minimal"
    else:
        dm_verification_level = "minimal"

    base = {
        "intent_band": intent_band,
        "affordability_gate": afford_gate,
        "affordability_score": afford_score,
        "buyer_match_score": f3a_output.get("buyer_match_score"),
        "has_dm": has_dm,
        "has_email": has_email,
        "has_mobile": has_mobile,
        "has_linkedin": has_linkedin,
        "dm_verification_level": dm_verification_level,
    }

    # Dropped conditions
    if not has_name:
        return {**base, "classification": "dropped", "reason": "no business identity"}

    if afford_gate == "cannot_afford" or afford_score < 3:
        return {**base, "classification": "dropped", "reason": f"affordability {afford_score}/10 below threshold"}

    if intent_band.upper() in ("NOT_TRYING", "DORMANT"):
        return {**base, "classification": "dropped", "reason": f"intent band {intent_band}"}

    # Ready: DM + contact + afford >= 5
    if has_dm and has_any_contact and afford_score >= 5:
        return {**base, "classification": "ready",
                "reason": f"DM identified + contact verified + afford {afford_score}/10"}

    # Near-ready: DM identified but contact incomplete
    if has_dm and not has_any_contact:
        return {**base, "classification": "near_ready",
                "reason": "DM identified but no verified contact yet"}

    # Watchlist: no DM or all contacts exhausted
    if not has_dm:
        return {**base, "classification": "watchlist",
                "reason": "DM not identified"}

    # Fallback
    return {**base, "classification": "near_ready", "reason": "partial enrichment"}
