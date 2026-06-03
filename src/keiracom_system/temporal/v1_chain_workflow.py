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
import re
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

# NB: httpx is intentionally NOT imported at module-top.
# This module defines BOTH the activity (run_chain_step) and the workflow
# (V1ChainWorkflow). Temporal validates every workflow under a sandbox that
# re-evaluates module imports with deterministic-only restrictions — httpx
# transitively pulls urllib.request which the sandbox refuses, killing the
# whole worker at startup (validates ALL workflows including
# FleetSupervisorWorkflow). httpx is only used in the activity, which runs
# outside the sandbox, so import it lazily inside run_chain_step instead.

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

# Interceptor reroute (Head-of-Ops directive 2026-06-03): route chain hops
# through the local dispatcher's interceptor proxy instead of calling the
# Anthropic SDK directly. The interceptor runs governance + spend + rate
# checks then forwards to LiteLLM (governance_tier_fast → gpt-4o-mini under
# Dave's 2026-05-20 provider policy). Replaces the dead direct-Anthropic
# auth path. Override via INTERCEPTOR_URL env for tests.
_INTERCEPTOR_URL_ENV = "INTERCEPTOR_URL"
_DEFAULT_INTERCEPTOR_URL = "http://127.0.0.1:4001/interceptor/forward"
_INTERCEPTOR_TIMEOUT_S = 300.0
_INTERCEPTOR_MODEL = "governance_tier_fast"
_INTERCEPTOR_TIER = "starter"
_INTERCEPTOR_MAX_TOKENS = (
    2000  # matches governance_tier_fast LiteLLM cap; required by /interceptor/forward schema
)


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
    response_text: str = ""  # raw LLM output — input to capture_hop_reasoning


@dataclass
class CaptureReasoningInput:
    """Input to the capture_hop_reasoning activity (DESIGN-AMENDMENT-v2)."""

    chain_id: str
    hop_name: str
    callsign: str
    response_text: str


@dataclass
class ChainWorkflowInput:
    task_id: str
    chain_id: str = ""  # defaults to task_id when empty (resolved in workflow.run)
    brief: str = ""
    dry_run: bool = False
    # DESIGN-AMENDMENT-v2 Gap 2: SHARED counter (NOT a separate cap). Default
    # matches src/keiracom_system/chain/v1_chain_orchestrator.V1_VERDICT_MAX_RETRIES.
    # Passing it via workflow input avoids the temporalio workflow sandbox
    # restriction on importing modules that read os.environ at module-top.
    # Dispatch script may override via --max-capture-retries.
    max_capture_retries: int = 3


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
        import httpx  # noqa: PLC0415 — activity-only; module-top import breaks the workflow sandbox

        from src.keiracom_system.vault.api_agent_cold_start import (  # noqa: PLC0415
            fetch_persona,
            insert_attribution,
        )

        persona_result = fetch_persona(inp.callsign)
        if persona_result is None:
            raise RuntimeError(
                f"run_chain_step: fetch_persona returned None for callsign={inp.callsign!r}"
            )
        persona, _persona_token_count = persona_result

        interceptor_url = os.environ.get(_INTERCEPTOR_URL_ENV, _DEFAULT_INTERCEPTOR_URL)
        body = {
            "tenant_id": inp.task_id or "proof-chain",
            "prompt": inp.brief,
            "model": _INTERCEPTOR_MODEL,
            "tier": _INTERCEPTOR_TIER,
            "max_tokens": _INTERCEPTOR_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": persona},
                {"role": "user", "content": inp.brief},
            ],
        }

        def _post() -> dict:
            with httpx.Client(timeout=_INTERCEPTOR_TIMEOUT_S) as client:
                resp = client.post(interceptor_url, json=body)
                resp.raise_for_status()
                return resp.json()

        started_at = time.monotonic()
        response = await asyncio.to_thread(_post)
        latency_ms = (time.monotonic() - started_at) * 1000.0

        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError(
                f"run_chain_step: interceptor returned no choices, "
                f"body_keys={sorted(response.keys())!r}"
            )
        response_text = (choices[0].get("message") or {}).get("content") or ""
        usage = response.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        cache_read_tokens = int(usage.get("cache_read_tokens", 0))
        cache_write_tokens = int(usage.get("cache_write_tokens", 0))
        rate_limit_retries = 0
        cost_cents_aud = int(response.get("cost_cents_aud", 0))
        cost_aud = cost_cents_aud / 100.0
        cost_usd = cost_aud / _USD_TO_AUD if cost_aud else 0.0

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
        response_text=response_text,
    )


