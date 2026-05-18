"""KEI-138 — Dispatch HMAC audit log writer.

Records one row per dispatch-queue pop in public.dispatch_audit_log. Used by
src/relay/relay_consumer.py to track signed-vs-unsigned outcomes and rotation
validity over time.

Design:
  - Synchronous psycopg connect-on-write (no shared pool — consumer pop is the
    only caller and dispatch rate is low; pool not justified yet).
  - Fail-open: any DB error logs a warning and returns without raising. The
    consumer's tmux inject path MUST NOT be blocked by audit DB unreachability.
  - Plaintext payload body NEVER stored. Only canonical_hash() of the payload.
  - DSN pattern matches src/security/customer_api_keys.py — strip +asyncpg,
    use psycopg3 with prepare_threshold=None (Supabase pooler is txn-mode).
"""

from __future__ import annotations

import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

HmacStatus = Literal["signed_verified", "signed_invalid", "unsigned", "no_secret"]


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def record_dispatch(
    *,
    queue: str,
    target: str,
    hmac_status: HmacStatus,
    payload_hash: str,
    secret_index: int = -1,
    reason: str | None = None,
) -> None:
    """Insert one audit row for a dispatch pop. Fail-open on any error.

    Never raises — relay_consumer must keep injecting tmux even if the audit
    DB is unreachable. Errors are logged at WARNING level for forensics.
    """
    try:
        import psycopg

        with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.dispatch_audit_log
                    (queue, target, hmac_status, secret_index, payload_hash, reason)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (queue, target, hmac_status, secret_index, payload_hash, reason),
            )
    except Exception as exc:
        logger.warning(
            "dispatch_audit insert failed queue=%s status=%s: %s",
            queue,
            hmac_status,
            exc,
        )
