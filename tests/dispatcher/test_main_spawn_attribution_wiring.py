"""KEI-213 — spawn attribution + per-task-type wiring tests for src.dispatcher.main.

Covers cutover-step-4.5 wiring of PR #1207 (spawn attribution) + PR #1209
(per-task-type telemetry extension) into /dispatcher/spawn.

bd: cutover-step-4.5-dispatcher-wiring-pr-D (KEI-213 mirror of PR #1220)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.tmux_lifecycle import SessionHandle


def _mock_supervisors(main_mod: Any) -> None:
    main_mod._watchdog = MagicMock()
    main_mod._reaper = MagicMock()
    main_mod._reaper.health_snapshot.return_value = {
        "tracked_tmux": 0,
        "tracked_containers": 0,
    }
    main_mod._watchdog.tracked = 0


def _make_handle() -> SessionHandle:
    return SessionHandle(session_name="disp-test", working_dir="/tmp", command="claude")


# ----- disabled fail-open -----


def test_disabled_no_jsonl_emit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """attribution_enabled=False → no JSONL entry written."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    monkeypatch.setattr(main_mod, "attribution_enabled", False)
    log_path = tmp_path / "spawn-attribution.jsonl"
    monkeypatch.setattr("src.keiracom_system.attribution.logger.DEFAULT_ATTRIBUTION_LOG", log_path)

    _mock_supervisors(main_mod)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn",
            json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}},
        )

    assert resp.status_code == 200
    assert not log_path.exists()


# ----- enabled writes JSONL -----


def test_enabled_writes_jsonl_after_spawn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """attribution_enabled=True → log_spawn_attribution called after register."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    monkeypatch.setattr(main_mod, "attribution_enabled", True)
    log_path = tmp_path / "spawn-attribution.jsonl"
    monkeypatch.setattr("src.keiracom_system.attribution.logger.DEFAULT_ATTRIBUTION_LOG", log_path)

    _mock_supervisors(main_mod)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn",
            json={
                "backend": "tmux",
                "key": "REVIEW-PR-1199",
                "spawn_kwargs": {"from": "elliot", "callsign": "orion"},
            },
        )

    assert resp.status_code == 200
    assert log_path.exists()
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["source_type"] == "inbox"  # from elliot → not dave/cron → inbox
    assert entry["task_type"] == "pr_review"  # REVIEW-PR key → pr_review
    assert entry["callsign"] == "orion"
    assert entry["source_id"] == "REVIEW-PR-1199"
    assert entry["model"] == "claude-sonnet-4-6"


# ----- source_type derivation -----


@pytest.mark.parametrize(
    "spawn_kwargs,expected",
    [
        ({"source_type": "slack"}, "slack"),
        ({"source_type": "cron"}, "cron"),
        ({"source_type": "pr"}, "pr"),
        ({"source_type": "unknown"}, "unknown"),
        ({"source_type": "bogus"}, "inbox"),  # invalid → fallback
        ({"from": "dave"}, "slack"),
        ({"from": "cron"}, "cron"),
        ({"from": "scheduler"}, "cron"),
        ({}, "inbox"),
        ({"from": "atlas"}, "inbox"),
    ],
)
def test_source_type_derivation(spawn_kwargs: dict, expected: str) -> None:
    import src.dispatcher.main as main_mod

    assert main_mod._spawn_kwargs_source_type(spawn_kwargs) == expected


# ----- task_type derivation -----


@pytest.mark.parametrize(
    "spawn_kwargs,registry_key,expected",
    [
        ({"task_type": "pr_review"}, "k1", "pr_review"),
        ({"task_type": "deliberation"}, "k1", "deliberation"),
        ({"task_type": "build"}, "k1", "build"),
        ({"task_type": "chat"}, "k1", "chat"),
        ({"task_type": "dispatch_mgmt"}, "k1", "dispatch_mgmt"),
        ({"task_type": "bogus"}, "k1", "build"),  # invalid → fallback
        ({}, "REVIEW-PR-1199", "pr_review"),
        ({}, "PR-REVIEW-1199", "pr_review"),
        ({}, "DELIBERATE-arch-v2", "deliberation"),
        ({}, "DELIBERATION-arch-v2", "deliberation"),
        ({}, "DISPATCH-rebase", "dispatch_mgmt"),
        ({"from": "dave"}, "any-key", "chat"),
        ({}, "any-key", "build"),  # default
        ({"from": "atlas"}, "k1", "build"),
    ],
)
def test_task_type_derivation(spawn_kwargs: dict, registry_key: str, expected: str) -> None:
    import src.dispatcher.main as main_mod

    assert main_mod._spawn_kwargs_task_type(spawn_kwargs, registry_key) == expected


# ----- telemetry failure fail-open -----


def test_telemetry_failure_does_not_block_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """log_spawn_attribution raises → spawn still succeeds with empty audit."""
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    monkeypatch.setattr(main_mod, "attribution_enabled", True)

    def _boom(**_kwargs: Any) -> None:
        raise RuntimeError("simulated telemetry failure")

    monkeypatch.setattr("src.dispatcher.main.log_spawn_attribution", _boom)

    _mock_supervisors(main_mod)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = client.post(
            "/dispatcher/spawn",
            json={"backend": "tmux", "key": "k1", "spawn_kwargs": {}},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["spawned"] is True  # spawn still completed
