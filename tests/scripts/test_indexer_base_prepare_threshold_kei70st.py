"""Regression: run_db_indexer must pass prepare_threshold=None to psycopg.connect.

KEI-70st root cause was Supabase pgbouncer txn-mode dropping PREPARE between
leases. Without prepare_threshold=None, psycopg3 auto-prepares after 5
executions and the next batch hits DuplicatePreparedStatement, then
InvalidSqlStatementName forever. Locks the fix in place so a future
refactor can't silently drop the kwarg.

Pattern mirrors reference_psycopg_supabase_pgbouncer (PR #881 / KEI-54B).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))


def test_run_db_indexer_passes_prepare_threshold_none(monkeypatch):
    """psycopg.connect must be called with prepare_threshold=None."""
    import indexer_base as mod  # noqa: PLC0415

    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setattr(sys, "argv", ["indexer_base_test", "--once"])

    captured_kwargs: dict = {}

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_connect(dsn, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["_dsn"] = dsn
        return _FakeConn()

    def _fake_indexer_factory(conn):
        indexer = mock.MagicMock()
        indexer.source_name = "test"
        indexer.target_class = "TestClass"
        indexer.ensure_target_class.return_value = None
        indexer.index_once.return_value = mod.BatchOutcome(selected=0, success=0, failed=0)
        return indexer

    fake_psycopg = mock.MagicMock()
    fake_psycopg.connect = _fake_connect
    fake_heartbeat_shim = mock.MagicMock()
    fake_heartbeat_shim.heartbeat_tick = mock.MagicMock()

    with (
        mock.patch.dict(
            sys.modules, {"psycopg": fake_psycopg, "_heartbeat_shim": fake_heartbeat_shim}
        ),
        mock.patch.object(mod, "aggregate_count", return_value=0),
    ):
        mod.run_db_indexer(
            _fake_indexer_factory,
            unit_name="test-unit",
            default_batch=10,
            poll_seconds=1,
        )

    assert "prepare_threshold" in captured_kwargs, (
        "psycopg.connect called without prepare_threshold kwarg — "
        "Supabase pgbouncer will drop PREPARE between leases and trigger "
        "DuplicatePreparedStatement after ~5 batches (see KEI-70st)."
    )
    assert captured_kwargs["prepare_threshold"] is None, (
        f"prepare_threshold must be None to disable psycopg3 auto-prepare, "
        f"got: {captured_kwargs['prepare_threshold']!r}"
    )
    assert captured_kwargs.get("autocommit") is True
