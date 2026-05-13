"""Tests for scripts/check_migration_completeness.py — Wave 1 Item 4.

Verifies the three exit-code contracts via subprocess (the script is a CLI
shipped to CI; testing through the CLI boundary catches argparse + path
plumbing in addition to the grep core).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_migration_completeness.py"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
        check=False,
    )


def test_pass_when_no_residual_readers(tmp_path):
    """Exit 0: ghost target string in a tiny scratch tree → no hits."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("print('hello world')\n")
    result = _run(
        "--removed-target",
        "ghost_table_xyz_42",
        "--check-paths",
        str(src),
    )
    assert result.returncode == 0, (
        f"expected 0, got {result.returncode}: {result.stdout}{result.stderr}"
    )
    assert "PASS" in result.stdout
    assert "no residual readers found" in result.stdout


def test_fail_when_residual_readers_found(tmp_path):
    """Exit 1: target appears in scratch source → script lists hits + Pattern A guidance."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "reader.py").write_text("from db import query\nquery('SELECT * FROM stale_table')\n")
    (src / "another.py").write_text("# stale_table referenced here too\n")

    result = _run(
        "--removed-target",
        "stale_table",
        "--check-paths",
        str(src),
    )
    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "stale_table" in result.stdout
    assert "Pattern A" in result.stdout
    # both reader files should show up
    assert "reader.py" in result.stdout
    assert "another.py" in result.stdout


def test_error_on_empty_target(tmp_path):
    """Exit 2: empty --removed-target is an invocation error."""
    result = _run("--removed-target", "", "--check-paths", str(tmp_path))
    assert result.returncode == 2
    assert "cannot be empty" in result.stderr


def test_missing_arg_returns_argparse_error():
    """argparse exits 2 when --removed-target is absent (Python convention)."""
    result = _run()
    assert result.returncode == 2
    assert "--removed-target" in result.stderr


def test_pass_when_check_path_absent(tmp_path):
    """Exit 0: if all --check-paths are missing on disk, no hits possible → pass."""
    nonexistent = tmp_path / "does-not-exist"
    result = _run(
        "--removed-target",
        "anything",
        "--check-paths",
        str(nonexistent),
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_multi_path_grep_finds_in_any(tmp_path):
    """Hits in ANY of the comma-separated --check-paths trigger FAIL."""
    src = tmp_path / "src"
    scripts = tmp_path / "scripts"
    src.mkdir()
    scripts.mkdir()
    (src / "clean.py").write_text("# nothing here\n")
    (scripts / "dirty.py").write_text("# uses removed_table heavily\n")

    result = _run(
        "--removed-target",
        "removed_table",
        "--check-paths",
        f"{src},{scripts}",
    )
    assert result.returncode == 1
    assert "dirty.py" in result.stdout


def test_excludes_pycache_dirs(tmp_path):
    """--exclude-dir __pycache__ keeps compiled bytecode comments out of hits."""
    src = tmp_path / "src"
    pycache = src / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "stale.pyc").write_text("references stale_target\n")
    (src / "good.py").write_text("# nothing\n")

    result = _run(
        "--removed-target",
        "stale_target",
        "--check-paths",
        str(src),
    )
    assert result.returncode == 0
    assert "stale_target" not in result.stdout or "PASS" in result.stdout


def test_fixed_string_handles_dots_and_slashes(tmp_path):
    """Default --fixed-strings mode lets target contain dots / slashes
    (e.g. 'elliot_internal.memories', '/var/lib/.session_') without regex escaping.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "consumer.py").write_text(
        "PATH = '/var/lib/.session_aiden'\nprint(elliot_internal.memories)\n"
    )

    r1 = _run("--removed-target", "elliot_internal.memories", "--check-paths", str(src))
    assert r1.returncode == 1
    assert "consumer.py" in r1.stdout

    r2 = _run("--removed-target", "/var/lib/.session_", "--check-paths", str(src))
    assert r2.returncode == 1
    assert "consumer.py" in r2.stdout


def test_sql_reserved_keyword_skips_gracefully():
    """KEI-47: when the upstream CI extractor captures a SQL reserved keyword
    (FROM/WHERE/SET/etc) as the supposed table — because prose like
    `[UPDATE FROM {callsign}]` slipped through the awk $NF regex — the
    Python checker recognises it and exits 0 (SKIP) instead of grep-ing
    100s of unrelated SQL queries and failing.
    """
    for keyword in ("FROM", "WHERE", "SET", "from", "Where"):  # case-insensitive
        result = _run("--removed-target", keyword)
        assert result.returncode == 0, (
            f"keyword {keyword!r} should SKIP not FAIL — stdout={result.stdout}"
        )
        assert "SKIP" in result.stdout
        assert "KEI-47" in result.stdout


def test_sql_reserved_set_completeness():
    """KEI-47: sanity-check that the SQL_RESERVED_WORDS frozenset includes the
    actual keyword that triggered the false-positive in PR #843 (FROM)
    plus the common ones a real schema-coupled diff might trip on."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_migration_completeness_kei47", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    must_include = {"FROM", "WHERE", "SET", "JOIN", "INTO", "VALUES", "WITH"}
    assert must_include <= mod.SQL_RESERVED_WORDS, (
        f"missing keywords: {must_include - mod.SQL_RESERVED_WORDS}"
    )
