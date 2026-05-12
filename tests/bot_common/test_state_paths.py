"""tests for src/bot_common/state_paths.py — XDG_STATE_HOME state-dir helper.

Covers:
  - _xdg_state_home: default fallback / env override / relative-path fallback
  - resolve_state_dir: happy path / env-override / dir auto-create / 0o700
  - callsign validation: empty / traversal / special chars / leading digit
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from src.bot_common import state_paths as sp

# _xdg_state_home ────────────────────────────────────────────────────────────


def test_xdg_state_home_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert sp._xdg_state_home() == tmp_path / ".local" / "state"


def test_xdg_state_home_env_override(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "custom"))
    assert sp._xdg_state_home() == tmp_path / "custom"


def test_xdg_state_home_relative_env_falls_back(monkeypatch, tmp_path) -> None:
    """Spec says XDG_STATE_HOME must be absolute — relative values are ignored."""
    monkeypatch.setenv("XDG_STATE_HOME", "relative/path")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert sp._xdg_state_home() == tmp_path / ".local" / "state"


def test_xdg_state_home_empty_env_falls_back(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", "   ")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert sp._xdg_state_home() == tmp_path / ".local" / "state"


# resolve_state_dir ──────────────────────────────────────────────────────────


def test_resolve_state_dir_creates_under_xdg(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    p = sp.resolve_state_dir("max")
    assert p == tmp_path / "agency-os" / "max"
    assert p.is_dir()


def test_resolve_state_dir_default_under_home(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    p = sp.resolve_state_dir("aiden")
    assert p == tmp_path / ".local" / "state" / "agency-os" / "aiden"
    assert p.is_dir()


def test_resolve_state_dir_idempotent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    p1 = sp.resolve_state_dir("orion")
    p2 = sp.resolve_state_dir("orion")
    assert p1 == p2
    assert p1.is_dir()


def test_resolve_state_dir_sets_owner_only_permissions(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    p = sp.resolve_state_dir("atlas")
    mode = stat.S_IMODE(p.stat().st_mode)
    # owner rwx (group + other should be unset; some systems mask differently
    # so we assert group/world are no broader than empty)
    assert mode & 0o700 == 0o700
    assert mode & 0o077 == 0


def test_resolve_state_dir_callsigns_are_isolated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    a = sp.resolve_state_dir("elliot")
    b = sp.resolve_state_dir("max")
    assert a != b
    assert a.parent == b.parent  # both under agency-os/


# Callsign validation ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "../etc",
        "max/sub",
        "max\\sub",
        "max.path",
        "max ",
        " max",
        "1max",  # must start with letter
        "max ../escape",
        ".hidden",
    ],
)
def test_resolve_state_dir_rejects_bad_callsign(bad, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="invalid callsign"):
        sp.resolve_state_dir(bad)


@pytest.mark.parametrize("good", ["max", "aiden", "orion-demo", "max_v2", "M1xeD"])
def test_resolve_state_dir_accepts_valid_callsigns(good, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    p = sp.resolve_state_dir(good)
    assert p.name == good
    assert p.is_dir()
