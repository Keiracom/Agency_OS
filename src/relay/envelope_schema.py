"""envelope_schema — inbox JSON envelope type registry + producer-side validator.

Defined by PR #1140 §5 (state-snapshot semantics) + §7 piece #3 (this module).
Canonical doc: docs/architecture/inbox_envelope_schema.md.

Inbox messages are signed JSON files written under /tmp/telegram-relay-*/inbox/.
The HMAC outer wrapper (security.inbox_hmac.sign) is type-agnostic; this module
captures the inner-payload contract so producers (scripts/sign_dispatch.py + any
future dispatcher) emit shapes consumers can actually route on.

Consumer-side enforcement (relay_watcher.sh / nats_to_inbox_bridge.py) belongs to
the dispatcher package KEI (PR #1140 §7 piece #1); out of scope here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

KNOWN_ENVELOPE_TYPES: frozenset[str] = frozenset(
    {
        "task_dispatch",
        "decision_request",
        "decision_response",
        "paused_pending_decision",
    }
)

# Required inner-payload fields per envelope type. `id`, `type`, `from` are
# universal (every envelope must carry them). Type-specific additions encode
# the routing + semantic requirements per PR #1140 §5.
REQUIRED_FIELDS: Mapping[str, frozenset[str]] = {
    "task_dispatch": frozenset({"id", "type", "from", "target", "brief"}),
    "decision_request": frozenset({"id", "type", "from", "target", "question", "options"}),
    "decision_response": frozenset(
        {"id", "type", "from", "target", "decision", "original_task_ref"}
    ),
    "paused_pending_decision": frozenset(
        {"id", "type", "from", "task_ref", "paused_at", "interim_state"}
    ),
}


class EnvelopeSchemaError(ValueError):
    """Raised when a payload fails KNOWN_ENVELOPE_TYPES or REQUIRED_FIELDS."""


def validate_envelope(payload: Mapping[str, Any]) -> None:
    """Producer-side check: payload has a known type + all required fields.

    Raises EnvelopeSchemaError on the first failure. Returns None on success.
    Does NOT validate field VALUES (caller's job — e.g. `options` is a list,
    `paused_at` is a unix-int) since shape varies and over-validation here
    would couple to producer details. Field-PRESENCE is the universal contract.
    """
    type_value = payload.get("type")
    if type_value is None:
        raise EnvelopeSchemaError("envelope missing 'type' field")
    if type_value not in KNOWN_ENVELOPE_TYPES:
        raise EnvelopeSchemaError(
            f"envelope type {type_value!r} not in {sorted(KNOWN_ENVELOPE_TYPES)}"
        )
    required = REQUIRED_FIELDS[type_value]
    missing = required - payload.keys()
    if missing:
        raise EnvelopeSchemaError(
            f"envelope type={type_value!r} missing required fields: {sorted(missing)}"
        )
