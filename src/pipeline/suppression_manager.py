"""Suppression list manager — prevents re-outreach to opted-out prospects.

Integrates with:
  - compliance_handler.py (opt-outs / unsubscribes)
  - reply_router.py (bounces, complaints)
  - booking_handler.py (converted prospects)

v1: in-memory store. Real implementation queries suppression_list table in Supabase.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Module-level in-memory store (thread-safe via lock)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# email -> {reason, channel, source, suppressed_at}
_store: dict[str, dict] = {}

VALID_REASONS = {"unsubscribe", "bounce", "complaint", "converted", "manual"}
VALID_CHANNELS = {"all", "email", "phone", "linkedin"}


class SuppressionManager:
    """Manage cross-campaign suppression to prevent re-contacting opted-out prospects."""

    @staticmethod
    def check_before_outreach(
        email: str,
        phone: Optional[str] = None,
    ) -> dict:
        """Check if a prospect should be suppressed before any outreach.

        Returns:
            {suppressed: bool, reason: str | None, suppressed_at: str | None}
        """
        key = email.lower().strip()
        with _lock:
            entry = _store.get(key)
        if entry:
            return {
                "suppressed": True,
                "reason": entry["reason"],
                "suppressed_at": entry["suppressed_at"],
            }
        return {"suppressed": False, "reason": None, "suppressed_at": None}

    @staticmethod
    def add_to_suppression(
        email: str,
        reason: str,
        channel: str = "all",
        source: str = "system",
    ) -> dict:
        """Add email to suppression list.

        Args:
            email:   Prospect email address.
            reason:  One of: unsubscribe, bounce, complaint, converted, manual.
            channel: Suppressed channel — 'all' suppresses every channel.
            source:  Who triggered the suppression (e.g. 'compliance_handler').

        Returns:
            {success: bool, email: str, reason: str, suppressed_at: str}
        """
        if reason not in VALID_REASONS:
            return {
                "success": False,
                "error": f"Invalid reason '{reason}'. Valid: {VALID_REASONS}",
            }
        if channel not in VALID_CHANNELS:
            return {
                "success": False,
                "error": f"Invalid channel '{channel}'. Valid: {VALID_CHANNELS}",
            }

        key = email.lower().strip()
        now = datetime.now(timezone.utc).isoformat()
        with _lock:
            _store[key] = {
                "reason": reason,
                "channel": channel,
                "source": source,
                "suppressed_at": now,
            }
        return {"success": True, "email": key, "reason": reason, "suppressed_at": now}

    @staticmethod
    def remove_from_suppression(email: str) -> dict:
        """Remove from suppression list (re-enable outreach).

        Returns:
            {success: bool, email: str, was_suppressed: bool}
        """
        key = email.lower().strip()
        with _lock:
            was_suppressed = key in _store
            if was_suppressed:
                del _store[key]
        return {"success": True, "email": key, "was_suppressed": was_suppressed}

    @staticmethod
    def get_suppression_stats() -> dict:
        """Return suppression statistics.

        Returns:
            {total: int, by_reason: dict[str, int], by_channel: dict[str, int]}
        """
        with _lock:
            entries = list(_store.values())

        by_reason: dict[str, int] = {}
        by_channel: dict[str, int] = {}
        for entry in entries:
            by_reason[entry["reason"]] = by_reason.get(entry["reason"], 0) + 1
            by_channel[entry["channel"]] = by_channel.get(entry["channel"], 0) + 1

        return {"total": len(entries), "by_reason": by_reason, "by_channel": by_channel}

    @staticmethod
    def bulk_check(emails: list[str]) -> dict[str, bool]:
        """Check multiple emails at once.

        Returns:
            {email: is_suppressed}  — keys are normalised (lowercased).
        """
        with _lock:
            return {email.lower().strip(): email.lower().strip() in _store for email in emails}
