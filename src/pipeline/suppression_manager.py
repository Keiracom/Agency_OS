"""Suppression list manager — prevents re-outreach to opted-out prospects.

Integrates with:
  - compliance_handler.py (opt-outs / unsubscribes)
  - reply_router.py (bounces, complaints)
  - booking_handler.py (converted prospects)

Primary store: Supabase public.suppression_list via PostgREST.
In-memory _store acts as a write-through cache (check cache first, fall back to DB).
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level in-memory cache (thread-safe via lock)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# email -> {reason, channel, source, suppressed_at}
_store: dict[str, dict] = {}

VALID_REASONS = {"unsubscribe", "bounce", "complaint", "converted", "manual"}
VALID_CHANNELS = {"all", "email", "phone", "linkedin", "sms", "voice"}

# ---------------------------------------------------------------------------
# PostgREST helpers (best-effort — non-fatal if Supabase is down)
# ---------------------------------------------------------------------------

def _get_supabase_creds() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    return url, key


async def _db_check(email: str) -> dict | None:
    """GET /rest/v1/suppression_list?email=eq.{email} — returns first row or None."""
    try:
        import httpx
        url, key = _get_supabase_creds()
        if not url or not key:
            return None
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{url}/rest/v1/suppression_list",
                params={"email": f"eq.{email}", "select": "email,reason,channel,source,suppressed_at", "limit": "1"},
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("suppression_manager: DB check failed (non-fatal): %s", exc)
    return None


async def _db_upsert(record: dict) -> bool:
    """POST /rest/v1/suppression_list with upsert prefer header."""
    try:
        import httpx
        url, key = _get_supabase_creds()
        if not url or not key:
            return False
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{url}/rest/v1/suppression_list",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                json=record,
            )
        return resp.status_code in (200, 201)
    except Exception as exc:  # noqa: BLE001
        logger.warning("suppression_manager: DB upsert failed (non-fatal): %s", exc)
    return False


async def _db_delete(email: str) -> bool:
    """DELETE /rest/v1/suppression_list?email=eq.{email}."""
    try:
        import httpx
        url, key = _get_supabase_creds()
        if not url or not key:
            return False
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.delete(
                f"{url}/rest/v1/suppression_list",
                params={"email": f"eq.{email}"},
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
        return resp.status_code in (200, 204)
    except Exception as exc:  # noqa: BLE001
        logger.warning("suppression_manager: DB delete failed (non-fatal): %s", exc)
    return False


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine on the running loop or create a new one if none."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except Exception as exc:  # noqa: BLE001
        logger.warning("suppression_manager: fire-and-forget failed: %s", exc)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class SuppressionManager:
    """Manage cross-campaign suppression to prevent re-contacting opted-out prospects."""

    @staticmethod
    def check_before_outreach(
        email: str,
        phone: Optional[str] = None,
    ) -> dict:
        """Check if a prospect should be suppressed before any outreach.

        Checks in-memory cache first; if not found, queries Supabase and
        populates cache for subsequent calls.

        Returns:
            {suppressed: bool, reason: str | None, suppressed_at: str | None}
        """
        key = email.lower().strip()

        # Cache hit
        with _lock:
            entry = _store.get(key)
        if entry:
            return {
                "suppressed": True,
                "reason": entry["reason"],
                "suppressed_at": entry["suppressed_at"],
            }

        # Cache miss — try DB (best-effort, run sync via new event loop)
        try:
            url, key_cred = _get_supabase_creds()
            if not url or not key_cred:
                # No creds — skip DB round-trip
                return {"suppressed": False, "reason": None, "suppressed_at": None}
            loop = asyncio.new_event_loop()
            row = loop.run_until_complete(_db_check(key))
            loop.close()
            if row:
                with _lock:
                    _store[key] = {
                        "reason": row.get("reason"),
                        "channel": row.get("channel", "all"),
                        "source": row.get("source", "system"),
                        "suppressed_at": row.get("suppressed_at"),
                    }
                return {
                    "suppressed": True,
                    "reason": row.get("reason"),
                    "suppressed_at": row.get("suppressed_at"),
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("suppression_manager: check DB fallback failed (non-fatal): %s", exc)

        return {"suppressed": False, "reason": None, "suppressed_at": None}

    @staticmethod
    def add_to_suppression(
        email: str,
        reason: str,
        channel: str = "all",
        source: str = "system",
    ) -> dict:
        """Add email to suppression list.

        Writes to in-memory cache immediately, then fires async upsert to Supabase.

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

        record = {
            "email": key,
            "reason": reason,
            "channel": channel,
            "source": source,
            "suppressed_at": now,
        }
        _fire_and_forget(_db_upsert(record))

        return {"success": True, "email": key, "reason": reason, "suppressed_at": now}

    @staticmethod
    def remove_from_suppression(email: str) -> dict:
        """Remove from suppression list (re-enable outreach).

        Removes from in-memory cache immediately, then fires async delete to Supabase.

        Returns:
            {success: bool, email: str, was_suppressed: bool}
        """
        key = email.lower().strip()
        with _lock:
            was_suppressed = key in _store
            if was_suppressed:
                del _store[key]

        if was_suppressed:
            _fire_and_forget(_db_delete(key))

        return {"success": True, "email": key, "was_suppressed": was_suppressed}

    @staticmethod
    def get_suppression_stats() -> dict:
        """Return suppression statistics from in-memory cache.

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
        """Check multiple emails at once (cache only — fast path).

        Returns:
            {email: is_suppressed}  — keys are normalised (lowercased).
        """
        with _lock:
            return {email.lower().strip(): email.lower().strip() in _store for email in emails}
