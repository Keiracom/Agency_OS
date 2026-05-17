"""KEI-179 — Customer Dispatcher service entrypoint.

FastAPI app exposing the customer-facing dispatcher endpoint that Max's
KEI-180 Strangler Fig router forwards Model B traffic to. Separate from
the existing src/api/main.py (agency-side app) — the dispatcher is a
distinct tenancy (customer_id, not client_id) and runs as its own
systemd unit on a separate port so blast radius stays contained.

Endpoints:
    GET  /health                — liveness probe (no auth, no DB)
    POST /dispatch              — accept a customer task body, rate-limit
                                  via tier, forward through the LiteLLM
                                  router, return the model response

Run locally:
    python3 -m src.dispatcher                       # uvicorn on :8090
    DISPATCHER_PORT=8091 python3 -m src.dispatcher  # override port

Run as a service:
    bash scripts/install_dispatcher.sh              # installs systemd unit
    systemctl --user start dispatcher.service
    systemctl --user is-active dispatcher           # → "active"
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.dispatcher.llm_router import (
    CostEvent,
    LiteLLMRateLimitExhaustedError,
    LiteLLMRouterError,
    forward,
)
from src.dispatcher.rate_limiter import RateLimitExceededError
from src.dispatcher.tier_limits import enforce_for_tenant

logger = logging.getLogger(__name__)


def _sanitize_for_log(value: str, *, max_len: int = 64) -> str:
    """Strip control chars + truncate user-controlled identifier before
    logging. Defends against log-injection (CRLF, ANSI escapes) per Sonar
    S5145. UUIDs / KEI-NNN style IDs pass through unchanged."""
    cleaned = "".join(c if c.isprintable() and c not in "\r\n" else "?" for c in str(value))
    return cleaned[:max_len]


app = FastAPI(
    title="Keiracom Dispatcher",
    description="Customer-facing dispatcher service (KEI-179). Receives Model B "
    "traffic from the Strangler Fig router (KEI-180); rate-limits per tier; "
    "forwards through LiteLLM; logs cost events.",
    version="0.1.0",
)


class DispatchRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    body: dict[str, Any] = Field(
        description="Opaque LiteLLM-shaped request body (model, messages, ...). "
        "Validated upstream by the governance proxy (KEI-115D)."
    )


class DispatchResponse(BaseModel):
    customer_id: str
    task_id: str
    rate_limit_decision: dict[str, Any]
    response: dict[str, Any]


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is alive. Intentionally
    does NOT touch the DB / Valkey / LiteLLM so a downstream outage
    doesn't take this service out of the load balancer."""
    return {"status": "ok", "service": "dispatcher"}


@app.post("/dispatch", response_model=None)
async def dispatch(payload: DispatchRequest) -> DispatchResponse:
    """Rate-limit the tenant per their subscription tier, then forward
    the request body through LiteLLM.

    Returns:
        200 with the LiteLLM response + the rate-limit decision metadata
        (limit, remaining headroom) so the customer can self-throttle.

    Raises:
        429 — tenant exceeded their per-window limit (tier-derived).
        502 — LiteLLM gateway returned a non-2xx non-429 OR transport error.
        500 — unexpected router failure.
    """
    safe_tenant = _sanitize_for_log(payload.customer_id)
    safe_task = _sanitize_for_log(payload.task_id)
    try:
        decision = await enforce_for_tenant(tenant_id=payload.customer_id)
    except RateLimitExceededError as exc:
        logger.info(
            "dispatcher 429 tenant=%s task=%s limit=%d window=%ds",
            safe_tenant,
            safe_task,
            exc.limit,
            exc.window_size_s,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.window_size_s)},
        ) from exc

    cost_events: list[CostEvent] = []
    try:
        response_body = forward(
            body=payload.body,
            customer_id=payload.customer_id,
            task_id=payload.task_id,
            cost_sink=cost_events.append,
        )
    except LiteLLMRateLimitExhaustedError as exc:
        # Upstream LiteLLM gateway exhausted retries — surface as 429
        # with a longer Retry-After than the tenant limit suggests so the
        # customer doesn't immediately retry into the same upstream issue.
        logger.warning(
            "dispatcher upstream-429 tenant=%s task=%s",
            safe_tenant,
            safe_task,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": "60"},
        ) from exc
    except LiteLLMRouterError as exc:
        logger.warning(
            "dispatcher 502 tenant=%s task=%s err=%s",
            safe_tenant,
            safe_task,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return DispatchResponse(
        customer_id=payload.customer_id,
        task_id=payload.task_id,
        rate_limit_decision={
            "limit": decision.limit,
            "current": decision.current,
            "window_size_s": decision.window_size_s,
            "retry_after_s": decision.retry_after_s,
        },
        response=response_body,
    )
