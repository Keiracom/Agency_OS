"""Tests for src/api/webhooks/github.py — KEI-97 Part A1.

Covers:
  - HMAC missing/wrong → 401 (NOT fail-open)
  - Non-PR event → 200 no-op
  - PR opened → INSERT/UPSERT with REVIEW-PR-N id
  - PR synchronize → ON CONFLICT path (idempotent)
  - PR closed → UPDATE status='done'
  - Closed with already-done row → WHERE guard in SQL
  - DB failure → fail-open 200
  - Heartbeat ticked on HMAC-passed events
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
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "github.py"
TEST_SECRET = "test-github-secret"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("github_webhook", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["github_webhook"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def client(mod, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def _sign(body: bytes, secret: str = TEST_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _pr_payload(action: str = "opened", number: int = 927, title: str = "My PR") -> dict:
    return {
        "action": action,
        "number": number,
        "pull_request": {
            "number": number,
            "title": title,
            "html_url": f"https://github.com/org/repo/pull/{number}",
            "state": "open" if action != "closed" else "closed",
            "merged": action == "closed",
        },
        "repository": {"full_name": "org/repo"},
        "sender": {"login": "developer"},
    }


def _post_pr(
    client: TestClient,
    payload: dict,
    secret: str = TEST_SECRET,
    event: str = "pull_request",
    omit_signature: bool = False,
    bad_signature: bool = False,
) -> object:
    raw = json.dumps(payload).encode()
    headers: dict[str, str] = {"content-type": "application/json", "x-github-event": event}
    if not omit_signature:
        sig = _sign(raw, secret) if not bad_signature else "sha256=" + "0" * 64
        headers["x-hub-signature-256"] = sig
    return client.post("/api/webhooks/github", content=raw, headers=headers)


# ── HMAC verification ────────────────────────────────────────────────────────


def test_hmac_missing_returns_401(client):
    resp = _post_pr(client, _pr_payload(), omit_signature=True)
    assert resp.status_code == 401


def test_hmac_wrong_returns_401(client):
    resp = _post_pr(client, _pr_payload(), bad_signature=True)
    assert resp.status_code == 401


def test_hmac_correct_returns_200(client, mod, monkeypatch):
    monkeypatch.setattr(mod, "_upsert_review_task", lambda **kw: None)
    resp = _post_pr(client, _pr_payload(action="opened"))
    assert resp.status_code == 200


# ── Non-PR event no-op ────────────────────────────────────────────────────────


def test_non_pr_event_noops(client, mod, monkeypatch):
    """push event → 200 no-op, no DB write."""
    upsert_calls: list = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda **kw: upsert_calls.append(kw))
    payload = {"ref": "refs/heads/main", "commits": []}
    raw = json.dumps(payload).encode()
    headers = {
        "content-type": "application/json",
        "x-github-event": "push",
        "x-hub-signature-256": _sign(raw),
    }
    resp = client.post("/api/webhooks/github", content=raw, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert upsert_calls == []


# ── PR opened → insert ────────────────────────────────────────────────────────


def test_pr_opened_inserts_task_row(mod, monkeypatch):
    """opened action → _upsert_review_task called with correct args."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    calls: list[dict] = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda **kw: calls.append(kw))
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)

    resp = _post_pr(c, _pr_payload(action="opened", number=927, title="Add feature X"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["op"] == "upsert"
    assert data["task_id"] == "REVIEW-PR-927"
    assert len(calls) == 1
    assert calls[0]["pr_number"] == 927
    assert calls[0]["pr_title"] == "Add feature X"


def test_pr_opened_task_id_format(mod, monkeypatch):
    """task_id must follow REVIEW-PR-{number} exactly."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(mod, "_upsert_review_task", lambda **kw: None)
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)

    resp = _post_pr(c, _pr_payload(action="opened", number=1))
    assert resp.json()["task_id"] == "REVIEW-PR-1"


# ── PR synchronize → upsert idempotent ───────────────────────────────────────


def test_pr_synchronize_upserts_idempotent(mod, monkeypatch):
    """synchronize on existing PR → same upsert path (ON CONFLICT in SQL)."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    calls: list[dict] = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda **kw: calls.append(kw))
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)

    resp = _post_pr(c, _pr_payload(action="synchronize", number=100))
    assert resp.status_code == 200
    assert resp.json()["op"] == "upsert"
    assert len(calls) == 1


# ── PR closed → mark done ─────────────────────────────────────────────────────


def test_pr_closed_marks_done(mod, monkeypatch):
    """closed action → _mark_review_done called."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    done_calls: list[int] = []
    monkeypatch.setattr(mod, "_mark_review_done", lambda pr_number: done_calls.append(pr_number))
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)

    resp = _post_pr(c, _pr_payload(action="closed", number=927))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["op"] == "done"
    assert data["task_id"] == "REVIEW-PR-927"
    assert done_calls == [927]


def test_pr_closed_already_done_no_downgrade(mod, monkeypatch):
    """_mark_review_done SQL must NOT include `AND status != 'done'` guard
    on the done-path itself (we ARE setting to done, matching linear.py:265 pattern).
    Verify the UPDATE SQL targets the row by id only — the guard that prevents
    *non-done* transitions is only needed for non-done status updates.

    We extract the SQL string directly from the source to avoid matching docstring text.
    """
    import ast
    import inspect

    src = inspect.getsource(mod._mark_review_done)
    # Parse the source and extract all string literals (SQL is passed as a string arg)
    tree = ast.parse(src)
    string_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    # Find the SQL string — it contains UPDATE public.tasks
    sql_strings = [s for s in string_literals if "UPDATE public.tasks" in s]
    assert sql_strings, "Could not find UPDATE SQL in _mark_review_done"
    sql = sql_strings[0]

    # SQL must set status='done'
    assert "status" in sql and "'done'" in sql
    # SQL must NOT have a downgrade guard on the done-path
    assert "AND status != 'done'" not in sql
    # SQL must target by id
    assert "WHERE id = %s" in sql


# ── DB failure → fail-open ────────────────────────────────────────────────────


def test_db_failure_fails_open_returns_200(mod, monkeypatch):
    """psycopg.connect raises → handler returns 200 (fail-open)."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake:5432/db")

    import psycopg as _psycopg_real

    def _boom(*a, **kw):
        raise _psycopg_real.OperationalError("connection refused")

    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)

    with patch.object(_psycopg_real, "connect", side_effect=_boom):
        resp = _post_pr(c, _pr_payload(action="opened", number=50))

    assert resp.status_code == 200
    # Fail-open means we still got a response — the task_id was computed even
    # though DB write failed.
    assert resp.json()["status"] == "ok"


# ── Heartbeat ticked on HMAC pass ─────────────────────────────────────────────


def test_heartbeat_ticked_on_hmac_pass(mod, monkeypatch):
    """_heartbeat_tick called exactly once on a valid HMAC-passed payload."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(mod, "_upsert_review_task", lambda **kw: None)

    tick_calls: list[dict] = []

    def _fake_tick(name, **kwargs):
        tick_calls.append({"name": name, **kwargs})

    monkeypatch.setattr(mod, "_heartbeat_tick", _fake_tick)

    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)

    _post_pr(c, _pr_payload(action="opened", number=200))

    assert len(tick_calls) == 1
    assert tick_calls[0]["name"] == "github-webhook-handler"
    assert tick_calls[0].get("outcome_increment", 0) >= 1
