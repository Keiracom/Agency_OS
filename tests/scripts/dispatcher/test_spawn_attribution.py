"""Tests for scripts/dispatcher/_spawn_attribution.py (cutover step 4.5 PR #4).

Covers:
  - disabled fail-open (rollout phase 1)
  - source_type derivation (slack / pr / cron / inbox default + explicit)
  - task_type derivation (pr_review / deliberation / dispatch_mgmt / chat / build default)
  - source_id derivation (source_id > task_ref > id > unknown)
  - JSONL emit smoke (real log_spawn_attribution call with tmp_path)
  - Telemetry failure fail-open (invalid source_type via patched config)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.dispatcher import _spawn_attribution

# ----- disabled fail-open -----


def test_disabled_returns_none() -> None:
    result = _spawn_attribution.emit({"from": "elliot", "type": "task_dispatch"}, callsign="orion")
    assert result is None


# ----- source_type derivation -----


@pytest.mark.parametrize(
    "envelope,expected",
    [
        ({"source_type": "slack"}, "slack"),
        ({"source_type": "pr"}, "pr"),
        ({"source_type": "cron"}, "cron"),
        ({"source_type": "inbox"}, "inbox"),
        ({"source_type": "unknown"}, "unknown"),
        ({"source_type": "bogus"}, "inbox"),  # invalid → fallback
        ({"from": "dave"}, "slack"),
        ({"from": "cron"}, "cron"),
        ({"from": "scheduler"}, "cron"),
        ({"task_ref": "PR-1234"}, "pr"),
        ({"task_ref": "pr-1234"}, "pr"),
        ({"task_ref": "pull-request-1234"}, "pr"),
        ({}, "inbox"),  # default
        ({"from": "atlas"}, "inbox"),
    ],
)
def test_source_type_derivation(envelope: dict[str, Any], expected: str) -> None:
    assert _spawn_attribution._envelope_source_type(envelope) == expected


# ----- task_type derivation -----


@pytest.mark.parametrize(
    "envelope,expected",
    [
        ({"task_type": "pr_review"}, "pr_review"),
        ({"task_type": "deliberation"}, "deliberation"),
        ({"task_type": "build"}, "build"),
        ({"task_type": "chat"}, "chat"),
        ({"task_type": "dispatch_mgmt"}, "dispatch_mgmt"),
        ({"task_type": "unknown"}, "unknown"),
        ({"task_type": "bogus"}, "build"),  # invalid → fallback to build
        ({"task_ref": "REVIEW-PR-1199"}, "pr_review"),
        ({"task_ref": "pr-review-1199"}, "pr_review"),  # case-insensitive
        ({"task_ref": "DELIBERATE-arch-v2"}, "deliberation"),
        ({"task_ref": "DELIBERATION-arch-v2"}, "deliberation"),
        ({"task_ref": "DISPATCH-rebase-1212"}, "dispatch_mgmt"),
        ({"from": "dave"}, "chat"),
        ({}, "build"),  # default
        ({"from": "atlas"}, "build"),
    ],
)
def test_task_type_derivation(envelope: dict[str, Any], expected: str) -> None:
    assert _spawn_attribution._envelope_task_type(envelope) == expected


# ----- source_id derivation -----


@pytest.mark.parametrize(
    "envelope,expected",
    [
        ({"source_id": "SID-1", "task_ref": "REF-2", "id": "ID-3"}, "SID-1"),
        ({"task_ref": "REF-2", "id": "ID-3"}, "REF-2"),
        ({"id": "ID-3"}, "ID-3"),
        ({}, "unknown"),
    ],
)
def test_source_id_derivation(envelope: dict[str, Any], expected: str) -> None:
    assert _spawn_attribution._envelope_source_id(envelope) == expected


# ----- JSONL emit smoke (uses tmp log path via DEFAULT_ATTRIBUTION_LOG monkey-patch) -----


def test_emit_writes_jsonl_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "spawn-attribution.jsonl"
    monkeypatch.setattr("src.keiracom_system.attribution.logger.DEFAULT_ATTRIBUTION_LOG", log_path)
    entry = _spawn_attribution.emit(
        {
            "from": "elliot",
            "type": "task_dispatch",
            "task_ref": "REVIEW-PR-1199",
            "id": "evt-42",
        },
        callsign="orion",
        enabled=True,
    )
    assert entry is not None
    assert entry.callsign == "orion"
    assert entry.source_type == "inbox"  # from elliot → inbox (not dave/cron/pr)
    assert entry.task_type == "pr_review"
    assert entry.source_id == "REVIEW-PR-1199"
    assert log_path.exists()
    line = log_path.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["callsign"] == "orion"
    assert parsed["source_type"] == "inbox"
    assert parsed["task_type"] == "pr_review"


def test_emit_dave_dm_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "spawn-attribution.jsonl"
    monkeypatch.setattr("src.keiracom_system.attribution.logger.DEFAULT_ATTRIBUTION_LOG", log_path)
    entry = _spawn_attribution.emit(
        {
            "from": "dave",
            "type": "task_dispatch",
            "task_ref": "hello",
        },
        callsign="elliot",
        enabled=True,
    )
    assert entry is not None
    assert entry.source_type == "slack"  # dave → slack
    assert entry.task_type == "chat"  # dave → chat
    assert entry.callsign == "elliot"


def test_emit_pr_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_path = tmp_path / "spawn-attribution.jsonl"
    monkeypatch.setattr("src.keiracom_system.attribution.logger.DEFAULT_ATTRIBUTION_LOG", log_path)
    entry = _spawn_attribution.emit(
        {
            "from": "atlas",
            "task_ref": "PR-1199-cleanup",
        },
        callsign="atlas",
        enabled=True,
    )
    assert entry is not None
    assert entry.source_type == "pr"
    assert entry.task_type == "build"  # default for non-keyword task_ref


# ----- Telemetry failure fail-open -----


def test_emit_failure_does_not_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch log_spawn_attribution to raise; emit should swallow + return None."""

    def _boom(**_kwargs: Any) -> None:
        raise RuntimeError("simulated telemetry failure")

    monkeypatch.setattr("scripts.dispatcher._spawn_attribution.log_spawn_attribution", _boom)

    result = _spawn_attribution.emit(
        {"from": "atlas", "type": "task_dispatch"},
        callsign="atlas",
        enabled=True,
    )
    assert result is None  # fail-open
