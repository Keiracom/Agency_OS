"""Tests for scripts/orchestrator/install_systemd_units.sh — Agency_OS-34s.

Mocks systemd entirely via env overrides (AGENCY_OS_SYSTEMD_INSTALL_DIR points
to a tmp dir; AGENCY_OS_SYSTEMCTL_SKIP=1 short-circuits systemctl calls).
No real user systemd touched.

Covers:
  - new unit: source file present, host missing → install + (timer) enable
  - changed unit: source differs from host → re-install
  - removed-from-source: file gone from repo, still on host → LEFT ALONE
  - no-op: source == host → exit 0, no copies
  - dry-run mode: plan logged, no copies, no systemctl
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "install_systemd_units.sh"


def _make_source_dir(tmp_path: Path) -> Path:
    """Create an ephemeral repo-like source dir under tmp_path/src/alerts."""
    d = tmp_path / "src" / "alerts"
    d.mkdir(parents=True)
    return d


def _make_install_dir(tmp_path: Path) -> Path:
    d = tmp_path / "install" / "user"
    d.mkdir(parents=True)
    return d


def _run_installer(
    *,
    source_dirs: list[Path],
    install_dir: Path,
    args: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Resolve relative-to-repo expansion via AGENCY_OS_SYSTEMD_SOURCE_DIRS — but
    # since the installer joins against REPO_ROOT, we point it at an absolute
    # path by setting REPO_ROOT-equivalent indirectly: the script computes
    # REPO_ROOT from its own __file__ location. Easier: feed absolute source
    # dirs via env (the script's `$abs="$REPO_ROOT/$sd"` resolves against
    # REPO_ROOT, so we need relative paths). Use a symlink trick: create a
    # subdir under the real repo path? No — much simpler: invoke a copy of
    # the script from inside tmp_path so its computed REPO_ROOT lines up.
    env["AGENCY_OS_SYSTEMD_INSTALL_DIR"] = str(install_dir)
    env["AGENCY_OS_SYSTEMCTL_SKIP"] = "1"
    # Source dirs are passed as absolute paths joined to a REPO_ROOT that the
    # script computes relative to itself; we make REPO_ROOT == tmp by copying
    # the script under tmp/scripts/orchestrator/install_systemd_units.sh.
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT), *(args or [])],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _stage_script_in_tmp(tmp_path: Path) -> Path:
    """Copy the installer into tmp_path so its computed REPO_ROOT == tmp_path."""
    target = tmp_path / "scripts" / "orchestrator" / "install_systemd_units.sh"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(SCRIPT.read_bytes())
    target.chmod(0o755)
    return target


def _run_against_tmp_repo(
    tmp_path: Path,
    *,
    source_subdir: str = "infra/alerts",
    args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Stage the installer at tmp_path/scripts/orchestrator/ and run it. Source
    dirs default to tmp_path/<source_subdir>/; install dir to tmp_path/install/."""
    staged = _stage_script_in_tmp(tmp_path)
    install_dir = tmp_path / "install"
    install_dir.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["AGENCY_OS_SYSTEMD_SOURCE_DIRS"] = source_subdir
    env["AGENCY_OS_SYSTEMD_INSTALL_DIR"] = str(install_dir)
    env["AGENCY_OS_SYSTEMCTL_SKIP"] = "1"
    return subprocess.run(
        ["bash", str(staged), *(args or [])],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _write_unit(dir_: Path, name: str, content: str) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    p = dir_ / name
    p.write_text(content)
    return p


# ─── 1. New unit: install + enable timer ───────────────────────────────


def test_new_unit_installed_and_timer_enabled(tmp_path: Path):
    src_dir = tmp_path / "infra" / "alerts"
    _write_unit(src_dir, "agency-os-foo.service", "[Service]\nExecStart=/bin/true\n")
    _write_unit(src_dir, "agency-os-foo.timer", "[Timer]\nOnCalendar=hourly\n")

    result = _run_against_tmp_repo(tmp_path)

    assert result.returncode == 0, result.stderr
    # Files copied to install dir
    assert (tmp_path / "install" / "agency-os-foo.service").is_file()
    assert (tmp_path / "install" / "agency-os-foo.timer").is_file()
    # daemon-reload + enable invoked (via the skip-marker log line)
    assert "(skipped) systemctl --user daemon-reload" in result.stdout
    assert "(skipped) systemctl --user enable --now agency-os-foo.timer" in result.stdout
    # And it must NOT enable the .service directly (timer pulls it in)
    assert "enable --now agency-os-foo.service" not in result.stdout


# ─── 2. Changed unit: re-install + daemon-reload ───────────────────────


def test_changed_unit_reinstalled(tmp_path: Path):
    src_dir = tmp_path / "infra" / "alerts"
    src = _write_unit(src_dir, "agency-os-bar.timer", "[Timer]\nOnCalendar=hourly\n")

    # Stage a DIFFERENT version already on host
    install_dir = tmp_path / "install"
    install_dir.mkdir(parents=True, exist_ok=True)
    (install_dir / "agency-os-bar.timer").write_text("[Timer]\nOnCalendar=daily\n")

    result = _run_against_tmp_repo(tmp_path)
    assert result.returncode == 0, result.stderr

    # Host file now matches source
    assert (install_dir / "agency-os-bar.timer").read_text() == src.read_text()
    # daemon-reload invoked
    assert "(skipped) systemctl --user daemon-reload" in result.stdout
    # CHANGED diagnostic in plan
    assert "CHANGED agency-os-bar.timer" in result.stdout


# ─── 3. Removed-from-source: host file left alone ──────────────────────


def test_unit_only_on_host_is_left_alone(tmp_path: Path):
    # Source dir EMPTY (no units shipped from repo).
    (tmp_path / "infra" / "alerts").mkdir(parents=True)

    # Host has a legacy unit.
    install_dir = tmp_path / "install"
    install_dir.mkdir(parents=True, exist_ok=True)
    legacy = install_dir / "agency-os-legacy.timer"
    legacy.write_text("[Timer]\nOnCalendar=weekly\n")

    result = _run_against_tmp_repo(tmp_path)
    assert result.returncode == 0, result.stderr

    # Legacy file untouched
    assert legacy.is_file()
    assert legacy.read_text() == "[Timer]\nOnCalendar=weekly\n"
    # No copy happened
    assert "copied" not in result.stdout


# ─── 4. No-op: source matches host ─────────────────────────────────────


def test_noop_when_source_matches_host(tmp_path: Path):
    src_dir = tmp_path / "infra" / "alerts"
    content = "[Timer]\nOnCalendar=hourly\n"
    _write_unit(src_dir, "agency-os-baz.timer", content)
    install_dir = tmp_path / "install"
    install_dir.mkdir(parents=True, exist_ok=True)
    (install_dir / "agency-os-baz.timer").write_text(content)

    result = _run_against_tmp_repo(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "no-op" in result.stdout
    # No daemon-reload, no enable
    assert "daemon-reload" not in result.stdout
    assert "enable --now" not in result.stdout


# ─── 5. Dry-run: plans but does not copy or invoke systemctl ───────────


def test_dry_run_plans_but_does_not_apply(tmp_path: Path):
    src_dir = tmp_path / "infra" / "alerts"
    _write_unit(src_dir, "agency-os-dry.timer", "[Timer]\nOnCalendar=hourly\n")

    result = _run_against_tmp_repo(tmp_path, args=["--dry-run"])
    assert result.returncode == 0, result.stderr
    # Plan was logged
    assert "NEW     agency-os-dry.timer" in result.stdout
    # Nothing was copied (host install dir is empty)
    install_dir = tmp_path / "install"
    assert not (install_dir / "agency-os-dry.timer").exists()
    # No systemctl skip-marker emitted (because we never got past the dry-run gate)
    assert "(skipped) systemctl" not in result.stdout
    assert "--dry-run set" in result.stdout


# ─── 6. Bad arg → exit 2 ────────────────────────────────────────────────


def test_bad_arg_exits_2(tmp_path: Path):
    staged = _stage_script_in_tmp(tmp_path)
    env = os.environ.copy()
    env["AGENCY_OS_SYSTEMCTL_SKIP"] = "1"
    env["AGENCY_OS_SYSTEMD_INSTALL_DIR"] = str(tmp_path / "install")
    result = subprocess.run(
        ["bash", str(staged), "--gibberish"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "unknown arg" in result.stderr


# ─── 7. Empty source set → clean exit 0 ────────────────────────────────


def test_no_source_dirs_clean_exit(tmp_path: Path):
    # No source subdir created → script reports "no source unit files found"
    result = _run_against_tmp_repo(tmp_path)
    assert result.returncode == 0
    assert "no source unit files found" in result.stdout


# ─── 8. Idempotency: second run after install is a no-op ───────────────


def test_idempotent_second_run_is_noop(tmp_path: Path):
    src_dir = tmp_path / "infra" / "alerts"
    _write_unit(src_dir, "agency-os-idem.timer", "[Timer]\nOnCalendar=hourly\n")

    r1 = _run_against_tmp_repo(tmp_path)
    assert r1.returncode == 0
    assert "copied agency-os-idem.timer" in r1.stdout

    r2 = _run_against_tmp_repo(tmp_path)
    assert r2.returncode == 0
    assert "no-op" in r2.stdout
    assert "copied" not in r2.stdout
