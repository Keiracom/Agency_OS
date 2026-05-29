"""v1_chain_orchestrator.py — per-task chain-state tracker and NATS dispatcher.

V1 chain order (left to right):
    Face → aiden_plan → max_challenge → nova_build
                                              ↓ (parallel)
                                    orion_spec + atlas_safety
                                              ↓ (both done)
                                           complete

Coordination point with Orion zr7e.9 (atom_id NATS transport):
    The envelope key ``atom_id`` carries the atom_id returned by the PRIOR
    chain step's Atom completion signal. On the first hop (Face → Aiden) this
    is None. Each subsequent ``advance_step`` call receives the completing
    step's atom_id and propagates it forward in the envelope so the next agent
    can link its work to the prior Atom. When Orion's zr7e.9 ships, the
    subscriber loop will read ``atom_id`` from the envelope and wire it into
    the Atom store automatically.

Explicit non-goals for this PR (Agency_OS-zr7e.2):
    - No live status-event subscriber loop — Orion's zr7e.9 atom_id publisher
      does not exist yet; a subscriber would be misleading scaffolding.
    - vault/agent_cold_start.py notify-suppression — Orion's zr7e.9 scope.
    - NATS ACLs — rlfh part 1, separate PR.

Usage (first-hop acceptance test):
    chain_id = dispatch({"id": "task-1", "brief": "scaffold the auth module"})
    # Subscribing to keiracom.dispatch.aiden will receive the envelope.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
DISPATCH_SUBJECT_PATTERN = "keiracom.dispatch.{callsign}"
STATE_FILE = Path(os.environ.get("V1_CHAIN_STATE_FILE", "/tmp/v1_chain_state.json"))

CHAIN_STEPS: tuple[str, ...] = (
    "aiden_plan",
    "max_challenge",
    "nova_build",
    "orion_spec",
    "atlas_safety",
    "complete",
)

ROLE_FOR_STEP: dict[str, str] = {
    "aiden_plan": "aiden",
    "max_challenge": "max",
    "nova_build": "nova",
    "orion_spec": "orion",
    "atlas_safety": "atlas",
}

# Steps whose completion fans out to multiple parallel dispatches.
# Value = list of *next* steps to dispatch simultaneously.
PARALLEL_AFTER_STEP: dict[str, list[str]] = {
    "nova_build": ["orion_spec", "atlas_safety"],
}

# Consumer-loop contract (Agency_OS-oevr): subscribes to the subject Orion's
# zr7e.9 (PR #1330) publishes on. Envelope expected: {task_id, atom_id,
# from_callsign}. `chain_id == task_id` per Elliot's spec — dispatch() defaults
# chain_id to task["id"] so state lookups by task_id resolve.
CONSUMER_SUBJECT = "keiracom.agent.handoff"
FROM_TO_STEP: dict[str, str] = {
    "aiden": "aiden_plan",
    "max": "max_challenge",
    "nova": "nova_build",
    "orion": "orion_spec",
    "atlas": "atlas_safety",
}

log = logging.getLogger(__name__)

# Agency_OS-zqni — final-result #ceo path. Architecture (Scout / Elliot ratified):
# POST to a dedicated dispatcher endpoint /dispatcher/chain_complete (separate
# from /task_complete so nd3b's intermediate-step suppression stays clean), the
# dispatcher centralises cost lookup + Slack formatting + relay. Mirrors the
# notify_complete → /task_complete urllib pattern in vault/agent_cold_start.py.
_DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:4001")

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _post_chain_complete(
    entry: dict, chain_id: str, *, dispatcher_url: str = _DISPATCHER_URL
) -> None:
    """Agency_OS-zqni — POST to /dispatcher/chain_complete when the chain ends.

    Pairs with nd3b's notify_complete suppression (PR #1337): intermediate per-
    step task_complete posts are gated off; this single chain-result line is
    fired by the orchestrator and centralised in the dispatcher (cost lookup,
    multi-line formatting, Slack relay). Module-level so tests can monkeypatch.

    Fail-open: any error logged + swallowed — a notify failure must NEVER block
    advance_step or the state save.
    """
    import urllib.error  # noqa: PLC0415 — lazy, only the complete-transition path needs it
    import urllib.request  # noqa: PLC0415

    payload = json.dumps(
        {
            "task_id": entry.get("task_id") or "?",
            "chain_id": chain_id,
            "brief": entry.get("brief") or "(no brief)",
            "steps": list(entry.get("steps_done") or []),
        }
    ).encode()
    url = f"{dispatcher_url.rstrip('/')}/dispatcher/chain_complete"
    try:
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 — fixed loopback host
            log.info(
                "chain_complete notify: dispatcher status=%d for chain=%s", resp.status, chain_id
            )
    except (urllib.error.URLError, OSError):
        log.warning(
            "chain_complete notify: dispatcher unreachable for chain=%s", chain_id, exc_info=True
        )
    except Exception:  # noqa: BLE001 — must not break advance_step
        log.warning("chain_complete notify: unexpected error for chain=%s", chain_id, exc_info=True)


def _load_state() -> dict:
    """Return the full state dict from STATE_FILE, or {} if absent/invalid."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception as exc:  # noqa: BLE001
        log.warning("v1_chain: failed to load state file %s: %s", STATE_FILE, exc)
    return {}


