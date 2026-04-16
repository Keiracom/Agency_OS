"""Tests for scripts/three_store_save.py — LAW XVII callsign discipline."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

# Load the script as a module (it's in scripts/, not src/)
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "three_store_save.py"
spec = importlib.util.spec_from_file_location("three_store_save", SCRIPT_PATH)
tss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tss)


def test_callsign_defaults_to_elliot(monkeypatch):
    """When CALLSIGN env var is unset, default is 'elliot'."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    assert tss.get_callsign() == "elliot"


def test_callsign_respects_aiden(monkeypatch):
    """When CALLSIGN=aiden, return aiden."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    assert tss.get_callsign() == "aiden"


def test_callsign_empty_string_fails_loud(monkeypatch):
    """LAW XVII: empty CALLSIGN refuses to save (raises SystemExit)."""
    monkeypatch.setenv("CALLSIGN", "")
    with pytest.raises(SystemExit, match="LAW XVII"):
        tss.get_callsign()


def test_manual_entry_tagged_with_callsign():
    """Manual entry includes [CALLSIGN] prefix."""
    entry = tss.manual_entry("D1.8", 329, "test summary", "elliot")
    assert "[ELLIOT]" in entry
    assert "D1.8" in entry
    assert "PR #329" in entry


def test_manual_entry_tagged_aiden():
    """Aiden entries tagged [AIDEN]."""
    entry = tss.manual_entry("D2.2", 999, "aiden run", "aiden")
    assert "[AIDEN]" in entry
