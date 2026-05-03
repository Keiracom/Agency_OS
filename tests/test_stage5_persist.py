"""
Tests for _persist_stage5_to_bu in cohort_runner.

Verifies:
1. propensity_score (composite_score) is written to business_universe
2. stage_metrics includes stage5 JSONB data
3. scored_at is set (NOW() in SQL)
4. DB error does not crash the pipeline (fail-safe)
5. DATABASE_URL missing is handled gracefully
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.orchestration.cohort_runner import _persist_stage5_to_bu

SAMPLE_SCORES = {
    "composite_score": 72,
    "budget_score": 18,
    "pain_score": 20,
    "fit_score": 17,
    "reachability_score": 17,
    "is_viable_prospect": True,
    "viability_reason": "viable",
}


def _make_asyncpg_conn_mock():
    """Return a mock asyncpg connection that records execute calls."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.close = AsyncMock(return_value=None)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


class TestPersistStage5ToBu:
    """Verify _persist_stage5_to_bu writes correct columns."""

    @pytest.mark.asyncio
    async def test_writes_propensity_score(self):
        """composite_score must be passed as the propensity_score positional arg ($3)."""
        conn = _make_asyncpg_conn_mock()
        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake/db"}),
            patch("asyncpg.connect", AsyncMock(return_value=conn)),
        ):
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)

        conn.execute.assert_awaited_once()
        args = conn.execute.call_args[0]
        # $1=domain, $2=display_name, $3=composite, $4=budget, $5=pain, $6=fit, $7=reachability, $8=stage5_jsonb
        assert args[1] == "example.com.au", "domain mismatch"
        assert args[3] == 72, f"propensity_score (composite) should be 72, got {args[3]}"
        assert args[4] == 18, f"budget_score should be 18, got {args[4]}"
        assert args[5] == 20, f"pain_score should be 20, got {args[5]}"
        assert args[6] == 17, f"fit_score should be 17, got {args[6]}"
        assert args[7] == 17, f"reachability_score should be 17, got {args[7]}"

    @pytest.mark.asyncio
    async def test_stage_metrics_contains_stage5_jsonb(self):
        """stage_metrics JSONB arg must be a JSON string with a 'stage5' key."""
        conn = _make_asyncpg_conn_mock()
        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake/db"}),
            patch("asyncpg.connect", AsyncMock(return_value=conn)),
        ):
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)

        args = conn.execute.call_args[0]
        # $8 is the JSONB arg
        stage_metrics_arg = args[8]
        parsed = json.loads(stage_metrics_arg)
        assert "stage5" in parsed, f"stage_metrics must contain 'stage5' key, got: {parsed.keys()}"
        assert parsed["stage5"]["composite_score"] == 72

    @pytest.mark.asyncio
    async def test_scored_at_is_set_via_now(self):
        """The SQL must include scored_at = NOW() — check SQL text contains scored_at."""
        conn = _make_asyncpg_conn_mock()
        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake/db"}),
            patch("asyncpg.connect", AsyncMock(return_value=conn)),
        ):
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)

        sql = conn.execute.call_args[0][0]
        assert "scored_at" in sql, "SQL must reference scored_at column"
        assert "NOW()" in sql, "SQL must set scored_at to NOW()"

    @pytest.mark.asyncio
    async def test_db_error_does_not_raise(self):
        """A DB connection failure must be swallowed — pipeline must not crash."""
        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake/db"}),
            patch(
                "asyncpg.connect",
                AsyncMock(side_effect=OSError("connection refused")),
            ),
        ):
            # Must not raise anything
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)

    @pytest.mark.asyncio
    async def test_missing_database_url_skips_silently(self):
        """If DATABASE_URL is not set, function must return without calling asyncpg."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("asyncpg.connect") as mock_connect,
        ):
            # Remove DATABASE_URL if present
            import os as _os

            _os.environ.pop("DATABASE_URL", None)
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)

        mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_on_first_failure_succeeds(self):
        """First connect fails, retry succeeds — no exception raised, execute called once on retry."""
        conn_ok = _make_asyncpg_conn_mock()
        calls = {"n": 0}

        async def connect_side_effect(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("transient error")
            return conn_ok

        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake/db"}),
            patch("asyncpg.connect", side_effect=connect_side_effect),
            patch("asyncio.sleep", AsyncMock()),
        ):
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)

        conn_ok.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_both_retries_fail_no_exception(self):
        """Both connect attempts fail — must not raise, just log error."""
        with (
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://fake/db"}),
            patch("asyncpg.connect", AsyncMock(side_effect=OSError("always fails"))),
            patch("asyncio.sleep", AsyncMock()),
        ):
            # Must not raise
            await _persist_stage5_to_bu("example.com.au", SAMPLE_SCORES)
