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

# JetStream durable consumer for keiracom.agent.handoff (Dave directive 2026-06-02
# — NATS handoff stall fix). Core pub/sub drops messages published during
# dispatcher downtime; a JS durable consumer with WorkQueue retention buffers
# them until the consumer reconnects and acks. Storage=File so messages also
# survive a NATS broker restart. Retention=WorkQueue (not Limits) so each
# message is consumed exactly once across all consumers and removed on ack —
# Limits would keep the message until age/size eviction, causing duplicate
# dispatches if the consumer reset its sequence cursor.
JS_STREAM_NAME = "agent_handoff"
JS_CONSUMER_DURABLE = "chain-orchestrator"
JS_DELIVER_SUBJECT = "_INBOX.chain_orch"

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

# V1-battery Gate 1 — per-task A$10 spend ceiling (Elliot dispatch 2026-05-30
# ~11:35 AEST). Reads cumulative cost_aud per task_id from
# keiracom_spawn_attribution after each hop. Complements Orion's fleet-level
# cost_breaker (#1297 Agency_OS-wdws) — that's fleet daily/monthly aggregate at
# /spawn time; this is per-task SUM after each hop. Both must trip to be
# load-bearing for the V1 battery.
_TASK_COST_CEILING_AUD = float(os.environ.get("V1_TASK_COST_CEILING_AUD", "10.00"))

# Verdict-enforcement nucleus (Phase 1 — atlas-verdict-enforcement-phase1).
# Reviewer steps return a verdict atom; REJECT/HOLD halts forward progression
# and re-dispatches aiden_plan with the reviewer's context as the loop brief.
# Bounded retries: after V1_VERDICT_MAX_RETRIES iterations the chain escalates
# to Dave via /dispatcher/verdict_halt + state=halted_max_retries. GOV-12: the
# runtime conditional lives in advance_step below — this is not a comment-only
# enforcement.
REVIEWER_STEPS: frozenset[str] = frozenset({"max_challenge", "orion_spec", "atlas_safety"})
VERDICT_HALT_SET: frozenset[str] = frozenset({"REJECT", "HOLD"})
V1_VERDICT_MAX_RETRIES = int(os.environ.get("V1_VERDICT_MAX_RETRIES", "3"))

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _query_task_cost_aud(task_id: str) -> tuple[float, list[dict]] | None:
    """Return (sum_aud, per_hop_rows) for a task_id, or None on read failure.

    V1-battery Gate 1 helper — runs the dispatch's specified SUM(cost_aud) +
    per-hop breakdown query against public.keiracom_spawn_attribution. Per-hop
    breakdown shape: [{callsign, chain_step, cost_aud}, ...] ordered by ts.

    Returns None (not (0.0, [])) on read failure so callers can distinguish
    "checked, no spend yet" from "couldn't check". A read failure is fail-OPEN:
    the chain proceeds — Orion's fleet-level breaker (#1297) is the fail-SAFE
    backstop and this gate is the per-task complement.
    """
    if not task_id:
        return None
    # Fast-fail when no DSN — keeps unit tests + CI hosts off a 10s
    # psycopg.connect timeout. fail-OPEN per the docstring contract.
    if not os.environ.get("DATABASE_URL"):
        return None
    try:
        from src.keiracom_system.vault.agent_cold_start import _connect  # noqa: PLC0415
    except ImportError:
        return None
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT callsign, task_type, cost_aud "
                "FROM public.keiracom_spawn_attribution "
                "WHERE task_id = %s "
                "ORDER BY ts ASC",
                (task_id,),
            )
            rows = cur.fetchall() or []
    except Exception:  # noqa: BLE001 — fail-OPEN; fleet breaker is the fail-safe
        log.warning(
            "v1_chain Gate 1: cost-ceiling query failed for task=%s", task_id, exc_info=True
        )
        return None
    finally:
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
    per_hop = [
        {"callsign": r[0] or "?", "chain_step": r[1] or "?", "cost_aud": float(r[2] or 0)}
        for r in rows
    ]
    total = sum(h["cost_aud"] for h in per_hop)
    return total, per_hop


