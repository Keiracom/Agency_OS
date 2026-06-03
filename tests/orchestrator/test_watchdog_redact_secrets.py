"""Tests for _redact_secrets (SECURITY P1, 2026-06-03).

Confirm the watchdog masks credentials before any pane content reaches Slack:
  - postgresql DSNs (with or without +driver suffix)
  - PGPASSWORD / DATABASE_URL env-style lines
  - generic ':long-secret@' DSN passwords
  - Bearer tokens
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def cw():
    mod = importlib.import_module("scripts.orchestrator.context_watchdog")
    return importlib.reload(mod)


@pytest.mark.parametrize(
    ("raw", "must_be_absent"),
    [
        ("psql postgresql://user:s3cretpassword@db.host:5432/x", "s3cretpassword"),
        ("DSN postgresql+asyncpg://u:hunter22extra@host/db", "hunter22extra"),
        ("env PGPASSWORD=topsecretvalue123 set", "topsecretvalue123"),
        ("DATABASE_URL=postgresql://u:p@h/d AS dsn", "DATABASE_URL=postgresql"),
        ("redis://:longpasswordvalue@cache.host:6379/0", "longpasswordvalue"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123", "abcdefghijklmnopqrstuvwxyz0123"),
    ],
)
def test_redact_secrets_masks_known_patterns(cw, raw, must_be_absent):
    out = cw._redact_secrets(raw)
    assert must_be_absent not in out, f"secret leaked: {out!r}"
    assert "***" in out, f"expected mask marker; got {out!r}"


def test_redact_secrets_passes_through_safe_text(cw):
    assert cw._redact_secrets("just a normal log line") == "just a normal log line"


def test_redact_secrets_handles_empty(cw):
    assert cw._redact_secrets("") == ""
