"""tests for scripts/backfill_tasks_bd_id.py — KEI-227 K1 backfill.

Covers:
  - URL → bd_id index construction (with + without external_ref)
  - plan_backfill: matched / ambiguous (multi-bd) / ambiguous (URL-strip
    collision e.g. KEI-54 vs KEI-54B) / unmatched
  - URL variant generation (full slug, no slug, trailing-slash strip)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "backfill_tasks_bd_id.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("backfill_tasks_bd_id", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["backfill_tasks_bd_id"] = m
    spec.loader.exec_module(m)
    return m


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.rowcount = 0

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params or ()))
        if sql.lstrip().upper().startswith("UPDATE"):
            self.rowcount = 1

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeConn:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._cur = _FakeCursor(rows)
        self.committed = False

    def cursor(self) -> _FakeCursor:
        return self._cur

    def commit(self) -> None:
        self.committed = True


def test_url_variants_strip_slug(mod) -> None:
    url = "https://linear.app/keiracom/issue/KEI-227/atlas-k1-id-canonicalisation-foo"
    variants = mod._candidate_url_variants(url)
    assert url in variants
    assert "https://linear.app/keiracom/issue/KEI-227" in variants


def test_url_variants_handle_trailing_slash(mod) -> None:
    url = "https://linear.app/keiracom/issue/KEI-227/"
    variants = mod._candidate_url_variants(url)
    assert "https://linear.app/keiracom/issue/KEI-227" in variants


def test_url_variants_empty_input(mod) -> None:
    assert mod._candidate_url_variants("") == []


def test_build_url_index_skips_missing_external_ref(mod) -> None:
    issues = [
        {"id": "Agency_OS-aaa", "external_ref": "https://linear.app/keiracom/issue/KEI-1"},
        {"id": "Agency_OS-bbb"},  # no external_ref
        {"id": "Agency_OS-ccc", "external_ref": None},
        {
            "id": "Agency_OS-ddd",
            "metadata": {"external_ref": "https://linear.app/keiracom/issue/KEI-2"},
        },
    ]
    index = mod._build_url_to_bd_id(issues)
    assert "https://linear.app/keiracom/issue/KEI-1" in index
    assert "https://linear.app/keiracom/issue/KEI-2" in index
    assert index["https://linear.app/keiracom/issue/KEI-1"] == ["Agency_OS-aaa"]
    assert "Agency_OS-bbb" not in [b for v in index.values() for b in v]


def test_build_url_index_groups_duplicates(mod) -> None:
    issues = [
        {"id": "Agency_OS-aaa", "external_ref": "https://linear.app/keiracom/issue/KEI-18"},
        {"id": "Agency_OS-bbb", "external_ref": "https://linear.app/keiracom/issue/KEI-18"},
    ]
    index = mod._build_url_to_bd_id(issues)
    assert sorted(index["https://linear.app/keiracom/issue/KEI-18"]) == [
        "Agency_OS-aaa",
        "Agency_OS-bbb",
    ]


def test_plan_matched_simple_pairing(mod) -> None:
    rows = [("KEI-227", "https://linear.app/keiracom/issue/KEI-227/atlas-k1-foo")]
    url_to_ids = {"https://linear.app/keiracom/issue/KEI-227": ["Agency_OS-8c67"]}
    plan = mod.plan_backfill(_FakeConn(rows), url_to_ids)
    assert plan["matched"] == [("KEI-227", "Agency_OS-8c67", rows[0][1])]
    assert plan["ambiguous"] == []
    assert plan["unmatched"] == []


def test_plan_ambiguous_bd_side_multi(mod) -> None:
    rows = [("KEI-18", "https://linear.app/keiracom/issue/KEI-18")]
    url_to_ids = {
        "https://linear.app/keiracom/issue/KEI-18": ["Agency_OS-58f", "Agency_OS-jny867"],
    }
    plan = mod.plan_backfill(_FakeConn(rows), url_to_ids)
    assert plan["matched"] == []
    assert plan["ambiguous"][0][0] == "KEI-18"
    assert sorted(plan["ambiguous"][0][1]) == ["Agency_OS-58f", "Agency_OS-jny867"]


def test_plan_ambiguous_url_strip_collision(mod) -> None:
    """KEI-54 and KEI-54B both strip-match to /issue/KEI-54 → second is ambiguous."""
    rows = [
        ("KEI-54", "https://linear.app/keiracom/issue/KEI-54"),
        ("KEI-54B", "https://linear.app/keiracom/issue/KEI-54/kei-52-tool-call-log-export"),
    ]
    url_to_ids = {"https://linear.app/keiracom/issue/KEI-54": ["Agency_OS-r1krve"]}
    plan = mod.plan_backfill(_FakeConn(rows), url_to_ids)
    assert plan["matched"] == [("KEI-54", "Agency_OS-r1krve", rows[0][1])]
    assert plan["ambiguous"][0][0] == "KEI-54B"
    assert "already claimed by KEI-54" in plan["ambiguous"][0][2]


def test_plan_unmatched_no_bd_pair(mod) -> None:
    rows = [("KEI-999", "https://linear.app/keiracom/issue/KEI-999")]
    url_to_ids: dict[str, list[str]] = {}
    plan = mod.plan_backfill(_FakeConn(rows), url_to_ids)
    assert plan["unmatched"] == [("KEI-999", rows[0][1])]


def test_apply_writes_each_match(mod) -> None:
    matched = [
        ("KEI-227", "Agency_OS-8c67", "https://linear.app/keiracom/issue/KEI-227"),
        ("KEI-228", "Agency_OS-tfsl", "https://linear.app/keiracom/issue/KEI-228"),
    ]
    conn = _FakeConn(rows=[])
    written = mod.apply_backfill(conn, matched)
    assert written == 2
    assert conn.committed is True
    updates = [e for e in conn._cur.executed if "UPDATE" in e[0]]
    assert len(updates) == 2
    # Verify the params order: (bd_id, task_id)
    assert updates[0][1][0] == "Agency_OS-8c67"
    assert updates[0][1][1] == "KEI-227"
