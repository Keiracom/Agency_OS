"""Slack user-id ↔ callsign map for the enforcer bot.

Allows the enforcer to attribute incoming Slack messages to their canonical
callsign (elliot/aiden/max/dave/etc.) regardless of the Slack username
override used at post time. Per PR #672 spec § 4.

bot_id is shared across all our agency_os Slack-app posts (B0B2W7VL7T4); the
differentiator at receive time is `event.username` (or `event.user` for human
messages). We map both shapes here.
"""

from __future__ import annotations

# All bots share this Slack app's bot_id (chat:write.customize lets each post
# under a distinct username while sharing the underlying bot identity).
SHARED_BOT_ID = "B0B2W7VL7T4"

# bot username (set via chat:write.customize at post time) → canonical callsign
USERNAME_TO_CALLSIGN: dict[str, str] = {
    "Elliot": "elliot",
    "Aiden": "aiden",
    "Max": "max",
    "Enforcer": "enforcer",
    # future additions land here without a code change elsewhere
}

# Slack user ID (humans only — bot posts use bot_id + username) → callsign
HUMAN_USER_TO_CALLSIGN: dict[str, str] = {
    "U091TGTPB9": "dave",  # Dave's Slack user_id (verified 2026-05-11 via curl history)
}


def attribute(event: dict) -> str:
    """Return canonical callsign for a Slack message event.

    Resolution order:
      1. bot_id == SHARED_BOT_ID  → look up by event.username
      2. user present (human)     → look up by event.user
      3. fallback                 → 'unknown'
    """
    if event.get("bot_id") == SHARED_BOT_ID:
        return USERNAME_TO_CALLSIGN.get(event.get("username", ""), "unknown-bot")
    user_id = event.get("user")
    if user_id:
        return HUMAN_USER_TO_CALLSIGN.get(user_id, f"human:{user_id}")
    return "unknown"
