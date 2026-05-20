"""KEI-143 — tests for scripts/git/check_callsign_match.sh.

Runs the hook script via subprocess against fixture IDENTITY.md files under
tmp_path, asserting exit code + stderr per the documented behavior matrix.

Tests use git worktree isolation via env GIT_TOPLEVEL_OVERRIDE NO — instead
they invoke the script with cwd=tmp_path and the script's `git rev-parse
--show-toplevel` returns tmp_path because we `git init` it.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "git" / "check_callsign_match.sh"


def _init_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo at tmp_path so the script's `git rev-parse
    --show-toplevel` succeeds and resolves to tmp_path."""
    subprocess.run(
        ["git", "init", "--initial-branch=main", "-q", str(tmp_path)],
        check=True,
    )
    return tmp_path


def _write_identity(repo: Path, callsign: str | None) -> None:
    """Write IDENTITY.md with a CALLSIGN line, OR omit the file if None."""
    if callsign is None:
        return
    (repo / "IDENTITY.md").write_text(
        f"# IDENTITY\n\n**CALLSIGN:** {callsign}\n**Workspace:** {repo}\n"
    )


def _run_hook(repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Invoke the hook with cwd=repo + the given env. Returns the
    CompletedProcess for assertions."""
    base_env = {k: v for k, v in os.environ.items() if k != "CALLSIGN"}
    base_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(repo),
        env=base_env,
        capture_output=True,
        text=True,
    )


# ─── positive paths ───────────────────────────────────────────────────────


def test_pass_when_callsign_env_unset(tmp_path):
    """Humans without the env var must NOT be blocked — exit 0."""
    repo = _init_repo(tmp_path)
    _write_identity(repo, "atlas")
    result = _run_hook(repo, env={})  # no CALLSIGN
    assert result.returncode == 0, result.stderr


def test_pass_on_exact_match(tmp_path):
    repo = _init_repo(tmp_path)
    _write_identity(repo, "atlas")
    result = _run_hook(repo, env={"CALLSIGN": "atlas"})
    assert result.returncode == 0, result.stderr


def test_pass_on_case_insensitive_match(tmp_path):
    """CALLSIGN=ATLAS env vs IDENTITY.md 'atlas' — match (case folded)."""
    repo = _init_repo(tmp_path)
    _write_identity(repo, "atlas")
    result = _run_hook(repo, env={"CALLSIGN": "ATLAS"})
    assert result.returncode == 0, result.stderr


def test_pass_on_whitespace_tolerance(tmp_path):
    """Trailing whitespace in IDENTITY.md line + env — both stripped."""
    repo = _init_repo(tmp_path)
    (repo / "IDENTITY.md").write_text("**CALLSIGN:** atlas   \n")
    result = _run_hook(repo, env={"CALLSIGN": "  atlas  "})
    assert result.returncode == 0, result.stderr


# ─── negative paths (the actual point of the hook) ────────────────────────


def test_fail_on_mismatch(tmp_path):
    """CALLSIGN env says elliot, IDENTITY.md says atlas → blocked."""
    repo = _init_repo(tmp_path)
    _write_identity(repo, "atlas")
    result = _run_hook(repo, env={"CALLSIGN": "elliot"})
    assert result.returncode == 1
    assert "mismatch" in result.stderr
    assert "CALLSIGN env: elliot" in result.stderr
    assert "IDENTITY.md:  atlas" in result.stderr


def test_fail_when_identity_missing(tmp_path):
    """CALLSIGN env set, IDENTITY.md absent → governance violation, block."""
    repo = _init_repo(tmp_path)
    # NO IDENTITY.md written
    result = _run_hook(repo, env={"CALLSIGN": "atlas"})
    assert result.returncode == 1
    assert "IDENTITY.md is missing" in result.stderr


def test_fail_when_identity_has_no_callsign_line(tmp_path):
    """IDENTITY.md exists but lacks the CALLSIGN line — block with the
    expected-format hint so the operator can fix the file."""
    repo = _init_repo(tmp_path)
    (repo / "IDENTITY.md").write_text("# IDENTITY\n\nSomething else here.\n")
    result = _run_hook(repo, env={"CALLSIGN": "atlas"})
    assert result.returncode == 1
    assert "no '**CALLSIGN:** <name>' line found" in result.stderr


def test_fail_message_includes_both_callsigns(tmp_path):
    """The mismatch error must show BOTH the env value AND the file value
    so the operator immediately sees which worktree they're in vs which
    callsign they should switch to."""
    repo = _init_repo(tmp_path)
    _write_identity(repo, "orion")
    result = _run_hook(repo, env={"CALLSIGN": "scout"})
    assert result.returncode == 1
    assert "scout" in result.stderr.lower()
    assert "orion" in result.stderr.lower()
