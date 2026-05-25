"""Phase A3 — indexer_base Hindsight dual-write mirror tests.

Locks the contract of `_post_object_hindsight_mirror` per the dispatch +
Elliot operational call (b):
- DEFAULT OFF — no Hindsight traffic without explicit env opt-in
- Best-effort — Hindsight failures must NOT fail the Weaviate write
- Class→bank mapping enforced; unmapped classes skip cleanly
- Metadata stringified per PR #1130 G2 (Hindsight metadata must be all-string)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))


@pytest.fixture
def mod(monkeypatch):
    """Reload indexer_base under controlled env so HINDSIGHT_MIRROR_ENABLED
    + HINDSIGHT_BASE are deterministic per test."""
    monkeypatch.setenv("INDEXER_HINDSIGHT_MIRROR", "on")
    monkeypatch.setenv("HINDSIGHT_BASE", "http://fake-hindsight:8889")
    if "indexer_base" in sys.modules:
        del sys.modules["indexer_base"]
    return importlib.import_module("indexer_base")


@pytest.fixture
def mod_off(monkeypatch):
    """Mirror DISABLED — default-off contract."""
    monkeypatch.setenv("INDEXER_HINDSIGHT_MIRROR", "off")
    if "indexer_base" in sys.modules:
        del sys.modules["indexer_base"]
    return importlib.import_module("indexer_base")


def test_default_off_when_env_var_absent(monkeypatch):
    monkeypatch.delenv("INDEXER_HINDSIGHT_MIRROR", raising=False)
    if "indexer_base" in sys.modules:
        del sys.modules["indexer_base"]
    m = importlib.import_module("indexer_base")
    assert m.HINDSIGHT_MIRROR_ENABLED is False


def test_off_short_circuits_before_any_http(mod_off, monkeypatch):
    """Mirror-off must not call urllib at all (zero blast radius when off)."""
    called = []
    monkeypatch.setattr(
        mod_off.urlrequest,
        "urlopen",
        lambda *a, **kw: called.append(1) or pytest.fail("must not call urlopen"),
    )
    mod_off._post_object_hindsight_mirror(
        {"class": "Decisions", "id": "x", "properties": {"raw_text": "y"}}
    )
    assert called == []


def test_unmapped_class_skips_cleanly(mod, monkeypatch):
    """Unknown Weaviate class → log debug + return; no HTTP call."""
    called = []
    monkeypatch.setattr(
        mod.urlrequest,
        "urlopen",
        lambda *a, **kw: called.append(1) or pytest.fail("must not call urlopen"),
    )
    mod._post_object_hindsight_mirror(
        {"class": "Discoveries", "id": "x", "properties": {"raw_text": "y"}}
    )
    assert called == []


def test_mapped_class_posts_to_bank_with_items_envelope(mod, monkeypatch):
    captured = []

    class _FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    def _fake_urlopen(req, timeout=None):
        captured.append(
            {
                "url": req.full_url,
                "method": req.get_method(),
                "body": req.data.decode() if req.data else None,
            }
        )
        return _FakeResp()

    monkeypatch.setattr(mod.urlrequest, "urlopen", _fake_urlopen)
    mod._post_object_hindsight_mirror(
        {
            "class": "Decisions",
            "id": "kei-decisions-42",
            "properties": {"raw_text": "We chose X.", "agent": "atlas"},
        }
    )
    import json as _json

    assert len(captured) == 1
    assert captured[0]["url"].endswith("/v1/default/banks/fleet_decisions/memories")
    assert captured[0]["method"] == "POST"
    body = _json.loads(captured[0]["body"])
    assert "items" in body
    assert body["async"] is False
    assert body["items"][0]["content"] == "We chose X."
    assert "weaviate_class:Decisions" in body["items"][0]["tags"]


def test_metadata_is_all_string_per_g2(mod, monkeypatch):
    captured = []
    import json as _json

    class _FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    monkeypatch.setattr(
        mod.urlrequest,
        "urlopen",
        lambda req, timeout=None: (captured.append(_json.loads(req.data.decode())), _FakeResp())[1],
    )
    mod._post_object_hindsight_mirror(
        {
            "class": "Keis",
            "id": "kei-99",
            "properties": {"raw_text": "x", "version": 3, "tags": ["a", "b"]},
        }
    )
    item = captured[0]["items"][0]
    assert all(isinstance(v, str) for v in item["metadata"].values()), item["metadata"]


def test_failure_logs_warn_does_not_raise(mod, monkeypatch):
    """Best-effort: URLError must not fail the indexer batch."""

    def _raise_urlerror(*a, **kw):
        from urllib import error

        raise error.URLError("network down")

    monkeypatch.setattr(mod.urlrequest, "urlopen", _raise_urlerror)
    # Must NOT raise
    mod._post_object_hindsight_mirror(
        {"class": "Decisions", "id": "x", "properties": {"raw_text": "y"}}
    )


def test_timeout_logs_warn_does_not_raise(mod, monkeypatch):
    def _raise_timeout(*a, **kw):
        raise TimeoutError("read timeout")

    monkeypatch.setattr(mod.urlrequest, "urlopen", _raise_timeout)
    mod._post_object_hindsight_mirror(
        {"class": "Decisions", "id": "x", "properties": {"raw_text": "y"}}
    )


def test_post_object_calls_mirror_on_success(mod, monkeypatch):
    """post_object success path triggers mirror call (when ON)."""
    mirror_calls = []
    monkeypatch.setattr(mod, "_post_object_hindsight_mirror", lambda obj: mirror_calls.append(obj))

    class _FakeResp:
        status = 200

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    # Force _http_request → success
    from contextlib import contextmanager

    @contextmanager
    def _fake_http(method, path, body=None):
        yield _FakeResp()

    monkeypatch.setattr(mod, "_http_request", _fake_http)
    ok = mod.post_object({"class": "Decisions", "id": "x", "properties": {"raw_text": "y"}})
    assert ok is True
    assert len(mirror_calls) == 1
    assert mirror_calls[0]["class"] == "Decisions"


def test_post_object_calls_mirror_on_422_already_exists(mod, monkeypatch):
    """422 idempotent no-op is treated as success → mirror still fires."""
    mirror_calls = []
    monkeypatch.setattr(mod, "_post_object_hindsight_mirror", lambda obj: mirror_calls.append(obj))
    from contextlib import contextmanager
    from urllib import error

    @contextmanager
    def _raise_422(method, path, body=None):
        raise error.HTTPError(url=path, code=422, msg="exists", hdrs=None, fp=None)
        yield  # unreachable

    monkeypatch.setattr(mod, "_http_request", _raise_422)
    ok = mod.post_object({"class": "Decisions", "id": "x", "properties": {"raw_text": "y"}})
    assert ok is True
    assert len(mirror_calls) == 1
