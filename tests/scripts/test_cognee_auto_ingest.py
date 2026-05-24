"""tests for scripts/cognee_auto_ingest.py + cognee_http_client.py.

Two scopes locked here:
- Agency_OS-zbvs (watch-set parity): the --watch set must cover the same
  root-level core-truth docs as the --once set (original anchor 2026-05-20).
- Agency_OS-cuee (cognify wiring + batched cognify): every successful /add
  must trigger /cognify, batched to bounded delta so cognee.service stays
  under MemoryHigh=2700M; /cognify TimeoutError must NOT crash callers.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "cognee_auto_ingest.py"
HTTP_SCRIPT = REPO_ROOT / "scripts" / "cognee_http_client.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def http():
    # Force-load THIS worktree's cognee_http_client so it carries the cognify()
    # symbol the PR adds. cognee_auto_ingest hard-codes sys.path to the main
    # worktree's scripts dir; pre-seeding sys.modules makes tests worktree-agnostic.
    return _load("cognee_http_client", HTTP_SCRIPT)


@pytest.fixture
def mod(http):
    return _load("cognee_auto_ingest", SCRIPT)


# ------------- Agency_OS-zbvs (existing locks, retained) -------------


def test_root_core_files_includes_architecture(mod):
    """ARCHITECTURE.md MUST be a tracked core-truth file — its absence from
    the watch set was the root cause of the memory-content drift."""
    assert "ARCHITECTURE.md" in mod._ROOT_CORE_FILES
    assert "CLAUDE.md" in mod._ROOT_CORE_FILES
    assert "DEFINITION_OF_DONE.md" in mod._ROOT_CORE_FILES


def test_files_in_uses_the_shared_root_core_constant(mod):
    """_files_in must include every _ROOT_CORE_FILES entry — so the --once
    set and the --watch set share one source of truth and cannot drift."""
    files = mod._files_in(REPO_ROOT)
    names = {p.name for p in files}
    for core in mod._ROOT_CORE_FILES:
        assert core in names, f"{core} missing from _files_in — watch/once drift risk"


# ------------- Agency_OS-cuee Defect 2 (batched cognify) -------------


def test_run_once_batches_to_groups_of_n(mod, monkeypatch):
    """52-file set → exactly 7 cognify calls (6×8 + 1×4); each batch sized ≤8."""
    paths = [Path(f"/tmp/dummy_{i}.md") for i in range(52)]
    monkeypatch.setattr(mod, "targets", lambda: paths)
    monkeypatch.setattr(mod, "cognee_health", lambda: {"status": "ready"})
    monkeypatch.setattr(mod, "ingest_one", lambda p: True)
    settle_calls: list[dict] = []
    monkeypatch.setattr(mod, "_cognify_settle", lambda **kw: settle_calls.append(kw))

    stats = mod.run_once()
    assert stats["files"] == 52
    assert stats["ok"] == 52
    assert stats["errors"] == 0
    assert stats["batches"] == 7
    assert len(settle_calls) == 7


def test_run_once_partial_batch_failure_still_cognifies(mod, monkeypatch):
    """batch_ok > 0 must still trigger cognify even when half the batch failed."""
    paths = [Path(f"/tmp/dummy_{i}.md") for i in range(8)]
    monkeypatch.setattr(mod, "targets", lambda: paths)
    monkeypatch.setattr(mod, "cognee_health", lambda: {"status": "ready"})
    calls = iter([False, False, False, False, True, True, True, True])
    monkeypatch.setattr(mod, "ingest_one", lambda p: next(calls))
    settle_calls: list[dict] = []
    monkeypatch.setattr(mod, "_cognify_settle", lambda **kw: settle_calls.append(kw))

    stats = mod.run_once()
    assert stats["ok"] == 4
    assert stats["errors"] == 4
    assert stats["batches"] == 1
    assert len(settle_calls) == 1


def test_run_once_all_batch_fails_skips_cognify(mod, monkeypatch):
    """batch_ok == 0 must NOT trigger cognify — avoids cognify-on-empty-delta noise."""
    paths = [Path(f"/tmp/dummy_{i}.md") for i in range(8)]
    monkeypatch.setattr(mod, "targets", lambda: paths)
    monkeypatch.setattr(mod, "cognee_health", lambda: {"status": "ready"})
    monkeypatch.setattr(mod, "ingest_one", lambda p: False)
    settle_calls: list[dict] = []
    monkeypatch.setattr(mod, "_cognify_settle", lambda **kw: settle_calls.append(kw))

    stats = mod.run_once()
    assert stats["ok"] == 0
    assert stats["errors"] == 8
    assert stats["batches"] == 0
    assert settle_calls == []


# ------------- Agency_OS-cuee Defect 1 (cognify wiring) -------------


def test_cognify_default_datasets_posts_empty_body(http, monkeypatch):
    """cognify() with no dataset arg → empty body (lets Cognee process all pending)."""
    captured: list[tuple] = []
    monkeypatch.setattr(
        http,
        "_authed_post",
        lambda p, b, timeout=30: captured.append((p, b, timeout)) or {"ok": True},
    )
    http.cognify()
    assert captured[0][0] == "/api/v1/cognify"
    assert captured[0][1] == {}


def test_cognify_with_datasets_posts_list(http, monkeypatch):
    """cognify(datasets=[...]) → POST body {'datasets': [...]} per CognifyPayloadDTO."""
    captured: list[tuple] = []
    monkeypatch.setattr(
        http,
        "_authed_post",
        lambda p, b, timeout=30: captured.append((p, b, timeout)) or {"ok": True},
    )
    http.cognify(datasets=["governance"])
    assert captured[0][1] == {"datasets": ["governance"]}


def test_watch_loop_calls_cognify_after_successful_ingest(mod):
    """Defect 1 regression — watch_loop's post-ingest path must call
    _cognify_settle, gated on ingest_one returning True (not unconditional).

    Structural lock: inotify-driven integration test would need subprocess +
    filesystem mocks (~30 LoC), which is high-fragility for a wiring check.
    Source inspection catches the same regressions (call removed, call before
    ingest, wrong settle constant) with no flake surface.
    """
    source = inspect.getsource(mod.watch_loop)
    assert "if ingest_one(ev):" in source, "ingest_one return value must gate cognify"
    assert "_cognify_settle(settle=WATCH_SETTLE_DEFAULT" in source, (
        "watch-mode cognify must use WATCH_SETTLE_DEFAULT (1s), not BATCH_SETTLE_DEFAULT (5s)"
    )
    ingest_pos = source.find("if ingest_one(ev):")
    cognify_pos = source.find("_cognify_settle(settle=WATCH_SETTLE_DEFAULT")
    assert ingest_pos < cognify_pos, "cognify must be inside the ingest_one success branch"


# ------------- Agency_OS-cuee same-PR timeout fix -------------


def test_authed_post_timeout_returns_error_dict(http, monkeypatch):
    """TimeoutError on long /cognify must NOT crash — urllib does not wrap
    socket read-timeouts in URLError, so they fall through the URLError except.
    Regression-lock from empirical smoke catch (see PR #1114 description)."""
    monkeypatch.setattr(http, "get_token", lambda: "fake-token")

    def _raise_timeout(*args, **kwargs):
        raise TimeoutError("read timeout")

    monkeypatch.setattr(http.urllib.request, "urlopen", _raise_timeout)
    result = http._authed_post("/api/v1/cognify", {"datasets": ["x"]}, timeout=1)
    assert isinstance(result, dict)
    assert result.get("error") == "read timeout"


def test_authed_post_bare_timeout_falls_back_to_class_name(http, monkeypatch):
    """Empty-message TimeoutError must fall back to type name via
    `str(e)[:200] or type(e).__name__`, so the caller never gets an empty error."""
    monkeypatch.setattr(http, "get_token", lambda: "fake-token")

    def _raise_bare_timeout(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(http.urllib.request, "urlopen", _raise_bare_timeout)
    result = http._authed_post("/api/v1/cognify", {}, timeout=1)
    assert result.get("error") == "TimeoutError"
