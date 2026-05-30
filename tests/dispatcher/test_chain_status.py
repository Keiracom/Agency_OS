"""Tests for GET /dispatcher/chain_status (V1 chain live status + cost view).

State source = v1_chain_orchestrator's STATE_FILE (path is monkeypatched per
test via the V1_CHAIN_STATE_FILE env var); cost-sum DB layer is monkeypatched
to avoid touching live Supabase. Fail-open behaviour is the key contract —
no leg can 500 the endpoint.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException  # noqa: F401 — kept for parity with other dispatcher tests

from src.dispatcher import main

# ---------------------------------------------------------------------------
# _load_chain_state — state-file loader (fail-open by design)
# ---------------------------------------------------------------------------


def test_load_chain_state_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("V1_CHAIN_STATE_FILE", str(tmp_path / "nope.json"))
    assert main._load_chain_state() == {}


def test_load_chain_state_returns_dict_when_valid(tmp_path, monkeypatch):
    state = {
        "c1": {"chain_id": "c1", "task_id": "t1", "current_step": "aiden_plan", "started_ts": 1.0}
    }
    p = tmp_path / "state.json"
    p.write_text(json.dumps(state))
    monkeypatch.setenv("V1_CHAIN_STATE_FILE", str(p))
    assert main._load_chain_state() == state


def test_load_chain_state_returns_empty_on_malformed_json(tmp_path, monkeypatch):
    p = tmp_path / "bad.json"
    p.write_text("{not-json")
    monkeypatch.setenv("V1_CHAIN_STATE_FILE", str(p))
    assert main._load_chain_state() == {}


def test_load_chain_state_returns_empty_on_non_dict_json(tmp_path, monkeypatch):
    """A list/string at the top level → fail-open to {} (defensive)."""
    p = tmp_path / "list.json"
    p.write_text("[]")
    monkeypatch.setenv("V1_CHAIN_STATE_FILE", str(p))
    assert main._load_chain_state() == {}


# ---------------------------------------------------------------------------
# _chain_cost_aud — DSN guard + USD→AUD conversion + fail-open
# ---------------------------------------------------------------------------


def test_chain_cost_aud_zero_when_dsn_unset(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_DSN", raising=False)
    assert asyncio.run(main._chain_cost_aud("c1", "t1")) == 0.0


def _patch_asyncpg(monkeypatch, *, fetchrow_return=None, connect_raises=None):
    class _FakeConn:
        async def fetchrow(self, query, *args):
            return fetchrow_return

        async def close(self):
            pass

    async def fake_connect(dsn):
        if connect_raises is not None:
            raise connect_raises
        return _FakeConn()

    monkeypatch.setattr("asyncpg.connect", fake_connect)


def test_chain_cost_aud_converts_usd_sum_to_aud(monkeypatch):
    """SUM(cost_usd) = 2.0 → 2.0 × 1.55 = 3.10 AUD (LAW II)."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://u:p@h/db")
    _patch_asyncpg(monkeypatch, fetchrow_return={"s": 2.0})
    out = asyncio.run(main._chain_cost_aud("c1", "t1"))
    assert out == pytest.approx(3.10)


def test_chain_cost_aud_handles_zero_sum(monkeypatch):
    """SUM returns 0.0 (no matching rows) → 0.0 AUD."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://u:p@h/db")
    _patch_asyncpg(monkeypatch, fetchrow_return={"s": 0.0})
    assert asyncio.run(main._chain_cost_aud("c1", "t1")) == 0.0


def test_chain_cost_aud_fail_open_on_db_error(monkeypatch):
    """asyncpg.connect raises → 0.0, no exception escapes."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://u:p@h/db")
    _patch_asyncpg(monkeypatch, connect_raises=OSError("db unreachable"))
    assert asyncio.run(main._chain_cost_aud("c1", "t1")) == 0.0


def test_chain_cost_aud_strips_asyncpg_suffix(monkeypatch):
    """DSN with +asyncpg suffix is stripped before connect."""
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql+asyncpg://u:p@h/db")
    captured: dict = {}

    class _FakeConn:
        async def fetchrow(self, query, *args):
            captured["query"] = query
            captured["args"] = args
            return {"s": 1.0}

        async def close(self):
            pass

    async def fake_connect(dsn):
        captured["dsn"] = dsn
        return _FakeConn()

    monkeypatch.setattr("asyncpg.connect", fake_connect)

    asyncio.run(main._chain_cost_aud("c1", "t1"))
    assert "+asyncpg" not in captured["dsn"]
    # source_id heuristic — query filters via ANY($1::text[]) with [chain_id, task_id].
    assert captured["args"][0] == ["c1", "t1"]


# ---------------------------------------------------------------------------
# /dispatcher/chain_status route — response shape + fail-open
# ---------------------------------------------------------------------------


def test_dispatcher_chain_status_empty_when_no_state(monkeypatch):
    monkeypatch.setattr(main, "_load_chain_state", lambda: {})
    resp = asyncio.run(main.dispatcher_chain_status())
    assert resp == {"chains": []}


def test_dispatcher_chain_status_returns_chain_row(monkeypatch):
    """Single active chain → response carries state fields + per-hop cost."""
    monkeypatch.setattr(
        main,
        "_load_chain_state",
        lambda: {
            "c-abc": {
                "chain_id": "c-abc",
                "task_id": "t-abc",
                "current_step": "max_challenge",
                "steps_done": ["aiden_plan"],
                "started_ts": 1780000000.5,
            }
        },
    )

    async def fake_cost(chain_id, task_id):
        return 5.50

    monkeypatch.setattr(main, "_chain_cost_aud", fake_cost)

    resp = asyncio.run(main.dispatcher_chain_status())
    assert resp["chains"] == [
        {
            "chain_id": "c-abc",
            "current_step": "max_challenge",
            "steps_done": ["aiden_plan"],
            "started_ts": 1780000000.5,
            "cost_aud_so_far": 5.50,
            "latency_ms_so_far": 0.0,
        }
    ]


def test_dispatcher_chain_status_skips_non_dict_chain_values(monkeypatch):
    """Defensive: a state with garbage values (e.g. legacy/corrupt) yields []
    rather than 500."""
    monkeypatch.setattr(main, "_load_chain_state", lambda: {"bad": "not-a-dict"})

    async def fake_cost(chain_id, task_id):
        return 0.0

    monkeypatch.setattr(main, "_chain_cost_aud", fake_cost)

    resp = asyncio.run(main.dispatcher_chain_status())
    assert resp == {"chains": []}


def test_dispatcher_chain_status_multiple_chains(monkeypatch):
    monkeypatch.setattr(
        main,
        "_load_chain_state",
        lambda: {
            "c1": {"chain_id": "c1", "current_step": "aiden_plan", "started_ts": 1.0},
            "c2": {"chain_id": "c2", "current_step": "atlas_safety", "started_ts": 2.0},
        },
    )

    async def fake_cost(chain_id, task_id):
        return {"c1": 1.0, "c2": 2.5}[chain_id]

    monkeypatch.setattr(main, "_chain_cost_aud", fake_cost)

    resp = asyncio.run(main.dispatcher_chain_status())
    by_id = {c["chain_id"]: c for c in resp["chains"]}
    assert by_id["c1"]["cost_aud_so_far"] == 1.0
    assert by_id["c2"]["cost_aud_so_far"] == 2.5
    assert by_id["c1"]["current_step"] == "aiden_plan"
    assert by_id["c2"]["current_step"] == "atlas_safety"
