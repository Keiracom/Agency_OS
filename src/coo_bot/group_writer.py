"""Max COO bot — Group writer.

Posts to the Agency OS supergroup with [MAX] prefix.
Called by dm_handler when Dave uses /post command.

Public API:
    post_to_group(bot_token: str, text: str) -> bool
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_GROUP_CHAT_ID = -1003926592540
_PREFIX = "[MAX] "


async def post_to_group(
    bot_token: str,
    text: str,
    *,
    dave_dm_id: int | None = None,
) -> bool:
    """Post a message to the Agency OS supergroup with [MAX] prefix.

    Args:
        bot_token: Telegram bot token for Max.
        text: Message body (prefix will be prepended automatically).
        dave_dm_id: Message ID of Dave's authorising DM (for audit trail).

    Returns:
        True on success, False on any failure (never raises).
    """
    prefixed_text = f"{_PREFIX}{text}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": _GROUP_CHAT_ID,
        "text": prefixed_text,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
        if response.status_code == 200:
            logger.info("group_writer: posted to group OK")
            # Audit trail — governance_events row per architecture spec
            await _write_audit_event(prefixed_text, dave_dm_id)
            return True
        logger.error(
            "group_writer: sendMessage returned HTTP %d: %s",
            response.status_code,
            response.text[:200],
        )
        return False
    except Exception as exc:
        logger.error("group_writer: post failed: %s", exc)
        return False


async def _write_audit_event(text: str, dave_dm_id: int | None) -> None:
    """Write a governance_events row for every Max group post. Best-effort."""
    import os
    try:
        from src.governance._mcp_helpers import governance_event_emit
        governance_event_emit(
            callsign="max",
            event_type="max_group_post",
            event_data={
                "text": text[:500],
                "dave_authorized_via_dm_id": dave_dm_id,
                "tier": int(os.environ.get("COO_APPROVAL_TIER", "0")),
            },
            tool_name="governance.coo_bot.group_writer",
        )
    except Exception as exc:
        logger.warning("group_writer: audit event failed (non-blocking): %s", exc)
