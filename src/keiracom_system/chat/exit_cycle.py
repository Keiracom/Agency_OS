"""exit_cycle.py — John's end-of-conversation decision capture.

An ephemeral John spawn has no persistent memory. If a conversation contained a
ratified decision (Viktor explained an architecture, Dave confirmed a
direction, a pattern was established), the only way that knowledge survives to
the next spawn is to write it to ceo_memory before this spawn exits. The
atomiser then promotes it to fleet_decisions; future spawns retrieve it via
Hindsight Layer 2.

`classify_and_save` scans a finished conversation with Gemini Flash, keeps items
with confidence > 0.8 (max 3), and upserts each to ceo_memory under
`ceo:conversation_capture:{date}:{topic_slug}` via the canonical KEI-87 writer.

Fail-open by contract: any Gemini or DB error skips gracefully and never blocks
conversation completion.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8
MAX_WRITES = 3
CALLSIGN = "john"
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
    keys_written: list[str] = field(default_factory=list)
    skipped_reason: str | None = None


WriterFn = Callable[[str, str, dict[str, Any]], None]


def _topic_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:48] or "untitled"


def _render(conversation: Sequence[dict[str, Any]]) -> str:
    return "\n".join(f"{m.get('role', '?')}: {m.get('content', '')}" for m in conversation)


def _default_writer(callsign: str, key: str, value: dict[str, Any]) -> None:
    from src.governance.ceo_memory_writer import upsert_ceo_memory_key

    upsert_ceo_memory_key(callsign, key, value)


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


def _build_value(item: dict[str, Any], customer_id: int, captured_at: str) -> dict[str, Any]:
    return {
        "decision": item["decision_text"],
        "kind": item["kind"],
        "confidence": float(item["confidence"]),
        "customer_id": customer_id,
        "captured_by": "john_exit_cycle",
        "captured_at": captured_at,
    }


async def classify_and_save(
    conversation: list[dict[str, Any]],
    customer_id: int,
    *,
    gemini_client: Any | None = None,
    writer: WriterFn | None = None,
) -> ExitCycleResult:
    """Detect ratified decisions in `conversation` and persist them to ceo_memory.

    Fail-open: returns a result with `skipped_reason` set rather than raising on
    any classification or write failure. `gemini_client` and `writer` are
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

    write = writer or _default_writer
    now = datetime.now(UTC)
    date = now.strftime("%Y-%m-%d")
    saved: list[str] = []
    for item in qualifying:
        key = f"ceo:conversation_capture:{date}:{_topic_slug(item.get('topic_slug') or item['decision_text'])}"
        value = _build_value(item, customer_id, now.isoformat())
        try:
            await asyncio.to_thread(write, CALLSIGN, key, value)
        except Exception as exc:  # noqa: BLE001 — fail-open per write
            logger.warning("exit_cycle: ceo_memory write failed for %s (skip): %s", key, exc)
            continue
        saved.append(key)
        logger.info(
            "exit_cycle: saved %s (kind=%s conf=%.2f): %s",
            key,
            item["kind"],
            float(item["confidence"]),
            item["decision_text"][:140],
        )

    if not saved:
        return ExitCycleResult(skipped_reason="all_writes_failed")
    return ExitCycleResult(decisions_saved=len(saved), keys_written=saved)
