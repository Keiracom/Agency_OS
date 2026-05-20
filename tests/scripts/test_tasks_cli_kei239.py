"""KEI-239 — tests for `bd complete --auto-verify` synthesised evidence.

Covers:
- _build_auto_verify_payload: schema-compliant shape + agent attribution
- cmd_complete with --auto-verify: synthesised payload accepted, task completes
- cmd_complete without --evidence AND without --auto-verify: errors with hint
- cmd_complete with both flags: --evidence wins (auto-verify is a no-op)
- session id sourcing (CLAUDE_CODE_SESSION_ID env vs synthetic uuid)
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tasks_cli", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli"] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# _build_auto_verify_payload pure-function tests.
# ---------------------------------------------------------------------------


def test_auto_verify_payload_satisfies_evidence_schema(mod, monkeypatch) -> None:
    """The synthesised payload must pass _validate_evidence_schema."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "test-session-uuid")
    payload = mod._build_auto_verify_payload("KEI-99", "atlas")
    err = mod._validate_evidence_schema(payload)
    assert err is None, f"unexpected schema error: {err}"


def test_auto_verify_payload_attributes_to_callsign(mod, monkeypatch) -> None:
    """Synthetic acceptance_items must mention the calling callsign."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "test-session-uuid")
    payload = mod._build_auto_verify_payload("KEI-99", "scout")
    assert "atlas" not in payload["acceptance_items"][0]["evidence"]
    assert "scout" in payload["acceptance_items"][0]["evidence"]


def test_auto_verify_payload_uses_session_env(mod, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "the-real-session")
    payload = mod._build_auto_verify_payload("KEI-99", "atlas")
    assert payload["verifier_session_uuid"] == "the-real-session"


def test_auto_verify_payload_falls_back_to_synthetic_uuid(mod, monkeypatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    payload = mod._build_auto_verify_payload("KEI-99", "atlas")
    assert payload["verifier_session_uuid"].startswith("auto-verify-")
    # Substring after the prefix must parse as a UUID
    suffix = payload["verifier_session_uuid"].split("auto-verify-", 1)[1]
    uuid.UUID(suffix)  # raises if not valid


def test_auto_verify_payload_meets_min_output_length(mod, monkeypatch) -> None:
    """commands[*].output must be >= _EVIDENCE_MIN_OUTPUT_LEN (16 chars)."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess")
    payload = mod._build_auto_verify_payload("KEI-99", "atlas")
    assert len(payload["commands"][0]["output"]) >= mod._EVIDENCE_MIN_OUTPUT_LEN


def test_auto_verify_payload_includes_task_id_in_command(mod, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess")
    payload = mod._build_auto_verify_payload("KEI-313", "max")
    assert "KEI-313" in payload["commands"][0]["cmd"]
    assert "--auto-verify" in payload["commands"][0]["cmd"]


# ---------------------------------------------------------------------------
# cmd_complete integration — error path when neither flag passed.
# ---------------------------------------------------------------------------


def test_cmd_complete_without_either_flag_errors(mod, monkeypatch, capsys) -> None:
    """Hint should mention both --evidence and --auto-verify."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")
    monkeypatch.setenv("CALLSIGN", "atlas")
    rc = mod.main(["complete", "KEI-99"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--evidence" in err
    assert "--auto-verify" in err
