"""Tests for src.keiracom_system.chain.v1_chain_orchestrator.

Covers:
  - dispatch(): first-hop HTTP publish + state persistence + fail-open on error
  - advance_step(): sequential steps, parallel fan-out, partial-parallel wait,
    and final parallel completion → complete
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import src.keiracom_system.chain.v1_chain_orchestrator as orch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_nats_module(*, connect_raises: Exception | None = None) -> types.ModuleType:
    """Build a fake nats module that records published envelopes."""
    published: list[tuple[str, bytes]] = []

    async def _connect(*args, **kwargs):
        if connect_raises is not None:
            raise connect_raises
        nc = AsyncMock()
        nc.published = published

        async def _publish(subject: str, payload: bytes):
            published.append((subject, payload))

        nc.publish = _publish
        nc.flush = AsyncMock()
        nc.close = AsyncMock()
        return nc

    mod = types.ModuleType("nats")
    mod.connect = _connect
    mod.published = published
    return mod


def _seed_state(tmp_path: Path, chain_id: str, entry: dict) -> None:
    """Write a state file with a single entry for testing advance_step."""
    state = {chain_id: entry}
    state_file = tmp_path / "v1_chain_state.json"
    state_file.write_text(json.dumps(state))


def _capture_publishes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[dict, str]]:
    """Monkeypatch orch._publish_envelope to capture (envelope, role) pairs in
    place of an HTTP POST. Tests use this instead of a transport-level mock so
    they verify the orchestrator's dispatch surface, not the urllib layer.
    The transport itself (the HTTP POST to /dispatcher/spawn) has its own
    dedicated integration test.
    """
    captured: list[tuple[dict, str]] = []

    def _fake_publish(envelope: dict, role: str) -> bool:
        captured.append((envelope, role))
        return True

    monkeypatch.setattr(
        "src.keiracom_system.chain.v1_chain_orchestrator._publish_envelope", _fake_publish
    )
    return captured


# ---------------------------------------------------------------------------
# dispatch() tests
# ---------------------------------------------------------------------------


def test_dispatch_first_hop_publishes_aiden_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """dispatch() must publish one envelope to aiden."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = orch.dispatch({"id": "t1", "brief": "hello"}, clock=lambda: 1.0)

    assert len(captured) == 1
    envelope, role = captured[0]
    assert role == "aiden"

    assert envelope["chain_step"] == "aiden_plan"
    assert envelope["atom_id"] is None
    assert envelope["brief"] == "hello"
    assert envelope["task_id"] == "t1"
    assert envelope["chain_id"] == chain_id
    assert envelope["from"] == "v1_chain_orchestrator"
    assert envelope["ts"] == 1.0


def test_dispatch_persists_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """dispatch() must persist chain state with correct initial values."""
    _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = orch.dispatch({"id": "t2", "brief": "do something"})

    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert chain_id in state
    entry = state[chain_id]
    assert entry["current_step"] == "aiden_plan"
    assert entry["steps_done"] == []
    assert entry["atom_ids"] == {}


def test_dispatch_fail_open_on_publish_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Dispatch must still return a chain_id and persist state when the
    /dispatcher/spawn HTTP POST fails — fail-open on transport errors."""
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)
    # Stub _publish_envelope to simulate HTTP failure.
    monkeypatch.setattr(
        "src.keiracom_system.chain.v1_chain_orchestrator._publish_envelope",
        lambda envelope, role: False,
    )
    cid = orch.dispatch({"id": "fail-task", "brief": "x"})
    assert cid  # chain_id still returned despite publish failure
    state = json.loads(state_file.read_text())
    assert "fail-task" in state  # state persisted


# ---------------------------------------------------------------------------
# advance_step() — sequential
# ---------------------------------------------------------------------------


def test_advance_step_aiden_to_max(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """aiden_plan → max_challenge: one envelope to max."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-aiden-max"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-am",
            "brief": "plan it",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )

    envelopes = orch.advance_step(chain_id, "aiden_plan", "atom-abc", clock=lambda: 2.0)

    assert len(envelopes) == 1
    assert len(captured) == 1
    envelope, role = captured[0]
    assert role == "max"

    env = envelopes[0]
    assert env["chain_step"] == "max_challenge"
    assert env["atom_id"] == "atom-abc"

    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert entry["current_step"] == "max_challenge"
    assert entry["steps_done"] == ["aiden_plan"]
    assert entry["atom_ids"] == {"aiden_plan": "atom-abc"}


