"""tests for scripts/anti_amnesia_capsule.py — Stream 4 Item #3 (capsule extension).

Mocks subprocess / HEARTBEAT.md / Supabase to test:
  - resolve_callsign env / IDENTITY.md / fallback
  - collect_heartbeat: missing / empty / multi-line strips + caps
  - collect_git: branch, dirty marker, commits
  - collect_recent_memories: no env vars / urllib error / ok path
  - compose_capsule: assembles sections, applies char cap, omits empty sections
  - write_capsule: writes to ~/.claude/capsules/<callsign>_capsule.md
  - read_capsule: missing capsule is a silent no-op; present capsule streams
  - main: --read mode vs default write mode, both return 0 (best-effort)
"""

from __future__ import annotations

import importlib.util
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "anti_amnesia_capsule.py"


@pytest.fixture(scope="module")
def capsule_mod():
    spec = importlib.util.spec_from_file_location("anti_amnesia_capsule", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["anti_amnesia_capsule"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect ~/.claude/capsules to a tmp path."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    return fake_home


# resolve_callsign ────────────────────────────────────────────────────────────


def test_resolve_callsign_from_env(capsule_mod, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "max")
    assert capsule_mod.resolve_callsign() == "max"


def test_resolve_callsign_lowercases(capsule_mod, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "MAX")
    assert capsule_mod.resolve_callsign() == "max"


def test_resolve_callsign_falls_back_to_unknown(capsule_mod, monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.chdir(tmp_path)
    assert capsule_mod.resolve_callsign() == "unknown"


def test_resolve_callsign_reads_identity_md(capsule_mod, monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CALLSIGN", raising=False)
    (tmp_path / "IDENTITY.md").write_text("# IDENTITY\n\n**CALLSIGN:** aiden\n")
    monkeypatch.chdir(tmp_path)
    assert capsule_mod.resolve_callsign() == "aiden"


# collect_heartbeat ──────────────────────────────────────────────────────────


def test_collect_heartbeat_missing(capsule_mod, monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    assert capsule_mod.collect_heartbeat() == []


def test_collect_heartbeat_strips_headers_and_blank(capsule_mod, monkeypatch, tmp_path) -> None:
    (tmp_path / "HEARTBEAT.md").write_text("# Title\n\nline1\n\nline2\n# H2\nline3\n")
    monkeypatch.chdir(tmp_path)
    out = capsule_mod.collect_heartbeat()
    assert out == ["HB: line1", "HB: line2", "HB: line3"]


def test_collect_heartbeat_caps_at_8_lines(capsule_mod, monkeypatch, tmp_path) -> None:
    body = "\n".join(f"line{i}" for i in range(20))
    (tmp_path / "HEARTBEAT.md").write_text(body)
    monkeypatch.chdir(tmp_path)
    assert len(capsule_mod.collect_heartbeat()) == 8


# collect_git ────────────────────────────────────────────────────────────────


def test_collect_git_branch_clean(capsule_mod, monkeypatch) -> None:
    outputs = iter(["main", "", "abc1234 feat: thing"])

    def fake_run(args, timeout=5):
        return next(outputs)

    monkeypatch.setattr(capsule_mod, "_run", fake_run)
    lines = capsule_mod.collect_git()
    assert lines[0] == "BRANCH: main"
    assert any("abc1234" in ln for ln in lines)


def test_collect_git_dirty_marker(capsule_mod, monkeypatch) -> None:
    outputs = iter(["mybranch", " M file.py", ""])
    monkeypatch.setattr(capsule_mod, "_run", lambda *a, **k: next(outputs))
    lines = capsule_mod.collect_git()
    assert "[DIRTY]" in lines[0]


# collect_recent_memories ────────────────────────────────────────────────────


def test_collect_recent_memories_no_env_returns_empty(capsule_mod, monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    assert capsule_mod.collect_recent_memories("max") == []


def test_collect_recent_memories_urllib_error_swallowed(capsule_mod, monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("nope")):
        assert capsule_mod.collect_recent_memories("max") == []


# compose_capsule ────────────────────────────────────────────────────────────


def test_compose_capsule_assembles_sections(capsule_mod, monkeypatch) -> None:
    monkeypatch.setattr(capsule_mod, "collect_heartbeat", lambda: ["HB: thing"])
    monkeypatch.setattr(capsule_mod, "collect_git", lambda: ["BRANCH: main"])
    monkeypatch.setattr(capsule_mod, "collect_recent_memories", lambda c: [])
    out = capsule_mod.compose_capsule("max")
    assert "Anti-Amnesia Capsule — max" in out
    assert "## LINEAR + BEADS" in out  # Outcome 4 — survives /compact
    assert "## HEARTBEAT" in out
    assert "## GIT" in out
    assert "## MEMORIES" not in out  # empty section omitted


def test_compose_capsule_linear_beads_reminders_present(capsule_mod) -> None:
    """Outcome 4 (Dave directive ts 1778568850): the two reminder lines
    survive /compact. They appear in the capsule output verbatim."""
    out = capsule_mod.compose_capsule("max")
    assert "Linear board: https://linear.app/keiracom" in out
    assert "Beads: run `bd ready`" in out


def test_compose_capsule_linear_beads_section_appears_first(capsule_mod, monkeypatch) -> None:
    """Reminders come first so they survive truncation under MAX_CAPSULE_CHARS."""
    long_hb = ["HB: " + "x" * 500 for _ in range(20)]
    monkeypatch.setattr(capsule_mod, "collect_heartbeat", lambda: long_hb)
    monkeypatch.setattr(capsule_mod, "collect_git", lambda: [])
    monkeypatch.setattr(capsule_mod, "collect_recent_memories", lambda c: [])
    out = capsule_mod.compose_capsule("max")
    assert out.index("## LINEAR + BEADS") < out.index("## HEARTBEAT")


def test_compose_capsule_applies_char_cap(capsule_mod, monkeypatch) -> None:
    long_hb = ["HB: " + "x" * 500 for _ in range(20)]
    monkeypatch.setattr(capsule_mod, "collect_heartbeat", lambda: long_hb)
    monkeypatch.setattr(capsule_mod, "collect_git", lambda: [])
    monkeypatch.setattr(capsule_mod, "collect_recent_memories", lambda c: [])
    out = capsule_mod.compose_capsule("max")
    assert len(out) <= capsule_mod.MAX_CAPSULE_CHARS
    assert out.endswith("[truncated]")
    # LINEAR + BEADS is first → must still be visible after truncation
    assert "## LINEAR + BEADS" in out
    assert "Linear board: https://linear.app/keiracom" in out


def test_collect_linear_beads_reminders_exact_content(capsule_mod) -> None:
    """Two reminder lines must be deterministic + verbatim."""
    lines = capsule_mod.collect_linear_beads_reminders()
    assert len(lines) == 2
    assert lines[0] == "Linear board: https://linear.app/keiracom — query at session start."
    assert lines[1] == "Beads: run `bd ready` before claiming any work."


# write_capsule + read_capsule + main ────────────────────────────────────────


def test_write_capsule_creates_file(capsule_mod, isolated_home, monkeypatch) -> None:
    monkeypatch.setattr(capsule_mod, "CAPSULE_DIR", isolated_home / ".claude" / "capsules")
    monkeypatch.setattr(capsule_mod, "collect_heartbeat", lambda: ["HB: x"])
    monkeypatch.setattr(capsule_mod, "collect_git", lambda: [])
    monkeypatch.setattr(capsule_mod, "collect_recent_memories", lambda c: [])
    capsule_mod.write_capsule("max")
    path = isolated_home / ".claude" / "capsules" / "max_capsule.md"
    assert path.exists()
    assert "HB: x" in path.read_text()


def test_read_capsule_missing_is_noop(capsule_mod, isolated_home, monkeypatch) -> None:
    monkeypatch.setattr(capsule_mod, "CAPSULE_DIR", isolated_home / ".claude" / "capsules")
    capsule_mod.read_capsule("ghost")  # silent no-op


def test_read_capsule_streams_to_stdout(capsule_mod, isolated_home, monkeypatch, capsys) -> None:
    cdir = isolated_home / ".claude" / "capsules"
    cdir.mkdir(parents=True)
    (cdir / "max_capsule.md").write_text("CAPSULE BODY 123")
    monkeypatch.setattr(capsule_mod, "CAPSULE_DIR", cdir)
    capsule_mod.read_capsule("max")
    captured = capsys.readouterr()
    assert "CAPSULE BODY 123" in captured.out
    assert "ANTI-AMNESIA CAPSULE" in captured.out


def test_main_write_mode_returns_zero(capsule_mod, isolated_home, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["anti_amnesia_capsule.py"])
    monkeypatch.setattr(capsule_mod, "CAPSULE_DIR", isolated_home / ".claude" / "capsules")
    monkeypatch.setenv("CALLSIGN", "max")
    monkeypatch.setattr(capsule_mod, "collect_heartbeat", lambda: [])
    monkeypatch.setattr(capsule_mod, "collect_git", lambda: ["BRANCH: x"])
    monkeypatch.setattr(capsule_mod, "collect_recent_memories", lambda c: [])
    assert capsule_mod.main() == 0


def test_main_read_mode_returns_zero(capsule_mod, isolated_home, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["anti_amnesia_capsule.py", "--read"])
    monkeypatch.setattr(capsule_mod, "CAPSULE_DIR", isolated_home / ".claude" / "capsules")
    monkeypatch.setenv("CALLSIGN", "max")
    assert capsule_mod.main() == 0
