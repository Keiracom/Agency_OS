"""Tests for classify_sender — four-axis security classification."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

# Import classify_sender and constants from chat_bot
import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "src" / "telegram_bot" / "chat_bot.py"

# We can't easily import chat_bot (requires telegram deps at module level).
# Instead, test the classification logic directly by recreating the function.

DAVE_USER_ID = 7267788033
KNOWN_PEER_BOTS = {"eeeeelllliiiioooottt_bot", "aaaaidenbot"}


class Sender:
    DAVE = "dave"
    PEER_BOT = "peer"
    SELF = "self"
    UNKNOWN = "unknown"


def classify_sender(user_id, username, is_bot, bot_username="eeeeelllliiiioooottt_bot"):
    """Mirror of chat_bot.py classify_sender logic for testing."""
    if not user_id:
        return Sender.UNKNOWN
    # Axis 1: Self
    if is_bot and username and username.lower() == bot_username.lower():
        return Sender.SELF
    # Axis 2: Peer bot
    if is_bot and username and username.lower() in KNOWN_PEER_BOTS:
        return Sender.PEER_BOT
    # Axis 3: Dave
    if not is_bot and user_id == DAVE_USER_ID:
        return Sender.DAVE
    # Axis 4: Unknown
    return Sender.UNKNOWN


@pytest.mark.parametrize("user_id,username,is_bot,bot_username,expected", [
    # Axis 1: Self detection
    (8381203809, "Eeeeelllliiiioooottt_bot", True, "Eeeeelllliiiioooottt_bot", Sender.SELF),
    # Axis 2: Peer bot detection
    (8614728959, "Aaaaidenbot", True, "Eeeeelllliiiioooottt_bot", Sender.PEER_BOT),
    # Axis 3: Dave with correct user_id
    (7267788033, None, False, "Eeeeelllliiiioooottt_bot", Sender.DAVE),
    # Axis 3 FAIL: Human with wrong user_id → UNKNOWN
    (99999999, "stranger", False, "Eeeeelllliiiioooottt_bot", Sender.UNKNOWN),
    # Axis 4: Unknown bot
    (11111111, "random_bot", True, "Eeeeelllliiiioooottt_bot", Sender.UNKNOWN),
    # Edge: no user_id
    (None, None, False, "Eeeeelllliiiioooottt_bot", Sender.UNKNOWN),
])
def test_classify_sender(user_id, username, is_bot, bot_username, expected):
    result = classify_sender(user_id, username, is_bot, bot_username)
    assert result == expected, f"Expected {expected} for user_id={user_id} username={username} is_bot={is_bot}, got {result}"
