"""Tests for scripts/session_uuid_resume.py — KEI-31 component 4."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "session_uuid_resume.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("session_uuid_resume", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["session_uuid_resume"] = m
    spec.loader.exec_module(m)
    return m


def test_render_resume_no_prior(mod):
    out = mod.render_resume("aiden", None)
    assert "Session UUID resume" in out
    assert "No prior session row found for callsign **aiden**" in out


def test_render_resume_with_prior(mod):
    prior = {
        "session_uuid": "abc-123-uuid",
        "started_at": "2026-05-12T22:00:00Z",
        "status": "closed",
    }
    out = mod.render_resume("aiden", prior)
    assert "abc-123-uuid" in out
    assert "2026-05-12T22:00:00Z" in out
    assert "closed" in out


def test_callsign_from_env(mod, monkeypatch):
    monkeypatch.setenv("CALLSIGN", "scout")
    assert mod._callsign() == "scout"


def test_callsign_unknown_when_no_env_no_identity(mod, monkeypatch, tmp_path, chdir):
    """When CALLSIGN env unset AND no IDENTITY.md present, return 'unknown'."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    chdir(tmp_path)
    assert mod._callsign() == "unknown"


def test_fetch_recent_session_no_env_returns_none(mod, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    assert mod.fetch_recent_session("aiden") is None


def test_main_returns_zero(mod, monkeypatch):
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setattr(mod, "fetch_recent_session", lambda cs: None)
    assert mod.main() == 0


@pytest.fixture
def chdir(monkeypatch):
    def _cd(path):
        monkeypatch.chdir(path)
    return _cd
