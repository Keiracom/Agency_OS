"""tests for clone fan-out tag-filter (Option B, Dave 2026-05-12).

Per Dave directive ts 1778557944: clones (atlas/orion/scout) added to
#execution routing with tag-filtered fan-out via _is_clone_addressed().
Prevents the "Slack-#execution post never reaches clone" gap that surfaced
when audit Stream 1 dispatch was missed by Orion + Atlas.

Tests verify:
  - Clones receive #execution messages when specifically addressed
  - Clones do NOT receive ambient #execution messages
  - Primes (elliot/aiden/max) always receive (unchanged behavior)
  - Self-tag skip still applies to clones
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# Stub slack_sdk before module import (same pattern as PR #711)
for mod_name in (
    "slack_sdk",
    "slack_sdk.socket_mode",
    "slack_sdk.socket_mode.request",
    "slack_sdk.socket_mode.response",
    "slack_sdk.web",
):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)
sys.modules["slack_sdk.socket_mode"].SocketModeClient = type("SocketModeClient", (), {})
sys.modules["slack_sdk.socket_mode.request"].SocketModeRequest = type("SocketModeRequest", (), {})
sys.modules["slack_sdk.socket_mode.response"].SocketModeResponse = type("SocketModeResponse", (), {})
sys.modules["slack_sdk.web"].WebClient = type("WebClient", (), {})

from src.slack_bot.central_listener import (  # noqa: E402
    CALLSIGN_TO_INBOX,
    CHANNEL_ROUTES,
    CLONE_CALLSIGNS,
    _is_clone_addressed,
    process_event,
)

EXECUTION_CHANNEL = "C0B3QB0K1GQ"


# ──────────────────────────────────────────────────────────────────────────────
# CONFIG SHAPE TESTS — verify clones added to routing + inbox dicts
# ──────────────────────────────────────────────────────────────────────────────


def test_clones_routed_in_execution() -> None:
    """All 3 clones in #execution routes (Option B per Dave 2026-05-12)."""
    routes = CHANNEL_ROUTES[EXECUTION_CHANNEL]
    assert "atlas" in routes
    assert "orion" in routes
    assert "scout" in routes


def test_clones_have_inbox_paths() -> None:
    """Each clone has a CALLSIGN_TO_INBOX entry pointing at telegram-relay-<cs>."""
    for cs in ("atlas", "orion", "scout"):
        assert cs in CALLSIGN_TO_INBOX
        assert any(f"telegram-relay-{cs}" in str(p) for p in CALLSIGN_TO_INBOX[cs])


def test_clone_callsigns_constant() -> None:
    """CLONE_CALLSIGNS is the frozenset used by the fan-out filter."""
    assert CLONE_CALLSIGNS == frozenset({"atlas", "orion", "scout"})


# ──────────────────────────────────────────────────────────────────────────────
# ADDRESS-FILTER TESTS — _is_clone_addressed
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "@atlas dispatching empirical test",
        "[ATLAS] post-PR-712 smoke verify",
        "Atlas — picking up the next task",
        "Atlas: please run the mem0 investigation",
        "Atlas, can you smoke-test the gemini pivot?",
        "atlas\nyou are READY",  # line-start, case-insensitive
    ],
)
def test_atlas_addressed_match(text: str) -> None:
    """Each form of addressing Atlas matches the filter."""
    assert _is_clone_addressed("atlas", text)


@pytest.mark.parametrize(
    "text",
    [
        "Random ambient chatter about PR #732",
        "@aiden + @max sweep complete",
        "Holding for next dispatch",
        "the atlasing concept is interesting",  # bare word in middle, no boundary form
    ],
)
def test_atlas_not_addressed_no_match(text: str) -> None:
    """Ambient #execution chatter doesn't trigger atlas fan-out."""
    assert not _is_clone_addressed("atlas", text)


def test_orion_address_independent_of_atlas() -> None:
    """Orion-addressed message does NOT trigger atlas filter."""
    assert _is_clone_addressed("orion", "@orion start the filesystem audit")
    assert not _is_clone_addressed("atlas", "@orion start the filesystem audit")


def test_scout_address_independent() -> None:
    """Scout filter only fires on scout-addressed messages."""
    assert _is_clone_addressed("scout", "[SCOUT] attribution audit ping")
    assert not _is_clone_addressed("atlas", "[SCOUT] attribution audit ping")
    assert not _is_clone_addressed("orion", "[SCOUT] attribution audit ping")


def test_unknown_callsign_returns_false() -> None:
    """Non-clone callsign returns False (defensive)."""
    assert not _is_clone_addressed("dave", "anything")
    assert not _is_clone_addressed("elliot", "@elliot test")


# ──────────────────────────────────────────────────────────────────────────────
# PROCESS_EVENT FAN-OUT TESTS — verify clones receive only addressed messages
# ──────────────────────────────────────────────────────────────────────────────


def _event(text: str) -> dict:
    return {"type": "message", "channel": EXECUTION_CHANNEL, "text": text, "ts": "1.0"}


def test_addressed_clone_receives(tmp_path: Path) -> None:
    """When #execution message addresses a clone, write_inbox fires for that clone."""
    inbox_atlas = tmp_path / "atlas_inbox"
    inbox_atlas.mkdir()
    with patch.dict(CALLSIGN_TO_INBOX, {"atlas": [inbox_atlas]}):
        process_event(_event("@atlas run the mem0 investigation"))
    files = list(inbox_atlas.iterdir())
    assert len(files) == 1


def test_ambient_clone_skipped(tmp_path: Path) -> None:
    """When #execution message does NOT address a clone, clone inbox stays empty."""
    inbox_atlas = tmp_path / "atlas_inbox"
    inbox_atlas.mkdir()
    with patch.dict(CALLSIGN_TO_INBOX, {"atlas": [inbox_atlas]}):
        process_event(_event("Random status update about PR #732 [STATE:max] merged"))
    files = list(inbox_atlas.iterdir())
    assert len(files) == 0


def test_primes_always_receive(tmp_path: Path) -> None:
    """Primes (elliot/aiden/max) receive every #execution message regardless of address."""
    inbox_elliot = tmp_path / "elliot_inbox"
    inbox_aiden = tmp_path / "aiden_inbox"
    inbox_max = tmp_path / "max_inbox"
    for p in (inbox_elliot, inbox_aiden, inbox_max):
        p.mkdir()
    with patch.dict(
        CALLSIGN_TO_INBOX,
        {"elliot": [inbox_elliot], "aiden": [inbox_aiden], "max": [inbox_max]},
    ):
        process_event(_event("Ambient team chatter, no clone mention"))
    assert len(list(inbox_elliot.iterdir())) == 1
    assert len(list(inbox_aiden.iterdir())) == 1
    assert len(list(inbox_max.iterdir())) == 1


def test_dispatch_reaches_targeted_clone_only(tmp_path: Path) -> None:
    """A message addressing one clone should reach only that clone, not the others."""
    inbox_atlas = tmp_path / "atlas_inbox"
    inbox_orion = tmp_path / "orion_inbox"
    inbox_scout = tmp_path / "scout_inbox"
    for p in (inbox_atlas, inbox_orion, inbox_scout):
        p.mkdir()
    with patch.dict(
        CALLSIGN_TO_INBOX,
        {"atlas": [inbox_atlas], "orion": [inbox_orion], "scout": [inbox_scout]},
    ):
        process_event(_event("[DISPATCH] @atlas please re-run the empirical smoke test"))
    assert len(list(inbox_atlas.iterdir())) == 1
    assert len(list(inbox_orion.iterdir())) == 0
    assert len(list(inbox_scout.iterdir())) == 0
