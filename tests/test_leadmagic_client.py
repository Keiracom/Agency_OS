# tests/test_leadmagic_client.py
# PURPOSE: Tests for src/integrations/leadmagic.py — LeadmagicClient
# DIRECTIVE: #251 — all mocks, no live API calls

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.integrations.leadmagic import (
    LeadmagicClient,
    EmailFinderResult,
    MobileFinderResult,
    EmailStatus,
    MobileStatus,
    COST_EMAIL_FINDER_AUD,
    COST_MOBILE_FINDER_AUD,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture(autouse=True)
def disable_mock_mode():
    """
    Ensure LEADMAGIC_MOCK is NOT active for these tests.
    test_leadmagic_mock.py sets os.environ['LEADMAGIC_MOCK']='true' at module-level,
    which pollutes later tests when running the full suite.
    We patch _is_mock_mode to return False for all tests in this module.
    """
    with patch("src.integrations.leadmagic._is_mock_mode", return_value=False):
        yield


@pytest.fixture
def client():
    """LeadmagicClient with a fake API key (no mock mode — we mock _request)."""
    return LeadmagicClient(api_key="test-api-key-fake")


# ============================================================
# TEST 1: find_email — success (email found)
# ============================================================


@pytest.mark.asyncio
async def test_find_email_success(client):
    """find_email() returns EmailFinderResult with found=True and email set."""
    mock_response = {
        "email": "john.doe@example.com.au",
        "status": "valid",
        "confidence": 90,
        "first_name": "John",
        "last_name": "Doe",
        "domain": "example.com.au",
        "company": "Acme",
        "position": "CEO",
        "linkedin_url": None,
    }

    with patch.object(client, "_request", new=AsyncMock(return_value=mock_response)):
        result = await client.find_email("John", "Doe", "example.com.au", "Acme")

    assert result.found is True
    assert result.email == "john.doe@example.com.au"
    assert result.status == EmailStatus.VALID
    assert result.confidence == 90


# ============================================================
# TEST 2: find_email — not found (empty email in response)
# ============================================================


@pytest.mark.asyncio
async def test_find_email_not_found(client):
    """find_email() returns found=False when API response has no email."""
    mock_response = {
        "email": None,
        "status": "unknown",
        "confidence": 0,
    }

    with patch.object(client, "_request", new=AsyncMock(return_value=mock_response)):
        result = await client.find_email("Jane", "Doe", "noemail.com", "Corp")

    assert result.found is False
    assert result.email is None


# ============================================================
# TEST 3: find_mobile — success
# ============================================================


@pytest.mark.asyncio
async def test_find_mobile_success(client):
    """find_mobile() returns MobileFinderResult with found=True and mobile_number set."""
    mock_response = {
        "mobile": "+61400000001",
        "status": "verified",
        "confidence": 88,
        "first_name": "John",
        "last_name": "Doe",
        "title": "CEO",
        "company": "Acme",
        "linkedin_url": "https://linkedin.com/in/john-doe",
    }

    with patch.object(client, "_request", new=AsyncMock(return_value=mock_response)):
        result = await client.find_mobile("https://linkedin.com/in/john-doe")

    assert result.found is True
    assert result.mobile_number == "+61400000001"
    assert result.mobile_confidence == 88
    assert result.status == MobileStatus.VERIFIED


# ============================================================
# TEST 4: find_email not found returns falsy / found == False
# ============================================================


@pytest.mark.asyncio
async def test_find_email_not_found_returns_falsy(client):
    """find_email() with not-found response: result.found is falsy."""
    mock_response = {
        "email": "",
        "status": "invalid",
        "confidence": 0,
    }

    with patch.object(client, "_request", new=AsyncMock(return_value=mock_response)):
        result = await client.find_email("No", "Body", "nothing.com.au")

    # empty string is falsy; found should be False
    assert not result.found


# ============================================================
# TEST 5: cost tracking accumulates correctly
# ============================================================


@pytest.mark.asyncio
async def test_cost_tracking(client):
    """After 2 find_email (found) + 1 find_mobile (found), total_cost_aud is correct."""
    email_response_found = {
        "email": "test@example.com",
        "status": "valid",
        "confidence": 85,
    }
    mobile_response_found = {
        "mobile": "+61400123456",
        "status": "verified",
        "confidence": 90,
    }

    # Reset cost to be safe
    client.reset_cost_tracking()

    with patch.object(
        client,
        "_request",
        new=AsyncMock(
            side_effect=[
                email_response_found,
                email_response_found,
                mobile_response_found,
            ]
        ),
    ):
        await client.find_email("Alice", "Smith", "example.com")
        await client.find_email("Bob", "Jones", "example.com")
        await client.find_mobile("https://linkedin.com/in/test")

    expected_min = 2 * COST_EMAIL_FINDER_AUD + COST_MOBILE_FINDER_AUD
    assert client.total_cost_aud >= expected_min - 0.0001
    assert client.total_cost_aud == pytest.approx(
        2 * COST_EMAIL_FINDER_AUD + COST_MOBILE_FINDER_AUD, abs=0.0001
    )
