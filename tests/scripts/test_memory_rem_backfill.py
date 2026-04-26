"""
P10 — Tests for scripts/memory_rem_backfill.py.

Pure mocks — no real Supabase. Confirms:
  - fetch_old_daily_logs query parameters (cutoff direction + bounded
    vs unbounded LIMIT branch)
  - _chunked yields full + partial windows
  - replay() promotes only memories with composite >= min_score
  - replay() obeys max_rows cap (via fetch limit) + batch_size
  - replay() respects OC1 idempotency: when promote_to_core_fact returns
    False (guard skipped), 'skipped_dup_guard' increments
  - replay() in dry-run never invokes a real DB write through the
    promote_to_core_fact stub
  - render_human surfaces all four counts
  - CLI rejects negative thresholds + zero batch size
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "memory_rem_backfill.py"
_spec = importlib.util.spec_from_file_location("memory_rem_backfill", _SCRIPT)
rem = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["memory_rem_backfill"] = rem
_spec.loader.exec_module(rem)


def _row(i: int, content: str = "filler entry"):
    return {
        "id":           f"00000000-0000-0000-0000-{i:012d}",
        "content":      content,
        "content_hash": f"hash-{i}",
        "type":         "daily_log",
        "created_at":   datetime(2026, 1, 1, tzinfo=UTC),
        "metadata":     {},
    }


# ─── _chunked ──────────────────────────────────────────────────────────────

def test_chunked_yields_full_and_partial_windows():
    out = list(rem._chunked(list(range(7)), 3))
    assert out == [[0, 1, 2], [3, 4, 5], [6]]


def test_chunked_empty_list():
    assert list(rem._chunked([], 5)) == []


# ─── fetch_old_daily_logs ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_old_daily_logs_unbounded_branch():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_row(0), _row(1)])
    out = await rem.fetch_old_daily_logs(
        conn, age_threshold_days=7, max_rows=0,
    )
    assert len(out) == 2
    sql = conn.fetch.await_args.args[0]
    # Cold query uses < cutoff (older-than) — NOT >= cutoff
    assert "created_at < $1" in sql
    assert "LIMIT" not in sql  # unbounded branch


@pytest.mark.asyncio
async def test_fetch_old_daily_logs_bounded_branch():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_row(0)])
    await rem.fetch_old_daily_logs(
        conn, age_threshold_days=14, max_rows=500,
    )
    sql, *args = conn.fetch.await_args.args
    assert "LIMIT $2" in sql
    assert args[1] == 500


# ─── replay() — scoring + promotion routing ────────────────────────────────

@pytest.fixture
def patch_score(monkeypatch):
    """Score every memory at 0.7 by default; first arg of fetched list
    flagged at composite 0.4 to test below-threshold skip."""
    def _score(memories):
        for i, m in enumerate(memories):
            m.composite = 0.4 if i == 0 else 0.7
            m.factors = {"r": 1.0}
    monkeypatch.setattr(rem, "score", _score)
    return _score


@pytest.mark.asyncio
async def test_replay_promotes_only_above_threshold(monkeypatch, patch_score):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_row(i) for i in range(3)])
    promote = AsyncMock(return_value=True)
    monkeypatch.setattr(rem, "promote_to_core_fact", promote)

    result = await rem.replay(
        conn, age_threshold_days=7, min_score=0.6,
        batch_size=10, max_rows=0, dry_run=True,
    )

    assert result["scanned"] == 3
    assert result["above_threshold"] == 2  # 0th below threshold
    assert result["promoted"] == 2
    assert result["skipped_dup_guard"] == 0
    # promote called exactly twice (only above-threshold rows)
    assert promote.await_count == 2


@pytest.mark.asyncio
async def test_replay_counts_idempotency_skip(monkeypatch, patch_score):
    """When promote_to_core_fact returns False (OC1 WHERE NOT EXISTS
    skipped the row), the count moves to skipped_dup_guard."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_row(i) for i in range(3)])
    # First above-threshold row inserts; second already exists in DB.
    promote = AsyncMock(side_effect=[True, False])
    monkeypatch.setattr(rem, "promote_to_core_fact", promote)

    result = await rem.replay(
        conn, age_threshold_days=7, min_score=0.6,
        batch_size=10, max_rows=0, dry_run=False,
    )
    assert result["above_threshold"] == 2
    assert result["promoted"] == 1
    assert result["skipped_dup_guard"] == 1


@pytest.mark.asyncio
async def test_replay_chunks_into_batches(monkeypatch):
    """batch_size=2 over 5 rows → 3 batches → 3 score() invocations."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_row(i) for i in range(5)])
    promote = AsyncMock(return_value=True)
    monkeypatch.setattr(rem, "promote_to_core_fact", promote)

    score_calls = {"n": 0}

    def _score(batch):
        score_calls["n"] += 1
        for m in batch:
            m.composite = 1.0  # everything passes

    monkeypatch.setattr(rem, "score", _score)

    result = await rem.replay(
        conn, age_threshold_days=7, min_score=0.6,
        batch_size=2, max_rows=0, dry_run=True,
    )
    assert score_calls["n"] == 3
    assert result["scanned"] == 5
    assert result["promoted"] == 5


@pytest.mark.asyncio
async def test_replay_dry_run_passes_flag_to_promote(monkeypatch, patch_score):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_row(0)])
    captured = {"dry_run": None}

    async def fake_promote(conn, m, *, dry_run):
        captured["dry_run"] = dry_run
        return True

    monkeypatch.setattr(rem, "score", lambda batch: setattr(batch[0], "composite", 0.9))
    monkeypatch.setattr(rem, "promote_to_core_fact", fake_promote)

    await rem.replay(conn, age_threshold_days=7, min_score=0.6,
                     batch_size=10, max_rows=0, dry_run=True)
    assert captured["dry_run"] is True


# ─── render_human ──────────────────────────────────────────────────────────

def test_render_human_surfaces_all_counts():
    result = {
        "scanned": 100, "above_threshold": 40,
        "promoted": 30, "skipped_dup_guard": 10,
        "age_threshold_days": 7, "min_score": 0.6,
        "batch_size": 200, "max_rows": "unbounded",
        "top_promotions": [],
    }
    out = rem.render_human(result, dry_run=True)
    assert "DRY-RUN" in out
    assert "scanned (cold daily_log):           100" in out
    assert "above promotion threshold:          40" in out
    assert "promoted (new core_fact rows):      30" in out
    assert "skipped by OC1 idempotency guard:   10" in out


def test_render_human_lists_top_promotions():
    result = {
        "scanned": 1, "above_threshold": 1, "promoted": 1, "skipped_dup_guard": 0,
        "age_threshold_days": 7, "min_score": 0.6,
        "batch_size": 200, "max_rows": "unbounded",
        "top_promotions": [
            {"id": "abcdef12-...", "composite": 0.9,
             "created": "2026-04-01", "preview": "Session ended..."},
        ],
    }
    out = rem.render_human(result, dry_run=False)
    assert "EXECUTE" in out
    assert "0.900" in out
    assert "Session ended..." in out


# ─── CLI guards ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cli_rejects_negative_age_threshold():
    rc = await rem.main(["--age-threshold-days", "-1"])
    assert rc == 2


@pytest.mark.asyncio
async def test_cli_rejects_zero_batch_size():
    rc = await rem.main(["--batch-size", "0"])
    assert rc == 2
