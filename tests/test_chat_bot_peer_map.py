"""Unit tests for _PEER_MAP multi-peer shape and PEER_INBOXES derivation.

Tests cover: elliot, aiden, max, and unknown callsign perspectives.
Uses importlib.reload after monkeypatching os.environ["CALLSIGN"] so each
test sees the module-level constants recalculated for the target callsign.
"""

import importlib
import os

import pytest


def _reload_with_callsign(monkeypatch, callsign: str):
    """Set CALLSIGN env var and reload chat_bot, returning the fresh module."""
    monkeypatch.setenv("CALLSIGN", callsign)
    import src.telegram_bot.chat_bot as mod

    importlib.reload(mod)
    return mod


def test_elliot_peer_inboxes(monkeypatch):
    mod = _reload_with_callsign(monkeypatch, "elliot")
    assert mod.PEER_INBOXES == [
        "/tmp/telegram-relay-aiden/inbox",
        "/tmp/telegram-relay-max/inbox",
    ]


def test_aiden_peer_inboxes(monkeypatch):
    mod = _reload_with_callsign(monkeypatch, "aiden")
    assert mod.PEER_INBOXES == [
        "/tmp/telegram-relay-elliot/inbox",
        "/tmp/telegram-relay-max/inbox",
    ]


def test_max_peer_inboxes_empty(monkeypatch):
    """Max receives cross-posts but does not cross-post to others."""
    mod = _reload_with_callsign(monkeypatch, "max")
    assert mod.PEER_INBOXES == []
    assert mod.PEER_INBOX is None


def test_unknown_callsign_peer_inboxes_empty(monkeypatch):
    """Undefined callsign must return empty list — no KeyError."""
    mod = _reload_with_callsign(monkeypatch, "unknown_agent_xyz")
    assert mod.PEER_INBOXES == []
    assert mod.PEER_INBOX is None


def test_backward_compat_shim_elliot(monkeypatch):
    """PEER_INBOX shim points to first peer for callsigns that have peers."""
    mod = _reload_with_callsign(monkeypatch, "elliot")
    assert mod.PEER_INBOX == "/tmp/telegram-relay-aiden/inbox"


def test_peer_map_shape(monkeypatch):
    """_PEER_MAP values must all be lists, not strings."""
    mod = _reload_with_callsign(monkeypatch, "elliot")
    for callsign, peers in mod._PEER_MAP.items():
        assert isinstance(peers, list), (
            f"_PEER_MAP[{callsign!r}] is {type(peers).__name__}, expected list"
        )
