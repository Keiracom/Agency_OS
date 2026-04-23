"""
Contract: src/outreach/safety/compliance_guard.py
Purpose: Australian outreach compliance enforcement (SPAM Act, TCP, DNCR, suppression)
Layer: 3 - engines
Imports: stdlib + src.outreach.safety.timing_engine
Consumers: outreach orchestration

Evaluates a prospect + channel + datetime against all active compliance
rules and returns a ComplianceDecision with allow/deny, reason summary,
and list of specific violation codes. All codes accumulate; any violation
blocks the send.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from src.outreach.safety.timing_engine import AU_PUBLIC_HOLIDAYS_2026, Channel

logger = logging.getLogger(__name__)

DEFAULT_TZ = "Australia/Sydney"

# TCP: Telecommunications Consumer Protection Act hours for voice/SMS
TCP_START = 9   # 9am (inclusive)
TCP_END = 20    # 8pm (exclusive) — i.e. calls/SMS allowed until 19:59


@dataclass
class ComplianceDecision:
    allowed: bool
    reason: str
    violations: list[str] = field(default_factory=list)


def _default_suppression(contact: str) -> bool:  # noqa: ARG001
    return False


def _default_dncr(phone: str) -> bool:  # noqa: ARG001
    return False


def _resolve_dncr(lookup: Callable[[str], bool] | None) -> Callable[[str], bool]:
    """Return the supplied lookup, or build the live adapter, falling back to no-op."""
    if lookup is not None:
        return lookup
    try:
        from src.outreach.safety.dncr_adapter import build_dncr_lookup as _build_dncr
        return _build_dncr()
    except Exception as exc:
        logger.warning("DNCR adapter init failed, falling back to no-op: %s", exc)
        return _default_dncr


class ComplianceGuard:
    """
    Contract: src/outreach/safety/compliance_guard.py — ComplianceGuard
    Purpose:  Enforces AU legal compliance rules before any outreach send.
    Layer:    engines

    Violation codes:
        SUPPRESSION_HIT       — prospect in internal suppression list
        DNCR_HIT              — phone on Do Not Call Register
        TCP_HOURS_VIOLATION   — call/SMS outside TCP-permitted hours
        SPAM_ACT_UNSUBSCRIBED — prospect unsubscribed from email
    """

    def __init__(
        self,
        suppression_lookup: Callable[[str], bool] | None = None,
        dncr_lookup: Callable[[str], bool] | None = None,
    ) -> None:
        self._suppression = suppression_lookup or _default_suppression
        self._dncr = _resolve_dncr(dncr_lookup)

    def check(
        self,
        channel: Channel,
        prospect: dict,
        now: datetime,
    ) -> ComplianceDecision:
        """
        Run all compliance rules for the given channel/prospect/time.

        Args:
            channel:  Outreach channel being evaluated.
            prospect: Dict with keys: email, phone, tz (optional), has_unsubscribed (optional).
            now:      Current datetime (tz-aware preferred).

        Returns:
            ComplianceDecision — allowed=True only when violations is empty.
        """
        violations: list[str] = []

        _check_suppression(prospect, self._suppression, violations)
        _check_dncr(channel, prospect, self._dncr, violations)
        _check_tcp_hours(channel, prospect, now, violations)
        _check_spam_act(channel, prospect, violations)

        allowed = len(violations) == 0
        reason = _build_reason(violations) if violations else "compliant"

        return ComplianceDecision(allowed=allowed, reason=reason, violations=violations)


# ---------------------------------------------------------------------------
# Private rule checkers — each under 20 lines
# ---------------------------------------------------------------------------

def _check_suppression(
    prospect: dict,
    lookup: Callable[[str], bool],
    violations: list[str],
) -> None:
    """Block if email or phone appears in the suppression list."""
    email = prospect.get("email", "")
    phone = prospect.get("phone", "")
    if (email and lookup(email)) or (phone and lookup(phone)):
        violations.append("SUPPRESSION_HIT")


def _check_dncr(
    channel: Channel,
    prospect: dict,
    lookup: Callable[[str], bool],
    violations: list[str],
) -> None:
    """Block voice/SMS channels if phone is on the DNCR."""
    if channel not in (Channel.VOICE, Channel.SMS):
        return
    phone = prospect.get("phone", "")
    if phone and lookup(phone):
        violations.append("DNCR_HIT")


def _check_tcp_hours(
    channel: Channel,
    prospect: dict,
    now: datetime,
    violations: list[str],
) -> None:
    """Enforce TCP hours (9am–8pm Mon–Sat, never Sunday) for voice/SMS."""
    if channel not in (Channel.VOICE, Channel.SMS):
        return

    tz = ZoneInfo(prospect.get("tz") or DEFAULT_TZ)
    local = now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)

    weekday = local.weekday()  # 0=Mon .. 6=Sun
    hour = local.hour

    is_sunday = weekday == 6
    before_window = hour < TCP_START
    after_window = hour >= TCP_END

    if is_sunday or before_window or after_window:
        violations.append("TCP_HOURS_VIOLATION")


def _check_spam_act(
    channel: Channel,
    prospect: dict,
    violations: list[str],
) -> None:
    """Block email channel if prospect has unsubscribed (SPAM Act 2003)."""
    if channel != Channel.EMAIL:
        return
    if prospect.get("has_unsubscribed") is True:
        violations.append("SPAM_ACT_UNSUBSCRIBED")


def _build_reason(violations: list[str]) -> str:
    """Build a human-readable semicolon-separated reason string from violation codes."""
    messages = {
        "SUPPRESSION_HIT": "prospect is in the suppression list",
        "DNCR_HIT": "phone number is on the Do Not Call Register",
        "TCP_HOURS_VIOLATION": "outside TCP-permitted calling hours (9am–8pm Mon–Sat)",
        "SPAM_ACT_UNSUBSCRIBED": "prospect has unsubscribed from email (SPAM Act 2003)",
    }
    return "; ".join(messages.get(v, v) for v in violations)
