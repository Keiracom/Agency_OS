"""Tests for KEI-22 D6 — Layer 3 mechanical gates.

bd_check_claim.sh         — wrapper providing `bd check-claim --branch` semantics
.githooks/pre-commit       — repo-shipped hook
install_pre_commit_hook.sh — operator-run installer (sets core.hooksPath)

Tests shell out to bash with a fake bd binary on PATH so we don't depend on
real Beads. The fake bd is a small script that emits canned JSON.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECK_CLAIM = REPO_ROOT / "scripts" / "orchestrator" / "bd_check_claim.sh"
PRECOMMIT = REPO_ROOT / ".githooks" / "pre-commit"
INSTALLER = REPO_ROOT / "scripts" / "orchestrator" / "install_pre_commit_hook.sh"


def _fake_bd(tmp_path: Path, list_json: str) -> Path:
    """Write a fake `bd` binary that prints `list_json` on `bd list --json`.
    Stores the JSON in a sibling file so we avoid heredoc-indent hazards."""
    bdir = tmp_path / "bin"
    bdir.mkdir()
    json_path = bdir / "list.json"
    json_path.write_text(list_json)
    fake = bdir / "bd"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$1" == "list" && "$2" == "--json" ]]; then\n'
        f"    cat {json_path}\n"
        "    exit 0\n"
        "fi\n"
        'echo "fake bd: unknown args $*" >&2\n'
        "exit 1\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return bdir


def _env_with_fake_bd(fake_bin_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
    # Clear CALLSIGN so tests deterministically use --branch parsing.
    env.pop("CALLSIGN", None)
    return env


# ─── bd_check_claim.sh ─────────────────────────────────────────────────


def test_check_claim_files_exist():
    assert CHECK_CLAIM.is_file()
    assert PRECOMMIT.is_file()
    assert INSTALLER.is_file()
    # Executable bits set
    assert os.access(CHECK_CLAIM, os.X_OK)
    assert os.access(PRECOMMIT, os.X_OK)
    assert os.access(INSTALLER, os.X_OK)


def test_check_claim_succeeds_on_valid_claim(tmp_path: Path):
    bd_dir = _fake_bd(
        tmp_path,
        '[{"id":"Agency_OS-khf3an","status":"in_progress","assignee":"orion",'
        '"external":"https://linear.app/keiracom/issue/KEI-22/x"}]',
    )
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "orion/kei22-d6"],
        capture_output=True,
        text=True,
        env=_env_with_fake_bd(bd_dir),
        timeout=15,
    )
    assert r.returncode == 0, r.stderr
    assert "Agency_OS-khf3an" in r.stdout


def test_check_claim_fails_on_no_claim(tmp_path: Path):
    bd_dir = _fake_bd(tmp_path, "[]")
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "orion/kei22-d6"],
        capture_output=True,
        text=True,
        env=_env_with_fake_bd(bd_dir),
        timeout=15,
    )
    assert r.returncode == 1
    assert "no_valid_claim" in r.stderr


def test_check_claim_blocks_peer_assigned_work(tmp_path: Path):
    """Atlas's claim does NOT let orion commit on an orion/* branch."""
    bd_dir = _fake_bd(
        tmp_path,
        '[{"id":"Agency_OS-atlas","status":"in_progress","assignee":"atlas",'
        '"external":"https://linear.app/keiracom/issue/KEI-99/x"}]',
    )
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "orion/kei22-d6"],
        capture_output=True,
        text=True,
        env=_env_with_fake_bd(bd_dir),
        timeout=15,
    )
    assert r.returncode == 1


def test_check_claim_blocks_non_in_progress_claim(tmp_path: Path):
    bd_dir = _fake_bd(
        tmp_path,
        '[{"id":"Agency_OS-x","status":"open","assignee":"orion",'
        '"external":"https://linear.app/keiracom/issue/KEI-99/x"}]',
    )
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "orion/kei22-d6"],
        capture_output=True,
        text=True,
        env=_env_with_fake_bd(bd_dir),
        timeout=15,
    )
    assert r.returncode == 1


