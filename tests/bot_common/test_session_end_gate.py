"""tests for src/bot_common/session_end_gate.py — LAW XV mechanical gate (Outcome 2).

Mocks Supabase + MANUAL.md to test:
  - Trigger regex (hits + anti-broadening exempts)
  - Directive number extraction (multiple formats + edge cases)
  - Each store check (present + missing + stale + import-failure)
  - gate_check end-to-end (skip env, no-trigger, no-directive, all-pass, partial-fail)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from src.bot_common import session_end_gate as gate

# ─────────────────────────────────────────────────────────────────────────────
# Trigger regex
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "directive 9001 complete",
        "Directive #9001 complete!",
        "directive_9001 complete via three_store_save.py",
        "4-store save done for directive 7000",
        "all stores written for directive 9500",
        "store save complete for #1234",
        "directive 100 completed",
    ],
)
def test_has_completion_trigger_hits(text: str) -> None:
    assert gate.has_completion_trigger(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "directive 9001 is not complete yet",
        "will complete directive 9001 next",
        "going to complete directive 9000 after CI",
        "haven't saved directive 9001 yet",
        "just a status update — nothing to flag",
    ],
)
def test_has_completion_trigger_exempt(text: str) -> None:
    assert gate.has_completion_trigger(text) is False


# ─────────────────────────────────────────────────────────────────────────────
# Directive number extraction
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("directive 9001 complete", 9001),
        ("Directive #1234 complete", 1234),
        ("directive_500 complete", 500),
        ("ran scripts/three_store_save.py --directive 7000", 7000),
        ("Directive  #42  complete", 42),
    ],
)
def test_extract_directive_number_hits(text: str, expected: int) -> None:
    assert gate.extract_directive_number(text) == expected


def test_extract_directive_number_no_match_returns_none() -> None:
    assert gate.extract_directive_number("save completed, all stores written") is None


# ─────────────────────────────────────────────────────────────────────────────
# check_ceo_memory
# ─────────────────────────────────────────────────────────────────────────────


def _fake_sb_get_factory(rows: list[dict]):
    def _sb_get(table: str, params: dict) -> list[dict]:
        return rows

    return _sb_get


def test_check_ceo_memory_fresh_returns_true() -> None:
    now = datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)
    rows = [
        {
            "key": "ceo:directive_9001_complete",
            "updated_at": (now - timedelta(minutes=2)).isoformat(),
        }
    ]
    with patch("src.evo.supabase_client.sb_get", _fake_sb_get_factory(rows)):
        ok, reason = gate.check_ceo_memory(9001, now)
    assert ok is True
    assert reason == ""


def test_check_ceo_memory_missing_returns_false() -> None:
    now = datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)
    with patch("src.evo.supabase_client.sb_get", _fake_sb_get_factory([])):
        ok, reason = gate.check_ceo_memory(9001, now)
    assert ok is False
    assert "no row for key" in reason
    assert "ceo:directive_9001_complete" in reason


def test_check_ceo_memory_stale_returns_false() -> None:
    now = datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)
    rows = [
        {
            "key": "ceo:directive_9001_complete",
            "updated_at": (now - timedelta(minutes=30)).isoformat(),
        }
    ]
    with patch("src.evo.supabase_client.sb_get", _fake_sb_get_factory(rows)):
        ok, reason = gate.check_ceo_memory(9001, now)
    assert ok is False
    assert "stale" in reason


# ─────────────────────────────────────────────────────────────────────────────
# check_cis_metrics
# ─────────────────────────────────────────────────────────────────────────────


def test_check_cis_metrics_present_by_id() -> None:
    rows = [{"directive_id": 9001, "directive_ref": "Outcome 2"}]
    with patch("src.evo.supabase_client.sb_get", _fake_sb_get_factory(rows)):
        ok, reason = gate.check_cis_metrics(9001)
    assert ok is True


def test_check_cis_metrics_missing_returns_false() -> None:
    with patch("src.evo.supabase_client.sb_get", _fake_sb_get_factory([])):
        ok, reason = gate.check_cis_metrics(9001)
    assert ok is False
    assert "no row" in reason


# ─────────────────────────────────────────────────────────────────────────────
# check_manual_section_13
# ─────────────────────────────────────────────────────────────────────────────


def test_check_manual_section_13_hit(monkeypatch, tmp_path) -> None:
    manual = tmp_path / "MANUAL.md"
    manual.write_text(
        "# Manual\n\n"
        "## SECTION 12 — X\nfoo\n\n"
        "## SECTION 13 — BUILD SEQUENCE\n"
        "| Sprint 1 | #9001 | Outcome 2 build | COMPLETE |\n\n"
        "## SECTION 14 — Y\nbar\n"
    )
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)
    ok, reason = gate.check_manual_section_13(9001)
    assert ok is True


def test_check_manual_section_13_miss(monkeypatch, tmp_path) -> None:
    manual = tmp_path / "MANUAL.md"
    manual.write_text(
        "## SECTION 13 — BUILD SEQUENCE\n"
        "| Sprint 1 | #1234 | other | COMPLETE |\n\n"
        "## SECTION 14 — Y\nbar\n"
    )
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)
    ok, reason = gate.check_manual_section_13(9001)
    assert ok is False
    assert "#9001" in reason


def test_check_manual_section_13_directive_text_match(monkeypatch, tmp_path) -> None:
    """Should also match "directive 9001" text format."""
    manual = tmp_path / "MANUAL.md"
    manual.write_text(
        "## SECTION 13 — BUILD SEQUENCE\n"
        "Per directive 9001, this was shipped.\n\n"
        "## SECTION 14 — Y\n"
    )
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)
    ok, reason = gate.check_manual_section_13(9001)
    assert ok is True


def test_check_manual_section_13_missing_section_skipped(monkeypatch, tmp_path) -> None:
    manual = tmp_path / "MANUAL.md"
    manual.write_text("## SECTION 1 — X\n")  # no section 13
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)
    ok, reason = gate.check_manual_section_13(9001)
    assert ok is True
    assert "skipped" in reason


def test_check_manual_section_13_does_not_match_outside_section(monkeypatch, tmp_path) -> None:
    """A #9001 reference in Section 12 should NOT satisfy the Section 13 check."""
    manual = tmp_path / "MANUAL.md"
    manual.write_text(
        "## SECTION 12 — Notes\nSee #9001 for context.\n\n"
        "## SECTION 13 — BUILD SEQUENCE\nUnrelated rows.\n\n"
        "## SECTION 14 — Y\n"
    )
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)
    ok, _ = gate.check_manual_section_13(9001)
    assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# gate_check end-to-end
