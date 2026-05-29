"""Tests for src.keiracom_system.chain.v1_chain_orchestrator.

Covers:
  - dispatch(): first-hop NATS publish + state persistence + fail-open on error
  - advance_step(): sequential steps, parallel fan-out, partial-parallel wait,
    and final parallel completion → complete
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

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


# ---------------------------------------------------------------------------
# dispatch() tests
# ---------------------------------------------------------------------------


def test_dispatch_first_hop_publishes_aiden_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """dispatch() must publish one envelope to keiracom.dispatch.aiden."""
    fake_nats = _fake_nats_module()
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    with patch.dict("sys.modules", {"nats": fake_nats}):
        chain_id = orch.dispatch({"id": "t1", "brief": "hello"}, clock=lambda: 1.0)

    assert len(fake_nats.published) == 1
    subject, payload = fake_nats.published[0]
    assert subject == "keiracom.dispatch.aiden"

    env = json.loads(payload)
    assert env["chain_step"] == "aiden_plan"
    assert env["atom_id"] is None
    assert env["brief"] == "hello"
    assert env["task_id"] == "t1"
    assert env["chain_id"] == chain_id
    assert env["from"] == "v1_chain_orchestrator"
    assert env["ts"] == 1.0


def test_dispatch_persists_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """dispatch() must persist chain state with correct initial values."""
    fake_nats = _fake_nats_module()
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    with patch.dict("sys.modules", {"nats": fake_nats}):
        chain_id = orch.dispatch({"id": "t2", "brief": "do something"})

    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert chain_id in state
    entry = state[chain_id]
    assert entry["current_step"] == "aiden_plan"
    assert entry["steps_done"] == []
    assert entry["atom_ids"] == {}


def test_dispatch_fail_open_on_nats_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """dispatch() must return a chain_id and persist state even when NATS connect raises."""
    fake_nats = _fake_nats_module(connect_raises=ConnectionRefusedError("no nats"))
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    with patch.dict("sys.modules", {"nats": fake_nats}):
        chain_id = orch.dispatch({"id": "t3", "brief": "fail-open test"})

    assert isinstance(chain_id, str) and chain_id  # did not raise
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert chain_id in state


# ---------------------------------------------------------------------------
# advance_step() — sequential
# ---------------------------------------------------------------------------


def test_advance_step_aiden_to_max(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """aiden_plan → max_challenge: one envelope to keiracom.dispatch.max."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        envelopes = orch.advance_step(chain_id, "aiden_plan", "atom-abc", clock=lambda: 2.0)

    assert len(envelopes) == 1
    assert len(fake_nats.published) == 1
    subject, payload = fake_nats.published[0]
    assert subject == "keiracom.dispatch.max"

    env = envelopes[0]
    assert env["chain_step"] == "max_challenge"
    assert env["atom_id"] == "atom-abc"

    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert entry["current_step"] == "max_challenge"
    assert entry["steps_done"] == ["aiden_plan"]
    assert entry["atom_ids"] == {"aiden_plan": "atom-abc"}


