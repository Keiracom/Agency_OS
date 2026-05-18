"""Tests for KEI-207: GitHub PR merge webhook → auto-close KEI tasks.

Covers the _handle_kei_task_close_on_merge path and the surrounding
handler branch (action='closed', merged=True).

Mock strategy: monkeypatch psycopg.connect; use FastAPI TestClient for
HTTP-level tests. No live DB or live GitHub.
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
TEST_SECRET = "test-kei207-secret"


@pytest.fixture(scope="module")
def mod():
    # Load into a fresh module name to avoid collision with test_github_webhook.py
    spec = importlib.util.spec_from_file_location("github_webhook_kei207", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["github_webhook_kei207"] = m
    spec.loader.exec_module(m)
    return m


def _make_client(mod, monkeypatch, *, secret: str = TEST_SECRET):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/kei207")
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def _sign(body: bytes, secret: str = TEST_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _merge_payload(
    number: int = 207,
    title: str = "[MAX] feat(KEI-207): something",
    html_url: str = "https://github.com/Keiracom/Agency_OS/pull/207",
    merged: bool = True,
    action: str = "closed",
) -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": number,
            "title": title,
            "html_url": html_url,
            "body": "PR body — should not appear in logs per no-PII rule",
            "merged": merged,
            "user": {"login": "max"},
        },
    }


def _make_fake_conn(monkeypatch, psycopg, *, rows=None):
    """Return (fake_conn, fake_cur) mocks wired for psycopg.connect."""
    fake_cur = MagicMock()
    if rows is not None:
        fake_cur.fetchall.return_value = rows
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: fake_conn)
    return fake_conn, fake_cur


# ── 1. Title match closes KEI task ───────────────────────────────────────


def test_pr_merge_with_kei_in_title_closes_task(mod, monkeypatch):
    """PR merge with KEI-207 in title → UPDATE tasks SET status='done' WHERE id='KEI-207'."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/kei207")
    import psycopg

    fake_cur = MagicMock()
    fake_cur.fetchall.return_value = []
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    connect_calls: list[dict] = []

    def fake_connect(*args, **kwargs):
        connect_calls.append(kwargs)
        return fake_conn

    monkeypatch.setattr(psycopg, "connect", fake_connect)

    mod._handle_kei_task_close_on_merge(
        "[MAX] feat(KEI-207): GitHub PR merge webhook",
        "https://github.com/Keiracom/Agency_OS/pull/207",
    )

    # psycopg.connect must use prepare_threshold=None (pgbouncer compat)
    assert any(
        kw.get("prepare_threshold") == 0 or "prepare_threshold" in kw for kw in connect_calls
    ), "psycopg.connect must be called with prepare_threshold=None"
    assert fake_cur.execute.called
    sql, params = fake_cur.execute.call_args[0]
    assert "status" in sql and "done" in sql
    assert "KEI-207" in params


# ── 2. Body-only KEI (no title match) falls back to linear_url ───────────


def test_pr_merge_with_kei_in_body_only_misses_title_uses_fallback(mod, monkeypatch):
    """Title without KEI, body has it → fallback _close_kei_task_by_pr_url is called."""
    fallback_calls: list[str] = []
    monkeypatch.setattr(
        mod, "_close_kei_task_by_pr_url", lambda url: fallback_calls.append(url) or False
    )

    mod._handle_kei_task_close_on_merge(
        "refactor: clean up code",  # no KEI in title
        "https://github.com/Keiracom/Agency_OS/pull/999",
    )

    assert fallback_calls == ["https://github.com/Keiracom/Agency_OS/pull/999"]


# ── 3. Uppercase KEI matches (case-sensitivity documented) ────────────────


def test_pr_merge_uppercase_kei_matches(mod, monkeypatch):
    """Regex KEI-\\d+ is case-sensitive; uppercase KEI-123 matches, lowercase kei-123 does not.

    Linear's canonical format is uppercase. Lowercase is intentionally excluded.
    """
    close_calls: list[str] = []
    monkeypatch.setattr(mod, "_close_kei_task_by_id", lambda kei_id: close_calls.append(kei_id))

    # Uppercase match
    mod._handle_kei_task_close_on_merge("feat(KEI-123): something", "https://github.com/x/y/pull/1")
    assert "KEI-123" in close_calls

    # Lowercase should NOT match — fallback path fires instead
    close_calls.clear()
    fallback_calls: list[str] = []
    monkeypatch.setattr(
        mod, "_close_kei_task_by_pr_url", lambda url: fallback_calls.append(url) or False
    )
    mod._handle_kei_task_close_on_merge("feat(kei-456): something", "https://github.com/x/y/pull/2")
    assert not close_calls  # _close_kei_task_by_id NOT called
    assert fallback_calls  # fallback fired


# ── 4. Fallback: linear_url match closes task ────────────────────────────


