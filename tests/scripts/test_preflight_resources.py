"""Unit tests for scripts/orchestrator/preflight_resources.py (KEI-56)."""

from __future__ import annotations

from unittest import mock

import pytest

from scripts.orchestrator import preflight_resources as pf


def test_check_headroom_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pf, "_read_meminfo", lambda: {"MemAvailable": 4096})
    ok, available = pf.check_headroom(2048)
    assert ok is True
    assert available == 4096


def test_check_headroom_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pf, "_read_meminfo", lambda: {"MemAvailable": 1024})
    ok, available = pf.check_headroom(2048)
    assert ok is False
    assert available == 1024


def test_check_headroom_missing_meminfo_fails_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """If MemAvailable can't be read, default to 0 → block."""
    monkeypatch.setattr(pf, "_read_meminfo", lambda: {})
    ok, _ = pf.check_headroom(2048)
    assert ok is False


def test_main_exit_0_on_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pf, "_read_meminfo", lambda: {"MemAvailable": 10000})
    rc = pf.main(["--headroom-mb", "2048", "--service", "weaviate"])
    assert rc == 0


def test_main_exit_1_on_fail_and_posts_ceo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pf, "_read_meminfo", lambda: {"MemAvailable": 500})
    with mock.patch.object(pf, "_post_ceo_block") as post_mock:
        rc = pf.main(["--headroom-mb", "2048", "--service", "weaviate"])
    assert rc == 1
    post_mock.assert_called_once()
    args, _ = post_mock.call_args
    assert args[0] == "weaviate"
    assert args[1] == 500  # available
    assert args[2] == 2048  # required
