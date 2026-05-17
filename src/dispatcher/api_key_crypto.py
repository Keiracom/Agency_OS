"""KEI-116B — pgcrypto pgp_sym encrypt/decrypt helpers for customer API keys.

Server-side symmetric encryption via PostgreSQL's pgcrypto extension —
plaintext keys never leave the database server (we send plaintext via
parameterised psycopg query; pgcrypto encrypts inside the database and
returns the ciphertext). Master keys are pulled from env vars indexed
by ``rotation_id`` so a rolling key rotation can land without
re-encrypting historical rows (caller stores ``rotation_id`` alongside
the ``encrypted_key`` column so the decrypt call resolves the right
master key).

Env var convention:
    DISPATCHER_API_KEY_MASTER_V1   # current key
    DISPATCHER_API_KEY_MASTER_V2   # next rotation
    ...

Acceptance (Linear KEI-168):
- INSERT encrypts via pgp_sym_encrypt(plaintext, master_key)
- SELECT decrypts
- rotation_id allows future key rotation

Out of scope:
- ``customer_api_keys.rotation_id`` column (KEI-167 schema PR).
- ``lookup_hash`` SHA-256 derivation (KEI-169 / KEI-116C).
- Master-key provisioning (operator concern; documented env contract).
- Server-side function variant (current design sends plaintext via
  parameterised psycopg query; future hardening can wrap the same
  pgp_sym_encrypt call inside a PL/pgSQL SECURITY DEFINER function that
  reads the master from a Supabase secret — same call shape from Python).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

ROTATION_ID_ENV_PREFIX = "DISPATCHER_API_KEY_MASTER_V"
DEFAULT_ROTATION_ID = 1


class MasterKeyMissingError(RuntimeError):
    """The environment is missing the master key for the requested
    ``rotation_id``. Fail-closed — never silently encrypt with a fallback
    key, never silently decrypt with the wrong rotation."""


class CryptoError(RuntimeError):
    """pgcrypto returned an unexpected shape (empty row, wrong type).
    pgp_sym_decrypt with a wrong key returns the encrypted bytes garbled
    OR raises a Postgres error — we surface both as CryptoError."""


def _resolve_master_key(rotation_id: int) -> str:
    """Look up the master key for a rotation_id from the environment.
    Strips trailing whitespace; refuses empty values."""
    env_var = f"{ROTATION_ID_ENV_PREFIX}{int(rotation_id)}"
    raw = os.environ.get(env_var, "")
    key = raw.strip()
    if not key:
        raise MasterKeyMissingError(
            f"env {env_var} unset or empty — no master key for rotation_id={rotation_id}"
        )
    return key


def encrypt(conn, plaintext: str, *, rotation_id: int = DEFAULT_ROTATION_ID) -> bytes:
    """Encrypt ``plaintext`` via ``pgp_sym_encrypt(plaintext, master_key)``.

    Args:
        conn: psycopg connection (sync). Reused — caller owns lifecycle.
        plaintext: The API key string to encrypt. Must be non-empty.
        rotation_id: Index into the rolling master-key env. Default 1.

    Returns:
        ``bytes`` — the bytea ciphertext suitable for storing in the
        ``customer_api_keys.encrypted_key`` column.

    Raises:
        ValueError: plaintext empty/whitespace.
        MasterKeyMissingError: env var for rotation_id is unset.
        CryptoError: pgcrypto returned an unexpected shape.
    """
    if not plaintext or not plaintext.strip():
        raise ValueError("plaintext must be a non-empty string")
    master_key = _resolve_master_key(rotation_id)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pgp_sym_encrypt(%s::text, %s::text)",
            (plaintext, master_key),
        )
        row = cur.fetchone()
    if row is None or row[0] is None:
        raise CryptoError("pgp_sym_encrypt returned no row")
    return bytes(row[0])


def decrypt(conn, encrypted: bytes, *, rotation_id: int = DEFAULT_ROTATION_ID) -> str:
    """Decrypt ``encrypted`` bytea via
    ``pgp_sym_decrypt(encrypted, master_key)``.

    Args:
        conn: psycopg connection (sync).
        encrypted: The bytea ciphertext read from ``encrypted_key``.
        rotation_id: Must match the rotation_id used at encrypt time —
            caller is responsible for tracking which rotation each
            ``encrypted_key`` row was minted under.

    Returns:
        ``str`` — the original plaintext.

    Raises:
        ValueError: encrypted is empty.
        MasterKeyMissingError: env var for rotation_id is unset.
        CryptoError: pgcrypto returned an unexpected shape OR the master
            key doesn't match the rotation (Postgres raises; we re-raise).
    """
    if not encrypted:
        raise ValueError("encrypted must be a non-empty bytes-like")
    master_key = _resolve_master_key(rotation_id)
    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT pgp_sym_decrypt(%s::bytea, %s::text)",
                (bytes(encrypted), master_key),
            )
            row = cur.fetchone()
        except Exception as exc:
            # pgcrypto raises on wrong key / corrupt ciphertext — surface as
            # CryptoError so callers can branch without importing psycopg.
            raise CryptoError(f"pgp_sym_decrypt failed: {exc}") from exc
    if row is None or row[0] is None:
        raise CryptoError("pgp_sym_decrypt returned no row")
    return str(row[0])


def encrypt_for_storage(
    conn,
    plaintext: str,
    *,
    rotation_id: int = DEFAULT_ROTATION_ID,
) -> tuple[bytes, int]:
    """Convenience wrapper returning ``(encrypted_key, rotation_id)`` ready
    for INSERT alongside other columns.

    Caller still composes the INSERT statement — this helper keeps the
    encrypt + rotation_id pair atomic so callers don't accidentally store
    a ciphertext under the wrong rotation_id (e.g. by reading the env
    twice and getting different keys mid-flight, post-rotation).
    """
    return encrypt(conn, plaintext, rotation_id=rotation_id), int(rotation_id)
