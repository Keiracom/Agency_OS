"""KEI-116B — tests for src/dispatcher/api_key_crypto.

psycopg cursor is mocked at the conn.cursor boundary; no live Postgres
required. Master keys are injected via monkeypatch.setenv so rotation
behavior can be exercised deterministically.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.dispatcher import api_key_crypto
from src.dispatcher.api_key_crypto import (
    DEFAULT_ROTATION_ID,
    ROTATION_ID_ENV_PREFIX,
    CryptoError,
    MasterKeyMissingError,
    decrypt,
    encrypt,
    encrypt_for_storage,
)


def _fake_conn(row=(b"ciphertext-bytes",)):
    """Build a psycopg-like sync connection whose cursor returns ``row``
    from fetchone(). Cursor is exposed via conn._cursor for assertions."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone = MagicMock(return_value=row)
    conn.cursor = MagicMock(return_value=cursor)
    conn._cursor = cursor
    return conn


@pytest.fixture(autouse=True)
def _clean_master_keys(monkeypatch):
    """Strip every DISPATCHER_API_KEY_MASTER_V* env so tests start clean."""
    for k in list(__import__("os").environ.keys()):
        if k.startswith(ROTATION_ID_ENV_PREFIX):
            monkeypatch.delenv(k, raising=False)
    yield


# ─── _resolve_master_key ──────────────────────────────────────────────────


def test_resolve_master_key_reads_env(monkeypatch):
    """Default rotation reads DISPATCHER_API_KEY_MASTER_V1 from env."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "master-1-secret")
    assert api_key_crypto._resolve_master_key(1) == "master-1-secret"


def test_resolve_master_key_supports_multiple_rotations(monkeypatch):
    """Each rotation_id maps to its own env var so callers can hold ALL
    historical master keys for decrypt-side compatibility."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "v1-secret")
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}2", "v2-secret")
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}3", "v3-secret")
    assert api_key_crypto._resolve_master_key(1) == "v1-secret"
    assert api_key_crypto._resolve_master_key(2) == "v2-secret"
    assert api_key_crypto._resolve_master_key(3) == "v3-secret"


def test_resolve_master_key_strips_whitespace(monkeypatch):
    """Trailing newlines / spaces from k8s-secret mounts are stripped."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "  master-with-padding  \n")
    assert api_key_crypto._resolve_master_key(1) == "master-with-padding"


def test_resolve_master_key_raises_when_env_missing():
    """Missing env var → MasterKeyMissingError. Never silently fall back
    to a default key — that would silently lose data on rotation."""
    with pytest.raises(MasterKeyMissingError, match="V1"):
        api_key_crypto._resolve_master_key(1)


def test_resolve_master_key_raises_when_env_empty(monkeypatch):
    """Empty / whitespace-only env value is the same as missing — fail."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "   ")
    with pytest.raises(MasterKeyMissingError):
        api_key_crypto._resolve_master_key(1)


# ─── encrypt ──────────────────────────────────────────────────────────────


def test_encrypt_calls_pgp_sym_encrypt_with_correct_args(monkeypatch):
    """encrypt issues SELECT pgp_sym_encrypt(<plaintext>, <master_key>)
    bound via psycopg %s placeholders — no string interpolation."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "master-1")
    conn = _fake_conn(row=(b"encrypted-bytes",))
    result = encrypt(conn, "sk-anthropic-abc123")
    assert result == b"encrypted-bytes"
    sql_arg = conn._cursor.execute.call_args.args[0]
    params = conn._cursor.execute.call_args.args[1]
    assert "pgp_sym_encrypt" in sql_arg
    assert "%s" in sql_arg  # parameterised, not interpolated
    assert params == ("sk-anthropic-abc123", "master-1")


def test_encrypt_uses_requested_rotation(monkeypatch):
    """rotation_id=2 → looks up V2 master key."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}2", "master-v2-newer")
    conn = _fake_conn(row=(b"encrypted-v2",))
    encrypt(conn, "plaintext", rotation_id=2)
    params = conn._cursor.execute.call_args.args[1]
    assert params[1] == "master-v2-newer"


def test_encrypt_defaults_to_rotation_1(monkeypatch):
    """No rotation_id arg → uses DEFAULT_ROTATION_ID (1)."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "v1-key")
    assert DEFAULT_ROTATION_ID == 1
    conn = _fake_conn(row=(b"ct",))
    encrypt(conn, "pt")
    assert conn._cursor.execute.call_args.args[1][1] == "v1-key"


def test_encrypt_refuses_empty_plaintext(monkeypatch):
    """Empty plaintext is a caller bug — refuse before touching the
    database (no spurious 'empty encryption' row)."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "k")
    with pytest.raises(ValueError, match="non-empty"):
        encrypt(_fake_conn(), "")
    with pytest.raises(ValueError, match="non-empty"):
        encrypt(_fake_conn(), "   ")


