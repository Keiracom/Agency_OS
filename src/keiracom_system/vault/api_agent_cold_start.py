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
  4. anthropic.Anthropic(...).messages.create(model='claude-sonnet-4-6',
     max_tokens=8096, system=<persona>, messages=[{role:'user', content:brief}]).
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

# Exit codes
RC_NO_AGENT_ENV = 2
RC_PERSONA_FAILED = 3
RC_API_FAILED = 4
RC_SDK_MISSING = 5


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default) or default


def fetch_persona(callsign: str, *, dispatcher_url: str = _DISPATCHER_URL) -> str | None:
    """GET /dispatcher/persona with retry (up to 60s; Nova's worker persona may
    land in parallel). Returns the prompt_text or None on terminal failure.
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
                return prompt
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
    completion_status: str = "done",
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
                "cost_usd, cost_aud, latency_ms, chain_id, task_id, completion_status) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    str(uuid.uuid4()),
                    "v1_chain",
                    chain_id,
                    chain_step,
                    callsign,
                    _MODEL,
                    int(input_tokens),
                    int(output_tokens),
                    0,
                    0,
                    cost_usd,
                    cost_aud,
                    latency_ms,
                    chain_id,
                    task_id,
                    completion_status,
                ),
            )
    except Exception:  # noqa: BLE001 — bookkeeping must never break chain progression
        logger.exception("api_agent_cold_start: attribution INSERT failed (callsign=%s)", callsign)
    finally:
        if own and conn is not None:
            with contextlib.suppress(Exception):
                conn.close()


def call_anthropic(api_key: str, system: str, brief: str) -> tuple[str, int, int]:
    """Single Anthropic messages.create call. Returns (text, input_tokens, output_tokens).
    Raises on SDK import error or API failure (caller maps to exit code).
    """
    import anthropic  # noqa: PLC0415 — optional dep

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": brief}],
    )
    text = response.content[0].text if response.content else ""
    return text, int(response.usage.input_tokens), int(response.usage.output_tokens)


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
    # Note: AGENT_ATOM_ID (prior step's atom) is read by the persona's L2 recall
    # at spawn time, not by this entrypoint directly; we don't thread it into
    # the user message here. Leaving the env var pass-through to the dispatcher
    # so persona/recall layers can use it.
    brief = _env("AGENT_BRIEF")
    if not callsign or not brief:
        logger.error(
            "api_agent_cold_start: required env missing — callsign=%r brief_chars=%d",
            callsign,
            len(brief),
        )
        return RC_NO_AGENT_ENV

    persona = fetch_persona(callsign)
    if not persona:
        return RC_PERSONA_FAILED

    spawned_at = time.time()
    try:
        text, input_tokens, output_tokens = call_anthropic(api_key, persona, brief)
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
    )

    logger.info(
        "api_agent_cold_start: callsign=%s chain_step=%s in=%d out=%d cost_usd=%.6f cost_aud=%.6f latency_ms=%.1f",
        callsign,
        chain_step,
        input_tokens,
        output_tokens,
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