def test_advance_step_max_to_nova(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """max_challenge → nova_build: one envelope to nova with max's atom."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-max-nova"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-mn",
            "brief": "build it",
            "started_ts": 0.0,
            "current_step": "max_challenge",
            "steps_done": ["aiden_plan"],
            "atom_ids": {"aiden_plan": "atom-aiden"},
            "pending": [],
        },
    )

    envelopes = orch.advance_step(chain_id, "max_challenge", "atom-max", clock=lambda: 3.0)

    assert len(envelopes) == 1
    envelope, role = captured[0]
    assert role == "nova"

    env = envelopes[0]
    assert env["chain_step"] == "nova_build"
    assert env["atom_id"] == "atom-max"


# ---------------------------------------------------------------------------
# advance_step() — parallel fan-out
# ---------------------------------------------------------------------------


def test_advance_step_nova_to_dual_orion_atlas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """nova_build fans out to orion_spec + atlas_safety simultaneously."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-nova-parallel"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-np",
            "brief": "spec+safety",
            "started_ts": 0.0,
            "current_step": "nova_build",
            "steps_done": ["aiden_plan", "max_challenge"],
            "atom_ids": {"aiden_plan": "atom-a", "max_challenge": "atom-m"},
            "pending": [],
        },
    )

    envelopes = orch.advance_step(chain_id, "nova_build", "atom-nova", clock=lambda: 4.0)

    assert len(envelopes) == 2
    roles = {r for _, r in captured}
    assert roles == {"orion", "atlas"}

    for env in envelopes:
        assert env["atom_id"] == "atom-nova"

    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert set(entry["pending"]) == {"orion_spec", "atlas_safety"}


def test_advance_step_orion_done_waits_for_atlas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """After orion completes, atlas is still pending — no new dispatch."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-orion-wait"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-ow",
            "brief": "waiting",
            "started_ts": 0.0,
            "current_step": "orion_spec",
            "steps_done": ["aiden_plan", "max_challenge", "nova_build"],
            "atom_ids": {
                "aiden_plan": "a1",
                "max_challenge": "a2",
                "nova_build": "a3",
            },
            "pending": ["orion_spec", "atlas_safety"],
        },
    )

    envelopes = orch.advance_step(chain_id, "orion_spec", "atom-orion")

    assert envelopes == []
    assert len(captured) == 0

    state = json.loads(state_file.read_text())
    assert state[chain_id]["pending"] == ["atlas_safety"]


def test_advance_step_atlas_done_completes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When atlas is last parallel partner, chain reaches complete — no dispatch."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-atlas-complete"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-ac",
            "brief": "finishing",
            "started_ts": 0.0,
            "current_step": "atlas_safety",
            "steps_done": ["aiden_plan", "max_challenge", "nova_build", "orion_spec"],
            "atom_ids": {
                "aiden_plan": "a1",
                "max_challenge": "a2",
                "nova_build": "a3",
                "orion_spec": "a4",
            },
            "pending": ["atlas_safety"],
        },
    )

    envelopes = orch.advance_step(chain_id, "atlas_safety", "atom-atlas")

    assert envelopes == []
    assert len(captured) == 0

    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert entry["current_step"] == "complete"
    assert entry["pending"] == []


# ─── Edge cases (Max HOLD on PR #1329) ────────────────────────────────────────


def test_advance_step_unknown_chain_id_returns_empty_and_logs_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Unknown chain_id: return [], log error, no publish."""
    import logging

    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    with caplog.at_level(logging.ERROR):
        envelopes = orch.advance_step("does-not-exist", "aiden_plan", "atom-x")

    assert envelopes == []
    assert len(captured) == 0
    assert "unknown chain_id=does-not-exist" in caplog.text


def test_advance_step_duplicate_completion_no_double_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Duplicate advance_step for the same completed_step must not re-dispatch downstream."""
    import logging

    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-dup"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-dup",
            "brief": "dup test",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )

    first = orch.advance_step(chain_id, "aiden_plan", "atom-1", clock=lambda: 1.0)
    assert len(first) == 1
    assert len(captured) == 1  # max_challenge dispatched once
    state_after_first = json.loads(state_file.read_text())[chain_id]

    with caplog.at_level(logging.WARNING):
        second = orch.advance_step(chain_id, "aiden_plan", "atom-1-again", clock=lambda: 2.0)

    assert second == []
    assert len(captured) == 1  # NOT re-dispatched
    assert "duplicate completed_step=aiden_plan" in caplog.text
    # State unchanged by the second call.
    state_after_second = json.loads(state_file.read_text())[chain_id]
    assert state_after_second == state_after_first


def test_advance_step_unrecognized_step_returns_empty_and_logs_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Step not in PARALLEL_AFTER_STEP, not in _SEQ_NEXT, pending empty: [] + warning."""
    import logging

    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-bogus"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-b",
            "brief": "bogus step",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )

    with caplog.at_level(logging.WARNING):
        envelopes = orch.advance_step(chain_id, "garbage_step", "atom-g")

    assert envelopes == []
    assert len(captured) == 0
    assert "no known next for completed_step=garbage_step" in caplog.text


