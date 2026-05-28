"""Wave 3 — workflow-scoped recall wiring tests for src.dispatcher.main.

workflow_recall layers on top of Scout's spawn_recall (#1240): when both flags
are on and a spawn carries a workflow_id, spawn 1's prior-context block is
cached so spawn 2..N reuse it without re-running the Hindsight query. Covers:
default-off no-op, cache-hit reuse (query fires once), blank workflow_id no-op,
spawn_recall-off short-circuit, env injection, and fail-open.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.tmux_lifecycle import SessionHandle
from src.retrieval.spawn_recall import PRIOR_CONTEXT_ENV_KEY


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


def _spawn(client: TestClient, key: str, spawn_kwargs: dict) -> Any:
    return client.post(
        "/dispatcher/spawn",
        json={"backend": "tmux", "key": key, "spawn_kwargs": spawn_kwargs},
    )


def _prep(monkeypatch: pytest.MonkeyPatch, *, spawn_recall: bool, workflow_recall: bool) -> Any:
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://fake/db")
    import src.dispatcher.main as main_mod

    monkeypatch.setattr(main_mod, "spawn_recall_enabled", spawn_recall)
    monkeypatch.setattr(main_mod, "workflow_recall_enabled", workflow_recall)
    main_mod._workflow_recall.clear()
    _mock_supervisors(main_mod)
    return main_mod


def test_disabled_workflow_recall_no_response_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """spawn_recall on, workflow_recall off → fresh recall every spawn, no cache key."""
    main_mod = _prep(monkeypatch, spawn_recall=True, workflow_recall=False)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
        patch("src.retrieval.spawn_recall.query_for_spawn", return_value=["[a · Keis] hello"]) as q,
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        r1 = _spawn(client, "k1", {"workflow_id": "wf-1", "brief": "do x"})
        r2 = _spawn(client, "k2", {"workflow_id": "wf-1", "brief": "do x"})

    assert r1.status_code == 200 and r2.status_code == 200
    assert "workflow_recall" not in r1.json()
    assert q.call_count == 2  # no cache → re-queried each spawn


def test_spawn2_reuses_spawn1_recall(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both flags on, same workflow_id → query fires once; spawn 2 is cached."""
    main_mod = _prep(monkeypatch, spawn_recall=True, workflow_recall=True)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
        patch(
            "src.retrieval.spawn_recall.query_for_spawn",
            return_value=["[DEC-7 · Decisions] ratified hybrid recall"],
        ) as q,
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        r1 = _spawn(client, "k1", {"workflow_id": "wf-1", "brief": "step 1", "callsign": "atlas"})
        r2 = _spawn(client, "k2", {"workflow_id": "wf-1", "brief": "step 2", "callsign": "orion"})

    assert r1.status_code == 200 and r2.status_code == 200
    assert q.call_count == 1  # spawn 2 reused spawn 1's recall — no re-query
    wr1, wr2 = r1.json()["workflow_recall"], r2.json()["workflow_recall"]
    assert wr1["cached"] is False
    assert wr2["cached"] is True
    assert wr1["context_tokens"] > 0


def test_blank_workflow_id_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both flags on but no workflow_id → fresh per-spawn, no cache key."""
    main_mod = _prep(monkeypatch, spawn_recall=True, workflow_recall=True)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
        patch("src.retrieval.spawn_recall.query_for_spawn", return_value=["[a · Keis] x"]) as q,
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        r1 = _spawn(client, "k1", {"brief": "no workflow"})
        _spawn(client, "k2", {"brief": "no workflow"})

    assert "workflow_recall" not in r1.json()
    assert q.call_count == 2  # no workflow scope → no caching


def test_spawn_recall_off_short_circuits_workflow_recall(monkeypatch: pytest.MonkeyPatch) -> None:
    """workflow_recall only layers on spawn_recall — off means it never engages."""
    main_mod = _prep(monkeypatch, spawn_recall=False, workflow_recall=True)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
        patch("src.retrieval.spawn_recall.query_for_spawn") as q,
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = _spawn(client, "k1", {"workflow_id": "wf-1", "brief": "x"})

    assert resp.status_code == 200
    assert "workflow_recall" not in resp.json()
    assert q.call_count == 0  # spawn_recall off → no recall at all


def test_cached_block_injected_into_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reused block lands in env[PRIOR_CONTEXT_ENV_KEY] for spawn 2, same as spawn 1."""
    main_mod = _prep(monkeypatch, spawn_recall=True, workflow_recall=True)
    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
        patch("src.retrieval.spawn_recall.query_for_spawn", return_value=["[a · Keis] shared"]),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        _spawn(client, "k1", {"workflow_id": "wf-1", "brief": "s1"})
        _spawn(client, "k2", {"workflow_id": "wf-1", "brief": "s2"})

        # spawn 2's forwarded kwargs carry the cached prior-context block.
        forwarded = MockSM.return_value.spawn.call_args.kwargs
        assert PRIOR_CONTEXT_ENV_KEY in forwarded.get("env", {})
        assert "shared" in forwarded["env"][PRIOR_CONTEXT_ENV_KEY]
        # workflow_id is preserved (not stripped) in the forwarded kwargs.
        assert forwarded["workflow_id"] == "wf-1"


def test_recall_failure_does_not_block_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """query_for_spawn raising → spawn still succeeds, empty block (fail-open)."""
    main_mod = _prep(monkeypatch, spawn_recall=True, workflow_recall=True)

    def boom(*_a: Any, **_k: Any) -> list[str]:
        raise RuntimeError("hindsight down")

    with (
        patch("src.dispatcher.main.SessionManager") as MockSM,
        patch.object(main_mod, "_register_session"),
        patch("src.retrieval.spawn_recall.query_for_spawn", side_effect=boom),
    ):
        MockSM.return_value.spawn.return_value = _make_handle()
        client = TestClient(main_mod.app, raise_server_exceptions=False)
        resp = _spawn(client, "k1", {"workflow_id": "wf-err", "brief": "x"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["spawned"] is True
    assert resp.json()["workflow_recall"]["context_tokens"] == 0
