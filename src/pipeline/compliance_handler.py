"""compliance_handler.py — Unsubscribe/opt-out processing per AU Spam Act 2003.

AU Spam Act 2003 key obligations:
- s.16: Unsubscribe requests must be processed within 5 business days.
- s.17: Opt-out mechanism must be free and must not require disclosure of
        personal information beyond what is needed to process the request.
- s.18: Once opted out, the sender must not send further commercial electronic
        messages to that address on the relevant channel.
- Maintaining a suppression list and audit trail is standard compliance practice.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Suppression store — in-memory fallback; Supabase writes are best-effort
# ---------------------------------------------------------------------------

_SUPPRESSION: dict[str, dict[str, Any]] = {}

REASON_UNSUBSCRIBE = "unsubscribe"
REASON_OPT_OUT = "opt_out"
REASON_HARD_BOUNCE = "hard_bounce"
REASON_COMPLAINT = "complaint"

CHANNEL_ALL = "all"

_SOFT_BOUNCE_REASONS = {"soft_bounce", "mailbox_full", "quota_exceeded"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_suppression(
    email: str,
    reason: str,
    channel: str,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write suppression record to in-memory store and attempt Supabase write."""
    record: dict[str, Any] = {
        "email": email,
        "suppressed_at": _now_iso(),
        "reason": reason,
        "channel": channel,
        "source": source,
    }
    if extra:
        record.update(extra)

    # In-memory store (keyed by email; channel=all overwrites any per-channel entry)
    key = email.lower()
    existing = _SUPPRESSION.get(key)
    if existing is None or channel == CHANNEL_ALL or existing.get("channel") != CHANNEL_ALL:
        _SUPPRESSION[key] = record

    # Best-effort Supabase write via MCP bridge (non-fatal if unavailable)
    try:
        _write_supabase(record)
    except Exception as exc:  # noqa: BLE001
        logger.warning("compliance_handler: Supabase write failed (non-fatal): %s", exc)

    logger.info(
        "compliance_handler: suppressed email=%s reason=%s channel=%s source=%s",
        email, reason, channel, source,
    )
    return record


