"""KEI-138 — Tests for src/security/dispatch_audit.py.

Mocks psycopg.connect so we can exercise the audit insert path WITHOUT a real
DB. The critical contract is **fail-open**: when the DB is unreachable, the
function MUST NOT raise — relay_consumer's tmux inject path depends on this.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from src.security.dispatch_audit import record_dispatch


def _connect_ctx(mock_conn: MagicMock):
    """psycopg.connect returns a context manager — build the matching mock."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _cursor_ctx(mock_cursor: MagicMock):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_cursor)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_record_dispatch_inserts_with_correct_columns(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = _cursor_ctx(cur)
    with patch("psycopg.connect", return_value=_connect_ctx(conn)):
        record_dispatch(
            queue="dispatch:atlas",
            target="atlas:0.0",
            hmac_status="signed_verified",
            payload_hash="a" * 64,
            secret_index=0,
            reason=None,
        )
    cur.execute.assert_called_once()
    sql, params = cur.execute.call_args.args
    assert "INSERT INTO public.dispatch_audit_log" in sql
    assert params == ("dispatch:atlas", "atlas:0.0", "signed_verified", 0, "a" * 64, None)


def test_record_dispatch_fails_open_on_db_error(caplog, monkeypatch):
    """Critical contract: DB unreachability does NOT raise."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    caplog.set_level(logging.WARNING)
    with patch("psycopg.connect", side_effect=OSError("connection refused")):
        # Must not raise:
        record_dispatch(
            queue="dispatch:orion",
            target="orion:0.0",
            hmac_status="signed_invalid",
            payload_hash="b" * 64,
            secret_index=-1,
            reason="HMAC mismatch",
        )
    assert any("dispatch_audit insert failed" in r.getMessage() for r in caplog.records)


def test_record_dispatch_fails_open_on_dsn_missing(caplog, monkeypatch):
    """RuntimeError from _dsn (no DATABASE_URL) must NOT propagate."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    caplog.set_level(logging.WARNING)
    record_dispatch(
        queue="dispatch:atlas",
        target="atlas:0.0",
        hmac_status="unsigned",
        payload_hash="c" * 64,
        secret_index=-1,
        reason="hmac field missing or not a string (unsigned payload)",
    )
    # Function returned without raising → fail-open contract honoured.
    assert any("dispatch_audit insert failed" in r.getMessage() for r in caplog.records)


def test_record_dispatch_strips_asyncpg_prefix(monkeypatch):
    """+asyncpg DSN prefix is stripped so psycopg3 can connect to Supabase pooler."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    captured: dict = {}

    def fake_connect(dsn, **kwargs):
        captured["dsn"] = dsn
        captured["kwargs"] = kwargs
        return _connect_ctx(MagicMock(cursor=lambda: _cursor_ctx(MagicMock())))

    with patch("psycopg.connect", side_effect=fake_connect):
        record_dispatch(
            queue="dispatch:atlas",
            target="atlas:0.0",
            hmac_status="signed_verified",
            payload_hash="d" * 64,
            secret_index=0,
        )
    assert captured["dsn"] == "postgresql://u:p@h/db"
    assert captured["kwargs"].get("prepare_threshold") is None
