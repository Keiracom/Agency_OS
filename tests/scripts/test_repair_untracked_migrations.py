"""Unit tests for scripts/orchestrator/repair_untracked_migrations.py.

Pure-function tests for version derivation (git-free via monkeypatch). The
DB/CLI paths are integration-only and exercised live by the sweep itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

if importlib.util.find_spec("repair_untracked_migrations") is None:
    pytest.skip("module not importable", allow_module_level=True)

import repair_untracked_migrations as rum  # noqa: E402


def _no_git(monkeypatch):
    def _raise(*_a, **_k):
        raise subprocess.SubprocessError("no git")

    monkeypatch.setattr(rum.subprocess, "check_output", _raise)


def test_derive_version_fallback_from_date_prefix(monkeypatch):
    _no_git(monkeypatch)
    assert rum.derive_version("20260527_foo", set()) == "20260527000000"


def test_derive_version_collision_bumps(monkeypatch):
    _no_git(monkeypatch)
    used: set[str] = set()
    v1 = rum.derive_version("20260527_foo", used)
    v2 = rum.derive_version("20260527_foo", used)  # same fallback → must bump
    assert v1 == "20260527000000"
    assert v2 == "20260527000001"
    assert {v1, v2} <= used


def test_derive_version_non_date_basename_constant_fallback(monkeypatch):
    _no_git(monkeypatch)
    assert rum.derive_version("evo_task_queue", set()) == "20260101000000"


def test_derive_version_uses_git_timestamp_when_available(monkeypatch):
    monkeypatch.setattr(rum.subprocess, "check_output", lambda *_a, **_k: "20260604131432\n")
    assert rum.derive_version("anything", set()) == "20260604131432"
