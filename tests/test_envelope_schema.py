"""Unit tests for src/relay/envelope_schema.py.

Covers KNOWN_ENVELOPE_TYPES registry shape + validate_envelope() behaviour
across positive (each of the 4 types) and negative (missing type, unknown
type, missing required fields) paths.

bd: Agency_OS-1nf4 (PR #1140 §7 piece #3).
"""

from __future__ import annotations

import pytest

from src.relay.envelope_schema import (
    KNOWN_ENVELOPE_TYPES,
    REQUIRED_FIELDS,
    EnvelopeSchemaError,
    validate_envelope,
)


def test_known_envelope_types_is_the_4_named_in_pr_1140():
    """PR #1140 §5 + §7 piece #3 names exactly 4 envelope types — lock them."""
    assert (
        frozenset(
            {
                "task_dispatch",
                "decision_request",
                "decision_response",
                "paused_pending_decision",
            }
        )
        == KNOWN_ENVELOPE_TYPES
    )


def test_required_fields_registry_covers_every_known_type():
    """No type may appear in KNOWN_ENVELOPE_TYPES without a REQUIRED_FIELDS entry."""
    assert set(REQUIRED_FIELDS) == set(KNOWN_ENVELOPE_TYPES)


def test_required_fields_always_includes_universal_three():
    """Every envelope MUST carry id + type + from per §1 of the schema doc."""
    for type_name, required in REQUIRED_FIELDS.items():
        assert {"id", "type", "from"}.issubset(required), (
            f"{type_name} missing one of the universal three"
        )


def test_validate_task_dispatch_positive_path():
    validate_envelope(
        {
            "id": "task_1",
            "type": "task_dispatch",
            "from": "elliot",
            "target": "nova",
            "brief": "do the thing",
        }
    )


def test_validate_decision_request_positive_path():
    validate_envelope(
        {
            "id": "dec_req_1",
            "type": "decision_request",
            "from": "nova",
            "target": "elliot",
            "question": "push fix-up or override?",
            "options": ["push_fixup", "override"],
        }
    )


def test_validate_decision_response_positive_path():
    validate_envelope(
        {
            "id": "dec_resp_1",
            "type": "decision_response",
            "from": "elliot",
            "target": "nova",
            "decision": "push_fixup",
            "original_task_ref": "review-pr-N",
        }
    )


def test_validate_paused_pending_decision_positive_path():
    validate_envelope(
        {
            "id": "paused_1",
            "type": "paused_pending_decision",
            "from": "nova",
            "task_ref": "review-pr-N",
            "paused_at": 1748252600,
            "interim_state": {"notes": "waiting on Elliot"},
        }
    )


def test_validate_missing_type_field_raises():
    with pytest.raises(EnvelopeSchemaError, match="missing 'type' field"):
        validate_envelope({"id": "x", "from": "nova"})


def test_validate_unknown_type_raises():
    with pytest.raises(EnvelopeSchemaError, match="not in"):
        validate_envelope({"id": "x", "type": "not_a_real_type", "from": "nova"})


def test_validate_missing_required_field_raises():
    """task_dispatch without `brief` must fail; the message must name the gap."""
    with pytest.raises(EnvelopeSchemaError, match="missing required fields.*brief"):
        validate_envelope(
            {
                "id": "task_1",
                "type": "task_dispatch",
                "from": "elliot",
                "target": "nova",
                # brief missing
            }
        )


def test_validate_decision_request_missing_options_raises():
    """Catch the realistic copy-paste-from-task_dispatch error path."""
    with pytest.raises(EnvelopeSchemaError, match="missing required fields.*options"):
        validate_envelope(
            {
                "id": "dec_req_1",
                "type": "decision_request",
                "from": "nova",
                "target": "elliot",
                "question": "?",
                # options missing
            }
        )


def test_validate_paused_pending_decision_does_not_require_target():
    """paused_pending_decision is a self-snapshot per §2.4 — `target` not required."""
    # Should NOT raise even though `target` is absent.
    validate_envelope(
        {
            "id": "paused_1",
            "type": "paused_pending_decision",
            "from": "nova",
            "task_ref": "review-pr-N",
            "paused_at": 1748252600,
            "interim_state": {},
        }
    )
