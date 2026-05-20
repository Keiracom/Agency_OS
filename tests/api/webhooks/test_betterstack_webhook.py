"""Tests for src/api/webhooks/betterstack.py — KEI-26 BS incident → Linear KEI."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "betterstack.py"
SECRET = "test-bs-secret"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bs_webhook", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bs_webhook"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def client(mod, monkeypatch):
    monkeypatch.setenv("BETTERSTACK_WEBHOOK_SECRET", SECRET)
    captured: list[dict] = []
    monkeypatch.setattr(mod, "_dispatch_to_linear", lambda event: captured.append(event))
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app), captured


# Signature verify ────────────────────────────────────────────────────────────


def test_missing_token_returns_401(client):
    c, _ = client
    resp = c.post("/api/webhooks/betterstack", json={"data": {"id": "1"}})
    assert resp.status_code == 401


def test_wrong_token_returns_401(client):
    c, _ = client
    resp = c.post(
        "/api/webhooks/betterstack",
        json={"data": {"id": "1"}},
        headers={"x-webhook-secret": "wrong"},
    )
    assert resp.status_code == 401


def test_correct_header_token_accepted(client):
    c, _ = client
    resp = c.post(
        "/api/webhooks/betterstack",
        json={
            "data": {
                "id": "964390352",
                "attributes": {
                    "name": "railway-prefect",
                    "cause": "DNS lookup failure",
                    "status": "Started",
                    "url": "https://prefect.keiracom.app/api/health",
                    "started_at": "2026-05-12T12:48:08Z",
                    "metadata": {"Monitor pronounceable name": "railway-prefect", "Monitor URL": "https://prefect.keiracom.app/api/health"},
                },
                "relationships": {"monitor": {"data": {"id": "4400119"}}},
            },
        },
        headers={"x-webhook-secret": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_correct_query_token_accepted(client):
    c, _ = client
    resp = c.post(
        "/api/webhooks/betterstack?secret=" + SECRET,
        json={
            "data": {
                "id": "abc",
                "attributes": {"status": "Started", "name": "m", "cause": "c"},
            },
        },
    )
    assert resp.status_code == 200


# Event normalisation ─────────────────────────────────────────────────────────


def test_incident_started_dispatches(client):
    c, captured = client
    resp = c.post(
        "/api/webhooks/betterstack",
        json={
            "data": {
                "id": "964390352",
                "attributes": {
                    "name": "railway-prefect",
                    "cause": "DNS lookup failure",
                    "status": "Started",
                    "url": "https://prefect.keiracom.app/api/health",
                    "started_at": "2026-05-12T12:48:08Z",
                    "metadata": {"Monitor pronounceable name": "railway-prefect", "Monitor URL": "https://prefect.keiracom.app/api/health"},
                },
                "relationships": {"monitor": {"data": {"id": "4400119"}}},
            },
        },
        headers={"x-webhook-secret": SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    # KEI-20 added severity-routing fields ("channel", "severity") to the
    # response; the core ok/incident_id/monitor contract still holds.
    assert body["status"] == "ok"
    assert body["incident_id"] == "964390352"
    assert body["monitor"] == "railway-prefect"
    assert len(captured) == 1
    assert captured[0]["incident_id"] == "964390352"
    assert captured[0]["cause"] == "DNS lookup failure"


def test_incident_resolved_ignored(client):
    c, captured = client
    resp = c.post(
        "/api/webhooks/betterstack",
        json={
            "data": {
                "id": "964390352",
                "attributes": {"status": "Resolved", "name": "m", "cause": "c"},
            },
        },
        headers={"x-webhook-secret": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert captured == []


def test_missing_data_envelope_ignored(client):
    c, captured = client
    resp = c.post(
        "/api/webhooks/betterstack",
        json={"unrelated": "payload"},
        headers={"x-webhook-secret": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert captured == []


def test_malformed_json_returns_200_malformed(mod, monkeypatch):
    monkeypatch.setenv("BETTERSTACK_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(mod, "_dispatch_to_linear", lambda event: None)
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)
    resp = c.post(
        "/api/webhooks/betterstack",
        content=b"{not-json",
        headers={"x-webhook-secret": SECRET, "content-type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "malformed"


# Normaliser unit ─────────────────────────────────────────────────────────────


def test_normalise_extracts_canonical_fields(mod):
    payload = {
        "data": {
            "id": "964390352",
            "attributes": {
                "name": "supabase-rest",
                "cause": "Status 401",
                "status": "Started",
                "url": "https://x.supabase.co/rest/v1/",
                "started_at": "2026-05-12T12:48:07Z",
                "metadata": {"Monitor pronounceable name": "supabase-rest", "Monitor URL": "https://x.supabase.co/rest/v1/"},
            },
            "relationships": {"monitor": {"data": {"id": "4400118"}}},
        },
    }
    out = mod._normalise_incident(payload)
    assert out["incident_id"] == "964390352"
    assert out["monitor_name"] == "supabase-rest"
    assert out["monitor_id"] == "4400118"
    assert out["status"] == "started"
    assert out["cause"] == "Status 401"


def test_normalise_no_id_returns_none(mod):
    assert mod._normalise_incident({"data": {"attributes": {}}}) is None
    assert mod._normalise_incident({}) is None
