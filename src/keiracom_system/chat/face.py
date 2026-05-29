"""face.py — runnable entrypoint for the Face (the Dave/customer-facing chat agent).

The Face is the Chat leg of the V1 chain:
    Dave types in Slack → Face → Deliberator → Worker → Reviewer → result back.

This is the MINIMAL spawnable entrypoint (Agency_OS-ii3ucd). It:
  1. reads a brief / inbound messages,
  2. runs a message → classify → respond loop (classification via
     context_composer.compose_chat_context), and
  3. calls exit_cycle.classify_and_save before exit so any ratified decision in
     the conversation survives the ephemeral spawn.

The deliberator-spawn chain is deliberately NOT wired here — a classified message
yields a stub routing response. That leg lands in a later directive.

Spawnable:
    python3 -m src.keiracom_system.chat.face
  - Brief: argv[1] or FACE_BRIEF env (optional) seeds the first message.
  - Further messages: piped stdin, one per line ('exit'/'quit'/EOF ends the loop).
  - customer_id: FACE_CUSTOMER_ID env (default 1 — Dave = fleet tenant 1).

Fail-open: with no Gemini/Hindsight/DB creds, classification degrades to
'ambiguous' and the exit cycle skips — the process still runs clean and exits 0.
An interactive TTY with no brief prints a usage hint and exits 0 (never blocks).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections.abc import Awaitable, Callable, Iterable

from src.keiracom_system.chat.context_composer import ChatContextResult, compose_chat_context
from src.keiracom_system.chat.exit_cycle import ExitCycleResult, classify_and_save

logger = logging.getLogger(__name__)

CALLSIGN = "face"
DEFAULT_CUSTOMER_ID = 1  # Dave = fleet tenant 1
EXIT_SENTINELS = {"exit", "quit"}
MAX_HISTORY = 5  # recent user turns fed to the classifier

ClassifyFn = Callable[[str, int, list[str]], ChatContextResult]
SaveFn = Callable[[list[dict[str, str]], int], Awaitable[ExitCycleResult]]


def _customer_id() -> int:
    try:
        return int(os.environ.get("FACE_CUSTOMER_ID", DEFAULT_CUSTOMER_ID))
    except ValueError:
        logger.warning("face: bad FACE_CUSTOMER_ID — defaulting to %d", DEFAULT_CUSTOMER_ID)
        return DEFAULT_CUSTOMER_ID


def _briefs() -> Iterable[str]:
    """Initial brief from argv[1] or FACE_BRIEF, then piped stdin lines.

    Reads stdin only when it is NOT a tty, so an interactive `python3 -m
    ...face` with no brief exits clean instead of blocking on input().
    """
    brief = (sys.argv[1] if len(sys.argv) > 1 else "") or os.environ.get("FACE_BRIEF", "")
    if brief.strip():
        yield brief.strip()
    if not sys.stdin.isatty():
        for line in sys.stdin:
            yield line.strip()


def _respond(result: ChatContextResult) -> str:
    """Stub routing response (the deliberator-spawn chain is not wired in V1)."""
    if result.classification == "ambiguous":
        return "Escalating to a deliberator — not enough context to route this."
    return (
        f"Classified as '{result.classification}'. Routing to the "
        f"{result.classification} tier (spawn not yet wired — V1 Chat leg)."
    )


def run_conversation(
    messages: Iterable[str],
    customer_id: int,
    *,
    classify: ClassifyFn = compose_chat_context,
) -> list[dict[str, str]]:
    """Drive the classify→respond loop. Returns the full conversation transcript.

    `classify` is the compose_chat_context seam (fail-open by contract — it
    degrades to 'ambiguous' rather than raising), injectable for tests.
    """
    conversation: list[dict[str, str]] = []
    for message in messages:
        if not message or message.lower() in EXIT_SENTINELS:
            break
        history = [m["content"] for m in conversation if m["role"] == "user"][-MAX_HISTORY:]
        reply = _respond(classify(message, customer_id, history))
        conversation.append({"role": "user", "content": message})
        conversation.append({"role": "assistant", "content": reply})
        print(reply, flush=True)
    return conversation


def run(
    *,
    briefs: Callable[[], Iterable[str]] = _briefs,
    classify: ClassifyFn = compose_chat_context,
    save: SaveFn = classify_and_save,
) -> int:
    """Spawn orchestration: run the loop, then the exit cycle. Returns exit code."""
    logging.basicConfig(level=logging.INFO)
    customer_id = _customer_id()
    messages = list(briefs())
    if not messages and sys.stdin.isatty():
        logger.info(
            "face: no brief and stdin is a tty — nothing to do. "
            "Usage: FACE_BRIEF='...' python3 -m %s  (or pipe messages on stdin)",
            __spec__.name if __spec__ else __name__,
        )
    conversation = run_conversation(messages, customer_id, classify=classify)
    result: ExitCycleResult = asyncio.run(save(conversation, customer_id))
    logger.info(
        "face: exit cycle — saved=%d skipped=%s bank=%s",
        result.decisions_saved,
        result.skipped_reason,
        result.bank,
    )
    return 0


def main() -> int:  # pragma: no cover — process entrypoint
    return run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
