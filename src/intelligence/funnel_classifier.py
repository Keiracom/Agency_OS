"""Funnel classifier — maps intent band to funnel stage.

Converts F3a/F3b intent_band output to a standardised pipeline funnel stage.
Used downstream for routing, prioritisation, and outreach sequencing.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

INTENT_TO_FUNNEL: dict[str, str] = {
    "DORMANT": "cold",
    "DABBLING": "warm",
    "TRYING": "hot",
    "STRUGGLING": "urgent",
    "NOT_TRYING": "disqualified",
}

FUNNEL_PRIORITY: dict[str, int] = {
    "urgent": 1,
    "hot": 2,
    "warm": 3,
    "cold": 4,
    "disqualified": 99,
}


def classify_funnel_stage(intent_band: str | None) -> str:
    """Map an intent band string to a funnel stage label.

    Args:
        intent_band: One of DORMANT, DABBLING, TRYING, STRUGGLING, NOT_TRYING.

    Returns:
        Funnel stage string. Returns "unknown" if band is None or unrecognised.
    """
    if not intent_band:
        return "unknown"
    return INTENT_TO_FUNNEL.get(intent_band.upper(), "unknown")


def get_funnel_priority(funnel_stage: str) -> int:
    """Return sort priority for a funnel stage (lower = higher priority).

    Args:
        funnel_stage: Output of classify_funnel_stage().

    Returns:
        Integer priority. Returns 50 for unknown stages.
    """
    return FUNNEL_PRIORITY.get(funnel_stage, 50)


def classify_prospect(f3a_output: dict, f3b_output: dict | None = None) -> dict:
    """Produce a funnel classification from F3a (and optionally F3b) output.

    F3b intent_band_final takes precedence over F3a preliminary if present.

    Args:
        f3a_output: Parsed F3a JSON dict.
        f3b_output: Parsed F3b JSON dict (optional).

    Returns:
        {
            "intent_band": str,
            "funnel_stage": str,
            "funnel_priority": int,
            "affordability_gate": str,
            "buyer_match_score": int | None,
        }
    """
    # Prefer F3b final intent if available
    if f3b_output and f3b_output.get("intent_band_final"):
        intent_band = f3b_output["intent_band_final"]
    else:
        intent_band = f3a_output.get("intent_band_preliminary") or "DORMANT"

    funnel_stage = classify_funnel_stage(intent_band)
    priority = get_funnel_priority(funnel_stage)

    return {
        "intent_band": intent_band,
        "funnel_stage": funnel_stage,
        "funnel_priority": priority,
        "affordability_gate": f3a_output.get("affordability_gate") or "unknown",
        "buyer_match_score": f3a_output.get("buyer_match_score"),
    }
