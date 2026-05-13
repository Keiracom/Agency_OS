"""
FILE: tests/memory/test_sanitise.py
PURPOSE: 20-item positive corpus + 5 negative tests for src/memory/sanitise.py.
         Verifies every SECRET_PATTERNS entry fires on realistic strings and that
         false-positive rate is low for legitimate text.

KEI-57 — secret redaction middleware.
"""

from __future__ import annotations

import pytest

from src.memory.sanitise import (
    REDACTED,
    audit_event,
    sanitise,
    sanitise_with_audit,
    summarise_match,
)

# ---------------------------------------------------------------------------
# Positive corpus — 20 items, one or more secrets each
# ---------------------------------------------------------------------------

POSITIVE_CASES = [
    # 1. OpenAI / legacy Anthropic key in export statement
    (
        "export OPENAI_API_KEY=sk-proj-abc123DEF456ghi789JKLmnopqrst",
        "openai_or_anthropic_legacy_key or env_file_secret matched",
    ),
    # 2. Anthropic new-format key in JSON config
    (
        '{"api_key": "sk-ant-api03-AAABBBCCCDDDEEEFFFGGGHHHIIIJJJ'
        "KKKLLLL-MMMNNNOOO-PPPQQQRRRSSSTTTUUUVVVWWW1234567890ab"
        'cdefghijklmnopqrstuvwxyz"}',
        "anthropic_key matched",
    ),
    # 3. Google API key in .env file
    (
        "GOOGLE_API_KEY=AIzaSyA0123456789ABCDEFGHIJKLMNOPQRSTUVwx",
        "google_api_key or env_file_secret matched",
    ),
    # 4. Bearer token in HTTP log
    (
        "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9",
        "bearer_token matched",
    ),
    # 5. Full JWT in Authorization header
    (
        "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9"
        ".eyJzdWIiOiJ1c2VyMTIzIiwiaWF0IjoxNjAwMDAwMDAwfQ"
        ".AbCdEfGhIjKlMnOpQrStUvWxYzABCDEFGHIJKLMNOPQRSTU",
        "jwt matched",
    ),
    # 6. Postgres connection string in config file
    (
        "db_url = postgres://admin:s3cr3tp4ss@db.example.com:5432/agencyos",
        "db_connection_string matched",
    ),
    # 7. MySQL connection string in shell script
    (
        "DATABASE_URL=mysql://root:hunter2@localhost:3306/leads",
        "db_connection_string or env_file_secret matched",
    ),
    # 8. MongoDB connection string in Python code
    (
        'client = MongoClient("mongodb://user:password123@cluster0.abc123.mongodb.net/mydb")',
        "db_connection_string matched",
    ),
    # 9. Redis connection string in YAML config
    (
        "redis_url: redis://:myredispassword@redis-server:6379/0",
        "db_connection_string matched",
    ),
    # 10. AWS access key ID in credentials file
    (
        "[default]\naws_access_key_id = AKIAIOSFODNN7EXAMPLE",
        "aws_access_key_id matched",
    ),
    # 11. AWS key in export (AKIA + exactly 16 uppercase alphanumeric chars = 20 total)
    (
        "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        "aws_access_key_id matched",
    ),
    # 12. Generic password assignment (= form)
    (
        "password = hunter2secret",
        "generic_secret_assignment matched",
    ),
    # 13. Generic token assignment (: form)
    (
        "token: ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        "generic_secret_assignment matched",
    ),
    # 14. Generic secret assignment (case-insensitive)
    (
        "SECRET=MySuperSecretValue",
        "env_file_secret matched",
    ),
    # 15. .env file secret — API_SECRET
    (
        "SALESFORGE_API_SECRET=abc123def456ghi789jkl012",
        "env_file_secret matched",
    ),
    # 16. .env file TOKEN
    (
        "TELEGRAM_BOT_TOKEN=1234567890:ABCDefGHIjKLmnopQRsTUVwxyz",
        "env_file_secret matched",
    ),
    # 17. .env PASSWORD var
    (
        "DB_PASSWORD=v3ryS3cur3P4ssw0rd!",
        "env_file_secret matched",
    ),
    # 18. PEM private key header in pasted key block
    (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...",
        "private_key_header matched",
    ),
    # 19. EC private key header
    (
        "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIK...",
        "private_key_header matched",
    ),
    # 20. Mixed: JWT + env secret in one log line (multi-match)
    (
        "DEBUG auth=eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWRtaW4ifQ.abc123 "
        "SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "jwt and env_file_secret matched",
    ),
]


