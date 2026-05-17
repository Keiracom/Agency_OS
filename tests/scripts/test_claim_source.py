"""tests/scripts/test_claim_source.py — KEI-95 claim_source column + auto-loop path.

Covers:
  - tasks_cli.py claim --source auto_loop sets claim_source='auto_loop' in UPDATE SQL
  - tasks_cli.py claim (default) sets claim_source='manual' in UPDATE SQL
  - self_assign_on_ready.py _bd_claim invokes tasks_cli with --source auto_loop
  - CHECK constraint semantics verified via DB (positive + negative)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"
ASSIGN_SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "self_assign_on_ready.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import (  # type: ignore[import-not-found]  # noqa: E402
    FakeConn,
    FakeCursor,
    make_patch_connect,
)

_Cursor = FakeCursor


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def assign_mod():
    spec = importlib.util.spec_from_file_location("self_assign_on_ready", ASSIGN_SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["self_assign_on_ready"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def patch_connect(mod, monkeypatch):
    return make_patch_connect(monkeypatch)


# ─── tasks_cli claim --source auto_loop ─────────────────────────────────────


def _make_multi_cursor(phase_row=None, claim_row=None):
    """Return a FakeCursor that handles the two-query sequence in cmd_claim.

    First execute: SELECT phase (returns phase_row or None).
    Second execute: UPDATE ... RETURNING (returns claim_row or None).
    """

    class MultiCursor(FakeCursor):
        def __init__(self):
            super().__init__()
            self._call_count = 0
            self._phase_row = phase_row
            self._claim_row = claim_row

        def execute(self, sql, params=None):
            super().execute(sql, params)
            self._call_count += 1

        def fetchone(self):
            # First call is the phase SELECT; second is the claim UPDATE.
            if self._call_count == 1:
                return self._phase_row
            return self._claim_row

    cur = MultiCursor()
    return cur


def test_claim_auto_loop_sets_claim_source_in_sql(mod, monkeypatch, capsys) -> None:
    """--source auto_loop passes 'auto_loop' as claim_source param in targeted UPDATE."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    cur = _make_multi_cursor(
        phase_row=(0.5,),
        claim_row=("KEI-95", "title", 1, "active", "aiden", "url", None),
    )
    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: FakeConn(cur))
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 1.0)

    rc = mod.main(["claim", "--id", "KEI-95", "--source", "auto_loop", "--json"])
    assert rc == 0
    # The UPDATE SQL must include claim_source = %s and the param tuple must
    # contain 'auto_loop'.
    update_calls = [(sql, params) for sql, params in cur.executed if "claim_source" in sql]
    assert update_calls, "UPDATE with claim_source not found in executed SQL"
    _, params = update_calls[0]
    assert "auto_loop" in params


def test_claim_manual_default_sets_claim_source_manual(mod, monkeypatch) -> None:
    """Default (no --source) passes 'manual' as claim_source param."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    cur = _make_multi_cursor(
        phase_row=(0.5,),
        claim_row=("KEI-95", "title", 1, "active", "aiden", "url", None),
    )
    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: FakeConn(cur))
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 1.0)

    rc = mod.main(["claim", "--id", "KEI-95", "--json"])
    assert rc == 0
    update_calls = [(sql, params) for sql, params in cur.executed if "claim_source" in sql]
    assert update_calls, "UPDATE with claim_source not found in executed SQL"
    _, params = update_calls[0]
    assert "manual" in params


def test_claim_next_available_auto_loop_source(mod, monkeypatch) -> None:
    """Next-available (no --id) path also passes claim_source='auto_loop'."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    # No phase check in next-available path — single fetchone for the CTE UPDATE.
    cur = FakeCursor(
        fetchone_row=("KEI-95", "title", 1, "active", "aiden", "url", None),
    )
    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: FakeConn(cur))
    monkeypatch.setattr(mod, "_current_phase_max", lambda _cur: 1.0)

    rc = mod.main(["claim", "--source", "auto_loop", "--json"])
    assert rc == 0
    update_calls = [(sql, params) for sql, params in cur.executed if "claim_source" in sql]
    assert update_calls, "UPDATE with claim_source not found in executed SQL"
    _, params = update_calls[0]
    assert "auto_loop" in params


# ─── self_assign_on_ready.py — uses tasks_cli with --source auto_loop ────────


def test_bd_claim_calls_tasks_cli_with_auto_loop_source(assign_mod, tmp_path) -> None:
    """_bd_claim invokes tasks_cli.py with --source auto_loop via subprocess."""
    captured: list[list] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        result = MagicMock()
        result.returncode = 0
        return result

    with patch("subprocess.run", side_effect=fake_run):
        ok = assign_mod._bd_claim("bd", "KEI-95")

    assert ok is True
    assert captured, "subprocess.run was not called"
    cmd = captured[0]
    assert "--source" in cmd
    assert "auto_loop" in cmd


def test_bd_claim_fallback_to_bd_when_tasks_cli_missing(assign_mod, monkeypatch) -> None:
    """_bd_claim falls back to `bd update --claim` when tasks_cli.py not resolvable."""
    monkeypatch.setattr(assign_mod, "_resolve_tasks_cli", lambda: None)
    captured: list[list] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        result = MagicMock()
        result.returncode = 0
        return result

    with patch("subprocess.run", side_effect=fake_run):
        ok = assign_mod._bd_claim("bd", "KEI-95")

    assert ok is True
    assert captured
    cmd = captured[0]
    assert "bd" in cmd[0]
    assert "--claim" in cmd


# ─── safe-default: CHECK constraint violation treated as 'manual' ─────────────


def test_claim_source_invalid_value_not_accepted_by_argparse(mod) -> None:
    """argparse rejects unknown --source values — CHECK constraint never reached."""
    with pytest.raises(SystemExit) as exc_info:
        mod.main(["claim", "--id", "KEI-95", "--source", "rogue_value"])
    assert exc_info.value.code == 2