# ─── Final #ceo post on complete (Agency_OS-zqni) ─────────────────────────────


def test_advance_step_final_post_fires_on_chain_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """When the last parallel partner completes, _post_chain_complete is called once."""
    _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    posts: list[tuple] = []
    monkeypatch.setattr(
        orch, "_post_chain_complete", lambda entry, chain_id: posts.append((entry, chain_id))
    )

    chain_id = "chain-final-post"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-zq",
            "brief": "wire X to Y",
            "started_ts": 0.0,
            "current_step": "atlas_safety",
            "steps_done": ["aiden_plan", "max_challenge", "nova_build", "orion_spec"],
            "atom_ids": {
                "aiden_plan": "a1",
                "max_challenge": "a2",
                "nova_build": "a3",
                "orion_spec": "a4",
            },
            "pending": ["atlas_safety"],
        },
    )

    orch.advance_step(chain_id, "atlas_safety", "atom-atlas")

    assert len(posts) == 1
    entry, posted_chain_id = posts[0]
    assert posted_chain_id == chain_id
    assert entry["task_id"] == "t-zq"
    assert entry["brief"] == "wire X to Y"
    assert entry["current_step"] == "complete"


def test_advance_step_intermediate_does_not_post_to_ceo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Intermediate transitions (e.g. aiden_plan → max_challenge) must NOT post to #ceo."""
    _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    posts: list = []

    def boom_post(_entry, _chain_id):
        posts.append(True)
        raise AssertionError("_post_chain_complete MUST NOT be called for intermediate steps")

    monkeypatch.setattr(orch, "_post_chain_complete", boom_post)

    chain_id = "chain-intermediate"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-int",
            "brief": "in flight",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )

    orch.advance_step(chain_id, "aiden_plan", "atom-aiden", clock=lambda: 2.0)

    assert posts == []  # final post never invoked


def test_advance_step_final_post_failure_does_not_break_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A raising _post_chain_complete must NOT abort advance_step (fail-open guard)."""
    _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    def boom_post(_entry, _chain_id):
        raise RuntimeError("slack down")

    monkeypatch.setattr(orch, "_post_chain_complete", boom_post)

    chain_id = "chain-failopen"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-fo",
            "brief": "fail-open",
            "started_ts": 0.0,
            "current_step": "atlas_safety",
            "steps_done": ["aiden_plan", "max_challenge", "nova_build", "orion_spec"],
            "atom_ids": {
                "aiden_plan": "a1",
                "max_challenge": "a2",
                "nova_build": "a3",
                "orion_spec": "a4",
            },
            "pending": ["atlas_safety"],
        },
    )

    # Must NOT raise even though _post_chain_complete blows up.
    envelopes = orch.advance_step(chain_id, "atlas_safety", "atom-atlas")

    assert envelopes == []  # no further dispatch on complete
    state = json.loads(state_file.read_text())
    assert state[chain_id]["current_step"] == "complete"  # state still saved


def test_advance_step_async_consumer_path_fires_post_chain_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Aiden HOLD: the consumer-loop async path MUST also fire _post_chain_complete.

    Asserts the async _advance_step_async delegates through to the sync code
    path so the chain-complete post is guaranteed to fire — eliminates the
    parallel-implementation divergence bug class Aiden caught.
    """
    import asyncio

    _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    posts: list = []
    monkeypatch.setattr(
        orch, "_post_chain_complete", lambda entry, chain_id: posts.append((entry, chain_id))
    )

    chain_id = "chain-async-complete"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-async",
            "brief": "async complete",
            "started_ts": 0.0,
            "current_step": "atlas_safety",
            "steps_done": ["aiden_plan", "max_challenge", "nova_build", "orion_spec"],
            "atom_ids": {
                "aiden_plan": "a1",
                "max_challenge": "a2",
                "nova_build": "a3",
                "orion_spec": "a4",
            },
            "pending": ["atlas_safety"],
        },
    )

    asyncio.run(orch._advance_step_async(chain_id, "atlas_safety", "atom-atlas"))

    assert len(posts) == 1  # consumer-loop path fired the chain-complete post
    entry, posted_chain_id = posts[0]
    assert posted_chain_id == chain_id
    assert entry["task_id"] == "t-async"
    assert entry["current_step"] == "complete"