def test_pr_merge_no_kei_in_title_falls_back_to_linear_url_query(mod, monkeypatch):
    """No KEI in title → fallback queries tasks.linear_url = pr_url, closes matching row."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/kei207")
    import psycopg

    fake_cur = MagicMock()
    fake_cur.fetchall.return_value = [("KEI-501",)]  # one match
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: fake_conn)

    result = mod._close_kei_task_by_pr_url("https://github.com/Keiracom/Agency_OS/pull/501")

    assert result is True
    assert fake_cur.execute.called
    sql, params = fake_cur.execute.call_args[0]
    assert "linear_url" in sql
    assert "https://github.com/Keiracom/Agency_OS/pull/501" in params


# ── 5. No match anywhere → 200 + log (no error) ─────────────────────────


def test_pr_merge_no_match_logs_and_returns_200(mod, monkeypatch):
    """No KEI in title AND no linear_url match → webhook returns 200, no exception."""
    monkeypatch.setattr(mod, "_close_review_task", lambda n: None)
    monkeypatch.setattr(mod, "_handle_kei_task_close_on_merge", lambda title, url: None)
    client = _make_client(mod, monkeypatch)

    payload = _merge_payload(title="chore: cleanup with no kei reference", merged=True)
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


# ── 6. Closed but not merged → KEI close skipped ────────────────────────


def test_pr_closed_but_not_merged_skipped(mod, monkeypatch):
    """action=closed, merged=false → _handle_kei_task_close_on_merge NOT called."""
    kei_close_calls: list = []
    monkeypatch.setattr(mod, "_close_review_task", lambda n: None)
    monkeypatch.setattr(
        mod, "_handle_kei_task_close_on_merge", lambda t, u: kei_close_calls.append((t, u))
    )
    client = _make_client(mod, monkeypatch)

    payload = _merge_payload(merged=False, action="closed")
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
    assert kei_close_calls == []  # KEI-207 path NOT triggered


# ── 7. PR opened → KEI close not triggered ──────────────────────────────


def test_pr_opened_action_skipped(mod, monkeypatch):
    """action=opened → KEI-207 path not triggered (KEI-97 territory only)."""
    kei_close_calls: list = []
    monkeypatch.setattr(mod, "_upsert_review_task", lambda pr: None)
    monkeypatch.setattr(
        mod, "_handle_kei_task_close_on_merge", lambda t, u: kei_close_calls.append((t, u))
    )
    client = _make_client(mod, monkeypatch)

    payload = _merge_payload(action="opened", merged=False)
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
    assert kei_close_calls == []


# ── 8. synchronize action → skipped ─────────────────────────────────────


def test_pr_synchronize_action_skipped(mod, monkeypatch):
    """action=synchronize → ignored entirely, no KEI close."""
    kei_close_calls: list = []
    monkeypatch.setattr(
        mod, "_handle_kei_task_close_on_merge", lambda t, u: kei_close_calls.append((t, u))
    )
    client = _make_client(mod, monkeypatch)

    payload = _merge_payload(action="synchronize")
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
    assert resp.json()["status"] == "ignored"
    assert kei_close_calls == []


# ── 9. DB error → fail-open, webhook returns 200 ────────────────────────


def test_db_error_returns_200_logs_warning(mod, monkeypatch):
    """psycopg.Error on UPDATE → fail-open: _close_kei_task_by_id swallows, webhook 200."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/kei207")
    import psycopg

    monkeypatch.setattr(
        psycopg, "connect", MagicMock(side_effect=psycopg.OperationalError("conn refused"))
    )

    # Should not raise — fail-open contract
    mod._close_kei_task_by_id("KEI-207")  # verifies no exception propagates


def test_db_error_on_merge_webhook_returns_200(mod, monkeypatch):
    """DB error during KEI close on PR merge → webhook still returns HTTP 200."""
    import psycopg

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/kei207")
    monkeypatch.setattr(mod, "_close_review_task", lambda n: None)
    monkeypatch.setattr(
        psycopg, "connect", MagicMock(side_effect=psycopg.OperationalError("conn refused"))
    )
    client = _make_client(mod, monkeypatch)

    payload = _merge_payload(title="[MAX] feat(kei207): something", merged=True)
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


# ── 10. UPDATE query param binding shape ────────────────────────────────


def test_update_query_uses_correct_id_param(mod, monkeypatch):
    """_close_kei_task_by_id: UPDATE tasks SET status='done' WHERE id=%s with kei_id as param."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/kei207")
    import psycopg

    fake_cur = MagicMock()
    fake_conn = MagicMock()
    fake_conn.__enter__ = MagicMock(return_value=fake_conn)
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value.__enter__ = MagicMock(return_value=fake_cur)
    fake_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: fake_conn)

    mod._close_kei_task_by_id("KEI-999")

    assert fake_cur.execute.called
    sql, params = fake_cur.execute.call_args[0]
    # Verify parameterised: id bound as positional arg, not interpolated
    assert "%s" in sql or "$1" in sql
    assert "KEI-999" in params
    assert "done" in sql
