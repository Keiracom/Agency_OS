"""Publisher-side verdict wire-up tests (nova-verdict-publisher-wire).

Phase 1 final piece for verdict-enforcement: _publish_handoff must call
parse_reviewer_verdict(atom_id) when the completing agent is a reviewer
(max / orion / atlas) and attach verdict + verdict_reason to the envelope so
the orchestrator consumer (PR #1418 advance_step path) can halt + loop on
REJECT/HOLD.

All NATS publish + AtomStore seams mocked — no broker, no DB.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.keiracom_system.chain.reviewer_atom import ReviewerAtom
from src.keiracom_system.vault import agent_cold_start as acs


@pytest.fixture
def captured_payload(monkeypatch):
    """Stub _publish_handoff's NATS path; capture the json payload it built."""
    captured: dict[str, bytes] = {}

    class _StubClient:
        async def connect(self, *_a, **_kw):  # noqa: D401, ANN001
            return None

        async def publish(self, _subject, payload):  # noqa: ANN001
            captured["payload"] = payload

        async def flush(self):  # noqa: D401
            return None

        async def close(self):  # noqa: D401
            return None

    fake_module = MagicMock()
    fake_module.Client = _StubClient
    monkeypatch.setattr("nats.aio.client", fake_module, raising=False)
    # Also patch the lazy import path that _publish_handoff actually walks.
    import sys

    sys.modules["nats.aio.client"] = fake_module
    return captured


def _decode(payload: bytes) -> dict:
    return json.loads(payload.decode("utf-8"))


# ---- reviewer steps: verdict IS attached ---------------------------------


def test_publish_handoff_attaches_verdict_for_max(monkeypatch, captured_payload):
    """max (reviewer step max_challenge): parse_reviewer_verdict called,
    verdict + verdict_reason landed on payload."""
    monkeypatch.setenv("AGENT_CALLSIGN", "max")
    monkeypatch.setattr(
        acs,
        "_attach_verdict_if_reviewer",
        _capture_attach(
            MagicMock(
                return_value=ReviewerAtom(
                    verdict="REJECT",
                    rationale="missing guard",
                    atom_id="atom-max-1",
                )
            )
        ),
    )
    ok = acs._publish_handoff(task_id="t1", atom_id="atom-max-1")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert body["from_callsign"] == "max"
    assert body["verdict"] == "REJECT"
    assert body["verdict_reason"] == "missing guard"


def test_publish_handoff_attaches_verdict_for_orion(monkeypatch, captured_payload):
    monkeypatch.setenv("AGENT_CALLSIGN", "orion")
    monkeypatch.setattr(
        acs,
        "_attach_verdict_if_reviewer",
        _capture_attach(
            MagicMock(
                return_value=ReviewerAtom(
                    verdict="HOLD",
                    rationale="spec ambiguous",
                    atom_id="atom-orion-1",
                )
            )
        ),
    )
    ok = acs._publish_handoff(task_id="t1", atom_id="atom-orion-1")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert body["verdict"] == "HOLD"
    assert body["verdict_reason"] == "spec ambiguous"


def test_publish_handoff_attaches_verdict_for_atlas(monkeypatch, captured_payload):
    monkeypatch.setenv("AGENT_CALLSIGN", "atlas")
    monkeypatch.setattr(
        acs,
        "_attach_verdict_if_reviewer",
        _capture_attach(
            MagicMock(
                return_value=ReviewerAtom(
                    verdict="APPROVE",
                    rationale="safety ok",
                    atom_id="atom-atlas-1",
                )
            )
        ),
    )
    ok = acs._publish_handoff(task_id="t1", atom_id="atom-atlas-1")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert body["verdict"] == "APPROVE"
    assert body["verdict_reason"] == "safety ok"


# ---- non-reviewer steps: verdict NOT attached ----------------------------


def test_publish_handoff_no_verdict_for_aiden(monkeypatch, captured_payload):
    """aiden_plan is not a reviewer step — parse_reviewer_verdict MUST NOT be
    invoked and the envelope MUST NOT carry verdict/verdict_reason. The
    orchestrator's advance_step ignores verdict on non-reviewer steps as a
    no-op (PR #1418), but skipping the parse here also avoids a wasted
    AtomStore lookup on every aiden completion."""
    monkeypatch.setenv("AGENT_CALLSIGN", "aiden")
    parse_mock = MagicMock(return_value=ReviewerAtom(verdict="REJECT", rationale="x"))
    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        parse_mock,
    )
    ok = acs._publish_handoff(task_id="t1", atom_id="atom-aiden-1")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert "verdict" not in body
    assert "verdict_reason" not in body
    assert parse_mock.call_count == 0


def test_publish_handoff_no_verdict_for_nova(monkeypatch, captured_payload):
    monkeypatch.setenv("AGENT_CALLSIGN", "nova")
    parse_mock = MagicMock(return_value=ReviewerAtom(verdict="REJECT", rationale="x"))
    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        parse_mock,
    )
    ok = acs._publish_handoff(task_id="t1", atom_id="atom-nova-1")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert "verdict" not in body
    assert parse_mock.call_count == 0


