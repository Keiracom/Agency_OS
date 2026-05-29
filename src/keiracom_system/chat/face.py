"""face.py — runnable entrypoint for the Face (the Dave/customer-facing chat agent).

The Face is the Chat leg of the V1 chain:
    Dave types in Slack → Face → Deliberator → Worker → Reviewer → result back.

A 'task'-classified message triggers a NATS dispatch to Aiden (subject
``keiracom.dispatch.aiden``) — fail-open: if NATS is unreachable the Face
returns a human-readable retry response and the process keeps running.

This is the spawnable entrypoint (Agency_OS-ii3ucd + zr7e.1 dispatch wiring).
It:
  1. reads a brief / inbound messages,
  2. runs a message → classify → respond loop (classification via
     context_composer.compose_chat_context),
  3. on classification=='task', publishes {type, task_id, atom_id,
     from_callsign, to_callsign, brief, ts} to keiracom.dispatch.aiden, and
  4. calls exit_cycle.classify_and_save before exit so any ratified decision in
     the conversation survives the ephemeral spawn.

Spawnable:
    python3 -m src.keiracom_system.chat.face
  - Brief: argv[1] or FACE_BRIEF env (optional) seeds the first message.
  - Further messages: piped stdin, one per line ('exit'/'quit'/EOF ends the loop).
  - customer_id: FACE_CUSTOMER_ID env (default 1 — Dave = fleet tenant 1).

Fail-open: with no Gemini/Hindsight/DB/NATS creds, classification degrades to
'ambiguous', dispatch returns False, the exit cycle skips — the process still
runs clean and exits 0. An interactive TTY with no brief prints a usage hint
and exits 0 (never blocks).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable

from src.keiracom_system.chat.context_composer import ChatContextResult, compose_chat_context
from src.keiracom_system.chat.exit_cycle import ExitCycleResult, classify_and_save

logger = logging.getLogger(__name__)

CALLSIGN = "face"
DEFAULT_CUSTOMER_ID = 1  # Dave = fleet tenant 1
EXIT_SENTINELS = {"exit", "quit"}
MAX_HISTORY = 5  # recent user turns fed to the classifier

# zr7e.1 — NATS dispatch transport. Aiden's nats_tmux_bridge subscribes
# keiracom.dispatch.aiden (live per Elliot+Aiden architecture review 2026-05-29).
# Mirrors scripts/fleet_supervisor._nats_publish_state: lazy nats-py import,
# asyncio.run(connect/publish/flush/close), fail-open warn on failure.
NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
DISPATCH_SUBJECT = "keiracom.dispatch.aiden"
DISPATCH_TO = "aiden"

ClassifyFn = Callable[[str, int, list[str]], ChatContextResult]
SaveFn = Callable[[list[dict[str, str]], int], Awaitable[ExitCycleResult]]
DispatchFn = Callable[..., bool]  # (*, brief, task_id, atom_id) -> bool


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


def _dispatch_to_aiden(*, brief: str, task_id: str, atom_id: str | None = None) -> bool:
    """Publish a task_dispatch envelope to NATS keiracom.dispatch.aiden. Fail-open.

    Returns True on publish success, False on any failure — no exception escapes.
    Mirrors fleet_supervisor._nats_publish_state (lazy nats-py + asyncio.run).

    atom_id is None at V1 Face dispatch (atoms are written at conversation exit,
    not per-message); zr7e.9 will populate it once the exit_cycle pointer is the
    handoff signal.
    """
    payload = json.dumps(
        {
            "type": "task_dispatch",
            "task_id": task_id,
            "atom_id": atom_id,
            "from_callsign": CALLSIGN,
            "to_callsign": DISPATCH_TO,
            "brief": brief,
            "ts": int(time.time()),
        }
    ).encode()
    try:
        import nats.aio.client as nats_client  # noqa: PLC0415 — optional dep, lazy

        async def _publish() -> None:
            nc = nats_client.Client()
            await nc.connect(NATS_URL, connect_timeout=2)
            try:
                await nc.publish(DISPATCH_SUBJECT, payload)
                await nc.flush()
            finally:
                await nc.close()

        asyncio.run(_publish())
        logger.info("face: NATS PUBLISH %s → task_id=%s", DISPATCH_SUBJECT, task_id)
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open: NATS failure must never crash Face
        logger.warning("face: NATS dispatch failed (non-fatal): %s", exc)
        return False


def _respond(
    result: ChatContextResult,
    message: str = "",
    *,
    dispatch: DispatchFn = _dispatch_to_aiden,
) -> str:
    """Compose the Face's reply; on classification=='task', dispatch to Aiden first.

    Non-'task' branches keep the V1 stub routing strings (worker/reviewer spawn
    legs land in later directives). 'task' goes to Aiden via NATS, fail-open.
    """
    if result.classification == "ambiguous":
        return "Escalating to a deliberator — not enough context to route this."
    if result.classification == "task":
        task_id = str(uuid.uuid4())
        if dispatch(brief=message, task_id=task_id, atom_id=None):
            return f"Dispatching to Aiden (deliberator). Briefed on: {message[:100]}"
        return "Dispatch failed — try again."
    return (
        f"Classified as '{result.classification}'. Routing to the "
        f"{result.classification} tier (spawn not yet wired — V1 Chat leg)."
    )


def run_conversation(
    messages: Iterable[str],
    customer_id: int,
    *,
    classify: ClassifyFn = compose_chat_context,
    dispatch: DispatchFn = _dispatch_to_aiden,
) -> list[dict[str, str]]:
    """Drive the classify→respond loop. Returns the full conversation transcript.

    `classify` is the compose_chat_context seam (fail-open by contract — it
    degrades to 'ambiguous' rather than raising), injectable for tests.
    `dispatch` is the Face→Aiden NATS publish seam, also injectable for tests.
    """
    conversation: list[dict[str, str]] = []
    for message in messages:
        if not message or message.lower() in EXIT_SENTINELS:
            break
        history = [m["content"] for m in conversation if m["role"] == "user"][-MAX_HISTORY:]
        reply = _respond(classify(message, customer_id, history), message, dispatch=dispatch)
        conversation.append({"role": "user", "content": message})
        conversation.append({"role": "assistant", "content": reply})
        print(reply, flush=True)
    return conversation


def run(
    *,
    briefs: Callable[[], Iterable[str]] = _briefs,
    classify: ClassifyFn = compose_chat_context,
    save: SaveFn = classify_and_save,
    dispatch: DispatchFn = _dispatch_to_aiden,
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
    conversation = run_conversation(messages, customer_id, classify=classify, dispatch=dispatch)
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
