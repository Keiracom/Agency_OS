"""src/config/email_costs.py — per-send AUD cost constants.

Single source of truth for what each email-sending channel costs us in
AUD. Used by `src/api/routes/email.py` (Resend route) and
`src/engines/campaign_executor.py` (Resend dispatch) to populate the
`cost_aud` columns added in migration 20260506_cost_aud_columns.sql.

LAW II: all costs in AUD. USD-billed providers convert at 1.55× via the
constants below.

Update whenever provider pricing changes (and update the comment with
the source URL + date so future readers can verify).
"""

from __future__ import annotations

from decimal import Decimal

# ── Resend ────────────────────────────────────────────────────────────────────
# Resend Pro plan: $20 USD/mo for 50,000 emails = $0.0004 USD per email.
# AUD: 0.0004 × 1.55 = 0.00062 AUD/email.
# Reference: https://resend.com/pricing (snapshot 2026-05-06).
# Rounded up to 0.0001 for safety / round-numbers; reconciliation against
# the Resend invoice is the source of truth.
RESEND_COST_AUD_PER_EMAIL: Decimal = Decimal("0.0010")

# ── SmartLead ─────────────────────────────────────────────────────────────────
# SmartLead Pro: $94 USD/mo flat-rate for API access. Per-send cost is
# zero on the variable axis — the cost is the subscription, not per-email.
# Stored as 0 here so accounting reflects the variable cost; subscription
# fee is tracked separately in finance ledger.
# Reference: skills/smartlead/SKILL.md (PR #578, dual-approved 2026-05-06).
SMARTLEAD_COST_AUD_PER_EMAIL: Decimal = Decimal("0.0000")


def cost_for_channel(channel: str) -> Decimal:
    """Return per-send AUD cost for the given channel name.

    Args:
        channel: 'resend' or 'smartlead'. Case-insensitive.

    Returns:
        Decimal AUD cost. Decimal preserves precision through DB INSERT.

    Raises:
        ValueError on unknown channel — fail loud so we don't silently
        zero out cost on a typo.
    """
    name = (channel or "").strip().lower()
    if name == "resend":
        return RESEND_COST_AUD_PER_EMAIL
    if name == "smartlead":
        return SMARTLEAD_COST_AUD_PER_EMAIL
    raise ValueError(f"Unknown email channel: {channel!r} (expected 'resend' or 'smartlead')")


__all__ = [
    "RESEND_COST_AUD_PER_EMAIL",
    "SMARTLEAD_COST_AUD_PER_EMAIL",
    "cost_for_channel",
]
