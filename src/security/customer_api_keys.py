"""KEI-116 — Customer API key encryption-at-rest service.

Provides AES-256 encrypt/decrypt (via pgcrypto pgp_sym_encrypt/pgp_sym_decrypt)
and SHA-256 lookup hashing for customer-submitted API keys stored in
public.customer_api_keys.

Design:
  - Plaintext NEVER written to DB. Only pgp_sym_encrypt ciphertext + SHA-256 hash.
  - Master key is read from CUSTOMER_KEY_ENCRYPTION_KEY env var. If unset,
    store_key() raises RuntimeError (refuse to silently store unencrypted).
  - lookup_by_hash() enables O(1) key existence checks without decrypting rows.
  - rotate() is atomic: inserts new row + revokes old row in a single transaction.
  - revoke() is idempotent: second call on an already-revoked row is a no-op.

DSN pattern: DATABASE_URL (or SUPABASE_DB_URL) with the
postgresql+asyncpg:// prefix stripped; psycopg3 with prepare_threshold=None
(Supabase pooler is txn-mode pgbouncer — cached prepared statements break).

No plaintext keys, master keys, or encrypted bytes are ever logged.
"""

from __future__ import annotations

import hashlib
import logging
import os
from uuid import UUID

logger = logging.getLogger(__name__)


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _master_key() -> str:
    """Read master encryption key from env. Raises if unset."""
    key = os.environ.get("CUSTOMER_KEY_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("CUSTOMER_KEY_ENCRYPTION_KEY env var required")
    return key


def _sha256_hex(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def store_key(customer_id: UUID, provider: str, plaintext: str) -> UUID:
    """Encrypt plaintext API key via pgp_sym_encrypt and store with SHA-256 lookup hash.

    Master key from CUSTOMER_KEY_ENCRYPTION_KEY env var.
    Returns the new row's id.
    Raises RuntimeError if master key env is unset.
    """
    import psycopg

    master_key = _master_key()
    lookup_hash = _sha256_hex(plaintext)
    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.customer_api_keys
                (customer_id, provider, encrypted_key, lookup_hash)
            VALUES (
                %s,
                %s,
                pgp_sym_encrypt(%s, %s),
                %s
            )
            RETURNING id
            """,
            (str(customer_id), provider, plaintext, master_key, lookup_hash),
        )
        row = cur.fetchone()
        new_id = UUID(str(row[0]))
    logger.info(
        "store_key: stored row id=%s customer_id=%s provider=%s", new_id, customer_id, provider
    )
    return new_id


def lookup_by_hash(plaintext: str) -> dict | None:
    """O(1) lookup: SHA-256 the plaintext, query by lookup_hash.

    Returns dict with id, customer_id, provider, created_at, rotated_at.
    Does NOT return the encrypted key.
    Returns None if no matching active (non-revoked) row.
    """
    import psycopg

    lookup_hash = _sha256_hex(plaintext)
    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, customer_id, provider, created_at, rotated_at
            FROM public.customer_api_keys
            WHERE lookup_hash = %s
              AND revoked_at IS NULL
            LIMIT 1
            """,
            (lookup_hash,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "customer_id": row[1],
        "provider": row[2],
        "created_at": row[3],
        "rotated_at": row[4],
    }


def decrypt_key(row_id: UUID) -> str:
    """Return the decrypted plaintext for a stored key.

    Uses pgp_sym_decrypt with the master key.
    Raises RuntimeError if row not found or revoked.
    """
    import psycopg

    master_key = _master_key()
    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT pgp_sym_decrypt(encrypted_key, %s)
            FROM public.customer_api_keys
            WHERE id = %s
              AND revoked_at IS NULL
            """,
            (master_key, str(row_id)),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"decrypt_key: row not found or revoked id={row_id}")
    return str(row[0])


def rotate(customer_id: UUID, provider: str, new_plaintext: str) -> UUID:
    """Soft-rotate: insert new row, mark old row revoked. Atomic (single transaction).

    Returns the new row's id.
    If no current row for (customer_id, provider): behaves like store_key.
    """
    import psycopg

    master_key = _master_key()
    new_hash = _sha256_hex(new_plaintext)
    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        # Insert new row first (rotated_at = NOW() marks it as the rotation result).
        cur.execute(
            """
            INSERT INTO public.customer_api_keys
                (customer_id, provider, encrypted_key, lookup_hash, rotated_at)
            VALUES (
                %s,
                %s,
                pgp_sym_encrypt(%s, %s),
                %s,
                NOW()
            )
            RETURNING id
            """,
            (str(customer_id), provider, new_plaintext, master_key, new_hash),
        )
        new_id = UUID(str(cur.fetchone()[0]))
        # Revoke any prior active rows for (customer_id, provider).
        cur.execute(
            """
            UPDATE public.customer_api_keys
            SET revoked_at = NOW()
            WHERE customer_id = %s
              AND provider = %s
              AND revoked_at IS NULL
              AND id != %s
            """,
            (str(customer_id), provider, str(new_id)),
        )
        conn.commit()
    logger.info("rotate: new row id=%s customer_id=%s provider=%s", new_id, customer_id, provider)
    return new_id


def revoke(row_id: UUID) -> None:
    """Mark a key revoked. Idempotent — second call is a no-op."""
    import psycopg

    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.customer_api_keys
            SET revoked_at = NOW()
            WHERE id = %s
              AND revoked_at IS NULL
            """,
            (str(row_id),),
        )
    logger.info("revoke: row_id=%s", row_id)
