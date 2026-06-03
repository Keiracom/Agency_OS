"""Phase 1 verdict-enforcement tests for v1_chain_orchestrator.advance_step.

Covers the runtime conditional (GOV-12) that halts forward progression on
any reviewer step returning REJECT or HOLD, loops the chain back to
aiden_plan with the reviewer's context, and escalates after the retry budget
(V1_VERDICT_MAX_RETRIES) is exhausted.

Reviewer steps under enforcement: max_challenge, orion_spec, atlas_safety.
All other completions advance / behave as before — verified by the
"clean advance still works" regression block.

ref: atlas-verdict-enforcement-phase1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.keiracom_system.chain import v1_chain_orchestrator as orch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_state_and_capture(tmp_path, monkeypatch):
    """Redirect STATE_FILE into tmp_path; capture _publish_envelope + posts.

    Yields a dict of (published_envelopes, halt_posts) so each test can
    assert on what advance_step asked downstream to do without any real
    NATS / urllib traffic.
    """
    state_path = tmp_path / "v1_chain_state.json"
    monkeypatch.setattr(orch, "STATE_FILE", state_path)

    published: list[tuple[dict, str]] = []
    monkeypatch.setattr(
        orch, "_publish_envelope", lambda env, role: published.append((env, role)) or True
    )

    halt_posts: list[dict[str, Any]] = []
    monkeypatch.setattr(
        orch,
        "_post_verdict_halt",
        lambda entry, chain_id, step, verdict, retry, *, escalated, verdict_reason=None, **_: (
            halt_posts.append(
                {
                    "chain_id": chain_id,
                    "step": step,
                    "verdict": verdict,
                    "retry": retry,
                    "escalated": escalated,
                    "reason": verdict_reason,
                    "state_snapshot_current_step": entry.get("current_step"),
                }
            )
        ),
    )

    # The ceiling check tries to read DATABASE_URL — keep it short-circuited.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    yield {"published": published, "halt_posts": halt_posts, "state_path": state_path}


def _seed_chain(state_path: Path, chain_id: str = "T1", brief: str = "do the thing") -> None:
    state_path.write_text(
        json.dumps(
            {
                chain_id: {
                    "chain_id": chain_id,
                    "task_id": chain_id,
                    "brief": brief,
                    "started_ts": 0.0,
                    "current_step": "aiden_plan",
                    "steps_done": [],
                    "atom_ids": {},
                    "pending": [],
                }
            }
        )
    )


def _state(state_path: Path, chain_id: str = "T1") -> dict:
    return json.loads(state_path.read_text())[chain_id]


# ---------------------------------------------------------------------------
# Harness 1 — REJECT halts and loops
# ---------------------------------------------------------------------------


def test_max_challenge_reject_halts_and_loops_to_aiden(_isolated_state_and_capture):
    """max REJECT must NOT dispatch nova_build; must re-dispatch aiden_plan."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])

    # Walk aiden_plan → max_challenge with REJECT on the max hop.
    orch.advance_step("T1", "aiden_plan", "atom-aiden-1")
    cap["published"].clear()  # discard the aiden→max dispatch from the clean leg

    dispatched = orch.advance_step(
        "T1",
        "max_challenge",
        "atom-max-1",
        verdict="REJECT",
        verdict_reason="plan missing rollback path",
    )

    # No nova_build dispatch — only the loop-back aiden_plan envelope.
    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "aiden_plan"
    assert all(role == "aiden" for _env, role in cap["published"])

    entry = _state(cap["state_path"])
    assert entry["current_step"] == "aiden_plan"
    assert entry["retry_count"] == 1
    assert entry["steps_done"] == []  # cleared for the next loop iteration
    assert len(entry["rejections"]) == 1
    rej = entry["rejections"][0]
    assert rej["step"] == "max_challenge"
    assert rej["verdict"] == "REJECT"
    assert rej["reason"] == "plan missing rollback path"

    # Exactly one halt-post (loop, not escalated).
    assert len(cap["halt_posts"]) == 1
    assert cap["halt_posts"][0]["escalated"] is False
    assert cap["halt_posts"][0]["retry"] == 1


def test_orion_spec_hold_halts_chain(_isolated_state_and_capture):
    """orion_spec HOLD during parallel phase halts + loops, no chain_complete."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])

    # Walk to the parallel stage: aiden → max → nova.
    orch.advance_step("T1", "aiden_plan", "a1")
    orch.advance_step("T1", "max_challenge", "m1", verdict="APPROVE")
    orch.advance_step("T1", "nova_build", "n1")
    cap["published"].clear()
    cap["halt_posts"].clear()

    # orion_spec returns HOLD — chain must halt + loop, atlas_safety becomes
    # an in-flight orphan we cannot recall but the chain is no longer
    # "waiting on" it.
    dispatched = orch.advance_step(
        "T1", "orion_spec", "o1", verdict="HOLD", verdict_reason="spec ambiguous"
    )

    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "aiden_plan"
    entry = _state(cap["state_path"])
    assert entry["current_step"] == "aiden_plan"
    assert entry["pending"] == []  # parallel-partner wait cleared
    assert entry["retry_count"] == 1
    assert entry["rejections"][-1]["verdict"] == "HOLD"


def test_atlas_safety_reject_halts_chain(_isolated_state_and_capture):
    """atlas_safety REJECT halts + loops just like orion_spec."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])
    orch.advance_step("T1", "aiden_plan", "a1")
    orch.advance_step("T1", "max_challenge", "m1", verdict="APPROVE")
    orch.advance_step("T1", "nova_build", "n1")
    cap["published"].clear()
    cap["halt_posts"].clear()

    dispatched = orch.advance_step(
        "T1", "atlas_safety", "s1", verdict="REJECT", verdict_reason="unsafe shell call"
    )
    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "aiden_plan"
    entry = _state(cap["state_path"])
    assert entry["current_step"] == "aiden_plan"
    assert entry["retry_count"] == 1