def test_check_claim_blocks_non_linear_external_ref(tmp_path: Path):
    bd_dir = _fake_bd(
        tmp_path,
        '[{"id":"Agency_OS-x","status":"in_progress","assignee":"orion",'
        '"external":"https://github.com/Keiracom/x/issues/1"}]',
    )
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "orion/kei22-d6"],
        capture_output=True,
        text=True,
        env=_env_with_fake_bd(bd_dir),
        timeout=15,
    )
    assert r.returncode == 1


def test_check_claim_exits_2_when_bd_missing(tmp_path: Path):
    """Pattern A: bd binary missing → exit 2 (NOT 0 or 1). Pre-commit caller
    decides whether to fail-open or fail-closed via AGENCY_OS_BD_HARDFAIL."""
    # Keep system PATH for bash + coreutils; just remove anywhere bd lives.
    sys_path = "/usr/bin:/bin"
    env = os.environ.copy()
    env["PATH"] = sys_path
    env.pop("CALLSIGN", None)
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "orion/foo"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 2, r.stderr


def test_check_claim_callsign_env_overrides_branch_parse(tmp_path: Path):
    """CALLSIGN env wins over branch-prefix parse — useful for non-standard
    branch names."""
    bd_dir = _fake_bd(
        tmp_path,
        '[{"id":"Agency_OS-mine","status":"in_progress","assignee":"orion",'
        '"external":"https://linear.app/keiracom/issue/KEI-22/x"}]',
    )
    env = _env_with_fake_bd(bd_dir)
    env["CALLSIGN"] = "orion"
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "weird-name-no-prefix"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 0


def test_check_claim_no_callsign_resolvable_fails(tmp_path: Path):
    bd_dir = _fake_bd(tmp_path, "[]")
    env = _env_with_fake_bd(bd_dir)
    env.pop("CALLSIGN", None)
    r = subprocess.run(
        ["bash", str(CHECK_CLAIM), "--branch", "weird-name-no-prefix"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 1


# ─── pre-commit hook ───────────────────────────────────────────────────


def _git_init_repo(tmp_path: Path, hook_dir: Path) -> Path:
    """Init a tmp git repo with worktree + point core.hooksPath at hook_dir.
    Returns the repo path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "test-main"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath", str(hook_dir)],
        check=True,
    )
    # Seed initial commit so HEAD exists.
    (repo / "seed").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "seed"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--no-verify", "-m", "seed"],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-05-13T00:00:00",
            "GIT_COMMITTER_DATE": "2026-05-13T00:00:00",
        },
    )
    return repo


def _hooks_dir(tmp_path: Path, bd_check_claim_path: Path) -> Path:
    """Stage .githooks/pre-commit + a wrapping setup that points the hook
    at our local copies of bd_check_claim.sh."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    pre = hooks / "pre-commit"
    # Copy the real hook + override REPO_ROOT lookup so it finds OUR bd_check_claim copy.
    body = PRECOMMIT.read_text()
    # Hack: the hook resolves CHECK via REPO_ROOT/scripts/orchestrator/bd_check_claim.sh.
    # We can't override REPO_ROOT cleanly — instead we copy the real wrapper to a
    # matching path under the tmp repo.
    pre.write_text(body)
    pre.chmod(pre.stat().st_mode | stat.S_IEXEC)
    return hooks


def test_pre_commit_blocks_on_no_claim(tmp_path: Path):
    """End-to-end: tmp repo with hook installed + fake bd returning empty
    list → git commit fails with the KEI-22 D6 message."""
    hooks = _hooks_dir(tmp_path, CHECK_CLAIM)
    repo = _git_init_repo(tmp_path, hooks)
    # Stage real bd_check_claim alongside the hook (the hook's REPO_ROOT
    # lookup uses `git rev-parse --show-toplevel`).
    (repo / "scripts" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").write_text(CHECK_CLAIM.read_text())
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").chmod(0o755)

    # Fake bd returns empty.
    bd_dir = _fake_bd(tmp_path, "[]")
    env = _env_with_fake_bd(bd_dir)

    # Create branch + try to commit.
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "orion/kei22-d6"], check=True)
    (repo / "file.txt").write_text("change")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    r = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "feat: x"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode != 0, "pre-commit must block when no claim"
    assert "KEI-22 D6 Layer 3 mechanical gate" in r.stderr


def test_pre_commit_allows_on_valid_claim(tmp_path: Path):
    hooks = _hooks_dir(tmp_path, CHECK_CLAIM)
    repo = _git_init_repo(tmp_path, hooks)
    (repo / "scripts" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").write_text(CHECK_CLAIM.read_text())
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").chmod(0o755)

    bd_dir = _fake_bd(
        tmp_path,
        '[{"id":"Agency_OS-khf3an","status":"in_progress","assignee":"orion",'
        '"external":"https://linear.app/keiracom/issue/KEI-22/x"}]',
    )
    env = _env_with_fake_bd(bd_dir)

    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "orion/kei22-d6"], check=True)
    (repo / "file.txt").write_text("change")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    r = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "feat: x"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 0, r.stderr