def _write_supabase(record: dict[str, Any]) -> None:
    """Attempt to upsert suppression record to public.suppression_list via MCP bridge.

    Mirrors the pattern used in agent_memories: fire-and-forget, non-fatal.
    Table DDL (run once):
        CREATE TABLE IF NOT EXISTS public.suppression_list (
            email        TEXT PRIMARY KEY,
            suppressed_at TIMESTAMPTZ NOT NULL,
            reason       TEXT NOT NULL,
            channel      TEXT NOT NULL DEFAULT 'all',
            source       TEXT NOT NULL DEFAULT 'manual'
        );
    """
    import json
    import subprocess

    sql = (
        "INSERT INTO public.suppression_list "
        "(email, suppressed_at, reason, channel, source) "
        "VALUES ('{email}', '{suppressed_at}', '{reason}', '{channel}', '{source}') "
        "ON CONFLICT (email) DO UPDATE SET "
        "suppressed_at = EXCLUDED.suppressed_at, "
        "reason = EXCLUDED.reason, "
        "channel = EXCLUDED.channel, "
        "source = EXCLUDED.source;"
    ).format(**{k: str(v).replace("'", "''") for k, v in record.items()})

    bridge = (
        "/home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js"
    )
    args = json.dumps({"query": sql})
    subprocess.run(
        ["node", bridge, "call", "supabase", "execute_sql", args],
        capture_output=True,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_unsubscribe(email: str, reason: str | None = None) -> dict[str, Any]:
    """Process an unsubscribe request per AU Spam Act 2003 s.16/s.17.

    Adds email to the suppression list for all channels.  No additional data
    is collected from the requester (s.17 compliance).

    Args:
        email:  The email address requesting unsubscription.
        reason: Optional free-text reason supplied by the system (not requested
                from the user — s.17 prohibits requiring additional disclosure).

    Returns:
        Confirmation dict with email, suppressed_at, and status.
    """
    record = _upsert_suppression(
        email=email,
        reason=REASON_UNSUBSCRIBE,
        channel=CHANNEL_ALL,
        source="reply",
        extra={"operator_note": reason} if reason else None,
    )
    return {
        "status": "suppressed",
        "email": record["email"],
        "suppressed_at": record["suppressed_at"],
        "channel": record["channel"],
        "act_reference": "AU Spam Act 2003 s.16 — processed within 5 business days",
    }


def process_opt_out(email: str, channel: str = CHANNEL_ALL) -> dict[str, Any]:
    """Process a per-channel or global opt-out per AU Spam Act 2003 s.18.

    Args:
        email:   The email address opting out.
        channel: One of "email", "sms", "voice", "linkedin", or "all" (default).

    Returns:
        Confirmation dict with email, suppressed_at, channel, and status.
    """
    valid_channels = {"email", "sms", "voice", "linkedin", CHANNEL_ALL}
    if channel not in valid_channels:
        raise ValueError(f"Invalid channel '{channel}'. Must be one of {valid_channels}.")

    record = _upsert_suppression(
        email=email,
        reason=REASON_OPT_OUT,
        channel=channel,
        source="webhook",
    )
    return {
        "status": "suppressed",
        "email": record["email"],
        "suppressed_at": record["suppressed_at"],
        "channel": record["channel"],
        "act_reference": "AU Spam Act 2003 s.18 — no further messages on opted-out channel",
    }


def is_suppressed(email: str, channel: str = CHANNEL_ALL) -> bool:
    """Return True if the email is suppressed for the given channel.

    A global (channel=all) suppression blocks all channels.
    Per-channel suppression only blocks that specific channel.

    This check MUST be called before any outreach is initiated to comply
    with AU Spam Act 2003 s.18.

    Args:
        email:   Email address to check.
        channel: Channel to check.  Defaults to "all" (global check).

    Returns:
        True if the address is suppressed, False otherwise.
    """
    key = email.lower()
    record = _SUPPRESSION.get(key)
    if record is None:
        return False
    stored_channel = record.get("channel", CHANNEL_ALL)
    # Global suppression blocks everything
    if stored_channel == CHANNEL_ALL:
        return True
    # Per-channel suppression only blocks that channel
    return stored_channel == channel


def get_suppression_list() -> list[dict[str, Any]]:
    """Return the full in-memory suppression list for audit purposes.

    For a production audit, query public.suppression_list directly via
    Supabase.  This function returns the session-resident cache.

    Returns:
        List of suppression record dicts.
    """
    return list(_SUPPRESSION.values())


def process_bounce(email: str, bounce_type: str) -> dict[str, Any]:
    """Handle a bounce event.

    Per industry best practice and AU Spam Act 2003 intent:
    - Hard bounce  -> permanent suppression (delivery is impossible).
    - Soft bounce  -> logged but NOT permanently suppressed (transient issue).

    Args:
        email:        The email address that bounced.
        bounce_type:  "hard_bounce" for permanent failures, or a soft-bounce
                      descriptor (e.g. "soft_bounce", "mailbox_full").

    Returns:
        Confirmation dict including whether permanent suppression was applied.
    """
    is_hard = bounce_type not in _SOFT_BOUNCE_REASONS and "soft" not in bounce_type.lower()

    if is_hard:
        record = _upsert_suppression(
            email=email,
            reason=REASON_HARD_BOUNCE,
            channel=CHANNEL_ALL,
            source="webhook",
            extra={"bounce_type": bounce_type},
        )
        return {
            "status": "permanently_suppressed",
            "email": record["email"],
            "suppressed_at": record["suppressed_at"],
            "bounce_type": bounce_type,
            "permanent": True,
        }

    # Soft bounce — log but do not suppress
    logger.info(
        "compliance_handler: soft bounce email=%s bounce_type=%s — not suppressed",
        email, bounce_type,
    )
    return {
        "status": "soft_bounce_logged",
        "email": email,
        "bounce_type": bounce_type,
        "permanent": False,
        "note": "Soft bounces are not permanently suppressed per policy.",
    }


def generate_compliance_report(start_date: str, end_date: str) -> dict[str, Any]:
    """Generate an audit report of suppression events within a date range.

    Covers AU Spam Act 2003 audit trail requirements.  Reports:
    - Total opt-outs and unsubscribes in the period.
    - Processing time compliance (flag any record where the suppression
      timestamp exceeded 5 business days from the event — not calculable
      from in-memory store alone, so a placeholder is included).
    - Re-contact violation count (records present in suppression list that
      were contacted again — requires outreach log join, flagged as N/A here).
    - Breakdown by reason and channel.

    Args:
        start_date: ISO date string "YYYY-MM-DD" (inclusive).
        end_date:   ISO date string "YYYY-MM-DD" (inclusive).

    Returns:
        Report dict with counts, breakdowns, and compliance notes.
    """
    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end_date).replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc
    )

    by_reason: dict[str, int] = {}
    by_channel: dict[str, int] = {}
    total = 0

    for record in _SUPPRESSION.values():
        suppressed_at = datetime.fromisoformat(record["suppressed_at"])
        if not (start_dt <= suppressed_at <= end_dt):
            continue
        total += 1
        reason = record.get("reason", "unknown")
        channel = record.get("channel", "unknown")
        by_reason[reason] = by_reason.get(reason, 0) + 1
        by_channel[channel] = by_channel.get(channel, 0) + 1

    return {
        "report_period": {"start": start_date, "end": end_date},
        "total_suppressions": total,
        "by_reason": by_reason,
        "by_channel": by_channel,
        "processing_time_compliance": {
            "note": (
                "AU Spam Act 2003 s.16 requires processing within 5 business days. "
                "Full processing-time audit requires outreach log join — "
                "query public.suppression_list against campaign send timestamps."
            ),
            "status": "manual_audit_required",
        },
        "re_contact_violations": {
            "count": "N/A — requires join with outreach send log",
            "note": "Query: sent emails where recipient is in suppression_list and sent_at > suppressed_at.",
        },
        "act_reference": "AU Spam Act 2003 — Spam Act 2003 (Cth), Schedule 2",
    }