def test_publish_handoff_no_verdict_when_atom_id_empty(monkeypatch, captured_payload):
    """A reviewer can publish a handoff with empty atom_id (degenerate path —
    classify_and_save returned no atom). With no atom there is nothing to
    parse; skip the call and leave the envelope verdict-less. advance_step
    treats this as a clean advance, which is the pre-PR-1418 behaviour and
    matches Atlas's regression test for legacy callers."""
    monkeypatch.setenv("AGENT_CALLSIGN", "atlas")
    parse_mock = MagicMock(return_value=ReviewerAtom(verdict="HOLD", rationale=""))
    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        parse_mock,
    )
    ok = acs._publish_handoff(task_id="t1", atom_id="")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert "verdict" not in body
    assert parse_mock.call_count == 0


# ---- fail-open: parse errors NEVER block publish -------------------------


def test_publish_handoff_fail_open_when_parse_raises(monkeypatch, captured_payload, caplog):
    """parse_reviewer_verdict's contract says it never raises, but a bug or
    a broken import should NEVER block the NATS publish. The envelope is
    sent verdict-less; a warning is logged."""
    monkeypatch.setenv("AGENT_CALLSIGN", "orion")

    def _boom(_atom_id):
        raise RuntimeError("simulated parser bug")

    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        _boom,
    )
    with caplog.at_level("WARNING"):
        ok = acs._publish_handoff(task_id="t1", atom_id="atom-orion-9")
    assert ok is True
    body = _decode(captured_payload["payload"])
    assert "verdict" not in body
    assert any("verdict-attach failed" in r.message for r in caplog.records)


# ---- attach helper: directly exercised -----------------------------------


def test_attach_verdict_mutates_payload_for_reviewer(monkeypatch):
    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        MagicMock(
            return_value=ReviewerAtom(
                verdict="REJECT",
                rationale="boundary leak",
                atom_id="a1",
            )
        ),
    )
    payload: dict = {"task_id": "t1", "atom_id": "a1"}
    acs._attach_verdict_if_reviewer(payload, from_callsign="MAX", atom_id="a1")
    assert payload["verdict"] == "REJECT"
    assert payload["verdict_reason"] == "boundary leak"


def test_attach_verdict_skips_non_reviewer(monkeypatch):
    parse_mock = MagicMock(return_value=ReviewerAtom(verdict="HOLD"))
    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        parse_mock,
    )
    payload: dict = {"task_id": "t1", "atom_id": "a1"}
    acs._attach_verdict_if_reviewer(payload, from_callsign="aiden", atom_id="a1")
    assert payload == {"task_id": "t1", "atom_id": "a1"}
    assert parse_mock.call_count == 0


def test_attach_verdict_skips_when_atom_id_empty(monkeypatch):
    parse_mock = MagicMock(return_value=ReviewerAtom(verdict="HOLD"))
    monkeypatch.setattr(
        "src.keiracom_system.chain.reviewer_atom.parse_reviewer_verdict",
        parse_mock,
    )
    payload: dict = {"task_id": "t1", "atom_id": ""}
    acs._attach_verdict_if_reviewer(payload, from_callsign="orion", atom_id="")
    assert payload == {"task_id": "t1", "atom_id": ""}
    assert parse_mock.call_count == 0


# ---- drift guard: publisher callsigns must match chain reviewer steps ----


def test_publisher_reviewer_callsigns_match_chain_reviewer_steps():
    """If REVIEWER_STEPS in v1_chain_orchestrator changes (e.g. a 4th reviewer
    persona joins the chain), this test forces the publisher's callsign set
    to update too. Source of truth is the chain module; the publisher
    duplicates as callsigns to keep _publish_handoff DB/import-free at
    envelope build."""
    from src.keiracom_system.chain.v1_chain_orchestrator import (
        FROM_TO_STEP,
        REVIEWER_STEPS,
    )

    step_to_callsign = {step: cs for cs, step in FROM_TO_STEP.items()}
    expected_callsigns = frozenset(step_to_callsign[s] for s in REVIEWER_STEPS)
    assert expected_callsigns == acs._REVIEWER_HANDOFF_CALLSIGNS


# ---- helper ---------------------------------------------------------------


def _capture_attach(parse_mock):
    """Return an _attach_verdict_if_reviewer stand-in that delegates the
    parse to ``parse_mock`` and mutates the payload identically to the real
    helper. Used to inject the parsed ReviewerAtom into _publish_handoff
    without monkey-patching the chain module's parse function (which lives
    behind a lazy import inside the helper)."""

    def _stub(payload, *, from_callsign, atom_id):
        if from_callsign.lower() not in acs._REVIEWER_HANDOFF_CALLSIGNS:
            return
        if not atom_id:
            return
        ra = parse_mock(atom_id)
        payload["verdict"] = ra.verdict
        payload["verdict_reason"] = ra.rationale

    return _stub
