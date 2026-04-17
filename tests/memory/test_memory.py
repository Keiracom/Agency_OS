"""
FILE: tests/memory/test_memory.py
PURPOSE: Unit tests for the agent memory layer (v1 — no embeddings).
         All external HTTP calls are mocked via unittest.mock.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_UUID = str(uuid.uuid4())
FAKE_URL = "https://fake.supabase.co"
FAKE_KEY = "fake-key"

ENV_PATCH = {
    "SUPABASE_URL": FAKE_URL,
    "SUPABASE_SERVICE_KEY": FAKE_KEY,
}


def _fake_memory_row(**overrides) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "id": FAKE_UUID,
        "callsign": "aiden",
        "source_type": "pattern",
        "content": "test content",
        "typed_metadata": {},
        "tags": ["test"],
        "valid_from": now,
        "valid_to": None,
        "created_at": now,
    }
    base.update(overrides)
    return base


def _mock_response(status_code: int = 201, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else [_fake_memory_row()]
    resp.text = "ok"
    return resp


# ---------------------------------------------------------------------------
# store() tests
# ---------------------------------------------------------------------------

class TestStore:

    def test_store_validates_source_type(self):
        """Invalid source_type raises ValueError before any HTTP call."""
        from src.memory.store import store
        with pytest.raises(ValueError, match="Invalid source_type"):
            store("aiden", "not_a_valid_type", "content")

    def test_store_calls_supabase_without_embedding(self):
        """Payload sent to Supabase must NOT contain an embedding field."""
        from src.memory.store import store

        with patch.dict("os.environ", ENV_PATCH):
            with patch("src.memory.ratelimit.check_and_increment", return_value=1):
                with patch("httpx.post", return_value=_mock_response()) as mock_post:
                    store("aiden", "pattern", "some content", tags=["t1"])

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        assert "embedding" not in payload, "embedding must not appear in v1 payload"
        assert "vector" not in payload, "vector must not appear in v1 payload"

    def test_store_returns_uuid(self):
        """store() returns a uuid.UUID matching the inserted row id."""
        from src.memory.store import store

        with patch.dict("os.environ", ENV_PATCH):
            with patch("src.memory.ratelimit.check_and_increment", return_value=1):
                with patch("httpx.post", return_value=_mock_response(201, [_fake_memory_row(id=FAKE_UUID)])):
                    result = store("aiden", "decision", "a decision")

        assert isinstance(result, uuid.UUID)
        assert str(result) == FAKE_UUID

    def test_store_rate_limit(self):
        """RateLimitExceeded propagates before any HTTP call."""
        from src.memory.store import store
        from src.memory.types import RateLimitExceeded

        with patch("src.memory.ratelimit.check_and_increment", side_effect=RateLimitExceeded("cap")):
            with pytest.raises(RateLimitExceeded):
                store("aiden", "pattern", "content")

    def test_store_wraps_httpx_errors(self):
        """Non-2xx response from Supabase raises RuntimeError."""
        from src.memory.store import store

        with patch.dict("os.environ", ENV_PATCH):
            with patch("src.memory.ratelimit.check_and_increment", return_value=1):
                with patch("httpx.post", return_value=_mock_response(500, {})):
                    with pytest.raises(RuntimeError, match="Supabase returned 500"):
                        store("aiden", "research", "content")

    def test_store_defaults_valid_from_if_none(self):
        """When valid_from is None, the payload omits valid_from (DB DEFAULT fires)."""
        from src.memory.store import store

        with patch.dict("os.environ", ENV_PATCH):
            with patch("src.memory.ratelimit.check_and_increment", return_value=1):
                with patch("httpx.post", return_value=_mock_response()) as mock_post:
                    store("aiden", "pattern", "content", valid_from=None)

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        assert "valid_from" not in payload, "valid_from must be omitted when None so DB DEFAULT fires"


# ---------------------------------------------------------------------------
# retrieve() tests
# ---------------------------------------------------------------------------

class TestRetrieve:

    def _run_retrieve(self, **kwargs):
        """Helper: patch env + httpx.get, run retrieve(), return (result, mock_get)."""
        from src.memory.retrieve import retrieve

        rows = [_fake_memory_row()]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = rows

        with patch.dict("os.environ", ENV_PATCH):
            with patch("httpx.get", return_value=mock_resp) as mock_get:
                result = retrieve(**kwargs)
        return result, mock_get

    def test_retrieve_by_type(self):
        """types filter produces source_type=in.(...) in query string."""
        result, mock_get = self._run_retrieve(types=["pattern", "decision"])
        url = mock_get.call_args[0][0]
        assert "source_type=in.(pattern,decision)" in url

    def test_retrieve_by_callsign(self):
        """callsigns filter produces callsign=in.(...) in query string."""
        result, mock_get = self._run_retrieve(callsigns=["aiden", "elliot"])
        url = mock_get.call_args[0][0]
        assert "callsign=in.(aiden,elliot)" in url

    def test_retrieve_by_tag_any(self):
        """tag_mode='any' produces tags=ov.{...} operator in query string."""
        result, mock_get = self._run_retrieve(tags=["memory", "test"], tag_mode="any")
        url = mock_get.call_args[0][0]
        assert "tags=ov.{memory,test}" in url

    def test_retrieve_by_tag_all(self):
        """tag_mode='all' produces tags=cs.{...} operator in query string."""
        result, mock_get = self._run_retrieve(tags=["memory", "test"], tag_mode="all")
        url = mock_get.call_args[0][0]
        assert "tags=cs.{memory,test}" in url

    def test_retrieve_content_contains(self):
        """content_contains produces ilike filter with wildcards."""
        result, mock_get = self._run_retrieve(content_contains="decision point")
        url = mock_get.call_args[0][0]
        assert "content=ilike.*decision" in url

    def test_retrieve_time_range(self):
        """since/until produce created_at gte/lte filters."""
        since = datetime(2026, 1, 1, tzinfo=timezone.utc)
        until = datetime(2026, 4, 1, tzinfo=timezone.utc)
        result, mock_get = self._run_retrieve(since=since, until=until)
        url = mock_get.call_args[0][0]
        assert "created_at=gte." in url
        assert "created_at=lte." in url


# ---------------------------------------------------------------------------
# recall() tests
# ---------------------------------------------------------------------------

class TestRecall:

    def _make_rows(self, types: list[str]) -> list[dict]:
        rows = []
        for st in types:
            rows.append(_fake_memory_row(
                id=str(uuid.uuid4()),
                source_type=st,
                content=f"Content about {st}",
            ))
        return rows

    def test_recall_with_topic_groups_by_type(self):
        """recall(topic=...) merges content + tag results and groups by source_type."""
        from src.memory.recall import recall

        mixed_rows = self._make_rows(["pattern", "decision", "research"])
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mixed_rows

        with patch.dict("os.environ", ENV_PATCH):
            with patch("httpx.get", return_value=mock_resp):
                result = recall(topic="test topic")

        assert isinstance(result, dict)
        # Every key should be a valid source_type, every value a list
        for key, val in result.items():
            assert isinstance(key, str)
            assert isinstance(val, list)
            assert len(val) > 0

    def test_recall_bare_returns_high_value_types(self):
        """recall(topic=None) calls retrieve with high-value types only."""
        from src.memory.recall import recall
        from src.memory import retrieve as mem_retrieve

        rows = self._make_rows(["pattern", "skill"])
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = rows

        with patch.dict("os.environ", ENV_PATCH):
            with patch("httpx.get", return_value=mock_resp) as mock_get:
                result = recall(topic=None)

        # Should only have called retrieve once (high-value path)
        assert mock_get.call_count == 1
        url = mock_get.call_args[0][0]
        # High-value types should be in the query
        assert "source_type=in." in url
        for ht in ["pattern", "decision", "skill", "dave_confirmed"]:
            assert ht in url