def _save_state(state: dict) -> None:
    """Atomically write state to STATE_FILE (temp + os.replace)."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_FILE.parent, prefix=".v1_chain_state_")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(state, fh, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


async def _publish_async(envelope: dict, role: str) -> bool:
    """Inner async NATS publish — mirrors supervisor_wake_publish.publish_wake."""
    subject = DISPATCH_SUBJECT_PATTERN.format(callsign=role)
    try:
        import nats  # lazy — keeps module collectable on CI hosts without nats-py
    except ImportError as exc:
        log.error("v1_chain: nats-py not installed; publish skipped (%s)", exc)
        return False
    payload = json.dumps(envelope).encode("utf-8")
    nc = None
    try:
        nc = await nats.connect(NATS_URL, connect_timeout=5)
    except Exception as exc:
        log.error("v1_chain: NATS connect failed url=%s: %s", NATS_URL, exc)
        return False
    try:
        await nc.publish(subject, payload)
        await nc.flush(timeout=5)
        log.info("v1_chain: published %d bytes to %s", len(payload), subject)
    except Exception as exc:
        log.error("v1_chain: publish failed subject=%s: %s", subject, exc)
        await nc.close()
        return False
    await nc.close()
    return True


def _publish_envelope(envelope: dict, role: str) -> bool:
    """Drive async publish via asyncio.run. Return True on success, False on any failure."""
    try:
        return asyncio.run(_publish_async(envelope, role))
    except Exception as exc:  # noqa: BLE001
        log.error("v1_chain: asyncio.run publish failed role=%s: %s", role, exc)
        return False


def _build_envelope(
    task_id: str,
    chain_id: str,
    chain_step: str,
    atom_id: str | None,
    brief: str,
    clock: Callable[[], float],
) -> dict:
    return {
        "task_id": task_id,
        "chain_id": chain_id,
        "chain_step": chain_step,
        "atom_id": atom_id,
        "brief": brief,
        "ts": clock(),
        "from": "v1_chain_orchestrator",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def dispatch(
    task: dict,
    *,
    chain_id: str | None = None,
    clock: Callable[[], float] = time.time,
) -> str:
    """Begin a new V1 chain from a task dict.

    Args:
        task: Must contain at least ``id`` (or ``chain_id`` as fallback) and
              ``brief`` (or ``description`` as fallback for the message text).
        chain_id: Optional — generated as uuid4 hex when omitted.
        clock: Injectable for tests.

    Returns:
        chain_id (str).

    Fail-open: NATS publish errors are logged but never raised — the chain_id
    and persisted state are returned even when NATS is unavailable.
    """
    # chain_id defaults to task["id"] when present (Elliot's `chain_id==task_id`
    # convention, Agency_OS-oevr) so the consumer can `advance_step(chain_id=
    # msg.task_id)` and find the right state entry. Falls back to a fresh uuid
    # only when task has no id (ad-hoc / smoke invocations).
    cid = chain_id or task.get("id") or uuid.uuid4().hex
    task_id = task.get("id") or cid
    brief = task.get("brief") or task.get("description") or ""

    state = _load_state()
    state[cid] = {
        "chain_id": cid,
        "task_id": task_id,
        "brief": brief,
        "started_ts": clock(),
        "current_step": "aiden_plan",
        "steps_done": [],
        "atom_ids": {},
        "pending": [],
    }
    _save_state(state)

    envelope = _build_envelope(task_id, cid, "aiden_plan", None, brief, clock)
    _publish_envelope(envelope, "aiden")  # fail-open — result not checked

    return cid


def advance_step(
    chain_id: str,
    completed_step: str,
    atom_id: str,
    *,
    clock: Callable[[], float] = time.time,
) -> list[dict]:
    """Record a step completion and dispatch the next step(s).

    Args:
        chain_id: Identifies the chain in the state file.
        completed_step: The step that just finished (e.g. "aiden_plan").
        atom_id: The atom_id returned by the completing agent for this step.
        clock: Injectable for tests.

    Returns:
        List of envelope dicts that were dispatched (empty list if no dispatch
        occurred — either the chain is waiting on parallel partners, or it has
        reached ``complete``).
    """
    state = _load_state()
    entry = state.get(chain_id)
    if entry is None:
        log.error("v1_chain: advance_step unknown chain_id=%s", chain_id)
        return []

    # Idempotency: a repeated completion for the same step must NOT re-dispatch
    # downstream (Max HOLD on PR #1329). State already records the first call;
    # second call is a no-op.
    if completed_step in entry["steps_done"]:
        log.warning(
            "v1_chain: advance_step duplicate completed_step=%s chain=%s — no re-dispatch",
            completed_step,
            chain_id,
        )
        return []

    # Record completion of the current step.
    entry["atom_ids"][completed_step] = atom_id
    if completed_step not in entry["steps_done"]:
        entry["steps_done"].append(completed_step)
    if completed_step in entry["pending"]:
        entry["pending"].remove(completed_step)

    dispatched: list[dict] = []

    if completed_step in PARALLEL_AFTER_STEP:
        # Fan-out: dispatch all parallel next steps simultaneously.
        next_steps = PARALLEL_AFTER_STEP[completed_step]
        entry["pending"] = list(next_steps)
        for next_step in next_steps:
            role = ROLE_FOR_STEP[next_step]
            env = _build_envelope(
                entry["task_id"], chain_id, next_step, atom_id, entry["brief"], clock
            )
            _publish_envelope(env, role)
            dispatched.append(env)
        entry["current_step"] = next_steps[0]  # first parallel step as nominal marker
    elif entry["pending"]:
        # Still waiting on remaining parallel partners — no new dispatch.
        pass
    else:
        # Sequential next step, or final parallel step completing.
        _SEQ_NEXT: dict[str, str | None] = {
            "aiden_plan": "max_challenge",
            "max_challenge": "nova_build",
            # nova_build is handled by PARALLEL_AFTER_STEP above
        }
        # Check if we've just closed a parallel set (all pending cleared).
        parallel_steps_done = set(entry["steps_done"])
        all_parallel_covered = all(
            s in parallel_steps_done for group in PARALLEL_AFTER_STEP.values() for s in group
        )
        if all_parallel_covered and any(
            completed_step in group for group in PARALLEL_AFTER_STEP.values()
        ):
            # Last parallel step completed → chain is complete.
            entry["current_step"] = "complete"
            entry["pending"] = []
            # Agency_OS-zqni — single final #ceo post for the directive.
            # Belt-and-suspenders fail-open: _post_chain_complete's internal try/except
            # is the primary guard, but a future refactor or a test-injected fake
            # MUST NOT abort the state save here.
            try:
                _post_chain_complete(entry, chain_id)
            except Exception:  # noqa: BLE001 — final-post failure must not break state save
                log.warning(
                    "v1_chain chain_complete raised at call site for chain=%s",
                    chain_id,
                    exc_info=True,
                )
        elif completed_step in _SEQ_NEXT:
            next_step = _SEQ_NEXT[completed_step]
            if next_step is not None:
                role = ROLE_FOR_STEP[next_step]
                env = _build_envelope(
                    entry["task_id"], chain_id, next_step, atom_id, entry["brief"], clock
                )
                _publish_envelope(env, role)
                dispatched.append(env)
                entry["current_step"] = next_step
        else:
            log.warning(
                "v1_chain: advance_step no known next for completed_step=%s", completed_step
            )

    _save_state(state)
    return dispatched


async def _advance_step_async(
    chain_id: str,
    completed_step: str,
    atom_id: str,
    *,
    clock: Callable[[], float] = time.time,
) -> list[dict]:
    """Async entrypoint for the V1 consumer loop (Atlas oevr) — Aiden HOLD fix.

    Delegates to the sync advance_step via asyncio.to_thread so the completion
    branch ALWAYS fires _post_chain_complete via the exact same code path the
    sync caller uses. Parity-by-delegation eliminates the parallel-implementation
    divergence bug class Aiden caught on PR #1340 — there can never be a "the
    sync path calls _post_chain_complete but the async path forgot" failure,
    because there is only one path.

    State I/O (state file read/write) and the urllib POST in _post_chain_complete
    are I/O-bound, so running them on a worker thread is the correct shape:
    advance_step returns when the dispatch + state-save + chain-complete-post
    are all done, and the event loop is not blocked during the urllib POST.
    """
    return await asyncio.to_thread(advance_step, chain_id, completed_step, atom_id, clock=clock)


# ---------------------------------------------------------------------------
# Script entry point (manual smoke)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Consumer loop — bridges Orion's zr7e.9 handoff publish to advance_step
# (Agency_OS-oevr). Wired into the dispatcher lifespan as a background task.
# Delegates to the sync advance_step via _advance_step_async (Nova #1340's
# to_thread wrapper), so the final-#ceo-post / _post_chain_complete branch
# always fires through the canonical sync path — no parallel-implementation
# divergence (Aiden HOLD class).
# ---------------------------------------------------------------------------


async def _consumer_handle_envelope_async(envelope: dict) -> list[dict]:
    """Per-message async helper for the consumer (Max HOLD on PR #1339).

    Takes an already-parsed dict — fully unit-testable without a NATS msg
    object. Maps envelope.from_callsign → completed step via FROM_TO_STEP, then
    awaits _advance_step_async (sync advance_step under the hood, fully wired
    to _post_chain_complete). Fail-open per message.
    """
    try:
        task_id = envelope.get("task_id")
        atom_id = envelope.get("atom_id") or ""
        from_callsign = (envelope.get("from_callsign") or "").lower()
        if not task_id or not from_callsign:
            log.warning(
                "v1_chain consumer: missing task_id/from_callsign — skip (envelope=%r)",
                envelope,
            )
            return []
        step = FROM_TO_STEP.get(from_callsign)
        if step is None:
            log.warning("v1_chain consumer: unknown from_callsign=%s — skip", from_callsign)
            return []
        envelopes = await _advance_step_async(
            chain_id=task_id, completed_step=step, atom_id=atom_id
        )
        log.info(
            "v1_chain consumer: chain=%s step=%s -> %d dispatch(es)",
            task_id,
            step,
            len(envelopes),
        )
        return envelopes
    except Exception as exc:  # noqa: BLE001 — fail-open per message
        log.warning("v1_chain consumer: handler error: %s", exc)
        return []


async def run_consumer(nats_url: str | None = None) -> None:
    """Subscribe to CONSUMER_SUBJECT and advance the chain on each handoff.

    Long-running; cancellable via task.cancel() — closes the NATS connection.
    Mirrors peer_event_ceo_relay.main() loop pattern.
    """
    try:
        import nats  # lazy — keeps module collectable on hosts without nats-py
    except ImportError as exc:
        log.error("v1_chain consumer: nats-py not installed; loop exits (%s)", exc)
        return
    url = nats_url or NATS_URL
    try:
        nc = await nats.connect(url, connect_timeout=5)
    except Exception as exc:  # noqa: BLE001
        log.error("v1_chain consumer: NATS connect failed url=%s: %s", url, exc)
        return

    async def _handler(msg) -> None:
        # Thin delegate (Max HOLD): bytes → dict → delegate to the async helper.
        try:
            payload = json.loads(msg.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            log.warning("v1_chain consumer: malformed payload: %s", exc)
            return
        await _consumer_handle_envelope_async(payload)

    try:
        await nc.subscribe(CONSUMER_SUBJECT, cb=_handler)
        log.info("v1_chain consumer: subscribed %s on %s", CONSUMER_SUBJECT, url)
        while True:
            await asyncio.sleep(60)
    finally:
        try:
            await nc.close()
        except Exception as exc:  # noqa: BLE001
            log.warning("v1_chain consumer: NATS close error: %s", exc)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys

    brief = " ".join(sys.argv[1:]) or "test task from v1_chain_orchestrator __main__"
    cid = dispatch({"id": "smoke-task-1", "brief": brief})
    print(f"dispatched chain_id={cid}")
