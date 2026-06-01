"""api_agent_cold_start.py — ephemeral V1 chain agent via Anthropic SDK (Agency_OS-l6i2).

Replaces the CLI subprocess spawn (Claude Code binary) with a direct Anthropic
SDK call so each chain hop captures REAL cost / latency / token usage and
fires AtomV1 + handoff publish on exit — what Dave requires for the V1
dress rehearsal.

Triggered by the dispatcher's /spawn endpoint when
``DISPATCHER_AGENT_COMMAND=python3 -m src.keiracom_system.vault.api_agent_cold_start``
is set in the host env.

Flow (per chain hop):
  1. Resolve env: ANTHROPIC_API_KEY (+ AGENT_* spawn_kwargs injected by the
     dispatcher per Agency_OS-qjl7).
  2. Map callsign → (role_type, variant) — persona_bank's schema uses
     deliberator/reviewer/worker as ``role`` and the callsign as ``variant``.
  3. GET /dispatcher/persona?role=<role_type>&tier=standard&variant=<variant>
     with bounded retry (Nova's worker persona may land in parallel — Elliot
     directive 2026-05-29 — so retry up to 60s instead of failing fast).
  3b. Build the L2 Hindsight recall block via spawn_recall.build_spawn_context_block
     (task_type derived from chain_step, brief from AGENT_BRIEF). Fail-open: any
     retrieval error → "" so the spawn proceeds without prior context.
  4. anthropic.Anthropic(...).messages.create(model='claude-sonnet-4-6',
     max_tokens=8096, system=<persona with cache_control>,
     messages=[{role:'user', content:[<recall_block with cache_control>, <brief>]}]).
  5. Record latency_ms; compute cost_usd = (in*3 + out*15) / 1e6 and
     cost_aud = cost_usd * 1.55 (LAW II — both columns stored so zqni reads AUD
     directly from the table without re-multiplying).
  6. INSERT keiracom_spawn_attribution row (Nova migration: cost_aud, latency_ms,
     chain_id, task_id are new NOT-NULL/NULLABLE columns).
  7. classify_and_save(conversation=[user, assistant], customer_id=1) — writes
     AtomV1 atoms to Hindsight fleet_decisions and returns atom_ids.
  8. _publish_handoff(task_id, atom_id, to_callsign='') per atom_id — fires the
     keiracom.agent.handoff NATS message the v1_chain_orchestrator consumer
     waits on (Agency_OS-oevr).
  9. Exit 0.

Exit codes (distinct so the loop can categorise failures):
  0 ok | 2 missing AGENT_* env | 3 persona fetch failed | 4 API call failed |
  5 anthropic-py not installed.

DB INSERT failures and handoff publish failures are fail-open (logged, not
blocking) — the chain hop has already completed the work; bookkeeping should
never break completion.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Pricing (USD per million tokens — Sonnet 4 / claude-sonnet-4-6).
_INPUT_USD_PER_M = 3.0
_OUTPUT_USD_PER_M = 15.0
_USD_TO_AUD = 1.55  # CLAUDE.md LAW II: 1 USD = 1.55 AUD (no exceptions).

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8096
_DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:4001")

# Persona_bank schema: role=<role_type>, variant=<callsign>. Maps the chain's
# callsigns (which the dispatcher injects as AGENT_ROLE/AGENT_CALLSIGN) to the
# (role, variant) pair the /dispatcher/persona endpoint expects.
CALLSIGN_TO_PERSONA: dict[str, tuple[str, str]] = {
    "aiden": ("deliberator", "aiden"),
    "max": ("deliberator", "max"),
    "nova": ("worker", "nova"),
    "orion": ("reviewer", "orion"),
    "atlas": ("reviewer", "atlas"),
    "face": ("face", "face"),
}

_PERSONA_RETRY_MAX_SECONDS = 60
_PERSONA_RETRY_INTERVAL = 1.0

# V1 chain step → workload class (TASK_TYPES). The attribution table's
# task_type column constrains values to the logger.py TASK_TYPES set
# {pr_review, deliberation, build, chat, dispatch_mgmt, unknown} — chain_step
# values (aiden_plan, max_challenge, ...) are chain *positions*, not workload
# classes, and inserting them raw violates the table CHECK. Map each step to
# its closest workload class so attribution rollups (cost-by-task_type) bucket
# the V1 chain into the same categories used by the rest of the dispatcher.
_CHAIN_STEP_TO_TASK_TYPE: dict[str, str] = {
    "aiden_plan": "deliberation",
    "max_challenge": "deliberation",
    "nova_build": "build",
    "orion_spec": "pr_review",
    "atlas_safety": "pr_review",
}

# V1-battery Gate 2 — 429/529 retry (Elliot dispatch 2026-05-30 ~11:35 AEST).
# Exponential backoff: 1s, 2s, 4s, 8s ... capped at 60s. max 4 attempts means
# the call_anthropic_with_retry helper attempts once + 3 retries. Retry-After
# header (when present, integer seconds) overrides backoff for that attempt.
_RATE_LIMIT_MAX_ATTEMPTS = 4
_RATE_LIMIT_BASE_BACKOFF_S = 1.0
_RATE_LIMIT_MAX_BACKOFF_S = 60.0

# Anthropic prompt-caching threshold (Sonnet 4.x — docs.anthropic.com/.../prompt-caching).
# Personas at or above this size go through the cache_control: ephemeral path so
# back-to-back chain hops with the same persona hit the 5-min cache (5x cheaper
# reads); personas below it would never cache anyway, so we send a plain str
# system. 1-hour TTL deliberately NOT used — 2x write cost vs 1.25x for 5-min.
_PROMPT_CACHE_MIN_TOKENS = 1024
_OVERLOADED_STATUS_CODES: frozenset[int] = frozenset({429, 503, 529})
_OPS_FAILURE_SUBJECT = os.environ.get("OPS_FAILURE_SUBJECT", "keiracom.ops.failure")
_NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")

# Exit codes
RC_NO_AGENT_ENV = 2
RC_PERSONA_FAILED = 3
RC_API_FAILED = 4
RC_SDK_MISSING = 5


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default) or default


def fetch_persona(
    callsign: str, *, dispatcher_url: str = _DISPATCHER_URL
) -> tuple[str, int] | None:
    """GET /dispatcher/persona with retry (up to 60s; Nova's worker persona may
    land in parallel). Returns (prompt_text, token_count) or None on terminal failure.

    The token_count is needed by call_anthropic to gate prompt caching on the
    1,024-token minimum cacheable prefix threshold (Sonnet 4.x — Anthropic docs
    2026-05-30). Personas below that threshold skip the cache_control block
    entirely; over-threshold personas get an ephemeral cache breakpoint.
    """
    mapping = CALLSIGN_TO_PERSONA.get(callsign)
    if mapping is None:
        logger.error("api_agent_cold_start: no persona mapping for callsign=%s", callsign)
        return None
    role_type, variant = mapping
    url = (
        f"{dispatcher_url.rstrip('/')}/dispatcher/persona"
        f"?role={role_type}&tier=standard&variant={variant}"
    )
    deadline = time.monotonic() + _PERSONA_RETRY_MAX_SECONDS
    last_err: Exception | None = None
    while True:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 — fixed loopback
                payload = json.loads(resp.read())
            prompt = payload.get("prompt_text")
            if isinstance(prompt, str) and prompt.strip():
                try:
                    token_count = int(payload.get("token_count") or 0)
                except (TypeError, ValueError):
                    token_count = 0
                return prompt, token_count
            logger.warning("api_agent_cold_start: persona endpoint returned empty prompt_text")
            return None
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code != 404:
                logger.error("api_agent_cold_start: persona HTTP %s on %s", exc.code, url)
                return None
            # 404 → maybe loading in parallel; retry until deadline.
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last_err = exc
        if time.monotonic() >= deadline:
            logger.error(
                "api_agent_cold_start: persona fetch gave up after %ds (last err: %s)",
                _PERSONA_RETRY_MAX_SECONDS,
                last_err,
            )
            return None
        time.sleep(_PERSONA_RETRY_INTERVAL)


def compute_cost(input_tokens: int, output_tokens: int) -> tuple[float, float]:
    """Return (cost_usd, cost_aud). Sonnet 4 pricing; LAW II 1.55 conversion."""
    usd = (input_tokens * _INPUT_USD_PER_M + output_tokens * _OUTPUT_USD_PER_M) / 1_000_000
    aud = usd * _USD_TO_AUD
    return usd, aud


def insert_attribution(
    *,
    callsign: str,
    chain_id: str,
    task_id: str,
    chain_step: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    cost_aud: float,
    latency_ms: float,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    rate_limit_retries: int = 0,
    completion_status: str = "success",
    conn: Any = None,
) -> None:
    """INSERT a row into public.keiracom_spawn_attribution. Fail-open.

    conn injectable for tests; default reuses agent_cold_start._connect().
    """
    own = conn is None
    try:
        if own:
            from src.keiracom_system.vault.agent_cold_start import _connect  # noqa: PLC0415

            conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.keiracom_spawn_attribution "
                "(spawn_id, source_type, source_id, task_type, callsign, model, "
                "input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, "
                "cost_usd, cost_aud, latency_ms, chain_id, task_id, "
                "rate_limit_retries, completion_status) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    str(uuid.uuid4()),
                    "v1_chain",
                    chain_id,
                    _CHAIN_STEP_TO_TASK_TYPE.get(chain_step, "unknown"),
                    callsign,
                    _MODEL,
                    int(input_tokens),
                    int(output_tokens),
                    int(cache_read_tokens),
                    int(cache_write_tokens),
                    cost_usd,
                    cost_aud,
                    latency_ms,
                    chain_id,
                    task_id,
                    int(rate_limit_retries),
                    completion_status,
                ),
            )
    except Exception:  # noqa: BLE001 — bookkeeping must never break chain progression
        logger.exception("api_agent_cold_start: attribution INSERT failed (callsign=%s)", callsign)
    finally:
        if own and conn is not None:
            with contextlib.suppress(Exception):
                conn.close()


def _parse_retry_after(exc: Any) -> float | None:
    """Pull Retry-After (integer seconds) from an anthropic APIStatusError-shaped
    exception. Returns None if absent or unparseable. Vendored here so the retry
    loop doesn't depend on internal SDK shape changes — best-effort header read.
    """
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None
    if headers is None:
        return None
    try:
        val = headers.get("retry-after")
    except (AttributeError, TypeError):
        return None
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _publish_rate_limit_exhaust(task_id: str, callsign: str, retries: int) -> None:
    """Publish keiracom.ops.failure envelope when 429/529 retry budget exhausts.

    peer_event_ceo_relay subscribes to this subject and fans rate-limit-exhaust
    events to #ceo as visible incidents — closes the 'silent hang on rate
    limit' failure mode the V1-battery gate dispatch called out. Fail-open: any
    NATS error logged + swallowed; the calling chain hop has already returned
    RC_API_FAILED so the orchestrator-side bookkeeping handles the rest.
    """
    import asyncio  # noqa: PLC0415 — lazy
    import json as _json  # noqa: PLC0415

    envelope = {
        "from": "api_agent_cold_start",
        "kind": "ops_failure",
        "unit": f"api_agent_cold_start/{callsign or '?'}",
        "task_id": task_id or "?",
        "callsign": callsign or "?",
        "retries": retries,
        "summary": (
            f"api_agent_cold_start: rate-limit retry budget exhausted "
            f"(callsign={callsign or '?'}, task_id={task_id or '?'}, "
            f"attempts={retries + 1})."
        ),
        "ts": time.time(),
    }

    async def _publish() -> None:
        try:
            import nats  # noqa: PLC0415 — lazy, optional dep
        except ImportError as exc:
            logger.warning(
                "api_agent_cold_start: nats-py not installed; ops.failure skipped (%s)", exc
            )
            return
        try:
            nc = await nats.connect(_NATS_URL, connect_timeout=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("api_agent_cold_start: NATS connect failed: %s", exc)
            return
        try:
            await nc.publish(_OPS_FAILURE_SUBJECT, _json.dumps(envelope).encode("utf-8"))
            await nc.flush(timeout=5)
            logger.info("api_agent_cold_start: published ops.failure for task_id=%s", task_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("api_agent_cold_start: ops.failure publish failed: %s", exc)
        finally:
            with contextlib.suppress(Exception):
                await nc.close()

    try:
        asyncio.run(_publish())
    except Exception:  # noqa: BLE001 — must never block the RC_API_FAILED exit
        logger.exception("api_agent_cold_start: _publish_rate_limit_exhaust raised")


def _build_system_param(persona: str, persona_token_count: int):
    """Wrap the persona in a cache_control block when it's over the cache
    threshold; pass through as a plain string otherwise.

    Anthropic SDK accepts ``system`` as either str OR a list of TextBlockParam
    dicts; the list form is what carries cache_control. Returning the str when
    we're under-threshold keeps the wire format minimal for tiny personas
    (Nova worker = 104 tokens today — would never cache regardless).
    """
    if persona_token_count >= _PROMPT_CACHE_MIN_TOKENS:
        return [
            {
                "type": "text",
                "text": persona,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    return persona


def _build_recall_block(*, task_type: str, brief: str) -> str:
    """L2 Hindsight recall block for this hop's prompt (Wave 3 / spawn_recall).

    Delegates to src.retrieval.spawn_recall.build_spawn_context_block, which
    queries fleet_decisions (the L2 store the c66k backfill populates) and
    returns a KEI-55-budget-capped text block. Without this call, the chain
    hop's user message is just the raw brief — no prior context, no recall,
    cache_hit_pct = 0 on warm replays because there is nothing shared to cache.

    Fail-open by contract: any exception (retrieval outage, agent_query missing,
    Weaviate down) → return "" so the spawn proceeds without recall rather than
    blocking. Caller (run()) logs the resulting length so the harness can
    distinguish "recall path live, corpus empty" from "recall path raised".
    """
    try:
        from src.retrieval.spawn_recall import (  # noqa: PLC0415 — lazy, optional dep
            build_spawn_context_block,
        )

        return build_spawn_context_block(task_type=task_type, task_brief=brief)
    except Exception:  # noqa: BLE001 — recall must never block a chain hop
        logger.warning("api_agent_cold_start: spawn_recall failed (non-fatal)", exc_info=True)
        return ""


def _build_messages_param(brief: str, recall_block: str):
    """Wrap user content with cache_control on the recall_block when present.

    Anthropic SDK accepts each message's ``content`` as either str OR a list of
    block dicts; the list form carries cache_control. The recall_block depends
    only on (task_type, brief) so within a chain it changes per hop, but on a
    warm replay of the SAME task it is byte-identical across cold/warm — that
    is exactly what cache_control here buys us. Empty recall → plain string
    content (no wire-format change vs the pre-recall baseline).
    """
    if recall_block:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": recall_block,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": brief},
                ],
            }
        ]
    return [{"role": "user", "content": brief}]


def call_anthropic(
    api_key: str,
    system: str,
    brief: str,
    *,
    task_id: str = "",
    callsign: str = "",
    persona_token_count: int = 0,
    recall_block: str = "",
) -> tuple[str, int, int, int, int, int]:
    """Anthropic messages.create with 429/529 retry. Returns (text, in_tok, out_tok, retries).

    V1-battery Gate 2 (Elliot dispatch 2026-05-30 ~11:35 AEST): retry on
    HTTP 429 (RateLimitError) and 529/503 (APIStatusError — overloaded /
    unavailable). Exponential backoff: 1s base, doubled per attempt, capped at
    60s. Max 4 attempts (1 initial + 3 retries). Retry-After header (when
    present and parseable) overrides the computed backoff for that attempt.

    On exhaust: publish a keiracom.ops.failure NATS envelope so the rate-limit
    incident surfaces to #ceo (not a silent hang), then re-raise the last
    APIStatusError. The run() caller maps to RC_API_FAILED.

    Non-retriable APIStatusError (400 / 401 / 403 etc) re-raises immediately —
    backoff helps overloaded servers, not bad requests.
    """
    import anthropic  # noqa: PLC0415 — optional dep

    client = anthropic.Anthropic(api_key=api_key)
    system_param = _build_system_param(system, persona_token_count)
    messages_param = _build_messages_param(brief, recall_block)
    retries = 0
    last_exc: Exception | None = None
    for attempt in range(_RATE_LIMIT_MAX_ATTEMPTS):
        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=system_param,
                messages=messages_param,
            )
            text = response.content[0].text if response.content else ""
            # Anthropic SDK exposes cache tokens on usage when prompt caching
            # is engaged (docs.anthropic.com/.../prompt-caching). Older SDK
            # versions / non-caching responses omit these fields → getattr
            # default 0. `or 0` covers an explicit None some SDK paths return.
            cache_write_tokens = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
            cache_read_tokens = getattr(response.usage, "cache_read_input_tokens", 0) or 0
            return (
                text,
                int(response.usage.input_tokens),
                int(response.usage.output_tokens),
                int(cache_read_tokens),
                int(cache_write_tokens),
                retries,
            )
        except anthropic.APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status not in _OVERLOADED_STATUS_CODES:
                raise
            last_exc = exc
            if attempt == _RATE_LIMIT_MAX_ATTEMPTS - 1:
                break  # no sleep after last attempt — fall through to exhaust
            retry_after = _parse_retry_after(exc)
            backoff = (
                retry_after
                if retry_after is not None and retry_after > 0
                else min(
                    _RATE_LIMIT_BASE_BACKOFF_S * (2**attempt),
                    _RATE_LIMIT_MAX_BACKOFF_S,
                )
            )
            logger.warning(
                "api_agent_cold_start: status=%s on attempt %d/%d (callsign=%s); "
                "backing off %.1fs (retry_after=%s)",
                status,
                attempt + 1,
                _RATE_LIMIT_MAX_ATTEMPTS,
                callsign or "?",
                backoff,
                retry_after,
            )
            time.sleep(backoff)
            retries += 1
    # Exhausted — surface as ops.failure and re-raise
    _publish_rate_limit_exhaust(task_id=task_id, callsign=callsign, retries=retries)
    assert last_exc is not None  # noqa: S101 — invariant: loop only breaks here after assignment
    raise last_exc


def run() -> int:
    """Orchestrate one chain-hop API call. Returns the process exit code."""
    logging.basicConfig(level=logging.INFO)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.error("api_agent_cold_start: ANTHROPIC_API_KEY missing")
        return RC_NO_AGENT_ENV

    # spawn_kwargs land as AGENT_<KEY> per src/dispatcher/main.py auto-injection;
    # chain_step lands as CHAIN_STEP (un-prefixed) per qjl7's _apply_chain_step_env.
    callsign = _env("AGENT_CALLSIGN") or _env("AGENT_ROLE")
    chain_step = _env("CHAIN_STEP") or _env("AGENT_CHAIN_STEP")
    chain_id = _env("AGENT_CHAIN_ID")
    task_id = _env("AGENT_TASK_ID")
    brief = _env("AGENT_BRIEF")
    if not callsign or not brief:
        logger.error(
            "api_agent_cold_start: required env missing — callsign=%r brief_chars=%d",
            callsign,
            len(brief),
        )
        return RC_NO_AGENT_ENV

    persona_result = fetch_persona(callsign)
    if not persona_result:
        return RC_PERSONA_FAILED
    persona, persona_token_count = persona_result

    # L2 Hindsight recall — fleet_decisions lookup (c66k backfill: 333 ceo_memory
    # + 225 supporting atoms). Without this, every hop's user message is just the
    # raw brief and cache_hit_pct stays at 0 because there is nothing shared to
    # cache between cold and warm runs. task_type drives the recall query's
    # workload-class filter so each chain position retrieves topically relevant
    # context (deliberation / build / pr_review). recall_block_len log gives the
    # battery harness a signal to distinguish "recall path live, corpus empty"
    # from "recall path silently failed" — both yield "" but only the latter is
    # a bug worth alerting on.
    task_type = _CHAIN_STEP_TO_TASK_TYPE.get(chain_step, "build")
    recall_block = _build_recall_block(task_type=task_type, brief=brief)
    logger.info(
        "api_agent_cold_start: recall_block_len=%d task_type=%s callsign=%s chain_step=%s",
        len(recall_block),
        task_type,
        callsign,
        chain_step or "?",
    )

    spawned_at = time.time()
    try:
        (
            text,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_write_tokens,
            rate_limit_retries,
        ) = call_anthropic(
            api_key,
            persona,
            brief,
            task_id=task_id,
            callsign=callsign,
            persona_token_count=persona_token_count,
            recall_block=recall_block,
        )
    except ImportError:
        logger.exception("api_agent_cold_start: anthropic SDK not installed")
        return RC_SDK_MISSING
    except Exception:  # noqa: BLE001
        logger.exception("api_agent_cold_start: messages.create failed (callsign=%s)", callsign)
        return RC_API_FAILED
    completed_at = time.time()
    latency_ms = (completed_at - spawned_at) * 1000.0
    cost_usd, cost_aud = compute_cost(input_tokens, output_tokens)

    insert_attribution(
        callsign=callsign,
        chain_id=chain_id,
        task_id=task_id,
        chain_step=chain_step or "?",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        cost_aud=cost_aud,
        latency_ms=latency_ms,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        rate_limit_retries=rate_limit_retries,
    )

    logger.info(
        "api_agent_cold_start: callsign=%s chain_step=%s in=%d out=%d cache_r=%d cache_w=%d cost_usd=%.6f cost_aud=%.6f latency_ms=%.1f",
        callsign,
        chain_step,
        input_tokens,
        output_tokens,
        cache_read_tokens,
        cache_write_tokens,
        cost_usd,
        cost_aud,
        latency_ms,
    )

    # AtomV1 + handoff publish — reuse existing chat.exit_cycle + agent_cold_start
    # helpers so the wiring contract matches everywhere (zr7e.4 + zr7e.9).
    try:
        import asyncio  # noqa: PLC0415 — lazy

        from src.keiracom_system.chat.exit_cycle import classify_and_save  # noqa: PLC0415

        customer_id = int(os.environ.get("AGENT_CUSTOMER_ID", "1"))
        conversation = [
            {"role": "user", "content": brief},
            {"role": "assistant", "content": text},
        ]
        result = asyncio.run(classify_and_save(conversation, customer_id))
    except Exception:  # noqa: BLE001 — must not block exit; atom capture is best-effort
        logger.exception("api_agent_cold_start: classify_and_save failed")
        result = None

    atom_ids = list(getattr(result, "atom_ids", None) or [])
    if atom_ids:
        try:
            from src.keiracom_system.vault.agent_cold_start import _publish_handoff  # noqa: PLC0415

            for aid in atom_ids:
                _publish_handoff(task_id=task_id, atom_id=aid, to_callsign="")
        except Exception:  # noqa: BLE001
            logger.exception("api_agent_cold_start: _publish_handoff failed")
    else:
        # No atom captured (e.g. classifier below confidence threshold) — still
        # fire one handoff with empty atom_id so the chain consumer advances.
        # Without this the chain would stall whenever the model output isn't
        # decision-shaped enough for atom emission.
        try:
            from src.keiracom_system.vault.agent_cold_start import _publish_handoff  # noqa: PLC0415

            _publish_handoff(task_id=task_id, atom_id="", to_callsign="")
        except Exception:  # noqa: BLE001
            logger.exception("api_agent_cold_start: empty-atom handoff publish failed")

    return 0


def main() -> int:  # pragma: no cover — process entrypoint
    return run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
