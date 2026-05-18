"""Tests for KEI-183 persona column extraction in src/api/webhooks/linear.py.

Covers:
  - title with [CALLSIGN] prefix → persona set (lowercase)
  - title without prefix → persona NULL
  - title with non-callsign bracket prefix → NULL (digits-only not a callsign prefix)
  - idempotent re-insert (ON CONFLICT DO UPDATE sets persona)
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "linear.py"

TEST_SECRET = "test-kei183-secret"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("linear_webhook_kei183", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["linear_webhook_kei183"] = m
    spec.loader.exec_module(m)
    return m


def _make_create_payload(title: str, identifier: str = "KEI-183") -> dict:
    return {
        "action": "create",
        "type": "Issue",
        "data": {
            "identifier": identifier,
            "title": title,
            "priority": 2,
            "url": f"https://linear.app/keiracom/issue/{identifier}",
        },
    }


def _signed_body(body: dict) -> tuple[bytes, str]:
    raw = json.dumps(body).encode()
    sig = hmac.new(TEST_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, sig


class _FakeCursor:
    """Minimal cursor mock that captures execute calls."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.rowcount = 0

    def execute(self, sql: str, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class _FakeConn:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


# ---------------------------------------------------------------------------
# Test: _CALLSIGN_PREFIX_RE regex directly
# ---------------------------------------------------------------------------


def test_callsign_prefix_re_matches_callsign(mod):
    m = mod._CALLSIGN_PREFIX_RE.match("[ELLIOT] feat: something")
    assert m is not None
    assert m.group(1) == "ELLIOT"


def test_callsign_prefix_re_no_prefix(mod):
    assert mod._CALLSIGN_PREFIX_RE.match("feat: something plain") is None


def test_callsign_prefix_re_lowercase_in_bracket_no_match(mod):
    # [elliot] lowercase — regex expects [A-Z]+ so won't match
    assert mod._CALLSIGN_PREFIX_RE.match("[elliot] something") is None


# ---------------------------------------------------------------------------
# Test: _dispatch_to_tasks persona extraction
# ---------------------------------------------------------------------------


def test_dispatch_to_tasks_sets_persona_for_callsign_prefix(mod, monkeypatch):
    """Title '[ELLIOT] feat: x' → persona='elliot' written to INSERT."""
    cursor = _FakeCursor()
    conn = _FakeConn(cursor)

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")

    with patch("psycopg.connect", return_value=conn):
        mod._dispatch_to_tasks(
            {
                "op": "create",
                "identifier": "KEI-183",
                "title": "[ELLIOT] feat: supervisor v2",
                "priority": 2,
                "url": "https://linear.app/keiracom/issue/KEI-183",
            }
        )

    # The INSERT call is the one with 5 params (id, title, priority, url, persona)
    insert_calls = [c for c in cursor.calls if "INSERT" in c[0]]
    assert insert_calls, "Expected an INSERT execute call"
    params = insert_calls[0][1]
    # persona is the 5th param (index 4)
    assert params[4] == "elliot", f"Expected persona='elliot', got {params[4]!r}"


def test_dispatch_to_tasks_persona_null_when_no_prefix(mod, monkeypatch):
    """Title with no [CALLSIGN] prefix → persona=None."""
    cursor = _FakeCursor()
    conn = _FakeConn(cursor)

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")

    with patch("psycopg.connect", return_value=conn):
        mod._dispatch_to_tasks(
            {
                "op": "create",
                "identifier": "KEI-183",
                "title": "Build supervisor v2 routing",
                "priority": 2,
                "url": "https://linear.app/keiracom/issue/KEI-183",
            }
        )

    insert_calls = [c for c in cursor.calls if "INSERT" in c[0]]
    assert insert_calls, "Expected an INSERT execute call"
    params = insert_calls[0][1]
    assert params[4] is None, f"Expected persona=None, got {params[4]!r}"


def test_dispatch_to_tasks_persona_null_for_digit_prefix(mod, monkeypatch):
    """Title '[123] something' — regex [A-Z]+ won't match digits → persona NULL."""
    cursor = _FakeCursor()
    conn = _FakeConn(cursor)

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")

    with patch("psycopg.connect", return_value=conn):
        mod._dispatch_to_tasks(
            {
                "op": "create",
                "identifier": "KEI-183",
                "title": "[123] some task",
                "priority": 3,
                "url": "https://linear.app/keiracom/issue/KEI-183",
            }
        )

    insert_calls = [c for c in cursor.calls if "INSERT" in c[0]]
    assert insert_calls
    params = insert_calls[0][1]
    assert params[4] is None


def test_dispatch_to_tasks_idempotent_upsert_updates_persona(mod, monkeypatch):
    """ON CONFLICT DO UPDATE includes persona=EXCLUDED.persona for idempotency."""
    cursor = _FakeCursor()
    conn = _FakeConn(cursor)

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")

    with patch("psycopg.connect", return_value=conn):
        mod._dispatch_to_tasks(
            {
                "op": "create",
                "identifier": "KEI-183",
                "title": "[MAX] refactor: persona column",
                "priority": 2,
                "url": "https://linear.app/keiracom/issue/KEI-183",
            }
        )

    insert_calls = [c for c in cursor.calls if "INSERT" in c[0]]
    assert insert_calls
    sql = insert_calls[0][0]
    # ON CONFLICT clause must include persona = EXCLUDED.persona
    assert "persona = EXCLUDED.persona" in sql, "ON CONFLICT must update persona"
    # persona value should be 'max'
    params = insert_calls[0][1]
    assert params[4] == "max"