def test_advance_step_max_to_nova(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """max_challenge → nova_build: one envelope to keiracom.dispatch.nova with max's atom."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        envelopes = orch.advance_step(chain_id, "max_challenge", "atom-max", clock=lambda: 3.0)

    assert len(envelopes) == 1
    subject, payload = fake_nats.published[0]
    assert subject == "keiracom.dispatch.nova"

    env = envelopes[0]
    assert env["chain_step"] == "nova_build"
    assert env["atom_id"] == "atom-max"


# ---------------------------------------------------------------------------
# advance_step() — parallel fan-out
# ---------------------------------------------------------------------------


def test_advance_step_nova_to_dual_orion_atlas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """nova_build fans out to orion_spec + atlas_safety simultaneously."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        envelopes = orch.advance_step(chain_id, "nova_build", "atom-nova", clock=lambda: 4.0)

    assert len(envelopes) == 2
    subjects = {s for s, _ in fake_nats.published}
    assert "keiracom.dispatch.orion" in subjects
    assert "keiracom.dispatch.atlas" in subjects

    for env in envelopes:
        assert env["atom_id"] == "atom-nova"

    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert set(entry["pending"]) == {"orion_spec", "atlas_safety"}


def test_advance_step_orion_done_waits_for_atlas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """After orion completes, atlas is still pending — no new dispatch."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        envelopes = orch.advance_step(chain_id, "orion_spec", "atom-orion")

    assert envelopes == []
    assert len(fake_nats.published) == 0

    state = json.loads(state_file.read_text())
    assert state[chain_id]["pending"] == ["atlas_safety"]


def test_advance_step_atlas_done_completes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When atlas is last parallel partner, chain reaches complete — no dispatch."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        envelopes = orch.advance_step(chain_id, "atlas_safety", "atom-atlas")

    assert envelopes == []
    assert len(fake_nats.published) == 0

    state = json.loads(state_file.read_text())
    entry = state[chain_id]
    assert entry["current_step"] == "complete"
    assert entry["pending"] == []


# ─── Edge cases (Max HOLD on PR #1329) ────────────────────────────────────────


def test_advance_step_unknown_chain_id_returns_empty_and_logs_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Unknown chain_id: return [], log error, no NATS publish."""
    import logging

    fake_nats = _fake_nats_module()
    state_file = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_file)

    with patch.dict("sys.modules", {"nats": fake_nats}), caplog.at_level(logging.ERROR):
        envelopes = orch.advance_step("does-not-exist", "aiden_plan", "atom-x")

    assert envelopes == []
    assert len(fake_nats.published) == 0
    assert "unknown chain_id=does-not-exist" in caplog.text


def test_advance_step_duplicate_completion_no_double_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Duplicate advance_step for the same completed_step must not re-dispatch downstream."""
    import logging

    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        first = orch.advance_step(chain_id, "aiden_plan", "atom-1", clock=lambda: 1.0)
    assert len(first) == 1
    assert len(fake_nats.published) == 1  # max_challenge dispatched once
    state_after_first = json.loads(state_file.read_text())[chain_id]

    with patch.dict("sys.modules", {"nats": fake_nats}), caplog.at_level(logging.WARNING):
        second = orch.advance_step(chain_id, "aiden_plan", "atom-1-again", clock=lambda: 2.0)

    assert second == []
    assert len(fake_nats.published) == 1  # NOT re-dispatched
    assert "duplicate completed_step=aiden_plan" in caplog.text
    # State unchanged by the second call.
    state_after_second = json.loads(state_file.read_text())[chain_id]
    assert state_after_second == state_after_first


def test_advance_step_unrecognized_step_returns_empty_and_logs_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Step not in PARALLEL_AFTER_STEP, not in _SEQ_NEXT, pending empty: [] + warning."""
    import logging

    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}), caplog.at_level(logging.WARNING):
        envelopes = orch.advance_step(chain_id, "garbage_step", "atom-g")

    assert envelopes == []
    assert len(fake_nats.published) == 0
    assert "no known next for completed_step=garbage_step" in caplog.text


# ─── Final #ceo post on complete (Agency_OS-zqni) ─────────────────────────────


def test_advance_step_final_post_fires_on_chain_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """When the last parallel partner completes, _post_chain_complete is called once."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
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
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        orch.advance_step(chain_id, "aiden_plan", "atom-aiden", clock=lambda: 2.0)

    assert posts == []  # final post never invoked


def test_advance_step_final_post_failure_does_not_break_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A raising _post_chain_complete must NOT abort advance_step (fail-open guard)."""
    fake_nats = _fake_nats_module()
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

    with patch.dict("sys.modules", {"nats": fake_nats}):
        # Must NOT raise even though _post_chain_complete blows up.
        envelopes = orch.advance_step(chain_id, "atlas_safety", "atom-atlas")

    assert envelopes == []  # no further dispatch on complete
    state = json.loads(state_file.read_text())
    assert state[chain_id]["current_step"] == "complete"  # state still saved
