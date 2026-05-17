"""KEI-116 — Unit tests for src/security/customer_api_keys.py.

All tests use mocked psycopg — no real DB hits. CI runs without Supabase access.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest

import src.security.customer_api_keys as module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_MASTER_KEY = "test-master-key-value"
FAKE_PLAINTEXT = "sk-anthropic-testkey-abc123"
FAKE_CUSTOMER_ID = uuid.uuid4()
FAKE_ROW_ID = uuid.uuid4()
FAKE_PROVIDER = "anthropic"


def _expected_hash(plaintext: str = FAKE_PLAINTEXT) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _make_conn_mock(fetchone_return=None):
    """Build a mock psycopg connection + cursor hierarchy."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_return
    # Support context-manager protocol for cursor
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cur
    # Support context-manager protocol for connection
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)

    return conn, cur


# ---------------------------------------------------------------------------
# store_key
# ---------------------------------------------------------------------------


def test_store_key_requires_master_key_env(monkeypatch):
    """If CUSTOMER_KEY_ENCRYPTION_KEY is unset, store_key must raise RuntimeError."""
    monkeypatch.delenv("CUSTOMER_KEY_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    with pytest.raises(RuntimeError, match="CUSTOMER_KEY_ENCRYPTION_KEY"):
        module.store_key(FAKE_CUSTOMER_ID, FAKE_PROVIDER, FAKE_PLAINTEXT)


def test_store_key_calls_pgp_sym_encrypt_with_master_key(monkeypatch):
    """store_key must call pgp_sym_encrypt with the plaintext and master key as params."""
    monkeypatch.setenv("CUSTOMER_KEY_ENCRYPTION_KEY", FAKE_MASTER_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    new_id = uuid.uuid4()
    conn, cur = _make_conn_mock(fetchone_return=(str(new_id),))

    with patch("psycopg.connect", return_value=conn):
        result = module.store_key(FAKE_CUSTOMER_ID, FAKE_PROVIDER, FAKE_PLAINTEXT)

    assert result == new_id
    # Find the INSERT execute call
    execute_calls = cur.execute.call_args_list
    assert len(execute_calls) >= 1
    insert_call = execute_calls[0]
    sql, params = insert_call[0]
    assert "pgp_sym_encrypt" in sql
    # plaintext and master key must appear as params, not interpolated
    assert FAKE_PLAINTEXT in params
    assert FAKE_MASTER_KEY in params


def test_store_key_computes_correct_sha256_hash(monkeypatch):
    """store_key must pass SHA-256 hex of plaintext as lookup_hash param."""
    monkeypatch.setenv("CUSTOMER_KEY_ENCRYPTION_KEY", FAKE_MASTER_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    new_id = uuid.uuid4()
    conn, cur = _make_conn_mock(fetchone_return=(str(new_id),))

    with patch("psycopg.connect", return_value=conn):
        module.store_key(FAKE_CUSTOMER_ID, FAKE_PROVIDER, FAKE_PLAINTEXT)

    execute_calls = cur.execute.call_args_list
    _, params = execute_calls[0][0]
    expected_hash = _expected_hash(FAKE_PLAINTEXT)
    assert expected_hash in params


# ---------------------------------------------------------------------------
# lookup_by_hash
# ---------------------------------------------------------------------------


def test_lookup_by_hash_uses_sha256_not_plaintext(monkeypatch):
    """lookup_by_hash must query by lookup_hash (sha256 hex), not the plaintext."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    conn, cur = _make_conn_mock(fetchone_return=None)

    with patch("psycopg.connect", return_value=conn):
        module.lookup_by_hash(FAKE_PLAINTEXT)

    _, params = cur.execute.call_args[0]
    expected_hash = _expected_hash(FAKE_PLAINTEXT)
    # The hash must appear in params
    assert expected_hash in params
    # The plaintext itself must NOT appear as a param
    assert FAKE_PLAINTEXT not in params


def test_lookup_by_hash_excludes_revoked(monkeypatch):
    """lookup_by_hash WHERE clause must include revoked_at IS NULL."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    conn, cur = _make_conn_mock(fetchone_return=None)

    with patch("psycopg.connect", return_value=conn):
        module.lookup_by_hash(FAKE_PLAINTEXT)

    sql, _ = cur.execute.call_args[0]
    assert "revoked_at IS NULL" in sql


def test_lookup_by_hash_returns_none_on_miss(monkeypatch):
    """When fetchone returns None, lookup_by_hash must return None."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    conn, _ = _make_conn_mock(fetchone_return=None)

    with patch("psycopg.connect", return_value=conn):
        result = module.lookup_by_hash(FAKE_PLAINTEXT)

    assert result is None


def test_lookup_by_hash_returns_dict_on_hit(monkeypatch):
    """When fetchone returns a row, lookup_by_hash returns a dict with expected keys and NO encrypted_key."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    import datetime

    row_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    now = datetime.datetime(2026, 5, 17, 0, 0, 0)
    conn, _ = _make_conn_mock(fetchone_return=(row_id, cust_id, FAKE_PROVIDER, now, None))

    with patch("psycopg.connect", return_value=conn):
        result = module.lookup_by_hash(FAKE_PLAINTEXT)

    assert result is not None
    assert set(result.keys()) == {"id", "customer_id", "provider", "created_at", "rotated_at"}
    assert "encrypted_key" not in result
    assert result["provider"] == FAKE_PROVIDER


# ---------------------------------------------------------------------------
# decrypt_key
# ---------------------------------------------------------------------------


def test_decrypt_key_uses_pgp_sym_decrypt_with_master_key(monkeypatch):
    """decrypt_key must call pgp_sym_decrypt with the master key as a param."""
    monkeypatch.setenv("CUSTOMER_KEY_ENCRYPTION_KEY", FAKE_MASTER_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    conn, cur = _make_conn_mock(fetchone_return=("decrypted-value",))

    with patch("psycopg.connect", return_value=conn):
        result = module.decrypt_key(FAKE_ROW_ID)

    assert result == "decrypted-value"
    sql, params = cur.execute.call_args[0]
    assert "pgp_sym_decrypt" in sql
    assert FAKE_MASTER_KEY in params


def test_decrypt_key_raises_if_row_not_found(monkeypatch):
    """decrypt_key must raise RuntimeError when fetchone returns None."""
    monkeypatch.setenv("CUSTOMER_KEY_ENCRYPTION_KEY", FAKE_MASTER_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    conn, _ = _make_conn_mock(fetchone_return=None)

    with (
        patch("psycopg.connect", return_value=conn),
        pytest.raises(RuntimeError, match="not found or revoked"),
    ):
        module.decrypt_key(FAKE_ROW_ID)


# ---------------------------------------------------------------------------
# rotate
# ---------------------------------------------------------------------------


def test_rotate_inserts_new_and_revokes_old_in_transaction(monkeypatch):
    """rotate must issue 2 execute calls (INSERT new + UPDATE revoked_at) and commit once."""
    monkeypatch.setenv("CUSTOMER_KEY_ENCRYPTION_KEY", FAKE_MASTER_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    new_id = uuid.uuid4()
    cur = MagicMock()
    # First fetchone returns the new row id
    cur.fetchone.return_value = (str(new_id),)
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)

    with patch("psycopg.connect", return_value=conn):
        result = module.rotate(FAKE_CUSTOMER_ID, FAKE_PROVIDER, "new-plaintext-key")

    assert result == new_id
    # Two execute calls: INSERT + UPDATE
    assert cur.execute.call_count == 2
    insert_sql = cur.execute.call_args_list[0][0][0]
    update_sql = cur.execute.call_args_list[1][0][0]
    assert "INSERT" in insert_sql
    assert "UPDATE" in update_sql
    assert "revoked_at" in update_sql
    # commit called once
    conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# revoke
# ---------------------------------------------------------------------------


def test_revoke_sets_revoked_at_now(monkeypatch):
    """revoke must issue an UPDATE setting revoked_at = NOW()."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    conn, cur = _make_conn_mock()

    with patch("psycopg.connect", return_value=conn):
        module.revoke(FAKE_ROW_ID)

    sql, params = cur.execute.call_args[0]
    assert "revoked_at = NOW()" in sql
    assert str(FAKE_ROW_ID) in params


# ---------------------------------------------------------------------------
# No plaintext or master key in logs
# ---------------------------------------------------------------------------


def test_no_plaintext_or_master_key_in_logs(monkeypatch, caplog):
    """Neither the plaintext key nor the master key must appear in any log output."""
    monkeypatch.setenv("CUSTOMER_KEY_ENCRYPTION_KEY", FAKE_MASTER_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    new_id = uuid.uuid4()
    conn, _ = _make_conn_mock(fetchone_return=(str(new_id),))

    with (
        caplog.at_level(logging.DEBUG, logger="src.security.customer_api_keys"),
        patch("psycopg.connect", return_value=conn),
    ):
        module.store_key(FAKE_CUSTOMER_ID, FAKE_PROVIDER, FAKE_PLAINTEXT)

    combined = "\n".join(caplog.messages)
    assert FAKE_PLAINTEXT not in combined
    assert FAKE_MASTER_KEY not in combined
