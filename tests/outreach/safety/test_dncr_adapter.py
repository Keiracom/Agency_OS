"""
Tests for src/outreach/safety/dncr_adapter.py

Coverage:
1. registered=True  -> adapter returns True
2. registered=False -> adapter returns False
3. registered=None (degraded) -> returns False + warning logged
4. Empty phone ""   -> returns False, client.lookup NOT called
5. None phone       -> returns False, client.lookup NOT called
6. log_degraded=False + degraded -> returns False, NO warning logged
7. Two calls with same phone produce consistent result (pass-through, no adapter cache)
8. Log message contains phone + status for operator audit trail
9. client=None path constructs a DNCRClient and returns a callable
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.dncr_client import DNCRResult
from src.outreach.safety.dncr_adapter import build_dncr_lookup

PHONE = "+61411111111"


def _make_result(registered, status="ok"):
    from datetime import datetime, timezone

    return DNCRResult(
        registered=registered,
        registered_at=None,
        last_checked=datetime.now(timezone.utc),
        status=status,
    )


def _mock_client(registered, status="ok"):
    client = MagicMock()
    client.lookup.return_value = _make_result(registered, status)
    return client


# ---------------------------------------------------------------------------
# Case 1 — registered=True
# ---------------------------------------------------------------------------


def test_registered_true_returns_true():
    client = _mock_client(True)
    lookup = build_dncr_lookup(client)
    assert lookup(PHONE) is True


# ---------------------------------------------------------------------------
# Case 2 — registered=False
# ---------------------------------------------------------------------------


def test_registered_false_returns_false():
    client = _mock_client(False)
    lookup = build_dncr_lookup(client)
    assert lookup(PHONE) is False


# ---------------------------------------------------------------------------
# Case 3 — degraded (registered=None) -> False + warning log
# ---------------------------------------------------------------------------


def test_degraded_returns_false_and_logs_warning(caplog):
    client = _mock_client(None, status="degraded:no_api_key")
    lookup = build_dncr_lookup(client)
    with caplog.at_level(logging.WARNING, logger="src.outreach.safety.dncr_adapter"):
        result = lookup(PHONE)
    assert result is False
    assert any("degraded" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Case 4 — empty phone -> False, client NOT called
# ---------------------------------------------------------------------------


def test_empty_phone_returns_false_without_lookup():
    client = _mock_client(True)
    lookup = build_dncr_lookup(client)
    assert lookup("") is False
    client.lookup.assert_not_called()


# ---------------------------------------------------------------------------
# Case 5 — None phone -> False, client NOT called
# ---------------------------------------------------------------------------


def test_none_phone_returns_false_without_lookup():
    client = _mock_client(True)
    lookup = build_dncr_lookup(client)
    assert lookup(None) is False  # type: ignore[arg-type]
    client.lookup.assert_not_called()


# ---------------------------------------------------------------------------
# Case 6 — log_degraded=False -> no warning logged
# ---------------------------------------------------------------------------


def test_degraded_no_log_when_disabled(caplog):
    client = _mock_client(None, status="degraded:network")
    lookup = build_dncr_lookup(client, log_degraded=False)
    with caplog.at_level(logging.WARNING, logger="src.outreach.safety.dncr_adapter"):
        result = lookup(PHONE)
    assert result is False
    assert not caplog.records


# ---------------------------------------------------------------------------
# Case 7 — two calls with same phone -> consistent result (adapter is pass-through)
# ---------------------------------------------------------------------------


def test_two_calls_consistent():
    client = _mock_client(True)
    lookup = build_dncr_lookup(client)
    assert lookup(PHONE) is True
    assert lookup(PHONE) is True
    assert client.lookup.call_count == 2  # adapter does NOT cache; DNCRClient caches internally


# ---------------------------------------------------------------------------
# Case 8 — log message contains phone + status
# ---------------------------------------------------------------------------


def test_degraded_log_contains_phone_and_status(caplog):
    status = "degraded:rate_limited"
    client = _mock_client(None, status=status)
    lookup = build_dncr_lookup(client)
    with caplog.at_level(logging.WARNING, logger="src.outreach.safety.dncr_adapter"):
        lookup(PHONE)
    assert caplog.records, "Expected at least one warning record"
    msg = caplog.records[0].message
    assert PHONE in msg
    assert status in msg


# ---------------------------------------------------------------------------
# Case 9 — client=None path: constructs DNCRClient, returns callable
# ---------------------------------------------------------------------------


def test_no_client_arg_constructs_default():
    """build_dncr_lookup() with no args should return a callable without raising."""
    with patch("src.outreach.safety.dncr_adapter.DNCRClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.lookup.return_value = _make_result(False)
        MockClient.return_value = mock_instance
        lookup = build_dncr_lookup()
    assert callable(lookup)
    result = lookup(PHONE)
    assert result is False
    mock_instance.lookup.assert_called_once()
