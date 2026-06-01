"""v1_chain_workflow.py — Temporal V1 chain: aiden_plan → max_challenge → nova_build → [orion_spec ‖ atlas_safety].

Chain design (Agency_OS phase-1-2-5):
  Sequential: aiden_plan → max_challenge → nova_build
  Parallel:   orion_spec ‖ atlas_safety

Temporal is the handoff mechanism between hops — no NATS _publish_handoff()
calls from activities. prior_atom_id threads context forward via ChainStepInput
so the persona/recall layer can read it; the Temporal event history is the
durable record.

Idempotency: the activity checks public.keiracom_spawn_attribution for
(chain_id, chain_step) before calling Anthropic. Fail-open — DB unreachable
means proceed, not block.

Heartbeat: every 30 s inside the Anthropic call so Temporal detects live
progress. Cancellation is in a finally block to prevent task leak on timeout.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

try:
    from temporalio import activity, workflow
    from temporalio.common import RetryPolicy
except ImportError:  # SDK absent — module remains importable for unit tests
    activity = None  # type: ignore[assignment]
    workflow = None  # type: ignore[assignment]
    RetryPolicy = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

CHAIN_WORKFLOW_ID_PREFIX = "v1-chain"
V1_CHAIN_TASK_QUEUE = "keiracom-default"

CHAIN_STEP_TO_CALLSIGN: dict[str, str] = {
    "aiden_plan": "aiden",
    "max_challenge": "max",
    "nova_build": "nova",
    "orion_spec": "orion",
    "atlas_safety": "atlas",
}

_USD_TO_AUD = 1.55  # LAW II: 1 USD = 1.55 AUD


@dataclass
class ChainStepInput:
    task_id: str
    chain_id: str
    chain_step: str
    callsign: str
    brief: str
    prior_atom_id: str = ""
    dry_run: bool = False


@dataclass
class ChainStepOutput:
    atom_id: str
    cost_usd: float
    cost_aud: float
    latency_ms: float
    dry_run: bool


@dataclass
class ChainWorkflowInput:
    task_id: str
    chain_id: str = ""   # defaults to task_id when empty (resolved in workflow.run)
    brief: str = ""
    dry_run: bool = False


async def run_chain_step(inp: ChainStepInput) -> ChainStepOutput:
    """Activity: execute one chain hop via Anthropic SDK.

    Idempotency check → heartbeat → fetch_persona → call_anthropic →
    insert_attribution → return. All bookkeeping is fail-open; only persona
    fetch failure raises (causes Temporal retry up to the 40-min timeout).
    """
    if inp.dry_run:
        await asyncio.sleep(5)
        fake_id = f"dry-{inp.chain_step}-{uuid4().hex[:8]}"
        return ChainStepOutput(
            atom_id=fake_id,
            cost_usd=0.0,
            cost_aud=0.0,
            latency_ms=5000.0,
            dry_run=True,
        )

    # Idempotency check — fail-open on DB unavailability.
    try:
        from src.keiracom_system.vault.agent_cold_start import _connect  # noqa: PLC0415

        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT spawn_id FROM public.keiracom_spawn_attribution "
                    "WHERE chain_id = %s AND callsign = %s LIMIT 1",
                    (inp.chain_id, inp.callsign),
                )
                row = cur.fetchone()
            if row is not None:
                log.info(
                    "run_chain_step: idempotent skip chain_id=%s chain_step=%s",
                    inp.chain_id,
                    inp.chain_step,
                )
                return ChainStepOutput(
                    atom_id="",
                    cost_usd=0.0,
                    cost_aud=0.0,
                    latency_ms=0.0,
                    dry_run=False,
                )
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — idempotency check must never block the hop
        log.warning(
            "run_chain_step: idempotency DB check failed (fail-open) chain_step=%s",
            inp.chain_step,
        )

    # Background heartbeat — tells Temporal we're still alive during the API call.
    hb_task: asyncio.Task | None = None  # type: ignore[type-arg]

    async def _heartbeat() -> None:
        while True:
            if activity is not None:
                with contextlib.suppress(Exception):
                    activity.heartbeat(f"running {inp.chain_step}")
            await asyncio.sleep(30)

    hb_task = asyncio.create_task(_heartbeat())

    try:
        from src.keiracom_system.vault.api_agent_cold_start import (  # noqa: PLC0415
            call_anthropic,
            compute_cost,
            fetch_persona,
            insert_attribution,
        )

        persona_result = fetch_persona(inp.callsign)
        if persona_result is None:
            raise RuntimeError(
                f"run_chain_step: fetch_persona returned None for callsign={inp.callsign!r}"
            )
        persona, persona_token_count = persona_result

        api_key = os.environ["ANTHROPIC_API_KEY"]
        started_at = time.monotonic()
        (
            _text,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_write_tokens,
            rate_limit_retries,
        ) = await asyncio.to_thread(
            call_anthropic,
            api_key,
            persona,
            inp.brief,
            task_id=inp.task_id,
            callsign=inp.callsign,
            persona_token_count=persona_token_count,
        )
        latency_ms = (time.monotonic() - started_at) * 1000.0
        cost_usd, cost_aud = compute_cost(input_tokens, output_tokens)

    finally:
        hb_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb_task

    # Bookkeeping — fail-open; chain hop already completed its work.
    try:
        insert_attribution(
            callsign=inp.callsign,
            chain_id=inp.chain_id,
            task_id=inp.task_id,
            chain_step=inp.chain_step,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            cost_aud=cost_aud,
            latency_ms=latency_ms,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            rate_limit_retries=rate_limit_retries,
        )
    except Exception:  # noqa: BLE001
        log.warning(
            "run_chain_step: insert_attribution failed (fail-open) chain_step=%s",
            inp.chain_step,
        )

    # atom_id is empty — Temporal event history is the durable handoff record.
    return ChainStepOutput(
        atom_id="",
        cost_usd=cost_usd,
        cost_aud=cost_aud,
        latency_ms=latency_ms,
        dry_run=False,
    )


if activity is not None:
    run_chain_step = activity.defn(name="run_chain_step")(run_chain_step)  # type: ignore[assignment]


if workflow is not None:

    @workflow.defn(name="V1ChainWorkflow")
    class V1ChainWorkflow:
        """Temporal workflow: drive the 5-hop V1 agent chain.

        Sequential: aiden_plan → max_challenge → nova_build
        Parallel:   orion_spec ‖ atlas_safety

        Each hop runs as a `run_chain_step` activity with a 40-minute
        start_to_close_timeout and no retry (RetryPolicy(maximum_attempts=1)).
        The 40-min cap matches the dispatcher's AGENT_TIMEOUT_SECONDS=2400 and
        is the authoritative V1 per-hop SLA ratified in ceo:dave_decisions_2026_05_26.
        """

        @workflow.run
        async def run(self, inp: ChainWorkflowInput) -> dict:
            chain_id = inp.chain_id or inp.task_id
            step_timeout = timedelta(minutes=40)
            no_retry = RetryPolicy(maximum_attempts=1)
            atom_id = ""

            for step in ("aiden_plan", "max_challenge", "nova_build"):
                result: ChainStepOutput = await workflow.execute_activity(
                    "run_chain_step",
                    ChainStepInput(
                        task_id=inp.task_id,
                        chain_id=chain_id,
                        chain_step=step,
                        callsign=CHAIN_STEP_TO_CALLSIGN[step],
                        brief=inp.brief,
                        prior_atom_id=atom_id,
                        dry_run=inp.dry_run,
                    ),
                    start_to_close_timeout=step_timeout,
                    retry_policy=no_retry,
                    result_type=ChainStepOutput,
                )
                atom_id = result.atom_id

            orion_result, atlas_result = await asyncio.gather(
                workflow.execute_activity(
                    "run_chain_step",
                    ChainStepInput(
                        task_id=inp.task_id,
                        chain_id=chain_id,
                        chain_step="orion_spec",
                        callsign="orion",
                        brief=inp.brief,
                        prior_atom_id=atom_id,
                        dry_run=inp.dry_run,
                    ),
                    start_to_close_timeout=step_timeout,
                    retry_policy=no_retry,
                    result_type=ChainStepOutput,
                ),
                workflow.execute_activity(
                    "run_chain_step",
                    ChainStepInput(
                        task_id=inp.task_id,
                        chain_id=chain_id,
                        chain_step="atlas_safety",
                        callsign="atlas",
                        brief=inp.brief,
                        prior_atom_id=atom_id,
                        dry_run=inp.dry_run,
                    ),
                    start_to_close_timeout=step_timeout,
                    retry_policy=no_retry,
                    result_type=ChainStepOutput,
                ),
            )

            return {
                "task_id": inp.task_id,
                "chain_id": chain_id,
                "completed_steps": [
                    "aiden_plan",
                    "max_challenge",
                    "nova_build",
                    "orion_spec",
                    "atlas_safety",
                ],
                "dry_run": inp.dry_run,
            }

else:
    # Stub so the name V1ChainWorkflow is importable without SDK.
    class V1ChainWorkflow:  # type: ignore[no-redef]
        pass
