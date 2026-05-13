"""
Module: src/memory/sanitise.py
Purpose: Secret-redaction middleware for Agency OS memory pipeline.
         Intercepts text before it reaches LlamaIndex / embeddings / Weaviate
         and replaces secrets with [REDACTED].

KEI-57 — CRITICAL pre-condition for KEI-46 / KEI-47 / KEI-48.

PATTERN OMISSION NOTE
---------------------
Dave's original spec included:

    r'[a-zA-Z0-9/+]{40}'  # AWS secret (contextual)

This pattern was intentionally dropped. A 40-character base64-ish string is
an extremely common substring in normal text (SHA-1 hex hashes, URL-safe
tokens, compressed IDs, Supabase row IDs, etc.).  Every legitimate hash
written to agent memory would be redacted, producing useless blobs.  The
AKIA* pattern below already catches the AWS *access key ID* (the narrow,
prefixed form); the AWS *secret access key* requires surrounding context
("AWS_SECRET_ACCESS_KEY=...") which is already covered by the
``env_file_secret`` and ``generic_secret_assignment`` patterns.  Adding the
broad 40-char pattern would be a false-positive disaster without meaningful
additional coverage.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Pattern registry
# Each entry: (compiled_regex, human_readable_name)
# ---------------------------------------------------------------------------

_RAW_PATTERNS: list[tuple[str, str]] = [
    (r"sk-ant-[a-zA-Z0-9\-_]{80,}", "anthropic_key"),
    (r"sk-[a-zA-Z0-9]{20,}", "openai_or_anthropic_legacy_key"),
    (r"AIza[0-9A-Za-z\-_]{35}", "google_api_key"),
    (r"Bearer [a-zA-Z0-9\-_\.]{20,}", "bearer_token"),
    # JWTs — three base64url segments separated by dots
    (r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+", "jwt"),
    # DB connection strings
    (r"(postgres|postgresql|mysql|mongodb|redis)://[^\s]+", "db_connection_string"),
    # AWS access key ID (narrow, prefix-anchored)
    (r"AKIA[0-9A-Z]{16}", "aws_access_key_id"),
    # Generic password/secret/token/key assignments (case-insensitive)
    (r"(?i)(password|secret|token|key|passwd)\s*[=:]\s*\S{8,}", "generic_secret_assignment"),
    # .env-style uppercase env var secrets
    (r"[A-Z_]+(KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD)\s*=\s*\S+", "env_file_secret"),
    # PEM private key headers
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key_header"),
]

SECRET_PATTERNS: list[str] = [raw for raw, _name in _RAW_PATTERNS]

_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(raw), name) for raw, name in _RAW_PATTERNS
]

REDACTED = "[REDACTED]"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def summarise_match(pattern: str) -> str:
    """Return the human-readable name for a raw pattern string."""
    for raw, name in _RAW_PATTERNS:
        if raw == pattern:
            return name
    return "unknown_pattern"


def audit_event(
    source: str,
    pattern_name: str,
    agent: str | None = None,
    kei: str | None = None,
) -> dict:
    """
    Build an audit-log dict for one redaction event.

    Does NOT write to Supabase — caller persists via existing supabase helpers.
    This keeps the module pure-Python and fully unit-testable without network.
    """
    return {
        "source": source,
        "pattern_matched": pattern_name,
        "agent": agent,
        "kei": kei,
        "redacted_at": datetime.now(UTC).isoformat(),
    }


def sanitise(text: str) -> str:
    """Replace all detected secrets in *text* with [REDACTED]."""
    for compiled, _name in _COMPILED:
        text = compiled.sub(REDACTED, text)
    return text


def sanitise_with_audit(
    text: str,
    source: str,
    agent: str | None = None,
    kei: str | None = None,
) -> tuple[str, list[dict]]:
    """
    Sanitise *text* and return (sanitised_text, audit_events).

    Each detected match produces one audit_event dict.  Caller is responsible
    for persisting audit_events to Supabase audit_logs.
    """
    events: list[dict] = []
    for compiled, name in _COMPILED:
        matches = compiled.findall(text)
        if matches:
            events.append(audit_event(source, name, agent, kei))
            text = compiled.sub(REDACTED, text)
    return text, events
