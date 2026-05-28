"""KEI-210 — interceptor_proxy: governance proxy between agents and LiteLLM.

Sits in front of LiteLLM (port 4000). On every model call:
  1. Schema + governance check (delegates to KEI-165 governance_proxy)
  2. Spend budget check (Valkey ``spend:<tenant>:<YYYY-MM>`` vs tier limit)
  3. Rate limit check (Valkey 60s sliding window per KEI-117A namespace)
  4. If all pass: forward to LiteLLM, log allow event
  5. If any fail: reject with structured error, log denial

Acceptance (Linear KEI-210):
  - interceptor_proxy.py in src/dispatcher/ ✓
  - GET /interceptor/health → 200 OK
  - Spend check queries Valkey correctly
  - Rate limit uses Valkey ``rl:<tenant>:<window>`` namespace from KEI-117A
  - Decisions logged to public.interceptor_events
  - Rejected calls return structured JSON error, not silent failure
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Final

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.dispatcher.governance_proxy import ProxyDecision, evaluate
from src.dispatcher.valkey_pool import (
    get_valkey_client,
    tenant_rl_key,
)
from src.relay.context_budget import (
    DECISION_REJECTED,
    DECISION_SPAWN_OK,
    DECISION_SUMMARISED,
    ROLE_BUILDER,
    ROLE_CEILINGS,
    check_context_budget,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier limits — sourced from CONSOLIDATED_RULES + dispatcher_customers tiers.
# Hardcoded here for KEI-210; KEI-117C will lift these from the DB.
# Spend caps are $AUD cents per calendar month (LAW II). Rate caps are
# requests-per-minute (matches the 60-second window in KEI-117A).
# ---------------------------------------------------------------------------

TIER_DEFAULT: Final = "free"
SPEND_BUDGET_AUD_CENTS: Final[dict[str, int]] = {
    "free": 0,
    "starter": 5_000_00,  # $5,000 AUD
    "growth": 50_000_00,  # $50,000 AUD
    "scale": 500_000_00,  # $500,000 AUD
    "enterprise": 5_000_000_00,
}
RATE_LIMIT_PER_MINUTE: Final[dict[str, int]] = {
    "free": 10,
    "starter": 60,
    "growth": 600,
    "scale": 6_000,
    "enterprise": 60_000,
}

SPEND_NAMESPACE_PREFIX: Final = "spend"
RATE_WINDOW_SECONDS: Final = 60
LITELLM_URL_ENV: Final = "LITELLM_URL"
DEFAULT_LITELLM_URL: Final = "http://127.0.0.1:4000/v1/chat/completions"

# Bounded-spawn discipline hook (Agency_OS-gcpm / Audit RED-7).
# Off by default; production startup wires the enforcer accessor below.
# The hook fires only when the request body carries both ``bounded_spawn_callsign``
# and ``bounded_spawn_task_id`` metadata — until the dispatcher task pipeline
# propagates that metadata to model calls this gate is a no-op even when wired.
_bounded_spawn_enforcer_accessor: Any | None = None


def set_bounded_spawn_enforcer_accessor(accessor: Any | None) -> None:
    """Inject a callable that returns the live BoundedSpawnEnforcer (or None).

    Using a callable accessor instead of a direct enforcer reference keeps the
    interceptor decoupled from ``src.dispatcher.main`` (no circular import)
    while still letting it consult the live state at request-time.
    """
    global _bounded_spawn_enforcer_accessor  # noqa: PLW0603
    _bounded_spawn_enforcer_accessor = accessor


def _check_bounded_spawn_via_metadata(body: dict) -> str | None:
    """Return a violation reason if request body indicates a bounded-spawn violator.

    Returns None when:
      - hook not wired (no accessor injected)
      - body lacks bounded-spawn metadata (rollout phase)
      - enforcer says the (callsign, task_id) pair is consistent with active slot

    Returns a structured reason string when the body's task_id does not match
    the active slot's task_id for that callsign — i.e. the model call is
    coming from a spawn that already had its slot reassigned (violator).
    """
    if _bounded_spawn_enforcer_accessor is None:
        return None
    callsign = str(body.get("bounded_spawn_callsign") or "").strip()
    task_id = str(body.get("bounded_spawn_task_id") or "").strip()
    if not callsign or not task_id:
        return None
    try:
        enforcer = _bounded_spawn_enforcer_accessor()
    except Exception:  # noqa: BLE001 — fail-open
        logger.exception("bounded-spawn accessor raised — failing open")
        return None
    if enforcer is None:
        return None
    try:
        if enforcer.would_violate(callsign=callsign, task_id=task_id):
            return f"bounded_spawn_violator callsign={callsign} task_id={task_id}"
    except Exception:  # noqa: BLE001 — fail-open
        logger.exception("bounded-spawn would_violate raised — failing open")
    return None


# Context-window budget gate (PR #1210 / Cat 21 lever 25 / cutover-blocker 3).
# Disabled by default; tests + production startup enable via env or DI.
CONTEXT_WINDOW_ENABLED_ENV: Final = "DISPATCHER_CONTEXT_WINDOW_ENABLED"

# Public toggle — production reads via env at startup; tests flip directly.
context_window_enabled: bool = os.environ.get(CONTEXT_WINDOW_ENABLED_ENV, "").lower() in {
    "1",
    "true",
    "yes",
}


def _body_to_context(body: dict) -> str:
    """Extract a context-shaped string from an OpenAI-style chat-completion body.

    Concatenates each message's role + content. Returns "" when no messages.
    """
    messages = body.get("messages") or []
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "")
        content = msg.get("content")
        if isinstance(content, str):
            parts.append(f"{role}: {content}")
        elif isinstance(content, list):
            # OpenAI multimodal: list of content blocks; pull text fields.
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(f"{role}: {block['text']}")
    return "\n".join(parts)


def _body_to_role(body: dict) -> str:
    """Derive context-budget role from body; default ROLE_BUILDER for unknowns."""
    explicit = str(body.get("dispatcher_role") or "").lower().strip()
    if explicit in ROLE_CEILINGS:
        return explicit
    return ROLE_BUILDER


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterceptorDecision:
    """Outcome of a single intercept_request call."""

    allowed: bool
    decision: str  # 'allow' | 'deny_spend' | 'deny_rate_limit' | 'deny_governance' | 'error'
    reason: str | None = None
    status_code: int = 200
    payload: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Helpers — internal
# ---------------------------------------------------------------------------


def _tier_for(body: dict, default: str = TIER_DEFAULT) -> str:
    """Resolve tier off the body. Real wiring (KEI-117C) will query the DB
    via tenant_id; until then accept an explicit ``tier`` hint or fall back
    to ``free`` so denies stay conservative for unknown callers."""
    tier = body.get("tier") or default
    return tier if tier in SPEND_BUDGET_AUD_CENTS else default


def _spend_key(tenant_id: str, now: dt.datetime | None = None) -> str:
    ts = now or dt.datetime.now(dt.UTC)
    return f"{SPEND_NAMESPACE_PREFIX}:{tenant_id}:{ts.strftime('%Y-%m')}"


async def _check_spend_budget(tenant_id: str, tier: str) -> tuple[bool, int]:
    """Return (allowed, spent_cents). Reads the monthly cumulative spend
    counter from Valkey; missing key counts as 0. Caller is responsible for
    incrementing after a successful forward via ``_accrue_spend``."""
    budget = SPEND_BUDGET_AUD_CENTS.get(tier, 0)
    client = get_valkey_client()
    try:
        raw = await client.get(_spend_key(tenant_id))
        spent = int(raw) if raw is not None else 0
    finally:
        await client.aclose()
    return (spent < budget, spent)


async def _check_rate_limit(tenant_id: str, tier: str) -> tuple[bool, int]:
    """Return (allowed, count). Increments the per-minute bucket and applies
    a 60s TTL on first write so old buckets auto-evict. Uses KEI-117A
    ``tenant_rl_key`` so the namespace stays canonical."""
    limit = RATE_LIMIT_PER_MINUTE.get(tier, 0)
    if limit <= 0:
        return (False, 0)
    bucket_start = int(time.time()) // RATE_WINDOW_SECONDS * RATE_WINDOW_SECONDS
    key = tenant_rl_key(tenant_id, bucket_start)
    client = get_valkey_client()
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, RATE_WINDOW_SECONDS)
    finally:
        await client.aclose()
    return (int(count) <= limit, int(count))


async def _accrue_spend(tenant_id: str, cost_cents_aud: int) -> None:
    """Bump the monthly spend counter after a successful forward."""
    if cost_cents_aud <= 0:
        return
    client = get_valkey_client()
    try:
        await client.incrby(_spend_key(tenant_id), cost_cents_aud)
    finally:
        await client.aclose()


async def _log_event(
    tenant_id: str,
    decision: str,
    reason: str | None,
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cost_cents_aud: int | None,
    latency_ms: int | None,
    insert_fn: Any | None = None,
) -> None:
    """Best-effort audit insert. ``insert_fn`` is injected for tests; real
    callers leave it None and we'll resolve a Supabase client lazily so the
    import surface doesn't pull supabase into unit tests."""
    row = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "decision": decision,
        "reason": reason,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_cents_aud": cost_cents_aud,
        "latency_ms": latency_ms,
    }
    try:
        if insert_fn is not None:
            await insert_fn(row)
            return
        from src.integrations.supabase import get_supabase_service_client

        client = get_supabase_service_client()
        client.table("interceptor_events").insert(row).execute()
    except Exception as exc:  # noqa: BLE001 — audit must not break the hot path
        logger.warning("interceptor_events insert failed (non-fatal): %s", exc)


