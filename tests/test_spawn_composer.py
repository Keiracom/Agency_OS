"""Unit tests for src/relay/spawn_composer.py.

Covers each Part helper independently with a fake DB + tmp_path fs, plus
the full compose_initial_prompt() positive + resume-context branches.

bd: Agency_OS-spawn-composer (PR #1140 §7 piece #5).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.relay.spawn_composer import (
    AGENT_MEMORY_LIMIT,
    CANONICAL_KEYS,
    DAILY_LOG_LIMIT,
    DAVE_CONFIRMED_WINDOW_SECONDS,
    MAX_PART_BYTES,
    _part_a_role_brief,
    _part_b_canonical_keys,
    _part_c_inbox_queue,
    _part_d_recent_ceo_memory,
    _part_e_recent_agent_memories,
    _truncate,
    compose_initial_prompt,
)


class _FakeDB:
    """In-memory _DBProtocol implementation. Caller scripts the script."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[Any, ...]]] = []
        self._next_one: Any = None
        self._next_all: list[Any] = []
        # Allow scripting per-query responses: list of (one, all) per execute call.
        self._script: list[tuple[Any, list[Any]]] = []

    def script(self, one: Any, all_: list[Any]) -> None:
        self._script.append((one, all_))

    def execute(self, query: str, *params: Any) -> Any:
        self.queries.append((query, params))
        if self._script:
            self._next_one, self._next_all = self._script.pop(0)
        return self

    def fetchone(self) -> Any:
        return self._next_one

    def fetchall(self) -> Any:
        return self._next_all


# ─── Truncation ────────────────────────────────────────────────────────────────


def test_truncate_preserves_short_text():
    assert _truncate("hello", max_bytes=100) == "hello"


def test_truncate_emits_marker_with_dropped_byte_count():
    big = "x" * 5000
    out = _truncate(big, max_bytes=100)
    assert out.startswith("x" * 100)
    assert "<truncated 4900 bytes>" in out


# ─── Part A — role brief ───────────────────────────────────────────────────────


def test_part_a_prefers_runbook_over_identity(tmp_path: Path):
    runbook_dir = tmp_path / "docs" / "runbooks"
    runbook_dir.mkdir(parents=True)
    (runbook_dir / "nova-identity.md").write_text("ROLE: Nova engineer brief")
    (tmp_path / "IDENTITY.md").write_text("FALLBACK: should not be used")
    out = _part_a_role_brief("nova", tmp_path)
    assert "ROLE: Nova engineer brief" in out
    assert "FALLBACK" not in out


def test_part_a_falls_back_to_repo_root_identity(tmp_path: Path):
    (tmp_path / "IDENTITY.md").write_text("FALLBACK identity content")
    out = _part_a_role_brief("nova", tmp_path)
    assert "FALLBACK identity content" in out


def test_part_a_returns_marker_when_no_files(tmp_path: Path):
    out = _part_a_role_brief("ghost", tmp_path)
    assert "<no role brief found" in out


# ─── Part B — canonical keys ───────────────────────────────────────────────────


def test_part_b_queries_three_canonical_keys_in_order():
    db = _FakeDB()
    # Script: one row per key, returning a (value,) tuple shape.
    db.script(("comm_arch_value",), [])
    db.script(("mal_value",), [])
    db.script(("separation_value",), [])
    out = _part_b_canonical_keys(db)
    queried_keys = [params[0] for (_, params) in db.queries]
    assert queried_keys == list(CANONICAL_KEYS)
    assert "comm_arch_value" in out
    assert "mal_value" in out
    assert "separation_value" in out


def test_part_b_emits_marker_when_key_missing():
    db = _FakeDB()
    db.script(None, [])
    db.script(None, [])
    db.script(None, [])
    out = _part_b_canonical_keys(db)
    assert out.count("<not set>") == len(CANONICAL_KEYS)


# ─── Part C — inbox queue ──────────────────────────────────────────────────────


def test_part_c_reads_all_json_files_sorted(tmp_path: Path):
    inbox_dir = tmp_path / "telegram-relay-nova" / "inbox"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "b.json").write_text('{"second": true}')
    (inbox_dir / "a.json").write_text('{"first": true}')
    out = _part_c_inbox_queue("nova", tmp_path)
    # a.json must precede b.json (sorted)
    assert out.index("a.json") < out.index("b.json")
    assert '"first"' in out
    assert '"second"' in out


def test_part_c_empty_inbox_emits_marker(tmp_path: Path):
    inbox_dir = tmp_path / "telegram-relay-nova" / "inbox"
    inbox_dir.mkdir(parents=True)
    assert "<inbox empty>" in _part_c_inbox_queue("nova", tmp_path)


def test_part_c_missing_dir_emits_marker(tmp_path: Path):
    out = _part_c_inbox_queue("nova", tmp_path)
    assert "<inbox dir not present" in out


# ─── Part D — recent ceo_memory ────────────────────────────────────────────────


def test_part_d_queries_with_callsign_and_window_cutoff():
    db = _FakeDB()
    db.script(None, [("daily_log", "summary", 1748000000)])
    now = 1748252600
    _part_d_recent_ceo_memory(db, "nova", now)
    query, params = db.queries[-1]
    assert "FROM public.agent_memories" in query
    assert params[0] == "nova"
    # Cutoff is `now - 7 days`
    assert params[1] == now - DAVE_CONFIRMED_WINDOW_SECONDS
    assert params[2] == DAILY_LOG_LIMIT


