"""agent_cold_start.py — ephemeral work-loop agent entrypoint (Agency_OS-yhm8 / 87ei).

The command the dispatcher runs (DISPATCHER_AGENT_COMMAND) INSIDE a scrubbed
``env -i`` tmux session: only VAULT_ADDR + VAULT_TOKEN + AGENT_* metadata are
inherited — no .env credentials (P10). Flow:

  1. resolve_into_env() — pull every fleet credential from Vault KV into os.environ
     (DATABASE_URL, ANTHROPIC_*, … are in SECRET_MANIFEST). The scrubbed env had
     none of these; this is the cold-start bootstrap.
  2. Resolve the task: AGENT_TASK_ID (or argv[1]) → fetch the public.tasks row.
  3. Claim it (available→active, auto_loop), compose a task-centric prompt, and
     spawn a FRESH headless ``claude`` subprocess (fresh-per-task V1, per
     docs/architecture/ephemeral_agent_system_scoping.md §4). Output flows to the
     tmux pane; the agent does the work and exits.
  4. Finalize the task lifecycle, then exit with the agent's return code.

Design decisions (Elliot-confirmed D1–D4, 2026-05-29):
  D1  self-composed task-centric prompt (NOT the callsign spawn_composer, which is
      inbox/callsign-centric and has no slot for a work-loop task brief).
  D2  headless ``claude -p <prompt> --dangerously-skip-permissions`` subprocess.
  D3  this entrypoint owns the public.tasks lifecycle (the consumer admits via a
      Valkey counter only and never touches status). rc 0 → 'done'.
  D4  a task_verifications row is ALWAYS inserted before 'done' — the
      require_verification_before_done trigger fires on every done transition and
      raises unless evidence exists, regardless of acceptance_criteria (Aiden catch).

NB: tasks_status_check has no 'failed' value, so a non-zero agent rc maps to
'blocked' (valid, needs-attention, not auto-retried) rather than 'failed'.

All external seams (resolve / fetch / claim / agent / finalize) are injectable so
the orchestration is unit-testable without Vault, a DB, or a real ``claude``.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from src.keiracom_system.vault.kv_resolver import resolve_into_env

logger = logging.getLogger(__name__)

AGENT_WORKDIR = os.environ.get("DISPATCHER_AGENT_WORKDIR", "/home/elliotbot/clawd/Agency_OS")
_DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:4001")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
# xjtn — callsign → (role, variant) for /dispatcher/persona. Mirrors
# api_agent_cold_start.CALLSIGN_TO_PERSONA so the CLI path injects the same
# persona_bank prompt the SDK path uses. Kept local (vs imported) to avoid
# coupling the CLI cold-start to the SDK module.
_CALLSIGN_TO_PERSONA: dict[str, tuple[str, str]] = {
    "aiden": ("deliberator", "aiden"),
    "max": ("deliberator", "max"),
    "nova": ("worker", "nova"),
    "orion": ("reviewer", "orion"),
    "atlas": ("reviewer", "atlas"),
    "face": ("face", "face"),
}
_PERSONA_FETCH_TIMEOUT_S = 2.0
# NB: public.tasks has NO task_type column — task_type is derived from tags and
# reaches the agent via the AGENT_TASK_TYPE env var (injected by the dispatcher).
_TASK_COLS = ("id", "title", "description", "priority", "acceptance_criteria")

# Exit codes (distinct from a claude rc so the loop can tell apart cold-start
# failures from agent failures): 0 ok / claim-lost; 2 no task id; 3 task absent.
RC_NO_TASK_ID = 2
RC_TASK_ABSENT = 3

# zr7e.9 — V1 chain AtomV1 handoff transport. After classify_and_save writes
# atoms to Hindsight fleet_decisions on exit, publish each (task_id, atom_id)
# to NATS so the next agent in the chain can recall the atom at spawn. Single
# subject; subscribers self-route by role until chain-progression wiring lands.
NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
HANDOFF_SUBJECT = "keiracom.agent.handoff"

# Phase 1 verdict-enforcement publisher wire-up (nova-verdict-publisher-wire).
# Reviewer callsigns whose handoff atoms carry a verdict (APPROVE / HOLD /
# REJECT). Mirrors v1_chain_orchestrator.REVIEWER_STEPS via FROM_TO_STEP:
#   max   -> max_challenge
#   orion -> orion_spec
#   atlas -> atlas_safety
# Source of truth for the chain side is v1_chain_orchestrator.REVIEWER_STEPS;
# duplicated as callsigns here to avoid importing the chain module at handoff
# publish (lazy import in _attach_verdict_if_reviewer keeps the cold-start path
# DB-free for envelope build). Drift is caught by
# test_publisher_reviewer_callsigns_match_chain_reviewer_steps.
_REVIEWER_HANDOFF_CALLSIGNS: frozenset[str] = frozenset({"max", "orion", "atlas"})


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_DSN")
    if not dsn:
        raise RuntimeError("agent_cold_start: DATABASE_URL absent after Vault resolve")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def _connect() -> Any:
    import psycopg

    return psycopg.connect(_dsn(), connect_timeout=10, prepare_threshold=None, autocommit=True)


def fetch_task(task_id: str, *, conn: Any = None) -> dict | None:
    """Fetch the public.tasks row for task_id. None if absent.

    If AGENT_BRIEF is set (injected by the dispatcher for chain spawns that
    pass the brief inline), return a synthetic task dict without hitting the
    DB — mirrors the SDK path's AGENT_BRIEF behaviour.
    """
    brief = os.environ.get("AGENT_BRIEF", "").strip()
    if brief:
        return {
            "id": task_id,
            "title": os.environ.get(
                "AGENT_TASK_TITLE", ""
            ),  # not in dispatcher passthrough → always "" for chain spawns
            "description": brief,
            "priority": None,
            "acceptance_criteria": None,
        }
    own = conn is None
    conn = conn or _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description, priority, acceptance_criteria "
                "FROM public.tasks WHERE id = %s",
                (task_id,),
            )
            row = cur.fetchone()
        return dict(zip(_TASK_COLS, row, strict=True)) if row else None
    finally:
        if own:
            conn.close()


def claim_task(task_id: str, callsign: str | None, *, conn: Any = None) -> bool:
    """Atomic available→active claim. True iff this agent won the claim.

    Short-circuits to True when AGENT_BRIEF is set — the task is synthetic
    (no public.tasks row), so the UPDATE WHERE status='available' returns
    rowcount=0 and claim would incorrectly abort the chain spawn.
    """
    if os.environ.get("AGENT_BRIEF", "").strip():
        return True
    own = conn is None
    conn = conn or _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.tasks SET status='active', claimed_at=now(), "
                "claim_source='auto_loop', claimed_by=COALESCE(%s, claimed_by) "
                "WHERE id=%s AND status='available'",
                (callsign, task_id),
            )
            return cur.rowcount == 1
    finally:
        if own:
            conn.close()


def compose_prompt(task: dict) -> str:
    """Task-centric initial prompt for the ephemeral worker (D1)."""
    parts = [
        "You are an ephemeral Keiracom worker agent. Do exactly this one task, "
        "then stop — do not wait for further input.",
        f"Task ID: {task['id']}",
        f"Title: {task.get('title') or '(none)'}",
        f"Type: {task.get('task_type') or 'build'}",
    ]
    if task.get("description"):
        parts.append(f"Description:\n{task['description']}")
    if task.get("acceptance_criteria"):
        parts.append(f"Acceptance criteria (must be met):\n{task['acceptance_criteria']}")
    parts.append("Complete the task end to end, then exit.")
    return "\n\n".join(parts)


def fetch_persona_prompt(
    callsign: str | None, *, dispatcher_url: str = _DISPATCHER_URL
) -> str | None:
    """xjtn — GET /dispatcher/persona for this callsign; return prompt_text or None.

    Fail-open by design: missing callsign, unknown mapping, network error, 4xx/5xx,
    or empty prompt_text all return None and the caller proceeds without
    --append-system-prompt. Bounded by _PERSONA_FETCH_TIMEOUT_S (no retry —
    blocking the cold-start on persona fetch is a worse failure than running with
    no persona). api_agent_cold_start.fetch_persona retries for 60s because the
    SDK path *requires* a persona; here it is an enhancement.
    """
    if not callsign:
        return None
    mapping = _CALLSIGN_TO_PERSONA.get(callsign)
    if mapping is None:
        logger.warning("agent_cold_start: no persona mapping for callsign=%s", callsign)
        return None
    role, variant = mapping
    url = (
        f"{dispatcher_url.rstrip('/')}/dispatcher/persona"
        f"?role={role}&tier=standard&variant={variant}"
    )
    try:
        with urllib.request.urlopen(url, timeout=_PERSONA_FETCH_TIMEOUT_S) as resp:  # noqa: S310
            payload = json.loads(resp.read())
        prompt = payload.get("prompt_text")
        if isinstance(prompt, str) and prompt.strip():
            return prompt
        logger.warning("agent_cold_start: persona endpoint returned empty prompt_text")
        return None
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("agent_cold_start: persona fetch failed (fail-open): %s", exc)
        return None


def run_agent(
    prompt: str,
    *,
    popen: Callable[..., Any] = subprocess.Popen,
    fetch_persona: Callable[[str | None], str | None] = fetch_persona_prompt,
) -> int:
    """Spawn a fresh headless ``claude`` subprocess for this task (D2). Returns its rc.

    xjtn: when AGENT_CALLSIGN resolves to a persona_bank entry, the prompt text
    is appended to claude's system prompt via --append-system-prompt so the
    worker actually inherits its role identity (Nova artifact-discipline /
    Orion+Atlas two-phase review). Fail-open — see fetch_persona_prompt.
    """
    cmd = [CLAUDE_BIN, "-p", prompt, "--dangerously-skip-permissions"]
    persona_prompt = fetch_persona(os.environ.get("AGENT_CALLSIGN"))
    if persona_prompt:
        cmd.extend(["--append-system-prompt", persona_prompt])
    proc = popen(cmd, cwd=AGENT_WORKDIR)
    return proc.wait()


def finalize_task(
    task_id: str, rc: int, acceptance_criteria: str | None, *, conn: Any = None
) -> None:
    """rc 0 → 'done'; rc != 0 → 'blocked' (no 'failed' in tasks_status_check).

    On 'done', ALWAYS insert a task_verifications row first: the
    require_verification_before_done trigger fires on every done transition and
    raises unless evidence exists — acceptance_criteria NULL/empty does NOT bypass
    the gate (Aiden catch). Without this, a NULL-acceptance task crashes on the
    UPDATE and stays stuck 'active'.

    Short-circuits (no-op) when AGENT_BRIEF is set — the task is synthetic
    (no public.tasks row), so the task_verifications INSERT would raise a
    ForeignKeyViolation and the tasks UPDATE would silently update 0 rows.
    """
    if os.environ.get("AGENT_BRIEF", "").strip():
        return
    own = conn is None
    conn = conn or _connect()
    status = "done" if rc == 0 else "blocked"
    try:
        with conn.cursor() as cur:
            if status == "done":
                test_output = (
                    f"claude rc=0 (acceptance: {acceptance_criteria[:300]})"
                    if acceptance_criteria
                    else "claude rc=0 (task ran to completion; no acceptance criteria)"
                )
                cur.execute(
                    "INSERT INTO public.task_verifications "
                    "(task_id, verified_by, behavioral_test, test_output) VALUES (%s,%s,%s,%s)",
                    (task_id, "agent_cold_start", "ephemeral agent ran to completion", test_output),
                )
            cur.execute("UPDATE public.tasks SET status=%s WHERE id=%s", (status, task_id))
    finally:
        if own:
            conn.close()


def notify_complete(
    task_id: str,
    callsign: str,
    title: str,
    status: str,
    rc: int,
    *,
    dispatcher_url: str = _DISPATCHER_URL,
) -> None:
    """POST /dispatcher/task_complete so Dave sees the result in #ceo.

    Fail-open: any error (network, dispatcher down, Slack failure) is logged
    and swallowed — a notification failure must never block the task lifecycle.

    Chain-step suppression (Agency_OS-nd3b): the v1_chain_orchestrator dispatch
    envelope carries `chain_step` and the dispatcher injects it as the CHAIN_STEP
    env var at spawn. Only the FINAL step (CHAIN_STEP=='complete') posts to #ceo
    — intermediate hops (aiden_plan / max_challenge / nova_build / orion_review /
    atlas_review) suppress to keep Dave from seeing N notifications per directive.
    CHAIN_STEP absent preserves today's behavior (single-step legacy tasks notify).
    """
    # Fallback to AGENT_CHAIN_STEP for forward-compat with the dispatcher's
    # AGENT_*-prefixed auto-injection from spawn_kwargs (Agency_OS-qjl7 /
    # Scout's finding on src/dispatcher/main.py:441-443+513-515). Either name
    # resolves so any upstream injector wins.
    chain_step = os.environ.get("CHAIN_STEP") or os.environ.get("AGENT_CHAIN_STEP")
    if chain_step and chain_step != "complete":
        logger.info(
            "notify_complete: suppressed (intermediate chain_step=%s) task=%s",
            chain_step,
            task_id,
        )
        return
    payload = json.dumps(
        {"task_id": task_id, "callsign": callsign, "title": title, "status": status, "rc": rc}
    ).encode()
    url = f"{dispatcher_url.rstrip('/')}/dispatcher/task_complete"
    try:
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
        logger.info("notify_complete: dispatcher responded %s", body[:200])
    except (urllib.error.URLError, OSError):
        logger.warning(
            "notify_complete: dispatcher unreachable for task=%s", task_id, exc_info=True
        )
    except Exception:  # noqa: BLE001
        logger.exception("notify_complete: unexpected error for task=%s", task_id)


def _attach_verdict_if_reviewer(payload: dict, *, from_callsign: str, atom_id: str) -> None:
    """Phase 1 verdict-enforcement publisher wire-up (nova-verdict-publisher-wire).

    Mutates ``payload`` in place: when ``from_callsign`` is a reviewer (max /
    orion / atlas) and ``atom_id`` is non-empty, calls
    ``parse_reviewer_verdict(atom_id)`` and sets payload['verdict'] +
    payload['verdict_reason']. The orchestrator consumer
    (_consumer_handle_envelope_async) reads these keys and forwards them to
    advance_step, where PR #1418's REJECT/HOLD halt+loop enforcement fires.

    Fail-open: any error (import miss, AtomStore unreachable, parse exception)
    leaves payload untouched. The consumer treats missing-verdict on a reviewer
    completion as legacy clean-advance — that's the safe-default behaviour for
    handoffs published before this wire-up, and remains correct when the parse
    fails: advance_step itself does NOT switch on verdict for non-reviewer
    steps, so the only impact of a missed reviewer parse is "advances when it
    should halt". Atlas's PR #1418 covers that exact race: HOLD is the
    safe-default verdict returned by parse_reviewer_verdict on fetch failure,
    so when the call succeeds it returns HOLD; only an outer raise (import
    missing, etc.) skips attachment entirely.

    No-op for non-reviewer callsigns (aiden / nova / face).
    """
    if from_callsign.lower() not in _REVIEWER_HANDOFF_CALLSIGNS:
        return
    if not atom_id:
        return
    try:
        from src.keiracom_system.chain.reviewer_atom import (  # noqa: PLC0415
            parse_reviewer_verdict,
        )

        ra = parse_reviewer_verdict(atom_id)
        payload["verdict"] = ra.verdict
        payload["verdict_reason"] = ra.rationale
    except Exception as exc:  # noqa: BLE001 — fail-open: handoff must never block
        logger.warning(
            "agent_cold_start: verdict-attach failed for atom_id=%s callsign=%s: %s",
            atom_id,
            from_callsign,
            exc,
        )


def _publish_handoff(*, task_id: str, atom_id: str, to_callsign: str = "") -> bool:
    """zr7e.9 — publish an AtomV1 handoff pointer to NATS keiracom.agent.handoff.

    Mirrors scripts/fleet_supervisor._nats_publish_state: lazy nats-py import,
    asyncio.run(connect/publish/flush/close), fail-open warn on failure. Returns
    True on success, False on any failure — never raises.

    Payload: {task_id, atom_id, from_callsign, to_callsign, ts}. from_callsign
    comes from AGENT_CALLSIGN (set by the dispatcher at spawn). to_callsign
    defaults to "" — subscribers on the single keiracom.agent.handoff subject
    self-route by their chain role until chain-progression wiring lands.

    Phase 1 verdict-enforcement (nova-verdict-publisher-wire): when the
    completing agent is a reviewer (max / orion / atlas), the payload is
    enriched with ``verdict`` + ``verdict_reason`` parsed from the atom. The
    orchestrator consumer reads these and forwards to advance_step's halt+loop
    enforcement (PR #1418). Non-reviewer callsigns are unaffected.
    """
    from_callsign = os.environ.get("AGENT_CALLSIGN", "")
    payload_dict: dict = {
        "task_id": task_id,
        "atom_id": atom_id,
        "from_callsign": from_callsign,
        "to_callsign": to_callsign,
        "ts": int(time.time()),
    }
    _attach_verdict_if_reviewer(payload_dict, from_callsign=from_callsign, atom_id=atom_id)
    payload = json.dumps(payload_dict).encode()
    try:
        import asyncio  # noqa: PLC0415 — lazy, mirrors save_exit_atoms / fleet_supervisor

        import nats.aio.client as nats_client  # noqa: PLC0415 — optional dep

        async def _publish() -> None:
            nc = nats_client.Client()
            await nc.connect(NATS_URL, connect_timeout=2)
            try:
                await nc.publish(HANDOFF_SUBJECT, payload)
                await nc.flush()
            finally:
                await nc.close()

        asyncio.run(_publish())
        logger.info(
            "agent_cold_start: NATS PUBLISH %s → task_id=%s atom_id=%s",
            HANDOFF_SUBJECT,
            task_id,
            atom_id,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open: handoff must never block agent exit
        logger.warning(
            "agent_cold_start: NATS handoff failed (non-fatal) task_id=%s: %s",
            task_id,
            exc,
        )
        return False


def save_exit_atoms(task: dict, rc: int, status: str) -> None:
    """Capture the completed task as AtomV1 atoms in Hindsight (Agency_OS-zr7e.4),
    then publish per-atom handoff pointers to NATS keiracom.agent.handoff (zr7e.9).

    Mirrors face.py's exit-cycle: feed the task brief + completion stamp to
    ``classify_and_save``, which writes an atom per ratified decision it detects
    above the confidence threshold (most build tasks detect none — that is fine).
    For each atom_id returned, publishes (task_id, atom_id) to NATS so the next
    agent in the V1 chain can recall the atom at spawn (L2 Hindsight recall).

    Fail-open: ``classify_and_save`` is already internally fail-open; the outer
    try/except also swallows import / asyncio.run / unexpected errors here, and
    ``_publish_handoff`` itself returns False rather than raising on NATS errors.
    Memory capture + handoff must NEVER block the task lifecycle.
    """
    try:
        import asyncio  # noqa: PLC0415 — lazy

        from src.keiracom_system.chat.exit_cycle import (  # noqa: PLC0415
            classify_and_save,
        )

        brief = task.get("description") or task.get("title") or ""
        conversation = [
            {
                "role": "user",
                "content": f"Task {task['id']}: {task.get('title') or ''}\n\n{brief}".strip(),
            },
            {
                "role": "assistant",
                "content": f"Task {task['id']} completed rc={rc} (status={status}).",
            },
        ]
        customer_id = int(os.environ.get("AGENT_CUSTOMER_ID", "1"))  # fleet tenant 1 = Dave
        result = asyncio.run(classify_and_save(conversation, customer_id))
        # zr7e.9 handoff publish — one NATS message per atom_id.
        for atom_id in getattr(result, "atom_ids", None) or []:
            _publish_handoff(task_id=str(task["id"]), atom_id=atom_id)
        logger.info("save_exit_atoms: %s", getattr(result, "skipped_reason", None) or "atoms saved")
    except Exception:  # noqa: BLE001 — never block completion on memory capture
        logger.exception("save_exit_atoms: unexpected error for task=%s", task.get("id"))


def _recall_spawn_context(task: dict) -> str:
    """zr7e.5 — L2 Hindsight recall block for this task's spawn prompt.

    Delegates to src.retrieval.spawn_recall.build_spawn_context_block which
    already enforces the KEI-55 per-block context-budget cap (so we never blow
    the agent's context window). Fail-open: returns "" on any error so the
    spawn proceeds without prior context rather than aborting.
    """
    try:
        from src.retrieval.spawn_recall import (  # noqa: PLC0415 — lazy
            build_spawn_context_block,
        )

        return build_spawn_context_block(
            task_type=task.get("task_type") or "build",
            task_brief=task.get("description") or task.get("title") or "",
        )
    except Exception as exc:  # noqa: BLE001 — recall must never block a spawn
        logger.warning("agent_cold_start: L2 spawn-recall failed (non-fatal): %s", exc)
        return ""


def run(
    *,
    resolve: Callable[..., Any] = resolve_into_env,
    fetch: Callable[..., dict | None] = fetch_task,
    claim: Callable[..., bool] = claim_task,
    agent: Callable[..., int] = run_agent,
    finalize: Callable[..., None] = finalize_task,
    notify: Callable[..., None] = notify_complete,
    save_atoms: Callable[..., None] = save_exit_atoms,
    spawn_recall: Callable[[dict], str] = _recall_spawn_context,
) -> int:
    """Cold-start orchestration. Returns the process exit code."""
    logging.basicConfig(level=logging.INFO)
    resolve()  # Vault bootstrap → fleet creds in os.environ
    task_id = os.environ.get("AGENT_TASK_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not task_id:
        logger.error("agent_cold_start: no AGENT_TASK_ID in env/argv")
        return RC_NO_TASK_ID
    task = fetch(task_id)
    if task is None:
        logger.error("agent_cold_start: task %s not found", task_id)
        return RC_TASK_ABSENT
    task["task_type"] = os.environ.get("AGENT_TASK_TYPE", "build")  # not a tasks column
    if not claim(task_id, os.environ.get("AGENT_CALLSIGN")):
        logger.warning(
            "agent_cold_start: task %s not claimable (already taken) — exiting clean", task_id
        )
        return 0  # another agent owns it; not our failure
    # zr7e.5: prepend the L2 Hindsight recall block (when present) ahead of the
    # task-centric prompt so the agent enters the chain with prior context
    # instead of cold.
    prompt = compose_prompt(task)
    recall_block = spawn_recall(task)
    if recall_block:
        prompt = f"{recall_block}\n\n{prompt}"
    rc = agent(prompt)
    finalize(task_id, rc, task.get("acceptance_criteria"))
    status = "done" if rc == 0 else "blocked"
    save_atoms(task, rc, status)  # AtomV1 memory capture (zr7e.4) — fail-open
    notify(
        task_id,
        os.environ.get("AGENT_CALLSIGN", "worker"),
        task.get("title") or "",
        status,
        rc,
    )
    logger.info("agent_cold_start: task %s finished rc=%d status=%s", task_id, rc, status)
    return rc


def main() -> int:  # pragma: no cover — process entrypoint
    return run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
