"""exit_cycle.py — John's end-of-conversation decision capture (direct-write).

An ephemeral John spawn has no persistent memory. If a conversation contained a
ratified decision (Viktor explained an architecture, Dave confirmed a
direction, a pattern was established), the only way that knowledge survives to
the next spawn is to write it before this spawn exits.

DIRECT-WRITE model (Path 1, Dave-ratified 2026-05-29, ceo:ephemeral_capture_model_v1
v2): `classify_and_save` scans a finished conversation with Gemini Flash, keeps
items with confidence > 0.8 (max 3), builds an AtomV1 decision atom from each,
and writes it DIRECTLY to the Hindsight `fleet_decisions` bank. The old two-step
(exit_cycle -> ceo_memory -> atomiser -> fleet_decisions) is decommissioned —
nothing is written to ceo_memory. Future spawns retrieve atoms via Hindsight
Layer 2 recall. Serialization is the shared one-source seam in
`atomization.hindsight_writer` (format-matched with the historical backfill).

Fail-open by contract: any Gemini or Hindsight error skips gracefully and never
blocks conversation completion.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.keiracom_system.atomization.decision_sources import decision_composition_tags
from src.keiracom_system.atomization.hindsight_writer import (
    DEFAULT_BANK,
    IngestFn,
    atom_to_hindsight_item,
    default_hindsight_ingest,
)
from src.keiracom_system.atomization.schema import AtomV1

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8
MAX_WRITES = 3
CALLSIGN = "john"
LIVE_SOURCE = "live_spawn_exit"
# Fleet/system tenant — fleet_decisions is a fleet-level bank (Dave = tenant 1).
# Mirrors SYSTEM_PIPELINE_CLIENT_ID; recall addresses the bank by the "default"
# slug (orchestrator.FLEET_TENANT_SLUG), so this UUID is provenance metadata.
FLEET_TENANT_UUID = UUID("00000000-0000-0000-0000-000000000001")
_VALID_KINDS = {
    "architectural_decision",
    "confirmed_pattern",
    "dave_approval",
    "viktor_explanation",
}

CLASSIFY_SYSTEM_PROMPT = (
    "You extract durable institutional knowledge from a finished conversation so "
    "it survives past an ephemeral agent that is about to exit. Return ONLY items "
    "that are one of: a ratified architectural decision ('we will use X for Y'); "
    "a confirmed pattern ('always do X when Y'); an explicit Dave approval ('yes', "
    "'go ahead', 'confirmed' against a concrete proposal); or a Viktor explanation "
    "of how something works. DO NOT return status updates, questions, routine task "
    "dispatches, or casual conversation. For each item give: decision_text (a "
    "self-contained one-sentence statement of the decision/pattern/fact — written "
    "so a future agent with no prior context understands it), topic_slug (2-5 "
    "kebab-case words), kind (one of architectural_decision|confirmed_pattern|"
    "dave_approval|viktor_explanation), and confidence (0.0-1.0). Return an empty "
    "items list when nothing qualifies. Be conservative — precision over recall."
)

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "decision_text": {"type": "string"},
                    "topic_slug": {"type": "string"},
                    "kind": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["decision_text", "topic_slug", "kind", "confidence"],
            },
        }
    },
    "required": ["items"],
}


@dataclass
class ExitCycleResult:
    decisions_saved: int = 0
    atom_ids: list[str] = field(default_factory=list)
    bank: str = DEFAULT_BANK
    skipped_reason: str | None = None


def _topic_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:48] or "untitled"


def _render(conversation: Sequence[dict[str, Any]]) -> str:
    return "\n".join(f"{m.get('role', '?')}: {m.get('content', '')}" for m in conversation)


async def _classify(gemini_client: Any, conversation_text: str) -> list[dict[str, Any]]:
    """Run Gemini Flash classification; [] on any non-success or bad shape."""
    result = await gemini_client.comprehend(
        system_prompt=CLASSIFY_SYSTEM_PROMPT,
        user_prompt=conversation_text,
        enable_grounding=False,
        response_schema=RESPONSE_SCHEMA,
    )
    if result.get("f3_status") != "success":
        return []
    content = result.get("content")
    if not isinstance(content, dict):
        return []
    items = content.get("items")
    return items if isinstance(items, list) else []


def _select_qualifying(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep valid-kind items above the confidence floor, capped at MAX_WRITES."""
    qualifying: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            confidence = float(it.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if confidence <= CONFIDENCE_THRESHOLD:
            continue
        if it.get("kind") not in _VALID_KINDS:
            continue
        if not (it.get("decision_text") or "").strip():
            continue
        qualifying.append(it)
    return qualifying[:MAX_WRITES]


def _build_atom(item: dict[str, Any], customer_id: int, captured_at: datetime) -> AtomV1:
    """Map a classified decision item to a fleet decision AtomV1."""
    date = captured_at.strftime("%Y-%m-%d")
    return AtomV1(
        atom_id=uuid4(),
        tenant_id=FLEET_TENANT_UUID,
        trigger_condition={
            "kind": "context_predicate",
            "params": {
                "topic": _topic_slug(item.get("topic_slug") or item["decision_text"]),
                "decision_kind": item["kind"],
            },
        },
        content=item["decision_text"],
        anti_pattern=None,
        example=None,
        provenance={
            "source": f"{LIVE_SOURCE}:john:customer_{customer_id}",
            "freshness": date,
            "confidence": float(item["confidence"]),
            "last_validated": date,
        },
        composition_tags=decision_composition_tags(),
    )


async def classify_and_save(
    conversation: list[dict[str, Any]],
    customer_id: int,
    *,
    gemini_client: Any | None = None,
    ingest_fn: IngestFn | None = None,
) -> ExitCycleResult:
    """Detect ratified decisions in `conversation` and write them as AtomV1 atoms
    directly to the Hindsight `fleet_decisions` bank.

    Fail-open: returns a result with `skipped_reason` set rather than raising on
    any classification or ingest failure. `gemini_client` and `ingest_fn` are
    injectable for testing.
    """
    if not conversation:
        return ExitCycleResult(skipped_reason="empty_conversation")

    client = gemini_client
    if client is None:
        try:
            from src.intelligence.gemini_client import GeminiClient

            client = GeminiClient()
        except Exception as exc:  # noqa: BLE001 — fail-open; never block completion
            logger.warning("exit_cycle: Gemini init failed (skip): %s", exc)
            return ExitCycleResult(skipped_reason=f"gemini_init_failed: {exc}")

    try:
        items = await _classify(client, _render(conversation))
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("exit_cycle: classification failed (skip): %s", exc)
        return ExitCycleResult(skipped_reason=f"classify_failed: {exc}")

    qualifying = _select_qualifying(items)
    if not qualifying:
        reason = "no_decisions_detected" if not items else "below_confidence_threshold"
        logger.info("exit_cycle: nothing to save (%s; %d raw items)", reason, len(items))
        return ExitCycleResult(skipped_reason=reason)

    now = datetime.now(UTC)
    hindsight_items: list[dict[str, Any]] = []
    atom_ids: list[str] = []
    for item in qualifying:
        try:
            atom = _build_atom(item, customer_id, now)
        except (ValueError, KeyError) as exc:
            logger.warning("exit_cycle: atom build failed (skip item): %s", exc)
            continue
        hindsight_items.append(atom_to_hindsight_item(atom, source=LIVE_SOURCE))
        atom_ids.append(str(atom.atom_id))

    if not hindsight_items:
        return ExitCycleResult(skipped_reason="all_atoms_invalid")

    ingest = ingest_fn or default_hindsight_ingest
    try:
        await asyncio.to_thread(ingest, DEFAULT_BANK, hindsight_items)
    except Exception as exc:  # noqa: BLE001 — fail-open; never block completion
        logger.warning("exit_cycle: fleet_decisions ingest failed (skip): %s", exc)
        return ExitCycleResult(skipped_reason=f"ingest_failed: {exc}")

    logger.info(
        "exit_cycle: wrote %d atom(s) to %s (kinds=%s)",
        len(atom_ids),
        DEFAULT_BANK,
        [q["kind"] for q in qualifying],
    )
    return ExitCycleResult(decisions_saved=len(atom_ids), atom_ids=atom_ids, bank=DEFAULT_BANK)