# ─── Consumer loop additions (Agency_OS-oevr) ─────────────────────────────────


def test_from_to_step_covers_all_chain_workers():
    """FROM_TO_STEP must map every callsign that completes a chain step."""
    assert set(orch.FROM_TO_STEP.values()) == {
        "aiden_plan",
        "max_challenge",
        "nova_build",
        "orion_spec",
        "atlas_safety",
    }


def test_dispatch_chain_id_defaults_to_task_id_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """When task carries an id and no chain_id is passed, chain_id == task['id']
    so consumer's advance_step(chain_id=msg.task_id) resolves."""
    _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)
    cid = orch.dispatch({"id": "task-abc-123", "brief": "x"})
    assert cid == "task-abc-123"
    state = json.loads(state_file.read_text())
    assert "task-abc-123" in state


async def test_consumer_handle_envelope_async_advances_aiden_to_max(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Async helper (Max HOLD shape): pass a dict, get back the list of
    dispatched envelopes. Aiden handoff → dispatch to max."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)
    chain_id = "task-cons-1"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": chain_id,
            "brief": "plan it",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )
    envelope = {"task_id": chain_id, "atom_id": "atom-aiden", "from_callsign": "aiden"}
    dispatched = await orch._consumer_handle_envelope_async(envelope)
    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "max_challenge"
    assert dispatched[0]["atom_id"] == "atom-aiden"
    assert len(captured) == 1
    env, role = captured[0]
    assert role == "max"


async def test_consumer_handle_envelope_async_unknown_callsign_skips(
    caplog: pytest.LogCaptureFixture,
):
    """Unknown from_callsign: returns [], logs warning, no dispatch."""
    import logging

    envelope = {"task_id": "t-x", "atom_id": "a", "from_callsign": "facehugger"}
    with caplog.at_level(logging.WARNING):
        dispatched = await orch._consumer_handle_envelope_async(envelope)
    assert dispatched == []
    assert "unknown from_callsign=facehugger" in caplog.text


async def test_consumer_handle_envelope_async_missing_fields_skips(
    caplog: pytest.LogCaptureFixture,
):
    """Missing task_id or from_callsign: returns [], logs warning."""
    import logging

    envelope = {"atom_id": "a"}
    with caplog.at_level(logging.WARNING):
        dispatched = await orch._consumer_handle_envelope_async(envelope)
    assert dispatched == []
    assert "missing task_id/from_callsign" in caplog.text


async def test_consumer_handle_envelope_async_failopen_on_bad_envelope(
    caplog: pytest.LogCaptureFixture,
):
    """Non-dict envelope (e.g. None): returns [], logs warning, never raises."""
    import logging

    with caplog.at_level(logging.WARNING):
        dispatched = await orch._consumer_handle_envelope_async(None)  # type: ignore[arg-type]
    assert dispatched == []
    assert "handler error" in caplog.text


# ---------------------------------------------------------------------------
# HTTP transport integration tests
# ---------------------------------------------------------------------------


def test_publish_envelope_posts_to_dispatcher_spawn_with_correct_body(
    monkeypatch: pytest.MonkeyPatch,
):
    """Integration test: _publish_envelope POSTs to /dispatcher/spawn with the
    spawn_kwargs spec'd by Elliot for Option B. Mocks urllib.urlopen + asserts:
      - URL ends with /dispatcher/spawn
      - body is JSON: {backend, key:<chain-<chain_id>-<chain_step>>, spawn_kwargs:{role, callsign, tier:'standard', variant, brief, chain_step, chain_id, task_id, atom_id}}
      - returns True on 2xx
    """
    import json
    import urllib.request

    captured: dict = {}

    class _FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data)
        captured["method"] = req.get_method()
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    envelope = {
        "task_id": "t-1",
        "chain_id": "chain-1",
        "chain_step": "max_challenge",
        "atom_id": "atom-aiden",
        "brief": "build it",
        "ts": 1.0,
        "from": "v1_chain_orchestrator",
    }
    ok = orch._publish_envelope(envelope, "max")

    assert ok is True
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/dispatcher/spawn")
    body = captured["body"]
    assert body["backend"] == "tmux"
    assert body["key"] == "chain-chain-1-max_challenge"
    sk = body["spawn_kwargs"]
    assert sk["role"] == "max"
    assert sk["callsign"] == "max"
    assert sk["tier"] == "standard"
    assert sk["variant"] == "max"
    assert sk["brief"] == "build it"
    assert sk["chain_step"] == "max_challenge"
    assert sk["chain_id"] == "chain-1"
    assert sk["task_id"] == "t-1"
    assert sk["atom_id"] == "atom-aiden"