if activity is not None:
    run_chain_step = activity.defn(name="run_chain_step")(run_chain_step)  # type: ignore[assignment]


# ───────────────────────────────────────────────────────────────────────────
# capture_hop_reasoning — DESIGN-AMENDMENT-v2 Gap 1+2 (Aiden+Max concur).
# ───────────────────────────────────────────────────────────────────────────
# Parses DECISION: / CHALLENGE: / TRADEOFFS: / REJECTED: section headers from
# the hop's LLM output. INSERTs one row into public.reasoning_records.
# Fires BEFORE the next hop's run_chain_step in the workflow — a hop that
# produces no reasoning cannot advance the chain.
#
# Retry policy lives on the workflow-side execute_activity call, using the
# SHARED V1_VERDICT_MAX_RETRIES counter (NOT a separate cap) per Gap 2.
# DatabaseWriteError is non-retryable at the workflow level (hard-fail on
# DB unavailable — fail-loud per the proof_gate principle).
# ───────────────────────────────────────────────────────────────────────────

_REASONING_HEADERS = ("DECISION", "CHALLENGE", "TRADEOFFS", "REJECTED")
_REASONING_HEADER_RE = re.compile(
    r"^\s*\**\s*(?P<key>" + "|".join(_REASONING_HEADERS) + r")\s*:\s*(?P<rest>.*)$",
    re.IGNORECASE | re.MULTILINE,
)


class ReasoningParseError(RuntimeError):
    """Raised when a hop's response_text is missing required section headers.

    Temporal retries this via the workflow's shared V1_VERDICT_MAX_RETRIES
    policy — see the workflow.run wiring below.
    """


class DatabaseWriteError(RuntimeError):
    """Raised when the reasoning_records INSERT fails. Non-retryable."""


def parse_reasoning_sections(text: str) -> dict[str, str]:
    """Return {decision, challenge, tradeoffs, rejected_options} from `text`.

    Raises ReasoningParseError if any of the four sections is missing or
    empty after parsing. Section boundaries: each header line starts a
    section; the section runs until the next header line or end of text.
    """
    if not text or not text.strip():
        raise ReasoningParseError("empty response_text — no reasoning to parse")
    matches = list(_REASONING_HEADER_RE.finditer(text))
    if not matches:
        raise ReasoningParseError(
            "no DECISION:/CHALLENGE:/TRADEOFFS:/REJECTED: headers in response"
        )
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group("key").upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = (m.group("rest") + "\n" + text[start:end]).strip()
        if key not in sections:  # first occurrence wins
            sections[key] = body
    missing = [h for h in _REASONING_HEADERS if h not in sections or not sections[h].strip()]
    if missing:
        raise ReasoningParseError(f"missing or empty section(s): {missing}")
    return {
        "decision": sections["DECISION"],
        "challenge": sections["CHALLENGE"],
        "tradeoffs": sections["TRADEOFFS"],
        "rejected_options": sections["REJECTED"],
    }


