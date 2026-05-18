"""Regression: ceo_memory_indexer.main() must pass prepare_threshold=None to psycopg.connect.

Agency_OS-hzk5 — ceo_memory_indexer.py has its OWN main() that bypasses
indexer_base.run_db_indexer (predates KEI-109 dedup extraction), so PR #1046's
fix to indexer_base did NOT reach this file. Decisions count was stuck at 300
across multiple restarts because every batch after the first ~5 executions
hit DuplicatePreparedStatement against the Supabase pgbouncer pool.

Locks the fix in place at the second site so a future refactor can't silently
drop the kwarg from this main() either. Pattern mirrors
test_indexer_base_prepare_threshold_kei70st (PR #1046).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import ceo_memory_indexer as mod  # noqa: E402


def test_ceo_memory_indexer_main_passes_prepare_threshold_none(monkeypatch):
    """ceo_memory_indexer.main() must call psycopg.connect with prepare_threshold=None."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setattr(sys, "argv", ["ceo_memory_indexer", "--once"])

    captured_kwargs: dict = {}

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return mock.MagicMock()

    def _fake_connect(dsn, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["_dsn"] = dsn
        return _FakeConn()

    monkeypatch.setattr(mod.psycopg, "connect", _fake_connect)
    monkeypatch.setattr(mod, "_heartbeat_tick", mock.MagicMock())
    monkeypatch.setattr(mod, "aggregate_count", lambda _c: 0)

    fake_indexer = mock.MagicMock()
    fake_indexer.ensure_target_class.return_value = None
    fake_indexer.index_once.return_value = mock.MagicMock(
        success=0,
        failed=0,
        to_dict=lambda: {"selected": 0, "success": 0, "failed": 0},
    )
    monkeypatch.setattr(mod, "CeoMemoryIndexer", lambda _conn: fake_indexer)

    mod.main()

    assert "prepare_threshold" in captured_kwargs, (
        "psycopg.connect called without prepare_threshold kwarg — "
        "Supabase pgbouncer will drop PREPARE between leases and trigger "
        "DuplicatePreparedStatement after ~5 batches (see Agency_OS-hzk5)."
    )
    assert captured_kwargs["prepare_threshold"] is None, (
        f"prepare_threshold must be None to disable psycopg3 auto-prepare, "
        f"got: {captured_kwargs['prepare_threshold']!r}"
    )
    assert captured_kwargs.get("autocommit") is True
