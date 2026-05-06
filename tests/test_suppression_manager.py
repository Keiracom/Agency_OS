"""Tests for SuppressionManager — in-memory v1."""

import pytest

from src.pipeline.suppression_manager import SuppressionManager, _store, _lock


@pytest.fixture(autouse=True)
def clear_store():
    """Reset in-memory store between tests."""
    with _lock:
        _store.clear()
    yield
    with _lock:
        _store.clear()


# ---------------------------------------------------------------------------
# add + check
# ---------------------------------------------------------------------------


def test_add_then_check_suppressed():
    result = SuppressionManager.add_to_suppression("dave@example.com", reason="unsubscribe")
    assert result["success"] is True

    check = SuppressionManager.check_before_outreach("dave@example.com")
    assert check["suppressed"] is True
    assert check["reason"] == "unsubscribe"
    assert check["suppressed_at"] is not None


def test_check_not_in_list_returns_not_suppressed():
    check = SuppressionManager.check_before_outreach("unknown@example.com")
    assert check["suppressed"] is False
    assert check["reason"] is None
    assert check["suppressed_at"] is None


def test_email_normalised_on_add_and_check():
    SuppressionManager.add_to_suppression("  DAVE@Example.COM  ", reason="bounce")
    check = SuppressionManager.check_before_outreach("dave@example.com")
    assert check["suppressed"] is True


def test_invalid_reason_rejected():
    result = SuppressionManager.add_to_suppression("x@y.com", reason="notareason")
    assert result["success"] is False
    assert "Invalid reason" in result["error"]


def test_invalid_channel_rejected():
    result = SuppressionManager.add_to_suppression("x@y.com", reason="bounce", channel="fax")
    assert result["success"] is False
    assert "Invalid channel" in result["error"]


# ---------------------------------------------------------------------------
# remove + check
# ---------------------------------------------------------------------------


def test_remove_then_check_not_suppressed():
    SuppressionManager.add_to_suppression("rm@example.com", reason="manual")
    remove = SuppressionManager.remove_from_suppression("rm@example.com")
    assert remove["success"] is True
    assert remove["was_suppressed"] is True

    check = SuppressionManager.check_before_outreach("rm@example.com")
    assert check["suppressed"] is False


def test_remove_non_existent_returns_was_suppressed_false():
    result = SuppressionManager.remove_from_suppression("ghost@example.com")
    assert result["success"] is True
    assert result["was_suppressed"] is False


# ---------------------------------------------------------------------------
# bulk_check
# ---------------------------------------------------------------------------


def test_bulk_check_mixed_list():
    SuppressionManager.add_to_suppression("a@x.com", reason="complaint")
    SuppressionManager.add_to_suppression("b@x.com", reason="converted")

    result = SuppressionManager.bulk_check(["a@x.com", "b@x.com", "c@x.com"])
    assert result["a@x.com"] is True
    assert result["b@x.com"] is True
    assert result["c@x.com"] is False


def test_bulk_check_empty_list():
    result = SuppressionManager.bulk_check([])
    assert result == {}


def test_bulk_check_normalises_email_case():
    SuppressionManager.add_to_suppression("upper@x.com", reason="bounce")
    result = SuppressionManager.bulk_check(["UPPER@X.COM"])
    assert result["upper@x.com"] is True


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def test_stats_shape_empty():
    stats = SuppressionManager.get_suppression_stats()
    assert stats["total"] == 0
    assert stats["by_reason"] == {}
    assert stats["by_channel"] == {}


def test_stats_shape_populated():
    SuppressionManager.add_to_suppression("a@x.com", reason="bounce", channel="email")
    SuppressionManager.add_to_suppression("b@x.com", reason="bounce", channel="all")
    SuppressionManager.add_to_suppression("c@x.com", reason="unsubscribe", channel="email")

    stats = SuppressionManager.get_suppression_stats()
    assert stats["total"] == 3
    assert stats["by_reason"]["bounce"] == 2
    assert stats["by_reason"]["unsubscribe"] == 1
    assert stats["by_channel"]["email"] == 2
    assert stats["by_channel"]["all"] == 1