def test_publish_envelope_failopen_on_http_error(monkeypatch: pytest.MonkeyPatch):
    """_publish_envelope returns False (not raises) when urlopen errors."""
    import urllib.error
    import urllib.request

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    ok = orch._publish_envelope({"chain_id": "x", "chain_step": "y", "brief": "z"}, "max")
    assert ok is False


# ---------------------------------------------------------------------------
# V1-battery Gate 1 — per-task A$10 spend ceiling
# (Elliot dispatch 2026-05-30 ~11:35 AEST)
# ---------------------------------------------------------------------------


def test_query_task_cost_aud_returns_none_on_empty_task_id():
    """Empty task_id → None (caller treats as 'couldn't check', fail-open)."""
    assert orch._query_task_cost_aud("") is None


def test_advance_step_halts_when_ceiling_breached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """SUM(cost_aud) > A$10 → chain halts: state.current_step='halted_ceiling_exceeded',
    ceiling_tripped=True, breach posted, ZERO new dispatches.
    """
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-ceiling-breach"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-runaway",
            "brief": "runaway",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )

    breach_calls: list[dict] = []

    def fake_post_breach(entry, cid, total, per_hop, *, dispatcher_url=None):
        breach_calls.append(
            {"chain_id": cid, "total": total, "per_hop": per_hop, "task_id": entry.get("task_id")}
        )

    monkeypatch.setattr(orch, "_post_ceiling_breach", fake_post_breach)
    # Simulate a query result over the A$10 ceiling.
    monkeypatch.setattr(
        orch,
        "_query_task_cost_aud",
        lambda _task_id: (
            12.34,
            [
                {"callsign": "aiden", "chain_step": "aiden_plan", "cost_aud": 12.34},
            ],
        ),
    )

    envelopes = orch.advance_step(chain_id, "aiden_plan", "atom-runaway", clock=lambda: 5.0)

    # Halt semantics — zero new dispatches, halt state recorded.
    assert envelopes == []
    assert captured == []
    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert entry["current_step"] == "halted_ceiling_exceeded"
    assert entry["ceiling_tripped"] is True
    assert entry["ceiling_total_aud"] == 12.34
    assert entry["ceiling_per_hop"][0]["chain_step"] == "aiden_plan"
    # Breach #ceo post must fire.
    assert len(breach_calls) == 1
    assert breach_calls[0]["chain_id"] == chain_id
    assert breach_calls[0]["task_id"] == "t-runaway"


def test_advance_step_proceeds_when_ceiling_not_breached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """SUM(cost_aud) ≤ A$10 → chain continues normally (one envelope to max)."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    chain_id = "chain-under-ceiling"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-cheap",
            "brief": "cheap run",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )
    monkeypatch.setattr(
        orch,
        "_query_task_cost_aud",
        lambda _task_id: (
            0.42,
            [{"callsign": "aiden", "chain_step": "aiden_plan", "cost_aud": 0.42}],
        ),
    )
    breach_fired = []
    monkeypatch.setattr(
        orch,
        "_post_ceiling_breach",
        lambda *a, **kw: breach_fired.append(True),
    )

    envelopes = orch.advance_step(chain_id, "aiden_plan", "atom-aiden", clock=lambda: 6.0)

    assert len(envelopes) == 1
    assert len(captured) == 1
    assert captured[0][1] == "max"
    assert not breach_fired
    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert entry["current_step"] == "max_challenge"
    assert entry.get("ceiling_tripped") is not True


def test_advance_step_fail_open_when_query_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Query read failure (None) → chain proceeds (fleet breaker is fail-SAFE backstop)."""
    captured = _capture_publishes(monkeypatch)
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)
    chain_id = "chain-query-fail"
    _seed_state(
        tmp_path,
        chain_id,
        {
            "chain_id": chain_id,
            "task_id": "t-unknown",
            "brief": "x",
            "started_ts": 0.0,
            "current_step": "aiden_plan",
            "steps_done": [],
            "atom_ids": {},
            "pending": [],
        },
    )
    monkeypatch.setattr(orch, "_query_task_cost_aud", lambda _task_id: None)
    envelopes = orch.advance_step(chain_id, "aiden_plan", "atom-x", clock=lambda: 7.0)
    # Fail-open: normal advance, NOT halted.
    assert len(envelopes) == 1
    assert len(captured) == 1
    state = json.loads(state_file.read_text())
    assert state[chain_id]["current_step"] == "max_challenge"
    assert state[chain_id].get("ceiling_tripped") is not True
