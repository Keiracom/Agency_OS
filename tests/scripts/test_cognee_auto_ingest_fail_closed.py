"""Tests for cognee_auto_ingest --once fail-closed behavior (Agency_OS-8egh).

Before this fix --once always returned 0, so a drift cron would see a green
no-op even when Cognee was down and nothing was ingested. --once must now exit
non-zero when Cognee health is down. --watch behavior is unchanged (fail-open).

No live Cognee dependency — health + targets are monkeypatched.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "cognee_auto_ingest.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("cognee_auto_ingest", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cognee_auto_ingest"] = m
    spec.loader.exec_module(m)
    return m


def test_once_returns_nonzero_when_cognee_down(mod, monkeypatch):
    """Health down -> nothing ingested -> rc != 0 (fail-closed)."""
    monkeypatch.setattr(mod, "cognee_health", lambda: {"status": "down", "error": "refused"})
    monkeypatch.setattr(sys, "argv", ["cognee_auto_ingest", "--once"])
    assert mod.main() != 0


def test_once_returns_zero_when_healthy_and_no_targets(mod, monkeypatch):
    """Health ready + empty target set -> clean rc 0 (no false failure)."""
    monkeypatch.setattr(mod, "cognee_health", lambda: {"status": "ready"})
    monkeypatch.setattr(mod, "targets", lambda: [])
    monkeypatch.setattr(sys, "argv", ["cognee_auto_ingest", "--once"])
    assert mod.main() == 0


def test_run_once_flags_skipped_unhealthy(mod, monkeypatch):
    """run_once surfaces the skipped_unhealthy sentinel main() keys off."""
    monkeypatch.setattr(mod, "cognee_health", lambda: {"status": "down"})
    stats = mod.run_once()
    assert stats.get("skipped_unhealthy") is True
    assert stats.get("ok") == 0