async def _forward_to_litellm(payload: dict, http_client: httpx.AsyncClient | None = None) -> dict:
    """POST to LiteLLM and return the parsed JSON response. The client is
    injectable for tests."""
    url = os.environ.get(LITELLM_URL_ENV, DEFAULT_LITELLM_URL)
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=30.0)
    try:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def intercept_request(
    body: dict,
    *,
    forward_fn: Any | None = None,
    insert_fn: Any | None = None,
) -> InterceptorDecision:
    """Run the governance → spend → rate-limit → forward pipeline.

    ``forward_fn`` and ``insert_fn`` are injection hooks for tests. Production
    callers pass neither and we use the default Valkey + LiteLLM + Supabase
    clients.
    """
    start = time.monotonic()
    tenant_id = body.get("tenant_id") or ""
    tier = _tier_for(body)
    model = body.get("model")

    governance: ProxyDecision = evaluate(body)
    if not governance.allowed:
        reason = governance.reason or "deny_governance"
        await _log_event(
            tenant_id,
            "deny_governance",
            reason,
            model,
            None,
            None,
            None,
            _ms_since(start),
            insert_fn,
        )
        return InterceptorDecision(
            allowed=False,
            decision="deny_governance",
            reason=reason,
            status_code=403,
            payload={"error": "governance_denied", "reason": reason},
        )

    # Bounded-spawn discipline hook (Agency_OS-gcpm / Audit RED-7).
    # Rejects model calls from violator spawns whose slot was already reassigned
    # to a different task. Only fires when body carries the metadata fields;
    # no-op until the dispatcher task pipeline starts tagging model calls.
    bs_violation = _check_bounded_spawn_via_metadata(body)
    if bs_violation is not None:
        await _log_event(
            tenant_id,
            "deny_bounded_spawn",
            bs_violation,
            model,
            None,
            None,
            None,
            _ms_since(start),
            insert_fn,
        )
        return InterceptorDecision(
            allowed=False,
            decision="deny_bounded_spawn",
            reason=bs_violation,
            status_code=409,
            payload={"error": "bounded_spawn_violation", "reason": bs_violation},
        )

    spend_ok, _ = await _check_spend_budget(tenant_id, tier)
    if not spend_ok:
        await _log_event(
            tenant_id,
            "deny_spend",
            "monthly_budget_exhausted",
            model,
            None,
            None,
            None,
            _ms_since(start),
            insert_fn,
        )
        return InterceptorDecision(
            allowed=False,
            decision="deny_spend",
            reason="monthly_budget_exhausted",
            status_code=402,
            payload={"error": "spend_budget_exceeded", "tier": tier},
        )

    rate_ok, _ = await _check_rate_limit(tenant_id, tier)
    if not rate_ok:
        await _log_event(
            tenant_id,
            "deny_rate_limit",
            "per_minute_limit",
            model,
            None,
            None,
            None,
            _ms_since(start),
            insert_fn,
        )
        return InterceptorDecision(
            allowed=False,
            decision="deny_rate_limit",
            reason="per_minute_limit",
            status_code=429,
            payload={"error": "rate_limit_exceeded", "tier": tier},
            headers={"Retry-After": str(RATE_WINDOW_SECONDS)},
        )

    # Context-window budget gate (Cat 21 lever 25 / cutover-blocker 3).
    # Fires AFTER governance + spend + rate-limit (cheaper checks first), BEFORE
    # forward to LiteLLM (token-counting is the most expensive check).
    if context_window_enabled:
        context_str = _body_to_context(body)
        if context_str:
            role = _body_to_role(body)
            try:
                ctx_result = check_context_budget(role, context_str)
            except Exception:  # noqa: BLE001 — fail-open per gate-layer design
                logger.exception("KEI-213 context-window gate raised — failing open")
                ctx_result = None
            if ctx_result is not None and ctx_result.decision == DECISION_REJECTED:
                await _log_event(
                    tenant_id,
                    "deny_context_window",
                    f"role={role} tokens={ctx_result.initial_tokens} ceiling={ctx_result.ceiling_tokens}",
                    model,
                    None,
                    None,
                    None,
                    _ms_since(start),
                    insert_fn,
                )
                return InterceptorDecision(
                    allowed=False,
                    decision="deny_context_window",
                    reason="context_window_exceeded",
                    status_code=413,
                    payload={
                        "error": "context_window_exceeded",
                        "role": role,
                        "initial_tokens": ctx_result.initial_tokens,
                        "ceiling_tokens": ctx_result.ceiling_tokens,
                    },
                )
            if ctx_result is not None and ctx_result.decision == DECISION_SUMMARISED:
                # Summariser fit context under ceiling — proceed with summarised body.
                # Phase 1: no summariser wired so this branch unreachable; preserved
                # for Phase 2 when production summariser lands.
                logger.info(
                    "KEI-213 context-window gate summarised context role=%s %d→%d",
                    role,
                    ctx_result.initial_tokens,
                    ctx_result.final_tokens,
                )
            elif ctx_result is not None and ctx_result.decision == DECISION_SPAWN_OK:
                logger.debug(
                    "KEI-213 context-window gate passed role=%s tokens=%d",
                    role,
                    ctx_result.initial_tokens,
                )

    try:
        result = await (forward_fn(body) if forward_fn else _forward_to_litellm(body))
    except Exception as exc:  # noqa: BLE001 — upstream errors surface as structured
        await _log_event(
            tenant_id,
            "error",
            f"forward_failed:{type(exc).__name__}",
            model,
            None,
            None,
            None,
            _ms_since(start),
            insert_fn,
        )
        return InterceptorDecision(
            allowed=False,
            decision="error",
            reason=f"forward_failed:{type(exc).__name__}",
            status_code=502,
            payload={"error": "upstream_unavailable"},
        )

    usage = result.get("usage") or {}
    in_tok = usage.get("prompt_tokens")
    out_tok = usage.get("completion_tokens")
    cost = int(result.get("cost_cents_aud", 0))
    if cost > 0:
        await _accrue_spend(tenant_id, cost)
    await _log_event(
        tenant_id,
        "allow",
        None,
        model,
        in_tok,
        out_tok,
        cost,
        _ms_since(start),
        insert_fn,
    )
    return InterceptorDecision(allowed=True, decision="allow", payload=result)


def _ms_since(start_monotonic: float) -> int:
    return int((time.monotonic() - start_monotonic) * 1000)


# ---------------------------------------------------------------------------
# FastAPI router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/interceptor", tags=["interceptor"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Returns 200 OK with a small body so the dispatcher
    health aggregator can see component=interceptor_proxy green."""
    return {"status": "ok", "component": "interceptor_proxy", "kei": "KEI-210"}


@router.post("/forward")
async def forward(body: dict) -> JSONResponse:
    """Public entry. Runs the full intercept pipeline and surfaces the
    decision as JSON. Rejected calls return structured error bodies so the
    agent can branch on ``decision`` without parsing strings."""
    decision = await intercept_request(body)
    payload = decision.payload or {"decision": decision.decision}
    return JSONResponse(
        status_code=decision.status_code,
        content={"decision": decision.decision, "reason": decision.reason, **payload},
        headers=decision.headers or {},
    )


__all__ = [
    "InterceptorDecision",
    "RATE_LIMIT_PER_MINUTE",
    "SPEND_BUDGET_AUD_CENTS",
    "intercept_request",
    "router",
]
