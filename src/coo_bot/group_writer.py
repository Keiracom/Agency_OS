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


async def post_to_group(bot_token: str, text: str) -> bool:
    """Post a message to the Agency OS supergroup with [MAX] prefix.

    Args:
        bot_token: Telegram bot token for Max.
        text: Message body (prefix will be prepended automatically).

    Returns:
        True on success, False on any failure (never raises).
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": _GROUP_CHAT_ID,
        "text": f"{_PREFIX}{text}",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
        if response.status_code == 200:
            logger.info("group_writer: posted to group OK")
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
