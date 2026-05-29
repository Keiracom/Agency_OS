"""Tests for GET /dispatcher/persona (persona_bank_v1 role-prompt lookup).

No real DB — the asyncpg connection / _fetch_persona layer is monkeypatched.
Covers the route's 200/404/503 contract plus the _fetch_persona query-branch
(default variant IS NULL vs explicit variant) and the unset-DSN failure.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from src.dispatcher import main

# ---------------------------------------------------------------------------
# Route: dispatcher_persona — 200 / 404 / 503 contract
# ---------------------------------------------------------------------------


def test_persona_found_returns_prompt(monkeypatch):
    """A persona match → handler returns {prompt_text, token_count} verbatim."""

    async def fake_fetch(role, tier, variant):
        return {"prompt_text": "You are a Worker.", "token_count": 5}

    monkeypatch.setattr(main, "_fetch_persona", fake_fetch)
    resp = asyncio.run(main.dispatcher_persona(role="worker", tier="standard"))
    assert resp == {"prompt_text": "You are a Worker.", "token_count": 5}


def test_persona_missing_returns_404(monkeypatch):
    """No match → 404 (not a 503)."""

    async def fake_fetch(role, tier, variant):
        return None

    monkeypatch.setattr(main, "_fetch_persona", fake_fetch)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.dispatcher_persona(role="ghost", tier="standard"))
    assert exc.value.status_code == 404


def test_persona_db_failure_returns_503(monkeypatch):
    """DB connectivity failure → 503, distinct from a real 404 miss."""

    async def fake_fetch(role, tier, variant):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(main, "_fetch_persona", fake_fetch)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.dispatcher_persona(role="worker", tier="standard"))
    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# _fetch_persona — DSN guard + query-branch selection
# ---------------------------------------------------------------------------


def test_fetch_persona_unset_dsn_raises(monkeypatch):
    """SUPABASE_DB_DSN unset → RuntimeError (caller maps to 503)."""
    monkeypatch.delenv("SUPABASE_DB_DSN", raising=False)
    with pytest.raises(RuntimeError):
        asyncio.run(main._fetch_persona("worker", "standard", None))


class _FakeConn:
    def __init__(self, row, captured):
        self._row = row
        self._captured = captured

    async def fetchrow(self, query, *args):
        self._captured["query"] = query
        self._captured["args"] = args
        return self._row

    async def close(self):
        self._captured["closed"] = True


def _patch_asyncpg(monkeypatch, row, captured):
    async def fake_connect(dsn):
        captured["dsn"] = dsn
        return _FakeConn(row, captured)

    monkeypatch.setattr("asyncpg.connect", fake_connect)


def test_fetch_persona_default_variant_uses_is_null(monkeypatch):
    """variant=None selects the default row via 'variant IS NULL' (2 bind args)."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql+asyncpg://u:p@h/db")
    captured: dict = {}
    _patch_asyncpg(monkeypatch, {"prompt_text": "P", "token_count": 1}, captured)

    out = asyncio.run(main._fetch_persona("worker", "standard", None))

    assert out == {"prompt_text": "P", "token_count": 1}
    assert "variant IS NULL" in captured["query"]
    assert captured["args"] == ("worker", "standard")
    # +asyncpg suffix stripped before connect.
    assert "+asyncpg" not in captured["dsn"]
    assert captured["closed"] is True


def test_fetch_persona_explicit_variant_binds_third_arg(monkeypatch):
    """A named variant uses the '= $3' branch with the variant bound."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://u:p@h/db")
    captured: dict = {}
    _patch_asyncpg(monkeypatch, {"prompt_text": "P", "token_count": 1}, captured)

    asyncio.run(main._fetch_persona("face", "deep", "concise"))

    assert "variant = $3" in captured["query"]
    assert captured["args"] == ("face", "deep", "concise")


def test_fetch_persona_miss_returns_none(monkeypatch):
    """fetchrow None → _fetch_persona returns None (route turns this into 404)."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://u:p@h/db")
    captured: dict = {}
    _patch_asyncpg(monkeypatch, None, captured)

    assert asyncio.run(main._fetch_persona("worker", "standard", None)) is None