async def capture_hop_reasoning(inp: CaptureReasoningInput) -> dict:
    """Activity: parse + persist deliberation reasoning for one chain hop.

    Returns {reasoning_record_id, hop_name, callsign} on success. Raises
    ReasoningParseError on parse failure (Temporal retries via the shared
    V1_VERDICT_MAX_RETRIES counter). Raises DatabaseWriteError on INSERT
    failure (non-retryable — hard-fail per Gap 2).
    """
    sections = parse_reasoning_sections(inp.response_text)
    try:
        from src.keiracom_system.vault.agent_cold_start import _connect  # noqa: PLC0415
    except ImportError as exc:
        raise DatabaseWriteError(f"reasoning_records: vault import failed: {exc}") from exc
    try:
        conn = _connect()
    except Exception as exc:  # noqa: BLE001
        raise DatabaseWriteError(f"reasoning_records: connect failed: {exc}") from exc
    try:
        # _connect() returns an autocommit=True connection. SET LOCAL /
        # set_config(is_local=true) only persists within a transaction, so
        # toggle autocommit off for this transaction. Restored in finally.
        prior_autocommit = conn.autocommit
        conn.autocommit = False
        with conn.cursor() as cur:
            # SET LOCAL rejects parameter binding — use set_config() to pass a value.
            cur.execute("SELECT set_config('agency_os.callsign', %s, true)", (inp.callsign,))
            cur.execute(
                "INSERT INTO public.reasoning_records "
                "(chain_id, hop_name, callsign, source, "
                "decision, challenge, tradeoffs, rejected_options) "
                "VALUES (%s, %s, %s, 'temporal_activity', %s, %s, %s, %s) "
                "RETURNING id",
                (
                    inp.chain_id,
                    inp.hop_name,
                    inp.callsign,
                    sections["decision"],
                    sections["challenge"],
                    sections["tradeoffs"],
                    sections["rejected_options"],
                ),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        raise DatabaseWriteError(f"reasoning_records: INSERT failed: {exc}") from exc
    finally:
        with contextlib.suppress(Exception):
            conn.autocommit = prior_autocommit
        with contextlib.suppress(Exception):
            conn.close()
    return {
        "reasoning_record_id": str(row[0]) if row else "",
        "hop_name": inp.hop_name,
        "callsign": inp.callsign,
    }


if activity is not None:
    capture_hop_reasoning = activity.defn(name="capture_hop_reasoning")(  # type: ignore[assignment]
        capture_hop_reasoning
    )


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
            # DESIGN-AMENDMENT-v2 Gap 2: SHARED counter, NOT a separate cap.
            # Value is plumbed through ChainWorkflowInput.max_capture_retries
            # (default matches v1_chain_orchestrator.V1_VERDICT_MAX_RETRIES) to
            # avoid the workflow-sandbox restriction on importing modules that
            # read os.environ at module-top.
            capture_retry = RetryPolicy(
                maximum_attempts=inp.max_capture_retries,
                non_retryable_error_types=["DatabaseWriteError"],
            )
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
                # Blocking position: capture deliberation BEFORE the next hop.
                # Dry-run skips capture (no response_text to parse).
                if not inp.dry_run:
                    await workflow.execute_activity(
                        "capture_hop_reasoning",
                        CaptureReasoningInput(
                            chain_id=chain_id,
                            hop_name=step,
                            callsign=CHAIN_STEP_TO_CALLSIGN[step],
                            response_text=result.response_text,
                        ),
                        start_to_close_timeout=step_timeout,
                        retry_policy=capture_retry,
                    )

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
            # Capture the parallel pair's reasoning BEFORE workflow completion.
            if not inp.dry_run:
                await asyncio.gather(
                    workflow.execute_activity(
                        "capture_hop_reasoning",
                        CaptureReasoningInput(
                            chain_id=chain_id,
                            hop_name="orion_spec",
                            callsign="orion",
                            response_text=orion_result.response_text,
                        ),
                        start_to_close_timeout=step_timeout,
                        retry_policy=capture_retry,
                    ),
                    workflow.execute_activity(
                        "capture_hop_reasoning",
                        CaptureReasoningInput(
                            chain_id=chain_id,
                            hop_name="atlas_safety",
                            callsign="atlas",
                            response_text=atlas_result.response_text,
                        ),
                        start_to_close_timeout=step_timeout,
                        retry_policy=capture_retry,
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
