"""Tests for KEI-32 verify_model_assignment.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "verify_model_assignment.py"

_spec = importlib.util.spec_from_file_location("verify_model_assignment", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["verify_model_assignment"] = _mod
_spec.loader.exec_module(_mod)


_FAKE_CEO_VALUE = {
    "primaries_unchanged": {
        "max": {"model": "claude-opus-4-7", "context_window": "1M"},
        "aiden": {"model": "claude-opus-4-7"},
        "elliot": {"model": "claude-opus-4-7"},
    },
    "clones_switched": {
        "atlas": {"model": "claude-sonnet-4-6", "context_window": "200K"},
        "orion": {"model": "claude-sonnet-4-6"},
        "scout": {"primary": "claude-sonnet-4-6 (200K)", "mechanical": "claude-haiku-4-5 (200K)"},
    },
}


def test_flatten_assignment_pulls_primaries_and_clones():
    out = _mod._flatten_assignment(_FAKE_CEO_VALUE)
    assert out == {
        "max": "claude-opus-4-7",
        "aiden": "claude-opus-4-7",
        "elliot": "claude-opus-4-7",
        "atlas": "claude-sonnet-4-6",
        "orion": "claude-sonnet-4-6",
        "scout": "claude-sonnet-4-6",
    }


def test_flatten_assignment_strips_context_window_suffix_from_scout_primary():
    val = {"clones_switched": {"scout": {"primary": "claude-sonnet-4-6 (200K)"}}}
    assert _mod._flatten_assignment(val) == {"scout": "claude-sonnet-4-6"}


def test_flatten_assignment_handles_missing_sections():
    assert _mod._flatten_assignment({}) == {}
    assert _mod._flatten_assignment({"primaries_unchanged": None}) == {}


def test_callsign_tmux_map_covers_six_canonical():
    assert set(_mod.TMUX_SESSION) == {"elliot", "aiden", "max", "atlas", "orion", "scout"}


def test_model_flag_regex_matches_space_and_equals_forms():
    assert (
        _mod._MODEL_FLAG_RE.search("claude --model claude-opus-4-7 --foo").group(1)
        == "claude-opus-4-7"
    )
    assert (
        _mod._MODEL_FLAG_RE.search("claude --model=claude-sonnet-4-6").group(1)
        == "claude-sonnet-4-6"
    )


def test_audit_all_match_returns_zero_drifted():
    expected = {
        "max": "opus-4-7",
        "elliot": "opus-4-7",
        "aiden": "opus-4-7",
        "atlas": "sonnet-4-6",
        "orion": "sonnet-4-6",
        "scout": "sonnet-4-6",
    }

    def expected_fn():
        return expected

    def running_fn(cs):
        return expected[cs]

    rows, drifted = _mod.audit(expected_fn=expected_fn, running_fn=running_fn)
    assert drifted == 0
    assert all(r["status"] == "match" for r in rows)


def test_audit_one_drift_returns_one_drifted():
    expected = dict.fromkeys(_mod.CALLSIGNS, "opus-4-7")

    def expected_fn():
        return expected

    def running_fn(cs):
        return "sonnet-4-6" if cs == "max" else "opus-4-7"

    rows, drifted = _mod.audit(expected_fn=expected_fn, running_fn=running_fn)
    assert drifted == 1
    max_row = next(r for r in rows if r["callsign"] == "max")
    assert max_row["status"] == "drift"


def test_audit_no_pane_counts_as_drift():
    expected = dict.fromkeys(_mod.CALLSIGNS, "opus-4-7")

    def expected_fn():
        return expected

    def running_fn(cs):
        return None if cs == "scout" else "opus-4-7"

    rows, drifted = _mod.audit(expected_fn=expected_fn, running_fn=running_fn)
    assert drifted == 1
    scout_row = next(r for r in rows if r["callsign"] == "scout")
    assert scout_row["status"] == "no-pane"


def test_audit_no_expected_does_not_count_as_drift():
    """If ceo_memory has no expected entry for a callsign, that's a config gap
    not a drift — we surface but don't fail the audit."""
    expected = {"max": "opus-4-7"}  # only one callsign in expected map

    def expected_fn():
        return expected

    def running_fn(cs):
        return "opus-4-7"

    rows, drifted = _mod.audit(expected_fn=expected_fn, running_fn=running_fn)
    assert drifted == 0  # no-expected does not increment drifted
    no_exp = [r for r in rows if r["status"] == "no-expected"]
    assert len(no_exp) == 5  # 5 callsigns have no expected entry


def test_main_returns_zero_when_no_drift(capsys):
    with (
        mock.patch.object(
            _mod, "fetch_expected_assignment", return_value=dict.fromkeys(_mod.CALLSIGNS, "x")
        ),
        mock.patch.object(_mod, "running_model_for", return_value="x"),
    ):
        rc = _mod.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "6/6 matched" in out
    assert "0 drifted" in out


def test_main_returns_one_when_drift(capsys):
    with (
        mock.patch.object(
            _mod,
            "fetch_expected_assignment",
            return_value=dict.fromkeys(_mod.CALLSIGNS, "expected"),
        ),
        mock.patch.object(
            _mod, "running_model_for", side_effect=lambda cs: "wrong" if cs == "max" else "expected"
        ),
    ):
        rc = _mod.main([])
    assert rc == 1


def test_main_returns_two_on_audit_error(capsys):
    with mock.patch.object(
        _mod,
        "fetch_expected_assignment",
        side_effect=_mod.AuditError("ceo_memory unreachable"),
    ):
        rc = _mod.main([])
    assert rc == 2
    assert "ceo_memory unreachable" in capsys.readouterr().err


def test_main_json_output_includes_rows_and_summary(capsys):
    with (
        mock.patch.object(
            _mod, "fetch_expected_assignment", return_value=dict.fromkeys(_mod.CALLSIGNS, "x")
        ),
        mock.patch.object(_mod, "running_model_for", return_value="x"),
    ):
        _mod.main(["--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "rows" in payload and "summary" in payload
    assert payload["summary"]["matched"] == 6
    assert payload["summary"]["drifted"] == 0


def test_running_model_for_returns_none_when_no_tmux_session():
    with mock.patch.object(_mod.subprocess, "run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=1, stdout="")
        assert _mod.running_model_for("max") is None


def test_running_model_for_unknown_callsign_returns_none():
    assert _mod.running_model_for("bogus") is None


def test_scan_pids_returns_implicit_when_claude_running_without_model_flag():
    """The actual production state — claude binary launched without --model."""
    with (
        mock.patch.object(_mod, "_read_cmdline", return_value="claude --resume <uuid>"),
        mock.patch.object(_mod, "_children_of", return_value=[]),
    ):
        result = _mod._scan_pids_for_model_flag(["1234"])
    assert result == "<implicit>"


def test_scan_pids_returns_model_when_explicit_flag_present():
    with (
        mock.patch.object(_mod, "_read_cmdline", return_value="claude --model claude-opus-4-7"),
        mock.patch.object(_mod, "_children_of", return_value=[]),
    ):
        result = _mod._scan_pids_for_model_flag(["1234"])
    assert result == "claude-opus-4-7"


def test_audit_implicit_counts_as_drift():
    """An implicit-running session is undetectable model — counts as drift to
    surface the gap (operator should restart with explicit --model)."""

    def expected_fn():
        return dict.fromkeys(_mod.CALLSIGNS, "claude-opus-4-7")

    def running_fn(cs):
        return "<implicit>"

    rows, drifted = _mod.audit(expected_fn=expected_fn, running_fn=running_fn)
    assert drifted == 6
    assert all(r["status"] == "implicit" for r in rows)