def test_encrypt_raises_crypto_error_when_no_row(monkeypatch):
    """pgcrypto returning no row is shape failure — surface, don't swallow."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "k")
    conn = _fake_conn(row=None)
    with pytest.raises(CryptoError, match="no row"):
        encrypt(conn, "pt")


def test_encrypt_raises_crypto_error_when_row_value_none(monkeypatch):
    """Row exists but column is NULL — same as no row."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "k")
    conn = _fake_conn(row=(None,))
    with pytest.raises(CryptoError, match="no row"):
        encrypt(conn, "pt")


def test_encrypt_propagates_master_key_missing(monkeypatch):
    """Env not set → MasterKeyMissingError before DB call."""
    conn = _fake_conn(row=(b"x",))
    with pytest.raises(MasterKeyMissingError):
        encrypt(conn, "pt")
    conn._cursor.execute.assert_not_called()


# ─── decrypt ──────────────────────────────────────────────────────────────


def test_decrypt_calls_pgp_sym_decrypt_with_correct_args(monkeypatch):
    """decrypt issues SELECT pgp_sym_decrypt(<encrypted>, <master_key>)."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "master-1")
    conn = _fake_conn(row=("sk-anthropic-abc123",))
    result = decrypt(conn, b"\\x80\\x01ciphertext-bytes")
    assert result == "sk-anthropic-abc123"
    sql_arg = conn._cursor.execute.call_args.args[0]
    params = conn._cursor.execute.call_args.args[1]
    assert "pgp_sym_decrypt" in sql_arg
    assert "%s" in sql_arg
    assert params[0] == b"\\x80\\x01ciphertext-bytes"
    assert params[1] == "master-1"


def test_decrypt_uses_requested_rotation(monkeypatch):
    """rotation_id=2 looks up V2 master key — required for decrypting
    historical rows minted before a rotation."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}2", "v2-key")
    conn = _fake_conn(row=("pt",))
    decrypt(conn, b"ct", rotation_id=2)
    assert conn._cursor.execute.call_args.args[1][1] == "v2-key"


def test_decrypt_refuses_empty_bytes(monkeypatch):
    """Empty ciphertext is a caller bug."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "k")
    with pytest.raises(ValueError, match="non-empty"):
        decrypt(_fake_conn(), b"")


def test_decrypt_wraps_db_exception_in_crypto_error(monkeypatch):
    """pgcrypto raises on wrong key / corrupt ciphertext. We re-raise as
    CryptoError so callers can branch without importing psycopg."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "wrong-key")
    conn = _fake_conn()
    conn._cursor.execute = MagicMock(side_effect=RuntimeError("Wrong key or corrupt data"))
    with pytest.raises(CryptoError, match="pgp_sym_decrypt failed"):
        decrypt(conn, b"some-bytes")


def test_decrypt_raises_crypto_error_when_no_row(monkeypatch):
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "k")
    conn = _fake_conn(row=None)
    with pytest.raises(CryptoError, match="no row"):
        decrypt(conn, b"ct")


# ─── encrypt_for_storage ───────────────────────────────────────────────────


def test_encrypt_for_storage_returns_pair(monkeypatch):
    """encrypt_for_storage returns (ciphertext, rotation_id) atomic pair —
    caller stores both alongside each other in customer_api_keys."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "k1")
    conn = _fake_conn(row=(b"ct-bytes",))
    ct, rot = encrypt_for_storage(conn, "plaintext-secret")
    assert ct == b"ct-bytes"
    assert rot == 1


def test_encrypt_for_storage_preserves_explicit_rotation(monkeypatch):
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}5", "k5")
    conn = _fake_conn(row=(b"v5-ct",))
    ct, rot = encrypt_for_storage(conn, "plaintext", rotation_id=5)
    assert ct == b"v5-ct"
    assert rot == 5


# ─── round-trip with mocked roundtrip ──────────────────────────────────────


def test_encrypt_decrypt_roundtrip_returns_original_plaintext(monkeypatch):
    """Mock pgcrypto as identity (ciphertext == plaintext bytes) — verifies
    that the encrypt → store-shape → decrypt code path preserves the
    payload without re-quoting / encoding bugs."""
    monkeypatch.setenv(f"{ROTATION_ID_ENV_PREFIX}1", "master-1")
    plaintext = "sk-anthropic-secret-xyz"

    # encrypt path: pgcrypto returns the plaintext encoded as bytes
    enc_conn = _fake_conn(row=(plaintext.encode(),))
    ciphertext = encrypt(enc_conn, plaintext)
    assert ciphertext == plaintext.encode()

    # decrypt path: pgcrypto returns the original plaintext string
    dec_conn = _fake_conn(row=(plaintext,))
    recovered = decrypt(dec_conn, ciphertext)
    assert recovered == plaintext
