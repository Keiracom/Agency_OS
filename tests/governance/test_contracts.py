"""tests/governance/test_contracts.py — B3 structured-output schemas tests."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.governance.contracts import (
    CompletionClaimContract,
    DirectiveContract,
    PeerReviewContract,
)


# ── DirectiveContract ──────────────────────────────────────────────────────

def test_directive_contract_validates_sample_dave_directive():
    """Sample modelled on the GOV-PHASE1-TRACK-B dispatch itself."""
    sample = {
        "intent": "Build Router + Coordinator + Structured Outputs governance services for Phase 1.",
        "context": (
            "Phase 1 governance redesign. ATLAS has Track A (PreToolUse hook). "
            "ORION takes Track B (Stop hook + claims + contracts)."
        ),
        "latitude": (
            "Build all 3 services on a single branch; tests must mock external clients. "
            "Escalate only if ATLAS branch hasn't landed before push."
        ),
        "frozen_artifacts": [
            "src/governance/router.py (NEW — exclusive ORION ownership)",
            "src/governance/coordinator.py (NEW — exclusive ORION ownership)",
            ".claude/settings.json PreToolUse hook (ATLAS-owned, do not edit)",
        ],
        "success_criteria": [
            "pytest tests/governance/test_router.py passes",
            "pytest tests/governance/test_coordinator.py passes",
            "pytest tests/governance/test_contracts.py passes",
            "raw test output pasted to outbox per R9",
        ],
        "scope_in": ["B1 router", "B2 coordinator", "B3 structured outputs"],
        "scope_out": ["PreToolUse hook (ATLAS)", "PR open"],
        "spend_aud_cap": 0.0,
        "step0_exemption": True,
        "source": "parent_bot",
        "task_ref": "GOV-PHASE1-TRACK-B",
    }
    contract = DirectiveContract.model_validate(sample)
    assert contract.intent.startswith("Build Router")
    assert contract.spend_aud_cap == 0.0
    assert contract.step0_exemption is True
    assert contract.source == "parent_bot"
    assert len(contract.success_criteria) == 4
    assert isinstance(contract.ratified_at, datetime)


def test_directive_contract_rejects_unknown_field():
    """extra='forbid' — Anthropic structured outputs require strict schemas."""
    with pytest.raises(ValidationError):
        DirectiveContract.model_validate({
            "intent": "x",
            "source": "dave",
            "unknown_field": "should be rejected",
        })


def test_directive_contract_requires_intent():
    with pytest.raises(ValidationError):
        DirectiveContract.model_validate({"source": "dave"})


def test_directive_contract_requires_source():
    with pytest.raises(ValidationError):
        DirectiveContract.model_validate({"intent": "x"})


def test_directive_contract_source_enum_constraint():
    with pytest.raises(ValidationError):
        DirectiveContract.model_validate({
            "intent": "x", "source": "investor",  # not in Literal
        })


def test_directive_contract_negative_spend_cap_rejected():
    with pytest.raises(ValidationError):
        DirectiveContract.model_validate({
            "intent": "x", "source": "dave", "spend_aud_cap": -5.0,
        })


def test_directive_contract_json_schema_is_anthropic_compatible():
    """Schema must serialise to JSON without unsupported types so it can
    be passed to Anthropic's structured-outputs tool surface."""
    schema = DirectiveContract.model_json_schema()
    assert schema["type"] == "object"
    assert "properties" in schema
    assert schema["additionalProperties"] is False
    assert "intent" in schema["properties"]


# ── PeerReviewContract ─────────────────────────────────────────────────────

def test_peer_review_contract_concur_status():
    contract = PeerReviewContract.model_validate({
        "reviewer_callsign": "elliot",
        "target_pr": "https://github.com/Keiracom/Agency_OS/pull/999",
        "status": "concur",
        "diff_findings": ["all tests pass", "no scope creep"],
        "recommendation": "merge",
    })
    assert contract.status == "concur"
    assert contract.reviewer_callsign == "elliot"


def test_peer_review_contract_yellow_flag_status():
    contract = PeerReviewContract.model_validate({
        "reviewer_callsign": "aiden",
        "target_pr": "branch:orion/foo",
        "status": "yellow_flag",
    })
    assert contract.status == "yellow_flag"


def test_peer_review_contract_status_enum_constraint():
    with pytest.raises(ValidationError):
        PeerReviewContract.model_validate({
            "reviewer_callsign": "elliot",
            "target_pr": "x",
            "status": "approved",  # not in Literal
        })


def test_peer_review_contract_callsign_enum_constraint():
    with pytest.raises(ValidationError):
        PeerReviewContract.model_validate({
            "reviewer_callsign": "dave",  # Dave is not a reviewer callsign
            "target_pr": "x",
            "status": "concur",
        })


# ── CompletionClaimContract ────────────────────────────────────────────────

def test_completion_claim_contract_minimal_valid():
    contract = CompletionClaimContract.model_validate({
        "callsign": "orion",
        "task_ref": "GOV-PHASE1-TRACK-B",
        "branch": "aiden/governance-phase1-track-b",
        "commit_sha": "abc1234",
    })
    assert contract.callsign == "orion"
    assert contract.audit_aud_spend == 0.0
    assert contract.four_store_complete() is False  # all four flags default False


def test_completion_claim_contract_four_store_complete_when_all_set():
    contract = CompletionClaimContract.model_validate({
        "callsign": "orion",
        "task_ref": "GOV-PHASE1-TRACK-B",
        "branch": "aiden/governance-phase1-track-b",
        "commit_sha": "abc1234",
        "stored_in_manual": True,
        "stored_in_ceo_memory": True,
        "stored_in_cis_metrics": True,
        "stored_in_drive_mirror": True,
    })
    assert contract.four_store_complete() is True


def test_completion_claim_contract_partial_four_store_returns_false():
    contract = CompletionClaimContract.model_validate({
        "callsign": "atlas",
        "task_ref": "X",
        "branch": "y",
        "commit_sha": "abcdefg",
        "stored_in_manual": True,
        "stored_in_ceo_memory": True,
        # Missing the other two — four_store_complete must return False.
    })
    assert contract.four_store_complete() is False


def test_completion_claim_contract_short_sha_below_minimum_rejected():
    with pytest.raises(ValidationError):
        CompletionClaimContract.model_validate({
            "callsign": "orion",
            "task_ref": "X",
            "branch": "y",
            "commit_sha": "abc",  # 3 chars — below min_length=7
        })


def test_completion_claim_contract_verification_stdout_field_present():
    """R9 Verify-Before-Claim: the schema must carry verification_stdout
    so it can be filled with raw command output rather than paraphrased."""
    contract = CompletionClaimContract.model_validate({
        "callsign": "orion",
        "task_ref": "X",
        "branch": "y",
        "commit_sha": "abcdefg",
        "verification_commands": ["pytest tests/governance/"],
        "verification_stdout": "===== 23 passed in 0.42s =====",
    })
    assert "23 passed" in contract.verification_stdout


def test_completion_claim_contract_negative_spend_rejected():
    with pytest.raises(ValidationError):
        CompletionClaimContract.model_validate({
            "callsign": "orion",
            "task_ref": "X",
            "branch": "y",
            "commit_sha": "abcdefg",
            "audit_aud_spend": -1.0,
        })


def test_completion_claim_contract_extra_field_rejected():
    with pytest.raises(ValidationError):
        CompletionClaimContract.model_validate({
            "callsign": "orion",
            "task_ref": "X",
            "branch": "y",
            "commit_sha": "abcdefg",
            "fabricated_field": "no",
        })
