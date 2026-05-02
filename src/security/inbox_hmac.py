"""HMAC sign/verify for clone inbox/outbox dispatch files.

Closes the trust gap in `/tmp/telegram-relay-*/inbox/` and `outbox/`: the
relay-watchers `tmux send-keys` any JSON they find. Without authentication,
any process running as the `elliotbot` user can write a fake dispatch that
gets injected into a parent or clone tmux. HMAC signing + verification makes
tampered or unsigned files detectable.

Threat model (Dave-ratified per B3 spec refinement #7):
    This is TAMPER DETECTION against corrupted or accidentally-written files,
    NOT authentication against a malicious insider with shell access. Anyone
    who can read the shared secret from ~/.config/agency-os/.env can also
    sign. Per-writer keys in Supabase Vault is the follow-up.

Payload contract:
    Dispatch files are JSON objects. Before HMAC, callers populate all task
    fields. `sign(payload, secret)` adds an `hmac` key whose value is
    HMAC-SHA256 over the canonical JSON of the payload (excluding `hmac`
    itself). `verify(path, secret)` re-computes the HMAC from the file on
    disk and returns True only if it matches the stored `hmac`.

Canonical form (deterministic across writers + readers):
    json.dumps(payload_without_hmac, sort_keys=True, separators=(",", ":"))

Environment:
    `INBOX_HMAC_SECRET` — shared secret, read from `~/.config/agency-os/.env`.
    Treat as secret-equivalent to TELEGRAM_BOT_TOKEN. Not to be logged.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"
_HMAC_KEY = "hmac"


def _canonical_bytes(payload: dict) -> bytes:
    """Deterministic serialisation over everything except the `hmac` field."""
    filtered = {k: v for k, v in payload.items() if k != _HMAC_KEY}
    return json.dumps(filtered, sort_keys=True, separators=(",", ":")).encode(_ENCODING)


def _compute(payload: dict, secret: str) -> str:
    return hmac.new(secret.encode(_ENCODING), _canonical_bytes(payload), hashlib.sha256).hexdigest()


def sign(payload: dict, secret: str | None = None) -> dict:
    """Return the payload with an `hmac` field added.

    The input payload is not mutated — a new dict is returned. If `secret`
    is None, falls back to the `INBOX_HMAC_SECRET` env var. Raises
    RuntimeError if no secret is available.
    """
    secret = secret or os.environ.get("INBOX_HMAC_SECRET")
    if not secret:
        raise RuntimeError("INBOX_HMAC_SECRET not set and no secret passed to sign()")
    signed = dict(payload)
    signed[_HMAC_KEY] = _compute(payload, secret)
    return signed


def verify(path: str | Path, secret: str | None = None) -> tuple[bool, str]:
    """Read `path`, recompute HMAC, compare with stored value.

    Returns (is_valid, reason). On mismatch, reason explains why — logs at
    WARNING level. Callers should log + skip-inject on (False, _).
    """
    secret = secret or os.environ.get("INBOX_HMAC_SECRET")
    if not secret:
        return False, "INBOX_HMAC_SECRET not set"

    p = Path(path)
    try:
        raw = p.read_text(encoding=_ENCODING)
    except OSError as exc:
        return False, f"read failed: {exc}"

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, f"not valid JSON: {exc}"

    if not isinstance(payload, dict):
        return False, "payload is not a JSON object"

    stored = payload.get(_HMAC_KEY)
    if not isinstance(stored, str):
        return False, f"{_HMAC_KEY} field missing or not a string (unsigned file)"

    expected = _compute(payload, secret)
    if not hmac.compare_digest(stored, expected):
        logger.warning(
            "HMAC mismatch for %s — computed %s, stored %s", p, expected[:12], stored[:12]
        )
        return False, "HMAC mismatch (tampered or signed with different secret)"

    return True, "ok"


__all__ = ["sign", "verify"]
