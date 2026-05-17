"""Tests for src/api/webhooks/github.py — KEI-97 GitHub PR → tasks upsert.

Covers:
  - PR opened → REVIEW-PR-<N> row inserted with correct fields
  - PR closed → row status='done'
  - HMAC fail → 401 + no DB write
  - Malformed payload → 200 + log
  - Author exclusion: PR opened by aiden → excluded_callsign='aiden'

Mocks psycopg + httpx; no live DB or live GitHub.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "github.py"
TEST_SECRET = "test-github-webhook-secret"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("github_webhook", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["github_webhook"] = m
    spec.loader.exec_module(m)
    return m


def _make_client(mod, monkeypatch, *, secret: str = TEST_SECRET):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def _sign(body: bytes, secret: str = TEST_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _pr_payload(
    number: int = 42,
    title: str = "My Feature",
    html_url: str = "https://github.com/org/repo/pull/42",
    body: str = "PR body",
    author: str = "aiden",
    action: str = "opened",
) -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": number,
            "title": title,
            "html_url": html_url,
            "body": body,
            "user": {"login": author},
        },
    }


# ── HMAC verification ───────────────────────────────────────────────────────


def test_missing_signature_returns_401(mod, monkeypatch):
    client = _make_client(mod, monkeypatch)
    resp = client.post(
        "/api/webhooks/github",
        json=_pr_payload(),
        headers={"x-github-event": "pull_request"},
    )
    assert resp.status_code == 401


def test_wrong_signature_returns_401(mod, monkeypatch):
    client = _make_client(mod, monkeypatch)
    raw = json.dumps(_pr_payload()).encode()
    resp = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "x-hub-signature-256": "sha256=" + "0" * 64,
            "x-github-event": "pull_request",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 401


def test_hmac_fail_does_not_write_db(mod, monkeypatch):
    """No DB write on HMAC failure — upsert and close helpers must NOT be called."""
    upsert_calls: list = []
    close_calls: list = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda pr: upsert_calls.append(pr))
    monkeypatch.setattr(mod, "_close_review_task", lambda n: close_calls.append(n))
    client = _make_client(mod, monkeypatch)
    raw = json.dumps(_pr_payload()).encode()
    client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "x-hub-signature-256": "sha256=" + "0" * 64,
            "x-github-event": "pull_request",
            "content-type": "application/json",
        },
    )
    assert upsert_calls == []
    assert close_calls == []


# ── PR opened ──────────────────────────────────────────────────────────────


def test_pr_opened_upserts_task(mod, monkeypatch):
    """PR opened → _upsert_review_task called with correct PR dict."""
    upsert_calls: list = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda pr: upsert_calls.append(pr))
    monkeypatch.setattr(mod, "_close_review_task", lambda n: None)
    client = _make_client(mod, monkeypatch)

    payload = _pr_payload(number=7, title="Fix Bug", author="elliot", action="opened")
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "x-hub-signature-256": _sign(raw),
            "x-github-event": "pull_request",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["task_id"] == "REVIEW-PR-7"
    assert len(upsert_calls) == 1
    assert upsert_calls[0]["number"] == 7


def test_pr_reopened_upserts_task(mod, monkeypatch):
    """PR reopened → same upsert path as opened."""
    upsert_calls: list = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda pr: upsert_calls.append(pr))
    monkeypatch.setattr(mod, "_close_review_task", lambda n: None)
    client = _make_client(mod, monkeypatch)

    payload = _pr_payload(number=9, action="reopened")
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "x-hub-signature-256": _sign(raw),
            "x-github-event": "pull_request",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert len(upsert_calls) == 1


# ── PR closed ──────────────────────────────────────────────────────────────


def test_pr_closed_marks_done(mod, monkeypatch):
    """PR closed → _close_review_task called with PR number."""
    close_calls: list = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda pr: None)
    monkeypatch.setattr(mod, "_close_review_task", lambda n: close_calls.append(n))
    client = _make_client(mod, monkeypatch)

    payload = _pr_payload(number=42, action="closed")
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "x-hub-signature-256": _sign(raw),
            "x-github-event": "pull_request",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["task_id"] == "REVIEW-PR-42"
    assert close_calls == [42]


# ── Malformed payload ──────────────────────────────────────────────────────


def test_malformed_payload_returns_200(mod, monkeypatch):
    """Malformed JSON → 200 (fail-open, no retry-storm)."""
    client = _make_client(mod, monkeypatch)
    bad_body = b"not json{"
    sig = _sign(bad_body)
    resp = client.post(
        "/api/webhooks/github",
        content=bad_body,
        headers={
            "x-hub-signature-256": sig,
            "x-github-event": "pull_request",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "malformed"


# ── Author exclusion ───────────────────────────────────────────────────────


def test_pr_author_exclusion_stored(mod, monkeypatch):
    """PR opened by 'aiden' → DB upsert sets excluded_callsign='aiden'."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: fake_conn)

    pr = {
        "number": 15,
        "title": "Aiden's PR",
        "html_url": "https://github.com/org/repo/pull/15",
        "body": "body text",
        "user": {"login": "Aiden"},  # mixed-case — should be lowercased
    }
    mod._upsert_review_task(pr)

    assert fake_cur.execute.called
    sql, params = fake_cur.execute.call_args[0]
    # excluded_callsign param should be lowercased 'aiden'
    assert "excluded_callsign" in sql
    assert "aiden" in params


# ── Non-PR events ─────────────────────────────────────────────────────────


def test_non_pr_event_ignored(mod, monkeypatch):
    """push events are ignored (status='ignored')."""
    client = _make_client(mod, monkeypatch)
    payload = {"ref": "refs/heads/main", "commits": []}
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "x-hub-signature-256": _sign(raw),
            "x-github-event": "push",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


# ── DB upsert internals ────────────────────────────────────────────────────


def test_upsert_writes_correct_fields(mod, monkeypatch):
    """_upsert_review_task writes title, description, status=available, phase=0, claim_source=manual."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: fake_conn)

    pr = {
        "number": 5,
        "title": "Test PR",
        "html_url": "https://github.com/org/repo/pull/5",
        "body": "Some description",
        "user": {"login": "elliot"},
    }
    mod._upsert_review_task(pr)

    assert fake_cur.execute.called
    sql, params = fake_cur.execute.call_args[0]
    assert "REVIEW-PR-5" in params
    assert "Review PR #5 — Test PR" in params
    assert "available" in sql
    assert "elliot" in params


def test_close_task_writes_done(mod, monkeypatch):
    """_close_review_task sets status='done'."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: fake_conn)

    mod._close_review_task(99)

    assert fake_cur.execute.called
    sql, params = fake_cur.execute.call_args[0]
    assert "done" in sql
    assert "REVIEW-PR-99" in params
