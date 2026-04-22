"""
tests/test_schema_f1.py — Unit tests for SCHEMA-F1 promotion wiring.

Covers:
  1. Promotion sets promoted_from_id correctly (+ typed_metadata keys)
  2. Below-threshold access does NOT set promoted_from_id
  3. Already-confirmed row does NOT get promoted_from_id
"""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# PROMOTION_ACCESS_THRESHOLD is 3 — imported from module
from src.telegram_bot.memory_listener import (
    PROMOTION_ACCESS_THRESHOLD,
    _increment_access_counts,
)

FAKE_URL = "https://fake.supabase.co"
FAKE_KEY = "fake-service-key"

HEADERS = {
    "apikey": FAKE_KEY,
    "Authorization": f"Bearer {FAKE_KEY}",
    "Content-Type": "application/json",
}


def _make_row(
    state: str = "tentative",
    access_count: int = 0,
    typed_metadata: dict | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "state": state,
        "access_count": access_count,
        "typed_metadata": typed_metadata or {},
    }


def _run(coro):
    """Helper: run async coroutine in test."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class TestPromotionSetsPromotedFromId:
    """
    Test 1: access_count reaches PROMOTION_ACCESS_THRESHOLD (2 + 1 = 3).
    Expect payload to include promoted_from_id = row['id'],
    typed_metadata with promoted_at and promoted_from_state.
    """

    def test_payload_includes_promoted_from_id(self):
        row = _make_row(state="tentative", access_count=PROMOTION_ACCESS_THRESHOLD - 1)
        captured_payloads = []

        mock_response = MagicMock()
        mock_response.status_code = 204

        async def fake_patch(url, headers, json):
            captured_payloads.append(json)
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = fake_patch

        env = {"SUPABASE_URL": FAKE_URL, "SUPABASE_SERVICE_KEY": FAKE_KEY}

        with patch("src.telegram_bot.memory_listener.SUPABASE_URL", FAKE_URL), \
             patch("src.telegram_bot.memory_listener.SUPABASE_KEY", FAKE_KEY), \
             patch("httpx.AsyncClient", return_value=mock_client):
            _run(_increment_access_counts([row], HEADERS))

        assert len(captured_payloads) == 1
        payload = captured_payloads[0]

        assert payload.get("state") == "confirmed", \
            f"Expected state='confirmed', got {payload.get('state')!r}"
        assert payload.get("promoted_from_id") == row["id"], \
            f"Expected promoted_from_id={row['id']!r}, got {payload.get('promoted_from_id')!r}"

        meta = payload.get("typed_metadata", {})
        assert "promoted_at" in meta, \
            f"Expected 'promoted_at' in typed_metadata, got keys: {list(meta.keys())}"
        assert meta.get("promoted_from_state") == "tentative", \
            f"Expected promoted_from_state='tentative', got {meta.get('promoted_from_state')!r}"

    def test_promoted_at_is_iso_timestamp(self):
        """promoted_at must be a parseable ISO 8601 string."""
        row = _make_row(state="tentative", access_count=PROMOTION_ACCESS_THRESHOLD - 1)
        captured_payloads = []

        mock_response = MagicMock()
        mock_response.status_code = 204

        async def fake_patch(url, headers, json):
            captured_payloads.append(json)
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = fake_patch

        with patch("src.telegram_bot.memory_listener.SUPABASE_URL", FAKE_URL), \
             patch("src.telegram_bot.memory_listener.SUPABASE_KEY", FAKE_KEY), \
             patch("httpx.AsyncClient", return_value=mock_client):
            _run(_increment_access_counts([row], HEADERS))

        meta = captured_payloads[0].get("typed_metadata", {})
        promoted_at = meta.get("promoted_at", "")
        # Must parse without exception
        datetime.fromisoformat(promoted_at)

    def test_existing_typed_metadata_preserved(self):
        """Existing typed_metadata keys must be merged, not overwritten."""
        existing_meta = {"some_existing_key": "some_value"}
        row = _make_row(
            state="tentative",
            access_count=PROMOTION_ACCESS_THRESHOLD - 1,
            typed_metadata=existing_meta,
        )
        captured_payloads = []

        mock_response = MagicMock()
        mock_response.status_code = 204

        async def fake_patch(url, headers, json):
            captured_payloads.append(json)
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = fake_patch

        with patch("src.telegram_bot.memory_listener.SUPABASE_URL", FAKE_URL), \
             patch("src.telegram_bot.memory_listener.SUPABASE_KEY", FAKE_KEY), \
             patch("httpx.AsyncClient", return_value=mock_client):
            _run(_increment_access_counts([row], HEADERS))

        meta = captured_payloads[0].get("typed_metadata", {})
        assert meta.get("some_existing_key") == "some_value", \
            "Existing typed_metadata keys must survive the merge"


class TestBelowThresholdNoPromotion:
    """
    Test 2: access_count=0 → new_count=1, below threshold=3.
    promoted_from_id must NOT appear in payload.
    """

    def test_below_threshold_no_promoted_from_id(self):
        row = _make_row(state="tentative", access_count=0)
        captured_payloads = []

        mock_response = MagicMock()
        mock_response.status_code = 204

        async def fake_patch(url, headers, json):
            captured_payloads.append(json)
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = fake_patch

        with patch("src.telegram_bot.memory_listener.SUPABASE_URL", FAKE_URL), \
             patch("src.telegram_bot.memory_listener.SUPABASE_KEY", FAKE_KEY), \
             patch("httpx.AsyncClient", return_value=mock_client):
            _run(_increment_access_counts([row], HEADERS))

        assert len(captured_payloads) == 1
        payload = captured_payloads[0]

        assert "promoted_from_id" not in payload, \
            f"promoted_from_id should NOT be in payload below threshold, got {payload}"
        assert payload.get("state") != "confirmed", \
            "state should NOT be 'confirmed' below threshold"


class TestAlreadyConfirmedNoPromotion:
    """
    Test 3: state='confirmed', access_count=5 → high count but already confirmed.
    promoted_from_id must NOT appear in payload (no re-promotion).
    """

    def test_confirmed_row_no_promoted_from_id(self):
        row = _make_row(state="confirmed", access_count=5)
        captured_payloads = []

        mock_response = MagicMock()
        mock_response.status_code = 204

        async def fake_patch(url, headers, json):
            captured_payloads.append(json)
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.patch = fake_patch

        with patch("src.telegram_bot.memory_listener.SUPABASE_URL", FAKE_URL), \
             patch("src.telegram_bot.memory_listener.SUPABASE_KEY", FAKE_KEY), \
             patch("httpx.AsyncClient", return_value=mock_client):
            _run(_increment_access_counts([row], HEADERS))

        assert len(captured_payloads) == 1
        payload = captured_payloads[0]

        assert "promoted_from_id" not in payload, \
            f"promoted_from_id should NOT be in payload for confirmed row, got {payload}"
        # access_count should still increment
        assert payload.get("access_count") == 6, \
            f"access_count should increment to 6 regardless, got {payload.get('access_count')}"
