"""Tests for scripts/orchestrator/betterstack_status_page.py — PR-D.

Mocks the urllib request layer via a closure-captured fake _request injector.
Verifies idempotency contract:
  - ensure_page: match-by-subdomain returns existing, else POSTs new page.
  - attach_resource: skips when (resource_id, resource_type) already present.
  - _by_name + _by_heartbeat_name: pronounceable_name vs name attribute.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "betterstack_status_page.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bs_status_page", SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bs_status_page"] = m
    spec.loader.exec_module(m)
    return m


# ensure_page ─────────────────────────────────────────────────────────────────


def test_ensure_page_match_by_subdomain_returns_existing(mod, monkeypatch):
    existing = [
        {"id": "111", "attributes": {"subdomain": "agency-os", "company_name": "Agency OS"}},
        {"id": "222", "attributes": {"subdomain": "other", "company_name": "Other"}},
    ]

    def _no_request(*args, **kwargs):
        raise AssertionError("ensure_page should not POST when subdomain matches")

    monkeypatch.setattr(mod, "_request", _no_request)
    result = mod.ensure_page("k", "agency-os", existing)
    assert result is not None
    assert result["id"] == "111"


def test_ensure_page_no_match_posts_new(mod, monkeypatch):
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        return {"data": {"id": "333", "attributes": {"subdomain": "agency-os"}}}

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_page("k", "agency-os", existing=[])
    assert result is not None
    assert result["id"] == "333"
    assert captured[0][0] == "POST"
    assert captured[0][1] == "/status-pages"
    assert captured[0][2]["subdomain"] == "agency-os"
    assert captured[0][2]["timezone"] == "UTC"


# attach_resource ─────────────────────────────────────────────────────────────


def test_attach_resource_skips_if_already_present(mod, monkeypatch):
    existing = [
        {
            "id": "8858461",
            "attributes": {"resource_id": 4400037, "resource_type": "Monitor", "public_name": "agencyxos.ai"},
        },
    ]

    def _no_request(*args, **kwargs):
        raise AssertionError("attach_resource must not POST when already present")

    monkeypatch.setattr(mod, "_request", _no_request)
    result = mod.attach_resource("k", "247160", 4400037, "Monitor", "agencyxos.ai", existing)
    assert result is not None
    assert result["id"] == "8858461"


def test_attach_resource_posts_when_missing(mod, monkeypatch):
    captured: list[tuple] = []

    def _fake(method, path, api_key, body=None):
        captured.append((method, path, body))
        return {"data": {"id": "9999", "attributes": body or {}}}

    monkeypatch.setattr(mod, "_request", _fake)
    result = mod.attach_resource("k", "247160", 4400118, "Monitor", "supabase-rest", existing=[])
    assert result is not None
    assert captured[0][0] == "POST"
    assert captured[0][1] == "/status-pages/247160/resources"
    assert captured[0][2] == {
        "resource_id": 4400118,
        "resource_type": "Monitor",
        "public_name": "supabase-rest",
    }


def test_attach_resource_distinguishes_type(mod, monkeypatch):
    """resource_id collision across types must NOT block attach."""
    existing = [
        {"attributes": {"resource_id": 5, "resource_type": "Monitor"}},
    ]
    captured: list[tuple] = []

    def _fake(method, path, api_key, body=None):
        captured.append((method, path, body))
        return {"data": {"id": "new"}}

    monkeypatch.setattr(mod, "_request", _fake)
    result = mod.attach_resource("k", "p", 5, "Heartbeat", "hb-name", existing)
    assert result is not None
    assert captured[0][0] == "POST"


# _by_name + _by_heartbeat_name ───────────────────────────────────────────────


def test_by_name_matches_pronounceable_name(mod):
    monitors = [
        {"id": "1", "attributes": {"pronounceable_name": "agencyxos.ai"}},
        {"id": "2", "attributes": {"pronounceable_name": "supabase-rest"}},
    ]
    assert mod._by_name(monitors, "agencyxos.ai")["id"] == "1"
    assert mod._by_name(monitors, "supabase-rest")["id"] == "2"
    assert mod._by_name(monitors, "missing") is None


def test_by_heartbeat_name_matches_name_attr(mod):
    hbs = [
        {"id": "10", "attributes": {"name": "elliot-polling-loop"}},
        {"id": "11", "attributes": {"name": "cognee-phase1-ingest"}},
    ]
    assert mod._by_heartbeat_name(hbs, "elliot-polling-loop")["id"] == "10"
    assert mod._by_heartbeat_name(hbs, "missing") is None


# main ────────────────────────────────────────────────────────────────────────


def test_main_missing_api_key_returns_2(mod, monkeypatch):
    monkeypatch.delenv("BETTERSTACK_API_KEY", raising=False)
    assert mod.main() == 2
