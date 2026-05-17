"""Tests for KEI-97 excluded_callsign filter in scripts/tasks_cli.py cmd_ready.

Covers:
  - bd ready --callsign=aiden does NOT return rows where excluded_callsign='aiden'
  - bd ready --callsign=elliot DOES return rows where excluded_callsign='aiden'
  - bd ready (no --callsign) returns all rows (backward compat, no exclusion filter)

Mocks psycopg cursor; no live DB.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeCursor, make_patch_connect  # type: ignore[import-not-found]  # noqa: E402


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli_excl", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli_excl"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def patch_connect(mod, monkeypatch):
    return make_patch_connect(monkeypatch)


# Column list for the ready query result rows (matches _READY_COLUMNS in tasks_cli.py)
_COLS = [
    ("id",),
    ("title",),
    ("priority",),
    ("status",),
    ("claimed_by",),
    ("claimed_at",),
    ("dependencies",),
    ("tags",),
    ("linear_url",),
    ("created_at",),
    ("updated_at",),
]

# A phase-lock row returned by the ceo_memory query (phase_max=99 = unlocked)
_PHASE_ROW = (json.dumps({"current_phase_max": 99}),)


def _make_cursor(rows: list[tuple]) -> FakeCursor:
    """Build a FakeCursor that returns _PHASE_ROW first, then rows."""
    cur = FakeCursor(
        fetchall_rows=rows,
        fetchone_row=_PHASE_ROW,
        description=_COLS,
    )
    # Override fetchone to return phase row on first call, then the rows via fetchall.
    # FakeCursor.fetchone always returns _one; that's fine because phase-lock query
    # uses fetchone and the ready query uses fetchall.
    return cur


# ── --callsign exclusion path ──────────────────────────────────────────────


def test_ready_with_callsign_includes_exclusion_clause(mod, patch_connect, capsys):
    """--callsign=aiden: SQL must contain the excluded_callsign != %s predicate."""
    review_row = (
        "REVIEW-PR-1",
        "Review PR #1",
        2,
        "available",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    cur = _make_cursor([review_row])
    patch_connect(cur)

    ret = mod.cmd_ready(
        type(
            "A",
            (),
            {
                "json": True,
                "limit": 50,
                "agent": None,
                "callsign": "aiden",
            },
        )()
    )
    assert ret == 0

    # Find the ready SQL (second execute — first is the phase-lock query)
    ready_exec = [e for e in cur.executed if "excluded_callsign" in e[0]]
    assert len(ready_exec) == 1, "Expected exactly one execute with excluded_callsign clause"
    sql, params = ready_exec[0]
    assert "excluded_callsign" in sql
    assert "aiden" in params


def test_ready_callsign_aiden_receives_non_excluded_rows(mod, patch_connect, capsys):
    """Rows where excluded_callsign IS NULL pass through for callsign=aiden."""
    # In this mock, the DB already filters; we simulate the DB returning 1 row.
    row = ("REVIEW-PR-2", "Review PR #2", 2, "available", None, None, None, None, None, None, None)
    cur = _make_cursor([row])
    patch_connect(cur)

    ret = mod.cmd_ready(
        type(
            "A",
            (),
            {
                "json": True,
                "limit": 50,
                "agent": None,
                "callsign": "aiden",
            },
        )()
    )
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["id"] == "REVIEW-PR-2"


def test_ready_callsign_elliot_receives_rows_excluded_for_aiden(mod, patch_connect, capsys):
    """Rows excluded for 'aiden' are visible to 'elliot'."""
    # For elliot, excluded_callsign='aiden' row should pass the filter.
    row = ("REVIEW-PR-3", "Review PR #3", 2, "available", None, None, None, None, None, None, None)
    cur = _make_cursor([row])
    patch_connect(cur)

    ret = mod.cmd_ready(
        type(
            "A",
            (),
            {
                "json": True,
                "limit": 50,
                "agent": None,
                "callsign": "elliot",
            },
        )()
    )
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1

    # SQL must contain exclusion for 'elliot', not 'aiden'
    ready_exec = [e for e in cur.executed if "excluded_callsign" in e[0]]
    assert len(ready_exec) == 1
    _, params = ready_exec[0]
    assert "elliot" in params


# ── Backward compat: no --callsign ────────────────────────────────────────


def test_ready_without_callsign_no_exclusion_clause(mod, patch_connect, capsys):
    """bd ready without --callsign does not add excluded_callsign filter (legacy)."""
    row = ("KEI-50", "Some task", 3, "available", None, None, None, None, None, None, None)
    cur = _make_cursor([row])
    patch_connect(cur)

    ret = mod.cmd_ready(
        type(
            "A",
            (),
            {
                "json": True,
                "limit": 50,
                "agent": None,
                "callsign": None,
            },
        )()
    )
    assert ret == 0

    # No execute should contain excluded_callsign clause
    excl_execs = [e for e in cur.executed if "excluded_callsign" in e[0]]
    assert excl_execs == [], "excluded_callsign clause must NOT appear without --callsign"


def test_ready_without_callsign_returns_all_rows(mod, patch_connect, capsys):
    """Without --callsign, all available rows are returned (no exclusion)."""
    rows = [
        ("REVIEW-PR-10", "Review PR #10", 2, "available", None, None, None, None, None, None, None),
        ("KEI-55", "Another task", 3, "available", None, None, None, None, None, None, None),
    ]
    cur = _make_cursor(rows)
    patch_connect(cur)

    ret = mod.cmd_ready(
        type(
            "A",
            (),
            {
                "json": True,
                "limit": 50,
                "agent": None,
                "callsign": None,
            },
        )()
    )
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 2