# ---------------------------------------------------------------------------
# Harness 2 — clean APPROVE still advances
# ---------------------------------------------------------------------------


def test_clean_advance_max_to_nova_still_works(_isolated_state_and_capture):
    """Regression: APPROVE verdict (and None) must NOT halt the chain."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])
    orch.advance_step("T1", "aiden_plan", "a1")
    cap["published"].clear()
    cap["halt_posts"].clear()

    dispatched = orch.advance_step("T1", "max_challenge", "m1", verdict="APPROVE")

    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "nova_build"
    entry = _state(cap["state_path"])
    assert entry["current_step"] == "nova_build"
    assert entry.get("retry_count", 0) == 0
    assert not entry.get("rejections")
    assert cap["halt_posts"] == []


def test_no_verdict_kwarg_preserves_legacy_advance(_isolated_state_and_capture):
    """advance_step called without verdict= must behave exactly as before."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])
    orch.advance_step("T1", "aiden_plan", "a1")
    cap["published"].clear()

    dispatched = orch.advance_step("T1", "max_challenge", "m1")  # no verdict kwarg
    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "nova_build"
    entry = _state(cap["state_path"])
    assert entry["current_step"] == "nova_build"


def test_verdict_on_non_reviewer_step_is_ignored(_isolated_state_and_capture):
    """verdict=REJECT on aiden_plan or nova_build must NOT halt — only
    reviewer steps trigger enforcement."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])

    # aiden_plan with REJECT should still dispatch max_challenge normally.
    dispatched = orch.advance_step("T1", "aiden_plan", "a1", verdict="REJECT")
    assert len(dispatched) == 1
    assert dispatched[0]["chain_step"] == "max_challenge"
    entry = _state(cap["state_path"])
    assert entry["current_step"] == "max_challenge"
    assert not entry.get("rejections")


# ---------------------------------------------------------------------------
# Harness 3 — bounded retries escalate
# ---------------------------------------------------------------------------


def test_max_retries_escalates_to_halted_state(_isolated_state_and_capture, monkeypatch):
    """After V1_VERDICT_MAX_RETRIES (default 3) reviewer rejections, the
    chain must halt permanently and post an escalation."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])

    # 3 REJECT loops: each loops retry_count 0→1, 1→2, 2→3.
    for i in range(orch.V1_VERDICT_MAX_RETRIES):
        orch.advance_step("T1", "aiden_plan", f"a{i}")
        dispatched = orch.advance_step(
            "T1",
            "max_challenge",
            f"m{i}",
            verdict="REJECT",
            verdict_reason=f"loop {i + 1}",
        )
        assert dispatched, f"loop {i + 1} should re-dispatch aiden_plan"
        assert dispatched[0]["chain_step"] == "aiden_plan"

    entry = _state(cap["state_path"])
    assert entry["retry_count"] == orch.V1_VERDICT_MAX_RETRIES

    # The next rejection exhausts the budget → escalation, no dispatch.
    cap["published"].clear()
    dispatched = orch.advance_step(
        "T1",
        "aiden_plan",
        "a_final",
    )
    assert dispatched and dispatched[0]["chain_step"] == "max_challenge"
    cap["published"].clear()

    dispatched = orch.advance_step(
        "T1",
        "max_challenge",
        "m_final",
        verdict="REJECT",
        verdict_reason="budget-exhaust",
    )
    assert dispatched == []

    entry = _state(cap["state_path"])
    assert entry["current_step"] == "halted_max_retries"
    assert entry["verdict_halt"]["escalated"] is True
    assert entry["verdict_halt"]["retry_count"] == orch.V1_VERDICT_MAX_RETRIES

    # Final halt post is the escalation one.
    escalations = [p for p in cap["halt_posts"] if p["escalated"]]
    assert len(escalations) == 1
    assert escalations[0]["retry"] == orch.V1_VERDICT_MAX_RETRIES


# ---------------------------------------------------------------------------
# Harness 4 — case-insensitive verdict normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_verdict", ["reject", " Reject ", "HOLD", "hold", "Hold"])
def test_verdict_token_case_and_whitespace_normalised(_isolated_state_and_capture, raw_verdict):
    """Reviewer verdicts must be case + whitespace insensitive."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])
    orch.advance_step("T1", "aiden_plan", "a1")
    cap["published"].clear()
    cap["halt_posts"].clear()

    dispatched = orch.advance_step("T1", "max_challenge", "m1", verdict=raw_verdict)
    assert dispatched and dispatched[0]["chain_step"] == "aiden_plan"
    entry = _state(cap["state_path"])
    assert entry["rejections"][-1]["verdict"] in orch.VERDICT_HALT_SET


def test_unknown_verdict_token_does_not_halt(_isolated_state_and_capture):
    """An unrecognised verdict string (e.g. 'MAYBE') is treated as
    'no enforcement' — the chain advances normally."""
    cap = _isolated_state_and_capture
    _seed_chain(cap["state_path"])
    orch.advance_step("T1", "aiden_plan", "a1")
    cap["published"].clear()
    cap["halt_posts"].clear()

    dispatched = orch.advance_step("T1", "max_challenge", "m1", verdict="MAYBE")
    assert dispatched and dispatched[0]["chain_step"] == "nova_build"
    entry = _state(cap["state_path"])
    assert entry["current_step"] == "nova_build"
    assert not entry.get("rejections")
