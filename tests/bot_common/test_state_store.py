"""tests for src/bot_common/state_store.py — JSON state file helpers.

Extracted from scripts/orchestrator/auto_session_recovery.py and
scripts/betterstack_to_linear.py (KEI-35) — covers the env-overridable
path resolver with allowlist validation, plus the load/save round trip.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.bot_common import state_store


@pytest.fixture
def caplog_warn(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.WARNING)
    return caplog


def test_resolve_state_path_uses_default_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEI35_TEST_STATE", raising=False)
    p = state_store.resolve_state_path("KEI35_TEST_STATE", "/tmp/kei35-default.json")
    assert p == Path("/tmp/kei35-default.json").resolve()


def test_resolve_state_path_honours_env_under_allowlist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """tmp_path is under /tmp, which is allowlisted."""
    override = tmp_path / "override.json"
    monkeypatch.setenv("KEI35_TEST_STATE", str(override))
    p = state_store.resolve_state_path("KEI35_TEST_STATE", "/tmp/default.json")
    assert p == override.resolve()


def test_resolve_state_path_falls_back_when_env_outside_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env override pointing outside ALLOWED_STATE_ROOTS → fallback to default."""
    monkeypatch.setenv("KEI35_TEST_STATE", "/etc/evil.json")
    p = state_store.resolve_state_path("KEI35_TEST_STATE", "/tmp/safe.json")
    assert p == Path("/tmp/safe.json").resolve()


def test_load_state_missing_returns_empty(tmp_path: Path) -> None:
    assert state_store.load_state(tmp_path / "absent.json") == {}


def test_load_state_unparseable_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "garbage.json"
    p.write_text("not json at all {")
    assert state_store.load_state(p) == {}


def test_load_state_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "round.json"
    data = {"alpha": {"foo": 1}, "beta": {"bar": 2}}
    state_store.save_state(p, data, logger=logging.getLogger("test"))
    assert state_store.load_state(p) == data


def test_save_state_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c.json"
    state_store.save_state(nested, {"x": {"y": 1}}, logger=logging.getLogger("test"))
    assert nested.exists()


def test_save_state_logs_on_oserror(
    tmp_path: Path, caplog_warn: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate write failure → warning logged with label, no exception."""

    def boom(*_a: object, **_kw: object) -> None:
        raise OSError("simulated disk full")

    target = tmp_path / "broken.json"
    monkeypatch.setattr(Path, "write_text", boom)
    state_store.save_state(
        target, {"k": {"v": 1}}, logger=logging.getLogger("kei35-test"), label="recovery-state"
    )
    assert any(
        "recovery-state save failed" in rec.message and "simulated disk full" in rec.message
        for rec in caplog_warn.records
    )


def test_is_under_helper_true_when_inside() -> None:
    assert state_store._is_under(Path("/tmp/agency-os/foo"), Path("/tmp"))


def test_is_under_helper_false_when_outside() -> None:
    assert not state_store._is_under(Path("/etc/passwd"), Path("/tmp"))
