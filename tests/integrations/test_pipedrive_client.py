"""tests/integrations/test_pipedrive_client.py — unit tests for pipedrive_client.py.

All sync. No live network calls — httpx.Client patched via unittest.mock.
Covers the 12 cases specified in the directive.
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from src.integrations import pipedrive_client as pd  # noqa: E402

# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    """Build a mock httpx.Response with status_code and .json() method."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    return resp


# ── (1) _dsn_base ──────────────────────────────────────────────────────────────


def test_dsn_base_builds_url():
    """_dsn_base assembles the correct v2 base URL."""
    assert pd._dsn_base("acme-agency") == "https://acme-agency.pipedrive.com/api/v2"


def test_dsn_base_rejects_empty():
    """_dsn_base raises ValueError on empty domain."""
    with pytest.raises(ValueError):
        pd._dsn_base("")


def test_dsn_base_rejects_whitespace():
    """_dsn_base raises ValueError on whitespace-only domain."""
    with pytest.raises(ValueError):
        pd._dsn_base("   ")


# ── (2) verify_token — 200 success ────────────────────────────────────────────


def test_verify_token_parses_200():
    """verify_token returns the user dict from a 200 response."""
    user_data = {"id": 1, "name": "Test User", "email": "test@acme.com"}
    resp = _mock_response(200, {"success": True, "data": user_data})
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp

    with patch("httpx.Client", return_value=mock_client):
        result = pd.verify_token("acme-agency")

    assert result == user_data


# ── (3) verify_token — 401 returns None ───────────────────────────────────────


def test_verify_token_returns_none_on_401():
    """verify_token returns None (not an exception) on 401 — used in onboarding flow."""
    resp = _mock_response(401)
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp

    with patch("httpx.Client", return_value=mock_client):
        result = pd.verify_token("acme-agency")

    assert result is None


# ── (4) search_person_by_email — parses search response ───────────────────────


def test_search_person_by_email_parses_response():
    """search_person_by_email returns the first matching person dict."""
    person = {"id": 42, "name": "Alice", "emails": [{"value": "alice@dental.com.au"}]}
    resp = _mock_response(200, {"data": {"items": [{"item": person}]}})
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp

    with patch("httpx.Client", return_value=mock_client):
        result = pd.search_person_by_email("acme-agency", "alice@dental.com.au")

    assert result == person


def test_search_person_by_email_returns_none_on_empty():
    """search_person_by_email returns None when no match found."""
    resp = _mock_response(200, {"data": {"items": []}})
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp

    with patch("httpx.Client", return_value=mock_client):
        result = pd.search_person_by_email("acme-agency", "nobody@example.com")

    assert result is None


# ── (5) create_person — validates email regex ──────────────────────────────────


def test_create_person_rejects_invalid_email():
    """create_person raises ValueError on malformed email."""
    with pytest.raises(ValueError, match="invalid email"):
        pd.create_person(
            "acme-agency",
            name="Bob Smith",
            email="not-an-email",
            owner_id=1,
        )


# ── (6) create_person — validates AU phone E.164 ──────────────────────────────


def test_create_person_rejects_invalid_au_phone():
    """create_person raises ValueError on non-AU E.164 phone."""
    with pytest.raises(ValueError, match="E.164"):
        pd.create_person(
            "acme-agency",
            name="Bob Smith",
            email="bob@dental.com.au",
            phone="0412345678",  # missing +61 prefix
            owner_id=1,
        )


def test_create_person_accepts_valid_au_phone():
    """create_person accepts a valid AU E.164 phone and calls the API."""
    created = {"id": 10, "name": "Bob Smith"}
    resp = _mock_response(201, {"data": created})
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp

    with patch("httpx.Client", return_value=mock_client):
        result = pd.create_person(
            "acme-agency",
            name="Bob Smith",
            email="bob@dental.com.au",
            phone="+61412345678",
            owner_id=1,
        )

    assert result == created


# ── (7) create_person — rejects empty name ────────────────────────────────────


def test_create_person_rejects_empty_name():
    """create_person raises ValueError on empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        pd.create_person(
            "acme-agency",
            name="",
            email="bob@dental.com.au",
            owner_id=1,
        )

    with pytest.raises(ValueError, match="name must not be empty"):
        pd.create_person(
            "acme-agency",
            name="   ",
            email="bob@dental.com.au",
            owner_id=1,
        )


# ── (8) create_person — rejects name >120 chars ───────────────────────────────


def test_create_person_rejects_name_over_120_chars():
    """create_person raises ValueError on name longer than 120 chars."""
    long_name = "A" * 121
    with pytest.raises(ValueError, match="120"):
        pd.create_person(
            "acme-agency",
            name=long_name,
            email="bob@dental.com.au",
            owner_id=1,
        )


def test_create_person_rejects_reserved_keys_in_custom_fields():
    """custom_fields cannot contain structural keys (name/email/phone/owner_id).

    Without this guard, body.update(custom_fields) would silently overwrite
    validated structural fields — bypassing the regex/length checks above.
    """
    with pytest.raises(ValueError, match="reserved structural keys"):
        pd.create_person(
            "acme-agency",
            name="Bob Smith",
            email="bob@dental.com.au",
            owner_id=1,
            custom_fields={"name": "Mallory"},  # would overwrite validated name
        )


# ── (9) create_deal — AUD hardcoded regression lock ───────────────────────────


def test_create_deal_currency_is_always_aud():
    """create_deal always sends currency='AUD' — regression lock for LAW II."""
    resp = _mock_response(201, {"data": {"id": 99, "currency": "AUD"}})
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp

    with patch("httpx.Client", return_value=mock_client):
        pd.create_deal(
            "acme-agency",
            title="Pymble Dental — SEO retainer",
            value=3000,
            stage_id=1,
            person_id=42,
            pipeline_id=3,
        )

    call_kwargs = mock_client.request.call_args
    sent_body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json") or {}
    assert sent_body.get("currency") == "AUD"


# ── (10) create_deal — rejects title >255 chars ───────────────────────────────


def test_create_deal_rejects_long_title():
    """create_deal raises ValueError on title longer than 255 chars."""
    with pytest.raises(ValueError, match="255"):
        pd.create_deal(
            "acme-agency",
            title="X" * 256,
            value=1000,
            stage_id=1,
            person_id=1,
            pipeline_id=1,
        )


# ── (11) verify_webhook_basic_auth — accepts valid header ─────────────────────


def test_verify_webhook_basic_auth_accepts_valid():
    """verify_webhook_basic_auth accepts a correctly formed Basic auth header."""
    user = "pipedrive-webhook"
    secret = "my-super-secret-s3cret"
    encoded = base64.b64encode(f"{user}:{secret}".encode()).decode()
    auth_header = f"Basic {encoded}"

    assert pd.verify_webhook_basic_auth(auth_header, secret) is True


# ── (12) verify_webhook_basic_auth — rejects malformed header ─────────────────


def test_verify_webhook_basic_auth_rejects_malformed():
    """verify_webhook_basic_auth returns False on malformed/missing input."""
    # None header
    assert pd.verify_webhook_basic_auth(None, "secret") is False
    # Empty header
    assert pd.verify_webhook_basic_auth("", "secret") is False
    # Wrong scheme
    assert pd.verify_webhook_basic_auth("Bearer sometoken", "secret") is False
    # Invalid base64
    assert pd.verify_webhook_basic_auth("Basic !!!not-base64!!!", "secret") is False
    # Wrong secret
    encoded = base64.b64encode(b"user:wrong-secret").decode()
    assert pd.verify_webhook_basic_auth(f"Basic {encoded}", "correct-secret") is False
