"""Tests for scripts/ci/check_atom_granularity.py — the atom-granularity CI gate.

Wave 1 CUTOVER GATE (Agency_OS-3g9t, Dave + Aiden + Viktor ratify 2026-05-27).

The validator MODULE (`src/keiracom_system/memory/atom_granularity.py`) is
unit-tested in `tests/keiracom_system/memory/test_atom_granularity.py`. THIS
file tests the gate SCRIPT end-to-end — file discovery, JSON/JSONL loading,
the three exit codes (0 pass / 1 violation / 2 config error), --report, and
the env-var path override — via subprocess, exactly as CI invokes it. Mirrors
the sibling pattern in `test_check_migration_manifest.py` (negative-path
discipline: every rule gets a synthetic offender asserting the exact code).

Dispatch deliverable #3 named `tests/ci/test_atom_granularity_check.py`; this
lives at the established CI-script test home `tests/scripts/ci/` next to
`test_check_migration_manifest.py` (the gate this one mirrors) rather than
spawning an orphan `tests/ci/` directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "scripts/ci/check_atom_granularity.py"

# Synthetic fixtures.
GOOD_ATOM = {"id": "good-1", "content": "X" * 120, "source_ref": "pr:1228"}
BAD_ATOM = {"id": "bad-1", "content": "short", "source_ref": "pr:1228"}  # R1.min
EXEMPT_ATOM = {"id": "ex-1", "content": "tiny", "granularity_exempt": True}


def _run(*paths: str, report: bool = False, env: dict | None = None) -> tuple[int, str, str]:
    args = [sys.executable, str(SCRIPT)]
    if paths:
        args += ["--paths", ",".join(paths)]
    if report:
        args.append("--report")
    cp = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False, env=env)
    return cp.returncode, cp.stdout, cp.stderr


def _write(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


# ── exit codes ───────────────────────────────────────────────────────────────


def test_no_fixtures_is_noop_exit_0(tmp_path):
    rc, out, _ = _run(str(tmp_path / "*.json"))
    assert rc == 0, out
    assert "gate inactive" in out


def test_all_atoms_pass_exit_0(tmp_path):
    f = _write(tmp_path / "atoms.json", [GOOD_ATOM, GOOD_ATOM])
    rc, out, _ = _run(str(f))
    assert rc == 0, out


def test_single_violation_exit_1(tmp_path):
    f = _write(tmp_path / "atoms.json", [GOOD_ATOM, BAD_ATOM])
    rc, out, _ = _run(str(f))
    assert rc == 1
    assert "R1.min" in out


def test_malformed_json_exit_2(tmp_path):
    f = tmp_path / "atoms.json"
    f.write_text("{ not valid json", encoding="utf-8")
    rc, _out, err = _run(str(f))
    assert rc == 2
    assert "ERROR" in err


def test_unsupported_json_shape_exit_2(tmp_path):
    f = _write(tmp_path / "atoms.json", "just a bare string")
    rc, _out, err = _run(str(f))
    assert rc == 2
    assert "unsupported JSON shape" in err


# ── JSONL handling ─────────────────────────────────────────────────────────────


def test_jsonl_violation_exit_1(tmp_path):
    f = tmp_path / "atoms.jsonl"
    f.write_text(json.dumps(GOOD_ATOM) + "\n" + json.dumps(BAD_ATOM) + "\n", encoding="utf-8")
    rc, out, _ = _run(str(f))
    assert rc == 1
    assert "R1.min" in out


def test_jsonl_skips_blank_and_comment_lines_exit_0(tmp_path):
    f = tmp_path / "atoms.jsonl"
    f.write_text("\n  \n# a comment line\n" + json.dumps(GOOD_ATOM) + "\n", encoding="utf-8")
    rc, out, _ = _run(str(f))
    assert rc == 0, out


# ── JSON wrapper shapes ─────────────────────────────────────────────────────────


def test_json_atoms_key_wrapper_passes(tmp_path):
    f = _write(tmp_path / "atoms.json", {"atoms": [GOOD_ATOM]})
    rc, out, _ = _run(str(f))
    assert rc == 0, out


def test_json_memories_key_wrapper_detects_violation(tmp_path):
    f = _write(tmp_path / "m.json", {"memories": [BAD_ATOM]})
    rc, out, _ = _run(str(f))
    assert rc == 1
    assert "R1.min" in out


# ── escape valve flows through the gate ─────────────────────────────────────────


def test_granularity_exempt_atom_passes_gate(tmp_path):
    f = _write(tmp_path / "atoms.json", [EXEMPT_ATOM])
    rc, out, _ = _run(str(f))
    assert rc == 0, out


# ── --report + env-var override ─────────────────────────────────────────────────


def test_report_mode_prints_ok_lines(tmp_path):
    f = _write(tmp_path / "atoms.json", [GOOD_ATOM])
    rc, out, _ = _run(str(f), report=True)
    assert rc == 0
    assert "OK" in out and "good-1" in out


def test_env_var_path_override_detects_violation(tmp_path):
    import os

    f = _write(tmp_path / "atoms.json", [BAD_ATOM])
    env = dict(os.environ)
    env["KEIRACOM_ATOM_SCAN_PATHS"] = str(f)
    rc, out, _ = _run(env=env)  # no --paths → env drives the scan
    assert rc == 1
    assert "R1.min" in out