# ─────────────────────────────────────────────────────────────────────────────


def test_gate_check_skip_env_bypasses(monkeypatch) -> None:
    monkeypatch.setenv("R_LAW_XV_SKIP", "1")
    ok, reason = gate.gate_check("directive 9001 complete — all stores written")
    assert ok is True
    assert reason is None


def test_gate_check_no_trigger_passes() -> None:
    ok, reason = gate.gate_check("just a status update")
    assert ok is True
    assert reason is None


def test_gate_check_trigger_but_no_directive_number_passes() -> None:
    """4-store save language without a number is ambiguous — don't block."""
    ok, reason = gate.gate_check("4-store save attempted but failed mid-way")
    assert ok is True
    assert reason is None


def test_gate_check_all_stores_present_passes(monkeypatch, tmp_path) -> None:
    now = datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)
    fresh_ts = (now - timedelta(minutes=1)).isoformat()
    manual = tmp_path / "MANUAL.md"
    manual.write_text("## SECTION 13 — BUILD SEQUENCE\n| Sprint X | #9001 | done | COMPLETE |\n")
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)

    def fake_sb_get(table: str, params: dict) -> list[dict]:
        if table == "ceo_memory":
            return [{"key": "ceo:directive_9001_complete", "updated_at": fresh_ts}]
        if table == "cis_directive_metrics":
            return [{"directive_id": 9001, "directive_ref": "Outcome 2"}]
        return []

    with patch("src.evo.supabase_client.sb_get", fake_sb_get):
        ok, reason = gate.gate_check("directive 9001 complete — saved", now=now)
    assert ok is True
    assert reason is None


def test_gate_check_partial_fail_blocks(monkeypatch, tmp_path) -> None:
    """ceo_memory missing → blocked with directive number in reason."""
    now = datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)
    manual = tmp_path / "MANUAL.md"
    manual.write_text("## SECTION 13 — BUILD SEQUENCE\n| #9001 | done | COMPLETE |\n")
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)

    def fake_sb_get(table: str, params: dict) -> list[dict]:
        if table == "ceo_memory":
            return []  # MISSING
        if table == "cis_directive_metrics":
            return [{"directive_id": 9001}]
        return []

    with patch("src.evo.supabase_client.sb_get", fake_sb_get):
        ok, reason = gate.gate_check("directive 9001 complete", now=now)
    assert ok is False
    assert "R_LAW_XV_BLOCKED" in reason
    assert "9001" in reason
    assert "ceo_memory" in reason
    assert "three_store_save.py" in reason


def test_gate_check_all_three_missing_lists_all_blockers(monkeypatch, tmp_path) -> None:
    now = datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)
    manual = tmp_path / "MANUAL.md"
    manual.write_text("## SECTION 13 — BUILD SEQUENCE\nnothing here\n")
    monkeypatch.setattr(gate, "MANUAL_PATH", manual)
    with patch("src.evo.supabase_client.sb_get", _fake_sb_get_factory([])):
        ok, reason = gate.gate_check("directive 7777 complete", now=now)
    assert ok is False
    assert "ceo_memory" in reason
    assert "cis_directive_metrics" in reason
    assert "MANUAL.md" in reason
