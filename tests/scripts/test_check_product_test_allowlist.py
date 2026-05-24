"""Tests for scripts/ci/check_product_test_allowlist.py — Phase 1.2.5 enforcer.

Negative-path discipline (Max HOLD on PR #1118 — per
feedback_negative_path_test_before_approve, gate/validator/enforcer PRs
require negative-path tests on synthetic offenders before approve).

7 test cases per Max's spec:
  (1) test_unmatched_file_returns_exit_1 — synthetic offender → exit 1 + stderr 'rejected'
  (2) test_all_matched_returns_exit_0 — synthetic happy-path → exit 0
  (3) test_double_star_in_allowlist_returns_exit_2 — `**/x.py` → exit 2 + stderr `**`
  (4) test_missing_allowlist_returns_exit_2 — --allowlist /nonexistent → exit 2
  (5) test_report_mode_never_enforces — synthetic offender + --report → exit 0
  (6) test_empty_tests_dir_returns_exit_0 — no .py files → exit 0
  (7) test_pycache_and_init_skipped — __pycache__/__init__ files don't count

All fixtures use tmp_path so no real-repo state touched.

Pattern: subprocess invocation of the script — tests it as it'll actually
run in CI (Python interpreter + argv + stderr inspection), not as an
imported function. Catches argv/parsing/exit-code issues a unit test wouldn't.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_product_test_allowlist.py"


def _run(allowlist: Path, tests_root: Path, *extra: str) -> subprocess.CompletedProcess:
    """Invoke the enforcer with explicit --allowlist + --tests-root."""
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--allowlist",
            str(allowlist),
            "--tests-root",
            str(tests_root),
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def _make_test_file(root: Path, rel: str) -> Path:
    """Create an empty test file at root/rel (parents created)."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# synthetic test\n")
    return path


def test_unmatched_file_returns_exit_1(tmp_path: Path):
    """(1) — synthetic tree with 1 file NOT in allowlist → exit 1 + 'rejected' on stderr."""
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("# allowlist with a single matching path\ntests/keep.py\n")
    tests_root = tmp_path / "tests"
    _make_test_file(tests_root, "keep.py")
    _make_test_file(tests_root, "stray.py")  # synthetic offender — not in allowlist
    result = _run(allowlist, tests_root)
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}: {result.stderr}"
    assert "rejected" in result.stderr
    assert "stray.py" in result.stderr


def test_all_matched_returns_exit_0(tmp_path: Path):
    """(2) — synthetic tree where every file matches → exit 0."""
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("tests/a.py\ntests/sub/b.py\n")
    tests_root = tmp_path / "tests"
    _make_test_file(tests_root, "a.py")
    _make_test_file(tests_root, "sub/b.py")
    result = _run(allowlist, tests_root)
    assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stderr}"
    assert "OK: every tests/** file is in the product allowlist" in result.stderr


def test_double_star_in_allowlist_returns_exit_2(tmp_path: Path):
    """(3) — `**` recursive glob disallowed; exit 2 + stderr mentions `**`."""
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("tests/**/something.py\n")
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    result = _run(allowlist, tests_root)
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}: {result.stderr}"
    assert "**" in result.stderr
    assert "disallowed" in result.stderr


def test_missing_allowlist_returns_exit_2(tmp_path: Path):
    """(4) — non-existent allowlist path → exit 2 + 'allowlist not found' on stderr."""
    allowlist = tmp_path / "does_not_exist.txt"
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    result = _run(allowlist, tests_root)
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}: {result.stderr}"
    assert "allowlist not found" in result.stderr


def test_report_mode_never_enforces(tmp_path: Path):
    """(5) — synthetic offender + --report → exit 0 (diagnostic, not enforcement)."""
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("tests/keep.py\n")
    tests_root = tmp_path / "tests"
    _make_test_file(tests_root, "keep.py")
    _make_test_file(tests_root, "would_reject.py")
    result = _run(allowlist, tests_root, "--report")
    assert result.returncode == 0, (
        f"--report should never enforce; expected exit 0, got {result.returncode}: {result.stderr}"
    )
    # Diagnostic body still surfaces the rejected file even though exit 0.
    assert "would_reject.py" in result.stderr


def test_empty_tests_dir_returns_exit_0(tmp_path: Path):
    """(6) — tests root exists but contains no .py files → exit 0 (nothing to enforce)."""
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("tests/anything.py\n")
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    result = _run(allowlist, tests_root)
    assert result.returncode == 0, (
        f"expected exit 0 on empty tree, got {result.returncode}: {result.stderr}"
    )


def test_pycache_and_init_skipped(tmp_path: Path):
    """(7) — __pycache__/*.py and __init__.py don't trigger enforcement.

    Walks must skip both per walk_tests() logic. If a __pycache__ artefact
    or __init__.py somehow ended up in the allowlist requirement it'd be a
    silent gotcha during CI; this test pins the behaviour.
    """
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("tests/real.py\n")
    tests_root = tmp_path / "tests"
    _make_test_file(tests_root, "real.py")
    _make_test_file(tests_root, "__init__.py")  # should be skipped
    _make_test_file(tests_root, "sub/__init__.py")  # should be skipped
    _make_test_file(tests_root, "__pycache__/x.cpython-312.py")  # should be skipped
    _make_test_file(tests_root, "sub/__pycache__/y.cpython-312.py")  # should be skipped
    result = _run(allowlist, tests_root)
    assert result.returncode == 0, (
        f"__init__/__pycache__ should be skipped; expected exit 0, got "
        f"{result.returncode}: {result.stderr}"
    )
