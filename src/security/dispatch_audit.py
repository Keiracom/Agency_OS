"""Dispatch HMAC audit emitter — KEI-138.

Single-call helper that writes a row to public.dispatch_audit. Fail-open on
every error path (no DSN, DB down, schema missing): a missed audit row MUST
NEVER block a dispatch from being delivered.

Callers:
    scripts/sign_dispatch.py        emit_audit("sign", result="ok", …)
    src/relay/relay_consumer.py     emit_audit("verify", result="ok"|"mismatch"|"unsigned", …)
    direct test callers             see tests/security/test_dispatch_audit.py
"""

from __future__ import annotations

import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def fingerprint(secret: str | None) -> str | None:
    """First 12 hex chars of SHA-256(secret) — identifies the key without
    revealing it. Returns None for empty/None input."""
    if not secret:
        return None
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]


def _dsn() -> str | None:
    return os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")


def emit_audit(
    action: str,
    *,
    result: str,
    payload_id: str | None = None,
    target: str | None = None,
    actor: str | None = None,
    secret_fingerprint: str | None = None,
    file_path: str | None = None,
    reason: str | None = None,
) -> bool:
    """Insert one row into public.dispatch_audit. Returns True on success,
    False on any failure. Never raises — fail-open by design."""
    dsn = _dsn()
    if not dsn:
        return False
    try:
        import psycopg  # noqa: PLC0415 — lazy import; audit is best-effort

        with psycopg.connect(dsn, connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.dispatch_audit
                       (action, result, payload_id, target, actor,
                        secret_fingerprint, file_path, reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (action, result, payload_id, target, actor, secret_fingerprint, file_path, reason),
            )
            conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001 — audit MUST NOT propagate
        logger.debug("dispatch_audit emit failed (non-fatal): %s", exc)
        return False


__all__ = ["emit_audit", "fingerprint"]
