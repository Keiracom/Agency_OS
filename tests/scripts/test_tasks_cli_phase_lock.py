"""Tests for KEI-86 phase-lock enforcement in scripts/tasks_cli.py.

Strategy:
  - _current_phase_max — exercised with a minimal in-line cursor double; checks
    fail-open behaviour when the ceo:phase_lock row is absent or malformed.
  - cmd_ready / cmd_claim integration — monkeypatch _current_phase_max to a
    fixed value, then mock psycopg.connect via the shared FakeCursor helper.
    Verifies that (a) the SQL contains the phase filter, (b) the params
    include the lock value, and (c) cmd_claim --id emits an explanatory
    error on over-lock.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeCursor, make_patch_connect  # type: ignore[import-not-found]  # noqa: E402


def _load_mod():
    spec = importlib.util.spec_from_file_location("tasks_cli", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli"] = m
    spec.loader.exec_module(m)
    return m


class _PhaseCursor:
    """Cursor double that returns a single configurable fetchone value."""

    def __init__(self, row: object) -> None:
        self.row = row
        self.executed: list[tuple] = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.row


def test_current_phase_max_fails_open_when_row_missing():
    mod = _load_mod()
    assert mod._current_phase_max(_PhaseCursor(None)) == 99.0


def test_current_phase_max_reads_value():
    mod = _load_mod()
    assert mod._current_phase_max(_PhaseCursor(({"current_phase_max": 0},))) == 0.0


def test_current_phase_max_fails_open_on_malformed_json():
    mod = _load_mod()
    assert mod._current_phase_max(_PhaseCursor(({"wrong_key": 1},))) == 99.0


def test_cmd_claim_id_rejects_above_lock(monkeypatch, capsys):
    mod = _load_mod()
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "max")
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 0.0)
    cur = FakeCursor(fetchone_row=(2.0,))
    make_patch_connect(monkeypatch)(cur)
    ns = argparse.Namespace(id="KEI-FAKE", callsign=None, json=False)
    assert mod.cmd_claim(ns) == 1
    err = capsys.readouterr().err
    assert "KEI-86 phase-lock" in err
    assert "phase 2" in err
    assert "current_phase_max is 0" in err


def test_cmd_ready_sql_includes_phase_filter(monkeypatch, capsys):
    mod = _load_mod()
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 0.5)
    cur = FakeCursor(fetchall_rows=[], description=[("id",), ("title",), ("priority",)])
    make_patch_connect(monkeypatch)(cur)
    ns = argparse.Namespace(json=True, limit=10, agent=None)
    assert mod.cmd_ready(ns) == 0
    last_sql = cur.last_sql
    assert "phase <= %s" in last_sql
    assert cur.last_params == (0.5, 10)


def test_cmd_claim_next_available_passes_phase_in_cte(monkeypatch):
    mod = _load_mod()
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "max")
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 0.0)
    cur = FakeCursor(fetchone_row=None)
    make_patch_connect(monkeypatch)(cur)
    ns = argparse.Namespace(id=None, callsign=None, json=True)
    assert mod.cmd_claim(ns) == 0
    assert "phase <= %s" in cur.last_sql
    assert cur.last_params is not None and cur.last_params[0] == 0.0
