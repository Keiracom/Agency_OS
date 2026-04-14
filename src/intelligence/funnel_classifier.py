"""F6 — Funnel classification: Ready / Near-ready / Watchlist / Dropped.

Pure function — no I/O. Takes F3 payload + contact resolution results.

Ratified: 2026-04-14. Pipeline F architecture.
"""
from __future__ import annotations


def classify_prospect(
    f3_payload: dict,
    contacts: dict,
    fills: dict,
) -> dict:
    """
    Classify a prospect into a funnel position.

    Classification rules:
      Ready      — has identity + afford >=5 + intent != DORMANT/NOT_TRYING
                   + DM name + at least one verified contact
      Near-ready — has identity + scoring pass + DM identified but contact incomplete
      Watchlist  — has identity + scoring pass but DM not identified
      Dropped    — identity fail OR afford <3 OR intent is DORMANT or NOT_TRYING

    Args:
        f3_payload: raw F3 Gemini output dict
        contacts:   result from ContactWaterfall.resolve()
                    {"linkedin": {...}, "email": {...}, "mobile": {...}}
        fills:      result from VerifyFills.fill() (used for supplemental phone data)

    Returns:
        {
          "classification": "ready" | "near_ready" | "watchlist" | "dropped",
          "reason": str,
          "has_email": bool,
          "has_mobile": bool,
          "has_linkedin": bool,
        }
    """
    identity = f3_payload.get("s2_identity", {}) or {}
    afford = f3_payload.get("s4_affordability", {}) or {}
    intent = f3_payload.get("s5_intent", {}) or {}
    dm = (f3_payload.get("s6_dm_identification", {}) or {}).get("primary_dm", {}) or {}

    has_name = bool(identity.get("canonical_business_name"))
    afford_score = afford.get("score_0_to_10", 0) or 0
    intent_band = intent.get("band", "DORMANT") or "DORMANT"
    has_dm = bool(dm.get("name"))

    # Contact resolution
    has_email = bool((contacts.get("email") or {}).get("email"))
    has_mobile = bool((contacts.get("mobile") or {}).get("mobile"))
    has_linkedin = bool((contacts.get("linkedin") or {}).get("linkedin_url"))
    has_any_contact = has_email or has_mobile or has_linkedin

    base = {
        "has_email": has_email,
        "has_mobile": has_mobile,
        "has_linkedin": has_linkedin,
    }

    # --- Drop gates ---
    if not has_name:
        return {**base, "classification": "dropped", "reason": "no canonical identity"}

    if intent_band in ("DORMANT", "NOT_TRYING"):
        return {
            **base,
            "classification": "dropped",
            "reason": f"intent band {intent_band}",
        }

    if afford_score < 3:
        return {
            **base,
            "classification": "dropped",
            "reason": f"affordability {afford_score}/10 below threshold (min 3)",
        }

    # --- Positive gates ---
    if has_dm and has_any_contact and afford_score >= 5:
        return {
            **base,
            "classification": "ready",
            "reason": f"DM identified + contact verified + afford {afford_score}/10",
        }

    if has_dm and not has_any_contact:
        return {
            **base,
            "classification": "near_ready",
            "reason": "DM identified but no verified contact resolved",
        }

    if has_dm and has_any_contact and afford_score < 5:
        return {
            **base,
            "classification": "near_ready",
            "reason": f"DM + contact found but affordability low ({afford_score}/10)",
        }

    if not has_dm:
        return {
            **base,
            "classification": "watchlist",
            "reason": "DM not identified",
        }

    return {
        **base,
        "classification": "near_ready",
        "reason": "partial enrichment — contact or DM incomplete",
    }
