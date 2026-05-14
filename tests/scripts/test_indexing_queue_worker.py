"""tests for scripts/indexing_queue_worker.py — KEI-61 durable staging buffer.

Mocks psycopg.connect so tests don't reach Supabase. Verifies:
  - DSN env var pickup (DATABASE_URL preferred, SUPABASE_DB_URL fallback)
  - processor_id env override
  - claim_batch invokes the SQL function with (batch_size, processor)
  - reset_stuck returns the row count
  - process_row stub backend returns a well-formed audit dict
  - process_row raises for unknown backend
  - mark_done writes UPDATE + audit INSERT
  - mark_failed flips to 'failed' at the max-attempts threshold
  - mark_failed flips back to 'pending' before threshold
  - run() iterates max_iterations and exits clean
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "indexing_queue_worker.py"

# Shared psycopg fakes (Aiden's KEI-54 amend extracted these; KEI-61 reuses).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeConn, FakeCursor  # type: ignore[import-not-found]  # noqa: E402

_Cursor = FakeCursor  # legacy alias kept for the existing test bodies below


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("indexing_queue_worker", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["indexing_queue_worker"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def patch_connect(mod, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    def _patch(cur: FakeCursor):
        import psycopg

        monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: FakeConn(cur))
        return cur

    return _patch


# ─── env helpers ───────────────────────────────────────────────────────────────


def test_dsn_prefers_database_url(mod, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://primary/x")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback/x")
    assert mod._dsn() == "postgresql://primary/x"


def test_dsn_falls_back_to_supabase_db_url(mod, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback/x")
    assert mod._dsn() == "postgresql://fallback/x"


def test_dsn_rewrites_asyncpg_driver(mod, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert mod._dsn() == "postgresql://x"


def test_dsn_missing_raises(mod, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(SystemExit):
        mod._dsn()


def test_processor_id_env_override(mod, monkeypatch) -> None:
    monkeypatch.setenv("INDEXING_WORKER_ID", "kei61-test-worker-1")
    assert mod._processor_id() == "kei61-test-worker-1"


def test_processor_id_default_includes_pid(mod, monkeypatch) -> None:
    monkeypatch.delenv("INDEXING_WORKER_ID", raising=False)
    pid = mod._processor_id()
    assert "." in pid  # hostname.pid pattern


# ─── claim_batch ───────────────────────────────────────────────────────────────


def test_claim_batch_invokes_sql_function(mod, patch_connect, monkeypatch) -> None:
    cur = _Cursor(
        fetchall_rows=[
            ("uuid-1", "linear", {"foo": "bar"}, "pending", 1, None, "proc-1", None, None, None),
        ],
        description=[
            ("id",),
            ("source",),
            ("payload",),
            ("status",),
            ("attempts",),
            ("error",),
            ("processor",),
            ("created_at",),
            ("processed_at",),
            ("indexed_at",),
        ],
    )
    patch_connect(cur)
    import psycopg

    with psycopg.connect("ignored") as conn:
        batch = mod.claim_batch(conn, batch_size=5, processor="proc-1")
    assert len(batch) == 1
    assert batch[0].id == "uuid-1"
    assert batch[0].source == "linear"
    assert batch[0].attempts == 1
    # Last execute call: claim_queue_batch(5, 'proc-1')
    assert "claim_queue_batch" in cur.executed[-1][0]
    assert cur.executed[-1][1] == (5, "proc-1")


def test_claim_batch_empty_returns_empty(mod, patch_connect) -> None:
    cur = _Cursor(fetchall_rows=[], description=[("id",)])
    patch_connect(cur)
    import psycopg

    with psycopg.connect("ignored") as conn:
        batch = mod.claim_batch(conn, 5, "proc")
    assert batch == []


# ─── reset_stuck ───────────────────────────────────────────────────────────────


def test_reset_stuck_returns_count(mod, patch_connect) -> None:
    cur = _Cursor(fetchone_row=(3,))
    patch_connect(cur)
    import psycopg

    with psycopg.connect("ignored") as conn:
        assert mod.reset_stuck(conn, stuck_minutes=10) == 3
    assert "reset_stuck_indexing_rows" in cur.executed[-1][0]


# ─── process_row ───────────────────────────────────────────────────────────────


def test_process_row_stub_backend(mod, monkeypatch) -> None:
    monkeypatch.setenv("INDEXING_PROCESSOR_BACKEND", "stub")
    row = mod.QueueRow(id="abc", source="linear", payload={"x": 1}, attempts=0)
    out = mod.process_row(row)
    assert out["event"] == "indexed"
    assert out["backend"] == "stub"
    assert out["payload_size"] > 0


def test_process_row_unknown_backend_raises(mod, monkeypatch) -> None:
    monkeypatch.setenv("INDEXING_PROCESSOR_BACKEND", "made-up")
    row = mod.QueueRow(id="abc", source="linear", payload={}, attempts=0)
    with pytest.raises(RuntimeError, match="unknown INDEXING_PROCESSOR_BACKEND"):
        mod.process_row(row)


def test_process_row_llamaindex_not_implemented(mod, monkeypatch) -> None:
    monkeypatch.setenv("INDEXING_PROCESSOR_BACKEND", "llamaindex")
    row = mod.QueueRow(id="abc", source="linear", payload={}, attempts=0)
    with pytest.raises(RuntimeError, match="not yet implemented"):
        mod.process_row(row)


# ─── mark_done / mark_failed ──────────────────────────────────────────────────


def test_mark_done_emits_update_and_audit_insert(mod, patch_connect) -> None:
    cur = _Cursor()
    patch_connect(cur)
    import psycopg

    with psycopg.connect("ignored") as conn:
        mod.mark_done(conn, "row-1", {"event": "indexed", "source": "linear"})
    sqls = [s[0] for s in cur.executed]
    assert any("UPDATE public.indexing_queue" in s and "'done'" in s for s in sqls)
    assert any("INSERT INTO public.audit_logs" in s for s in sqls)


def test_mark_failed_terminal_at_max_attempts(mod, patch_connect) -> None:
    cur = _Cursor()
    patch_connect(cur)
    import psycopg

    with psycopg.connect("ignored") as conn:
        terminal = mod.mark_failed(conn, "row-1", "boom", attempts=3, max_attempts=3)
    assert terminal is True
    # Verify status='failed' is in the params
    assert any("failed" in str(p) for _, p in cur.executed if p is not None)


def test_mark_failed_retry_below_max_attempts(mod, patch_connect) -> None:
    cur = _Cursor()
    patch_connect(cur)
    import psycopg

    with psycopg.connect("ignored") as conn:
        terminal = mod.mark_failed(conn, "row-1", "transient", attempts=1, max_attempts=3)
    assert terminal is False
    # Verify status='pending' (retry path)
    assert any("pending" in str(p) for _, p in cur.executed if p is not None)


# ─── process_batch ─────────────────────────────────────────────────────────────


def test_process_batch_happy_path(mod, patch_connect, monkeypatch) -> None:
    cur = _Cursor()
    patch_connect(cur)
    monkeypatch.setenv("INDEXING_PROCESSOR_BACKEND", "stub")
    rows = [
        mod.QueueRow(id="a", source="linear", payload={}, attempts=1),
        mod.QueueRow(id="b", source="slack", payload={"k": "v"}, attempts=1),
    ]
    import psycopg

    with psycopg.connect("ignored") as conn:
        counters = mod.process_batch(conn, rows, max_attempts=3)
    assert counters == {"done": 2, "retry": 0, "failed": 0}


def test_process_batch_failure_triggers_retry_or_terminal(mod, patch_connect, monkeypatch) -> None:
    cur = _Cursor()
    patch_connect(cur)
    monkeypatch.setenv("INDEXING_PROCESSOR_BACKEND", "made-up")  # forces RuntimeError
    monkeypatch.setattr(mod, "alert_ceo", lambda *a, **kw: None)
    rows = [
        mod.QueueRow(id="a", source="linear", payload={}, attempts=2),  # retry: 2<3
        mod.QueueRow(id="b", source="linear", payload={}, attempts=3),  # terminal: 3>=3
    ]
    import psycopg

    with psycopg.connect("ignored") as conn:
        counters = mod.process_batch(conn, rows, max_attempts=3)
    assert counters == {"done": 0, "retry": 1, "failed": 1}


# ─── run() integration ─────────────────────────────────────────────────────────


def test_run_max_iterations_exits_clean(mod, patch_connect, monkeypatch) -> None:
    cur = _Cursor(fetchall_rows=[], description=[("id",)], fetchone_row=(0,))
    patch_connect(cur)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    rc = mod.run(batch_size=1, poll_interval=1, max_attempts=3, max_iterations=2)
    assert rc == 0