@pytest.mark.parametrize("raw_input,description", POSITIVE_CASES)
def test_positive_sanitise(raw_input: str, description: str) -> None:
    """Each positive corpus item must produce at least one [REDACTED] token."""
    result = sanitise(raw_input)
    assert REDACTED in result, (
        f"Expected redaction but none found.\n"
        f"Description: {description}\n"
        f"Input:  {raw_input!r}\n"
        f"Output: {result!r}"
    )


# ---------------------------------------------------------------------------
# Negative corpus — 5 items that MUST NOT be redacted
# ---------------------------------------------------------------------------

NEGATIVE_CASES = [
    # 1. Plain prose — no secrets
    "The quick brown fox jumped over the lazy dog and found no secrets here.",
    # 2. SHA-256 hash — looks like base64 but is a normal hex digest
    "sha256: a3f5e7b9c1d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4b6c8d0e2f4",
    # 3. UUID — looks random but must not trigger generic patterns
    "record_id = 550e8400-e29b-41d4-a716-446655440000",
    # 4. Short key= value that is below 8-char threshold for generic_secret_assignment
    "key=abc",
    # 5. Normal config value assignment — key name lacks secret-indicator suffix
    "base_url=https://api.example.com/v1",
]


@pytest.mark.parametrize("raw_input", NEGATIVE_CASES)
def test_negative_no_false_positive(raw_input: str) -> None:
    """Negative corpus items must pass through unsanitised."""
    result = sanitise(raw_input)
    assert result == raw_input, (
        f"False positive: input was modified unexpectedly.\n"
        f"Input:  {raw_input!r}\n"
        f"Output: {result!r}"
    )


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


def test_sanitise_returns_string() -> None:
    assert isinstance(sanitise("hello world"), str)


def test_sanitise_clean_text_unchanged() -> None:
    text = "no secrets in this string at all, just normal prose."
    assert sanitise(text) == text


def test_sanitise_with_audit_returns_tuple() -> None:
    result = sanitise_with_audit("hello", source="test", agent="elliot", kei="KEI-57")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_sanitise_with_audit_no_events_on_clean_text() -> None:
    _text, events = sanitise_with_audit(
        "no secrets here", source="test", agent="elliot", kei="KEI-57"
    )
    assert events == []


def test_sanitise_with_audit_emits_event_on_match() -> None:
    inp = "postgres://user:pass@host:5432/db"
    _text, events = sanitise_with_audit(inp, source="pipeline", agent="atlas", kei="KEI-48")
    assert len(events) >= 1
    assert events[0]["source"] == "pipeline"
    assert events[0]["pattern_matched"] == "db_connection_string"
    assert events[0]["agent"] == "atlas"
    assert events[0]["kei"] == "KEI-48"
    assert "redacted_at" in events[0]


def test_audit_event_structure() -> None:
    ev = audit_event("source_x", "jwt", agent="orion", kei="KEI-57")
    assert ev["source"] == "source_x"
    assert ev["pattern_matched"] == "jwt"
    assert ev["agent"] == "orion"
    assert ev["kei"] == "KEI-57"
    assert "redacted_at" in ev


def test_summarise_match_known_patterns() -> None:
    from src.memory.sanitise import SECRET_PATTERNS

    assert summarise_match(SECRET_PATTERNS[0]) == "anthropic_key"
    assert summarise_match(SECRET_PATTERNS[1]) == "openai_or_anthropic_legacy_key"


def test_summarise_match_unknown_returns_unknown() -> None:
    assert summarise_match("some_nonexistent_pattern") == "unknown_pattern"