def test_pre_commit_no_verify_bypass(tmp_path: Path):
    """git commit --no-verify is the operator-authorised escape hatch."""
    hooks = _hooks_dir(tmp_path, CHECK_CLAIM)
    repo = _git_init_repo(tmp_path, hooks)
    (repo / "scripts" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").write_text(CHECK_CLAIM.read_text())
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").chmod(0o755)

    bd_dir = _fake_bd(tmp_path, "[]")  # no claim
    env = _env_with_fake_bd(bd_dir)

    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "orion/kei22-d6"], check=True)
    (repo / "file.txt").write_text("change")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    r = subprocess.run(
        ["git", "-C", str(repo), "commit", "--no-verify", "-m", "feat: emergency"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 0, r.stderr


def test_pre_commit_exempts_main_branch(tmp_path: Path):
    hooks = _hooks_dir(tmp_path, CHECK_CLAIM)
    repo = _git_init_repo(tmp_path, hooks)
    (repo / "scripts" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").write_text(CHECK_CLAIM.read_text())
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").chmod(0o755)

    bd_dir = _fake_bd(tmp_path, "[]")
    env = _env_with_fake_bd(bd_dir)

    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "main"], check=True)
    (repo / "file.txt").write_text("change")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    r = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "main: x"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 0, r.stderr


def test_pre_commit_soft_allows_when_bd_missing(tmp_path: Path):
    """bd binary missing → soft-allow unless AGENCY_OS_BD_HARDFAIL=1."""
    hooks = _hooks_dir(tmp_path, CHECK_CLAIM)
    repo = _git_init_repo(tmp_path, hooks)
    (repo / "scripts" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").write_text(CHECK_CLAIM.read_text())
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"  # system PATH minus bd
    env.pop("CALLSIGN", None)

    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "orion/kei22-d6"], check=True)
    (repo / "file.txt").write_text("change")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    r = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "feat: x"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode == 0, r.stderr


def test_pre_commit_hardfail_refuses_when_bd_missing(tmp_path: Path):
    hooks = _hooks_dir(tmp_path, CHECK_CLAIM)
    repo = _git_init_repo(tmp_path, hooks)
    (repo / "scripts" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").write_text(CHECK_CLAIM.read_text())
    (repo / "scripts" / "orchestrator" / "bd_check_claim.sh").chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"  # system PATH minus bd
    env["AGENCY_OS_BD_HARDFAIL"] = "1"
    env.pop("CALLSIGN", None)

    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "orion/kei22-d6"], check=True)
    (repo / "file.txt").write_text("change")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    r = subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "feat: x"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert r.returncode != 0
    assert "HARDFAIL=1" in r.stderr