def _post_ceiling_breach(
    entry: dict,
    chain_id: str,
    total_aud: float,
    per_hop: list[dict],
    *,
    dispatcher_url: str = _DISPATCHER_URL,
) -> None:
    """V1-battery Gate 1 — POST to /dispatcher/ceiling_breach when a task
    exceeds the per-task A$10 ceiling. Fail-open identical to
    _post_chain_complete: a notify failure must NEVER block the halt state save.
    """
    import urllib.error  # noqa: PLC0415 — lazy; only the breach-transition path needs it
    import urllib.request  # noqa: PLC0415

    payload = json.dumps(
        {
            "task_id": entry.get("task_id") or "?",
            "chain_id": chain_id,
            "brief": entry.get("brief") or "(no brief)",
            "ceiling_aud": _TASK_COST_CEILING_AUD,
            "total_aud": round(total_aud, 4),
            "per_hop": per_hop,
            "steps_done": list(entry.get("steps_done") or []),
        }
    ).encode()
    url = f"{dispatcher_url.rstrip('/')}/dispatcher/ceiling_breach"
    try:
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 — fixed loopback host
            log.info(
                "ceiling_breach notify: dispatcher status=%d for chain=%s total=A$%.4f",
                resp.status,
                chain_id,
                total_aud,
            )
    except (urllib.error.URLError, OSError):
        log.warning(
            "ceiling_breach notify: dispatcher unreachable for chain=%s", chain_id, exc_info=True
        )
    except Exception:  # noqa: BLE001 — must not break halt-state save
        log.warning("ceiling_breach notify: unexpected error for chain=%s", chain_id, exc_info=True)


def _post_verdict_halt(
    entry: dict,
    chain_id: str,
    rejecting_step: str,
    verdict: str,
    retry_count: int,
    *,
    escalated: bool,
    verdict_reason: str | None = None,
    dispatcher_url: str = _DISPATCHER_URL,
) -> None:
    """Phase 1 verdict-enforcement notify — POST to /dispatcher/verdict_halt.

    Fired in two cases:
    - escalated=False: chain looped back to aiden_plan with reviewer context.
      One #ceo line per loop iteration so Dave can see the retry chain.
    - escalated=True: retry budget exhausted (>= V1_VERDICT_MAX_RETRIES) —
      chain is halted permanently and needs Dave's call.

    Fail-open: dispatcher unreachable / non-2xx is logged + swallowed. A notify
    failure must NEVER block the halt-state save (mirrors _post_ceiling_breach).
    """
    import urllib.error  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    payload = json.dumps(
        {
            "task_id": entry.get("task_id") or "?",
            "chain_id": chain_id,
            "brief": entry.get("brief") or "(no brief)",
            "rejecting_step": rejecting_step,
            "verdict": verdict,
            "verdict_reason": verdict_reason or "",
            "retry_count": retry_count,
            "max_retries": V1_VERDICT_MAX_RETRIES,
            "escalated": escalated,
            "steps_done": list(entry.get("steps_done") or []),
            "rejections": list(entry.get("rejections") or []),
        }
    ).encode()
    url = f"{dispatcher_url.rstrip('/')}/dispatcher/verdict_halt"
    try:
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 — fixed loopback host
            log.info(
                "verdict_halt notify: dispatcher status=%d chain=%s step=%s verdict=%s "
                "retry=%d/%d escalated=%s",
                resp.status,
                chain_id,
                rejecting_step,
                verdict,
                retry_count,
                V1_VERDICT_MAX_RETRIES,
                escalated,
            )
    except (urllib.error.URLError, OSError):
        log.warning(
            "verdict_halt notify: dispatcher unreachable for chain=%s", chain_id, exc_info=True
        )
    except Exception:  # noqa: BLE001 — must not break halt-state save
        log.warning("verdict_halt notify: unexpected error for chain=%s", chain_id, exc_info=True)


