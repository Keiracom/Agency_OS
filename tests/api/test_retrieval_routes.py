"""Tests for src/api/routes/retrieval.py — Wave 5 memory override endpoint.

Mocks overrides.insert_override so the route is exercised without Supabase.
Confirms: flag-off returns 404, happy path returns 201 + row, invalid
override_type is rejected (422), and a missing-DSN RuntimeError maps to 503.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.retrieval import router

CREATED = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "memory_id": "KEI-49",
    "override_type": "ignore",
    "task_type": None,
    "expires_at": None,
    "created_at": CREATED,
}


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def test_returns_404_when_feature_disabled(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_OVERRIDES_ENABLED", raising=False)
    client = TestClient(_app())
    resp = client.post(
        "/api/v1/retrieval/overrides",
        json={"memory_id": "KEI-49", "override_type": "ignore"},
    )
    assert resp.status_code == 404


def test_happy_path_returns_201_and_row(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    with patch("src.api.routes.retrieval.overrides.insert_override", return_value=ROW) as m:
        client = TestClient(_app())
        resp = client.post(
            "/api/v1/retrieval/overrides",
            json={"memory_id": "KEI-49", "override_type": "ignore"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == ROW["id"]
    assert body["memory_id"] == "KEI-49"
    assert body["override_type"] == "ignore"
    m.assert_called_once_with("KEI-49", "ignore", task_type=None, expires_at=None)


def test_invalid_override_type_rejected_422(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    client = TestClient(_app())
    resp = client.post(
        "/api/v1/retrieval/overrides",
        json={"memory_id": "KEI-49", "override_type": "delete"},
    )
    assert resp.status_code == 422


def test_blank_memory_id_rejected_422(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    client = TestClient(_app())
    resp = client.post(
        "/api/v1/retrieval/overrides",
        json={"memory_id": "", "override_type": "prefer"},
    )
    assert resp.status_code == 422


def test_missing_dsn_maps_to_503(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    with patch(
        "src.api.routes.retrieval.overrides.insert_override",
        side_effect=RuntimeError("memory_overrides insert requires DATABASE_URL"),
    ):
        client = TestClient(_app())
        resp = client.post(
            "/api/v1/retrieval/overrides",
            json={"memory_id": "KEI-49", "override_type": "prefer"},
        )
    assert resp.status_code == 503