def test_part_d_empty_result_emits_marker():
    db = _FakeDB()
    db.script(None, [])
    out = _part_d_recent_ceo_memory(db, "nova", 1748252600)
    assert "<no recent ceo_memory entries>" in out


# ─── Part E — recent agent_memories ────────────────────────────────────────────


def test_part_e_limits_to_ten():
    db = _FakeDB()
    db.script(None, [("daily_log", f"entry {i}", 1748000000 + i) for i in range(10)])
    out = _part_e_recent_agent_memories(db, "nova")
    query, params = db.queries[-1]
    assert params == ("nova", AGENT_MEMORY_LIMIT)
    assert "entry 0" in out
    assert "entry 9" in out


def test_part_e_empty_emits_marker():
    db = _FakeDB()
    db.script(None, [])
    assert "<no recent agent_memories>" in _part_e_recent_agent_memories(db, "nova")


# ─── compose_initial_prompt ────────────────────────────────────────────────────


def _seed_db_for_full_compose(db: _FakeDB) -> None:
    # Part B: 3 canonical-key rows
    db.script(("comm_arch_v1",), [])
    db.script(("mal_v1",), [])
    db.script(("separation_v1",), [])
    # Part D: 1 row
    db.script(None, [("daily_log", "yesterday's summary", 1748000000)])
    # Part E: 2 rows
    db.script(None, [("daily_log", "later", 1748100000), ("core_fact", "earlier", 1747900000)])


def test_compose_positive_path_includes_all_five_parts(tmp_path: Path):
    (tmp_path / "IDENTITY.md").write_text("ROLE BRIEF")
    inbox_dir = tmp_path / "telegram-relay-nova" / "inbox"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "task_1.json").write_text('{"id":"task_1","type":"task_dispatch"}')
    db = _FakeDB()
    _seed_db_for_full_compose(db)
    out = compose_initial_prompt(
        "nova",
        db=db,
        repo_root=tmp_path,
        inbox_root=tmp_path,
        now=1748252600,
    )
    assert "=== PART A — ROLE BRIEF ===" in out
    assert "=== PART B — CANONICAL CEO_MEMORY KEYS ===" in out
    assert "=== PART C — PENDING INBOX QUEUE ===" in out
    assert "=== PART D — RECENT CEO_MEMORY ===" in out
    assert "=== PART E — RECENT AGENT MEMORIES ===" in out
    assert "ROLE BRIEF" in out
    assert "comm_arch_v1" in out
    assert "task_1.json" in out
    assert "yesterday's summary" in out
    # Resume header MUST NOT appear in positive path
    assert "RESUME CONTEXT" not in out


def test_compose_resume_branch_skips_part_c_and_adds_resume_section(tmp_path: Path):
    (tmp_path / "IDENTITY.md").write_text("ROLE BRIEF")
    inbox_dir = tmp_path / "telegram-relay-nova" / "inbox"
    inbox_dir.mkdir(parents=True)
    # File present in the inbox — must NOT appear in resume output (Part C skipped).
    (inbox_dir / "task_999.json").write_text("SHOULD_NOT_APPEAR")
    db = _FakeDB()
    # 3 canonical-key queries + Part D + Part E.
    db.script(("comm_arch_v1",), [])
    db.script(("mal_v1",), [])
    db.script(("separation_v1",), [])
    db.script(None, [])
    db.script(None, [])
    resume_ctx = {
        "decision": "push_fixup",
        "original_task_ref": "review-pr-1175",
        "interim_state": {"notes": "waiting on Elliot", "artifacts": ["draft.md"]},
    }
    out = compose_initial_prompt(
        "nova",
        db=db,
        repo_root=tmp_path,
        inbox_root=tmp_path,
        now=1748252600,
        resume_context=resume_ctx,
    )
    assert "PART C — PENDING INBOX QUEUE" not in out
    assert "SHOULD_NOT_APPEAR" not in out
    assert "RESUME CONTEXT" in out
    assert "push_fixup" in out
    assert "review-pr-1175" in out
    assert "waiting on Elliot" in out


def test_compose_empty_callsign_raises():
    db = _FakeDB()
    with pytest.raises(ValueError, match="callsign is required"):
        compose_initial_prompt("", db=db, repo_root=Path("/tmp"), now=1748252600)


def test_compose_oversize_inbox_truncates_part_c(tmp_path: Path):
    (tmp_path / "IDENTITY.md").write_text("ROLE")
    inbox_dir = tmp_path / "telegram-relay-nova" / "inbox"
    inbox_dir.mkdir(parents=True)
    # Single giant inbox file blows past the per-part cap.
    (inbox_dir / "huge.json").write_text("x" * (MAX_PART_BYTES * 3))
    db = _FakeDB()
    _seed_db_for_full_compose(db)
    out = compose_initial_prompt(
        "nova",
        db=db,
        repo_root=tmp_path,
        inbox_root=tmp_path,
        now=1748252600,
    )
    assert "<truncated" in out