def _post_chain_complete(
    entry: dict, chain_id: str, *, dispatcher_url: str = _DISPATCHER_URL
) -> None:
    """Agency_OS-zqni — POST to /dispatcher/chain_complete when the chain ends.

    Pairs with nd3b's notify_complete suppression (PR #1337): intermediate per-
    step task_complete posts are gated off; this single chain-result line is
    fired by the orchestrator and centralised in the dispatcher (cost lookup,
    multi-line formatting, Slack relay). Module-level so tests can monkeypatch.

    Dedup (Agency_OS-wdcw) is RECEIVER-SIDE — the dispatcher's
    /dispatcher/chain_complete endpoint consults a Supabase ledger
    (keiracom_chain_complete_posted) and skips the Slack relay when this
    chain_id was already posted. Receiver-side placement catches dup sources
    from anywhere (NATS redeliver, dispatcher restart, manual retry) AND keeps
    psycopg out of src/keiracom_system/ per boundary_matrix_v1 (the orchestrator
    is in the MAL-scoped tree; the dispatcher is the supabase-layer caller).

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
    """Inner async NATS publish — mirrors supervisor_wake_publish.publish_wake.

    Publishes to keiracom.dispatch.<role>, which is NOT bound to the
    agent_handoff JetStream — dispatch hops are routed via the
    /dispatcher/spawn HTTP path (_publish_envelope). This NATS publisher
    remains a core publish for any direct-NATS subscriber that may still
    listen on dispatch.<role>. The handoff JS stream subscribes to a
    different subject (CONSUMER_SUBJECT == keiracom.agent.handoff) — that
    capture is by subject binding on the publisher side too: any core
    nc.publish() to keiracom.agent.handoff is captured by the stream without
    requiring a js.publish() call.
    """
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
    """Dispatch a chain hop by POSTing to /dispatcher/spawn (HTTP).

    Was a NATS publish to keiracom.dispatch.<role>. Switched to /spawn
    (architectural Option B, Elliot 2026-05-29) so each chain hop spawns a
    fresh ephemeral agent_cold_start process:
        spawn → agent_cold_start.run() → save_exit_atoms publishes
        keiracom.agent.handoff → consumer's run_consumer fires advance_step
        → next hop dispatched.
    Closes the "persistent claude session has no handoff publisher" gap
    (the rehearsal-blocker found via research-task pre-build).

    spawn_kwargs are forwarded verbatim to SessionManager.spawn; the dispatcher
    auto-injects each non-None key as AGENT_<KEY> (src/dispatcher/main.py
    441-443/513-515) and pops `chain_step` first to land it as CHAIN_STEP
    un-prefixed (qjl7's _apply_chain_step_env at 421-435), which is what
    agent_cold_start's nd3b suppression reads.

    Fail-open: any error (transport, non-2xx) logged + False returned. The
    pure-NATS _publish_async (above) is kept for any remaining NATS-only
    subscribers / future use.
    """
    import urllib.error  # noqa: PLC0415 — lazy; only the hop-dispatch path needs it
    import urllib.request  # noqa: PLC0415

    body = {
        "backend": "tmux",  # Phase 1 scrubbed-tmux backend (Agency_OS-87ei)
        "key": f"chain-{envelope.get('chain_id', '?')}-{envelope.get('chain_step', '?')}",
        "spawn_kwargs": {
            "role": role,
            "callsign": role,  # bounded_spawn enforcer + supervisor attribution
            "tier": "standard",
            "variant": role,
            "brief": envelope.get("brief", ""),
            "chain_step": envelope.get("chain_step", ""),
            "chain_id": envelope.get("chain_id", ""),
            "task_id": envelope.get("task_id", ""),
            "atom_id": envelope.get("atom_id"),
        },
    }
    payload = json.dumps(body).encode()
    url = f"{_DISPATCHER_URL.rstrip('/')}/dispatcher/spawn"
    try:
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        # 35s client timeout to accommodate dispatcher's async ceiling queue
        # (PR #1361 — slot wait up to DISPATCHER_QUEUE_TIMEOUT_S default 300s).
        # 35s = enough to clear one slot-wait cycle; client times out before
        # the dispatcher's 300s ceiling timeout, so spurious queue timeouts
        # don't masquerade as transport failures.
        with urllib.request.urlopen(req, timeout=35) as resp:  # noqa: S310 — fixed loopback host
            status = resp.status
        log.info("v1_chain: /dispatcher/spawn role=%s key=%s status=%d", role, body["key"], status)
        return 200 <= status < 300
    except (urllib.error.URLError, OSError) as exc:
        log.error("v1_chain: /dispatcher/spawn failed role=%s: %s", role, exc)
        return False
    except Exception as exc:  # noqa: BLE001
        log.error("v1_chain: unexpected /spawn error role=%s: %s", role, exc)
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
    verdict: str | None = None,
    verdict_reason: str | None = None,
    clock: Callable[[], float] = time.time,
) -> list[dict]:
    """Record a step completion and dispatch the next step(s).

    Args:
        chain_id: Identifies the chain in the state file.
        completed_step: The step that just finished (e.g. "aiden_plan").
        atom_id: The atom_id returned by the completing agent for this step.
        verdict: Optional reviewer verdict. When ``completed_step`` is a
            reviewer step (max_challenge, orion_spec, atlas_safety) and the
            verdict is REJECT or HOLD, the chain halts forward progression and
            re-dispatches aiden_plan with the reviewer's context as the loop
            brief. Bounded by V1_VERDICT_MAX_RETRIES — after that the chain
            escalates to Dave (state=halted_max_retries). None / any other
            value = no enforcement (clean advance).
        verdict_reason: Optional one-liner the reviewer attaches to a non-clean
            verdict. Surfaced in the loop brief and the #ceo halt post.
        clock: Injectable for tests.

    Returns:
        List of envelope dicts that were dispatched (empty list if no dispatch
        occurred — either the chain is waiting on parallel partners, has
        reached ``complete``, or hit the retry-budget escalation).
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

    # Phase 1 verdict-enforcement nucleus. Runtime conditional (GOV-12):
    # if a reviewer step returned REJECT or HOLD, halt forward progression
    # and either (a) re-dispatch aiden_plan with the reviewer's context as a
    # loop brief, or (b) escalate to Dave when the retry budget is exhausted.
    # Must run BEFORE the ceiling check + fan-out so a rejecting parallel
    # partner cannot trigger further dispatches downstream.
    normalized_verdict = str(verdict).strip().upper() if verdict else ""
    if completed_step in REVIEWER_STEPS and normalized_verdict in VERDICT_HALT_SET:
        retries_so_far = int(entry.get("retry_count", 0) or 0)
        rejections = list(entry.get("rejections") or [])
        rejections.append(
            {
                "step": completed_step,
                "atom_id": atom_id,
                "verdict": normalized_verdict,
                "reason": verdict_reason or "",
                "loop_at": retries_so_far,
                "ts": clock(),
            }
        )
        entry["rejections"] = rejections
        # Cancel any in-flight parallel partner. We can't recall an already
        # published NATS envelope, but clearing pending here prevents the next
        # advance_step (from the partner's later completion) from falling
        # through to the "last parallel step" branch and marking complete.
        entry["pending"] = []

        if retries_so_far >= V1_VERDICT_MAX_RETRIES:
            # Retry budget exhausted — halt permanently and escalate.
            entry["current_step"] = "halted_max_retries"
            entry["verdict_halt"] = {
                "rejecting_step": completed_step,
                "verdict": normalized_verdict,
                "reason": verdict_reason or "",
                "retry_count": retries_so_far,
                "max_retries": V1_VERDICT_MAX_RETRIES,
                "escalated": True,
            }
            try:
                _post_verdict_halt(
                    entry,
                    chain_id,
                    completed_step,
                    normalized_verdict,
                    retries_so_far,
                    escalated=True,
                    verdict_reason=verdict_reason,
                )
            except Exception:  # noqa: BLE001 — must not break halt-state save
                log.warning(
                    "v1_chain verdict-halt(escalated): post raised for chain=%s",
                    chain_id,
                    exc_info=True,
                )
            _save_state(state)
            return []

        # Within retry budget — halt forward progression and loop back to
        # aiden_plan with the rejecter's atom + reason as the brief context.
        entry["retry_count"] = retries_so_far + 1
        entry["current_step"] = "aiden_plan"
        # Fresh slate for the next iteration. atom_ids per step is last-write-
        # wins (dict) so we leave the keys alone — the rejection list above is
        # the authoritative history.
        entry["steps_done"] = []
        loop_brief = (
            f"{entry.get('brief') or ''}\n\n"
            f"[verdict loop {retries_so_far + 1}/{V1_VERDICT_MAX_RETRIES}] "
            f"Reviewer {completed_step} returned {normalized_verdict}. "
            f"Reason: {verdict_reason or '(none given)'}. "
            f"Prior atom: {atom_id}. Re-plan addressing this feedback."
        )
        env = _build_envelope(entry["task_id"], chain_id, "aiden_plan", atom_id, loop_brief, clock)
        _publish_envelope(env, "aiden")
        dispatched.append(env)
        try:
            _post_verdict_halt(
                entry,
                chain_id,
                completed_step,
                normalized_verdict,
                retries_so_far + 1,
                escalated=False,
                verdict_reason=verdict_reason,
            )
        except Exception:  # noqa: BLE001 — must not break loop-state save
            log.warning(
                "v1_chain verdict-halt(loop): post raised for chain=%s",
                chain_id,
                exc_info=True,
            )
        _save_state(state)
        return dispatched

    # V1-battery Gate 1 — per-task A$10 ceiling. Query SUM(cost_aud) for
    # this task_id; halt + post #ceo if exceeded. Runs BEFORE the dispatch
    # branch so an over-ceiling task cannot fan out a new hop. fail-OPEN on
    # read error (None) — the chain proceeds and the fleet-level breaker
    # (#1297) remains the fail-SAFE backstop. GOV-12: this is the runtime
    # conditional, not a comment.
    task_id_for_query = entry.get("task_id") or chain_id
    ceiling_result = _query_task_cost_aud(task_id_for_query)
    if ceiling_result is not None:
        total_aud, per_hop = ceiling_result
        if total_aud > _TASK_COST_CEILING_AUD:
            log.error(
                "v1_chain Gate 1: ceiling breached chain=%s task=%s total=A$%.4f > A$%.2f — HALTING",
                chain_id,
                task_id_for_query,
                total_aud,
                _TASK_COST_CEILING_AUD,
            )
            entry["current_step"] = "halted_ceiling_exceeded"
            entry["ceiling_tripped"] = True
            entry["ceiling_total_aud"] = round(total_aud, 4)
            entry["ceiling_per_hop"] = per_hop
            entry["pending"] = []
            try:
                _post_ceiling_breach(entry, chain_id, total_aud, per_hop)
            except Exception:  # noqa: BLE001 — must not break halt-state save
                log.warning(
                    "v1_chain Gate 1: ceiling_breach raised at call site for chain=%s",
                    chain_id,
                    exc_info=True,
                )
            _save_state(state)
            return []

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
            # NOTE: _post_chain_complete is NOT called here — it fires from
            # _advance_step_async (the event-loop-level wrapper) instead.
            # asyncio.to_thread runs advance_step on a worker thread; parallel
            # hop completions (orion_spec + atlas_safety) arriving close in
            # time can both enter this branch before either has saved state,
            # causing duplicate (or triplicate) #ceo posts. Moving the post to
            # the single-threaded event loop with a `complete_posted` flag
            # serialises it (race found 2026-05-30 Elliot, fix Agency_OS-chain-
            # complete-post-event-loop).
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
    verdict: str | None = None,
    verdict_reason: str | None = None,
    clock: Callable[[], float] = time.time,
) -> list[dict]:
    """Async entrypoint for the V1 consumer loop (Atlas oevr).

    Delegates state-mutation work to advance_step on the thread pool (state
    I/O + urllib publishes are I/O-bound), then fires _post_chain_complete
    ONCE from the event-loop level. The post is here — not inside
    advance_step — to serialise it: parallel hop completions (orion_spec +
    atlas_safety) hitting the consumer back-to-back each enter advance_step
    on separate threads, and prior to this both threads could observe
    current_step == 'complete' before either persisted the
    "I already posted" flag → duplicate (or triplicate) #ceo posts.

    The complete_posted flag is a re-load-check-write triple under the
    event loop, which runs single-threaded: only one coroutine can observe
    `complete_posted is False` and flip it, so only one post fires.
    Race fixed 2026-05-30 (Elliot diagnosis).

    ``verdict`` / ``verdict_reason`` are forwarded verbatim into advance_step
    so the Phase 1 verdict-enforcement nucleus can halt + loop on REJECT/HOLD
    from a reviewer step.
    """
    envelopes = await asyncio.to_thread(
        advance_step,
        chain_id,
        completed_step,
        atom_id,
        verdict=verdict,
        verdict_reason=verdict_reason,
        clock=clock,
    )
    # Single-threaded serialisation point — only one coroutine wins the flip.
    state = _load_state()
    entry = state.get(chain_id) or {}
    if entry.get("current_step") == "complete" and not entry.get("complete_posted"):
        entry["complete_posted"] = True
        _save_state(state)
        try:
            _post_chain_complete(entry, chain_id)
        except Exception:  # noqa: BLE001 — final-post failure must not break completion
            log.warning(
                "v1_chain chain_complete raised at _advance_step_async for chain=%s",
                chain_id,
                exc_info=True,
            )
    return envelopes


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
        # Phase 1 verdict-enforcement (atlas-verdict-enforcement-phase1): the
        # handoff envelope may carry a reviewer's verdict + one-liner reason.
        # Forwarded verbatim — advance_step's runtime conditional decides
        # whether to halt+loop or advance.
        verdict = envelope.get("verdict")
        verdict_reason = envelope.get("verdict_reason")
        envelopes = await _advance_step_async(
            chain_id=task_id,
            completed_step=step,
            atom_id=atom_id,
            verdict=verdict,
            verdict_reason=verdict_reason,
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


async def _ensure_handoff_stream(js, subject: str = CONSUMER_SUBJECT) -> bool:
    """Bind to or create the JetStream stream covering subject. Returns success bool.

    Idempotent: if the stream already exists we proceed without modifying its
    config (an operator may have tuned storage tiers manually — refusing to
    overwrite preserves their intent). Returns False on any setup failure so
    run_consumer can fall back to core subscribe.
    """
    from nats.js.api import RetentionPolicy, StorageType, StreamConfig  # noqa: PLC0415
    from nats.js.errors import NotFoundError  # noqa: PLC0415

    try:
        await js.stream_info(JS_STREAM_NAME)
        return True
    except NotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001 — fall-back to core subscribe
        log.warning("v1_chain consumer: stream_info failed: %s", exc)
        return False
    try:
        await js.add_stream(
            config=StreamConfig(
                name=JS_STREAM_NAME,
                subjects=[subject],
                retention=RetentionPolicy.WORK_QUEUE,
                storage=StorageType.FILE,
            )
        )
        log.info(
            "v1_chain consumer: created JS stream=%s subject=%s retention=workqueue storage=file",
            JS_STREAM_NAME,
            subject,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("v1_chain consumer: add_stream failed: %s", exc)
        return False


async def _subscribe_jetstream_durable(js, subject, handler):
    """Create a durable push consumer + subscribe. Returns the subscription, or None on failure."""
    from nats.js.api import AckPolicy, ConsumerConfig  # noqa: PLC0415

    try:
        sub = await js.subscribe(
            subject=subject,
            durable=JS_CONSUMER_DURABLE,
            cb=handler,
            manual_ack=True,
            config=ConsumerConfig(
                durable_name=JS_CONSUMER_DURABLE,
                deliver_subject=JS_DELIVER_SUBJECT,
                ack_policy=AckPolicy.EXPLICIT,
            ),
        )
        log.info(
            "v1_chain consumer: JS durable=%s subscribed %s deliver=%s",
            JS_CONSUMER_DURABLE,
            subject,
            JS_DELIVER_SUBJECT,
        )
        return sub
    except Exception as exc:  # noqa: BLE001
        log.warning("v1_chain consumer: JS subscribe failed: %s", exc)
        return None


async def _dispatch_handoff_message(msg) -> None:
    """Decode + dispatch a single NATS message. Ack on success, nak on advance failure.

    Malformed payloads are acked (permanent — re-delivery would loop). Handler
    exceptions are naked so the WorkQueue stream re-delivers. Core (non-JS)
    subscribe path: ack/nak are no-ops because the msg object has no such methods.
    """
    ack_fn = getattr(msg, "ack", None)
    nak_fn = getattr(msg, "nak", None)
    try:
        payload = json.loads(msg.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        log.warning("v1_chain consumer: malformed payload: %s", exc)
        if callable(ack_fn):
            with contextlib.suppress(Exception):
                await ack_fn()
        return
    try:
        await _consumer_handle_envelope_async(payload)
    except Exception:  # noqa: BLE001 — log + nak; never raise out of cb
        log.warning("v1_chain consumer: dispatch failed; naking for redelivery", exc_info=True)
        if callable(nak_fn):
            with contextlib.suppress(Exception):
                await nak_fn()
        return
    if callable(ack_fn):
        with contextlib.suppress(Exception):
            await ack_fn()


async def run_consumer(nats_url: str | None = None) -> None:
    """Subscribe to CONSUMER_SUBJECT (durable JS consumer) and advance the chain on each handoff.

    Uses a JetStream durable push consumer (stream=agent_handoff,
    durable=chain-orchestrator, retention=WorkQueue, storage=File) so handoff
    messages published during dispatcher downtime survive restarts and get
    delivered when the consumer reconnects. Falls back to non-durable core
    nc.subscribe() if JetStream is unavailable or setup fails — preserves
    pre-fix behaviour on hosts without JS at the cost of dropped messages
    during downtime (logged loudly).

    Long-running; cancellable via task.cancel() — closes the NATS connection.
    """
    try:
        import nats  # noqa: PLC0415 — lazy; keeps module collectable without nats-py
    except ImportError as exc:
        log.error("v1_chain consumer: nats-py not installed; loop exits (%s)", exc)
        return
    url = nats_url or NATS_URL
    try:
        nc = await nats.connect(url, connect_timeout=5)
    except Exception as exc:  # noqa: BLE001
        log.error("v1_chain consumer: NATS connect failed url=%s: %s", url, exc)
        return

    js_subscribed = False
    try:
        js = nc.jetstream()
        if await _ensure_handoff_stream(js, CONSUMER_SUBJECT):
            sub = await _subscribe_jetstream_durable(
                js, CONSUMER_SUBJECT, _dispatch_handoff_message
            )
            js_subscribed = sub is not None
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "v1_chain consumer: JetStream setup failed (%s) — falling back to core subscribe", exc
        )

    if not js_subscribed:
        log.warning(
            "v1_chain consumer: durable JS unavailable — using core subscribe; "
            "handoffs published during downtime WILL be dropped"
        )
        try:
            await nc.subscribe(CONSUMER_SUBJECT, cb=_dispatch_handoff_message)
            log.info("v1_chain consumer: core-sub subscribed %s on %s", CONSUMER_SUBJECT, url)
        except Exception as exc:  # noqa: BLE001
            log.error("v1_chain consumer: core subscribe failed: %s", exc)
            with contextlib.suppress(Exception):
                await nc.close()
            return

    try:
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

    # --consumer: long-running NATS subscriber loop (systemd entry point for
    # keiracom-v1-chain-consumer.service — Agency_OS-zr7e). All other argv
    # forms fall through to the existing dispatch smoke for ad-hoc testing.
    if len(sys.argv) > 1 and sys.argv[1] == "--consumer":
        asyncio.run(run_consumer())
    else:
        brief = " ".join(sys.argv[1:]) or "test task from v1_chain_orchestrator __main__"
        cid = dispatch({"id": "smoke-task-1", "brief": brief})
        print(f"dispatched chain_id={cid}")
