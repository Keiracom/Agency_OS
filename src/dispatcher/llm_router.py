"""KEI-115E — LiteLLM router for customer dispatcher requests.

Forwards customer requests to the local LiteLLM gateway (default
``http://127.0.0.1:4000``), retries on 429 with bounded backoff, emits
cost-event metadata via an injectable ``cost_sink`` callback so the
consumer chooses where to persist (no DB write in this layer — see KEI
note: a dispatcher-customer cost table does not yet exist; existing
``vendor_usage_log`` / ``sdk_usage_log`` are agency-CRM-shaped).

Body is treated as an opaque pass-through. Governance/schema validation
lives upstream in the proxy (KEI-115D / KEI-165). Auth headers + tenant
context come from the caller — the router does not know about JWTs.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

DEFAULT_GATEWAY_URL = "http://127.0.0.1:4000/v1/chat/completions"
DEFAULT_HTTP_TIMEOUT_S = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_LADDER_S: tuple[float, ...] = (1.0, 2.0, 5.0)

CostSink = Callable[["CostEvent"], None]


class LiteLLMRouterError(RuntimeError):
    """Non-retryable router failure — bad gateway response or transport error."""


class LiteLLMRateLimitExhaustedError(LiteLLMRouterError):
    """Gateway returned 429 ``max_retries`` times in a row. Caller may decide
    to surface as a tier-limit message to the customer."""


@dataclass(frozen=True)
class CostEvent:
    """One forwarded request's cost-tracking record. The router never
    persists this — it hands it to ``cost_sink`` for the caller to write
    to whichever ledger fits their tenant model."""

    customer_id: str
    task_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_aud: float
    retry_count: int
    duration_ms: int
    success: bool
    error_message: str | None = None


def _extract_usage(response_body: dict[str, Any]) -> tuple[str, int, int, float]:
    """Pull model + token counts + cost out of a LiteLLM response. Falls
    back to zeros when LiteLLM didn't return the expected shape — cost
    accounting is best-effort, not load-bearing for request success."""
    model = str(response_body.get("model") or "unknown")
    usage = response_body.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    # LiteLLM exposes per-request cost under the non-standard
    # ``response_cost`` field when ``litellm.success_callback`` is set.
    # Coerce to AUD if the deploy is configured for AUD pricing; this
    # router does NOT do USD→AUD conversion (LAW II — let the gateway
    # config own currency).
    cost_aud = float(response_body.get("response_cost") or 0.0)
    return model, input_tokens, output_tokens, cost_aud


def _post_json(url: str, body: dict[str, Any], timeout_s: float) -> tuple[int, dict[str, Any]]:
    """POST JSON to ``url``, return (status_code, parsed_body). Raises
    LiteLLMRouterError on transport-level failure (DNS, refused, timeout)
    so the caller's retry loop can distinguish from 429s.
    """
    raw = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=raw,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 — fixed gateway URL
            status = int(resp.status)
            payload = json.loads(resp.read() or b"{}")
            return status, payload
    except urlerror.HTTPError as exc:
        # HTTPError IS the response — capture status + body so retry logic
        # can branch on 429 vs everything else.
        try:
            payload = json.loads(exc.read() or b"{}")
        except (json.JSONDecodeError, OSError):
            payload = {"error": str(exc)}
        return int(exc.code), payload
    except (urlerror.URLError, OSError) as exc:
        # TimeoutError is a subclass of OSError in Python 3.10+, covered already
        raise LiteLLMRouterError(f"litellm transport error: {exc}") from exc


def forward(
    *,
    body: dict[str, Any],
    customer_id: str,
    task_id: str,
    gateway_url: str = DEFAULT_GATEWAY_URL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_s: tuple[float, ...] = DEFAULT_BACKOFF_LADDER_S,
    timeout_s: float = DEFAULT_HTTP_TIMEOUT_S,
    cost_sink: CostSink | None = None,
) -> dict[str, Any]:
    """Forward a chat-completion request to LiteLLM with retry-on-429.

    Args:
        body: Opaque LiteLLM-shaped request body (model, messages, ...).
        customer_id: Tenant identifier — attached to the cost event only.
        task_id: KEI / dispatcher task identifier — attached to cost event.
        gateway_url: LiteLLM endpoint. Default is the systemd-managed local proxy.
        max_retries: Max 429 retries before raising LiteLLMRateLimitExhaustedError.
        backoff_s: Per-retry sleep ladder (truncated to ``max_retries``).
        timeout_s: HTTP timeout per attempt.
        cost_sink: Optional callback invoked once on success with a CostEvent.
            Exceptions from the sink are caught + logged — sink failure must
            NOT bubble into the forwarding result.

    Returns:
        Parsed LiteLLM response body on 2xx.

    Raises:
        LiteLLMRateLimitExhaustedError: 429 returned ``max_retries`` times.
        LiteLLMRouterError: Transport failure or non-2xx non-429 response.
    """
    started_monotonic = time.monotonic()
    retry_count = 0
    last_status = 0
    last_payload: dict[str, Any] = {}

    for attempt in range(max_retries + 1):
        status, payload = _post_json(gateway_url, body, timeout_s)
        last_status, last_payload = status, payload
        if 200 <= status < 300:
            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            _emit_cost(
                payload,
                customer_id=customer_id,
                task_id=task_id,
                retry_count=retry_count,
                duration_ms=duration_ms,
                success=True,
                error_message=None,
                cost_sink=cost_sink,
            )
            return payload
        if status == 429 and attempt < max_retries:
            sleep_for = backoff_s[min(attempt, len(backoff_s) - 1)]
            logger.info(
                "litellm 429 on attempt %d/%d — sleeping %.1fs",
                attempt + 1,
                max_retries,
                sleep_for,
            )
            time.sleep(sleep_for)
            retry_count += 1
            continue
        # Non-2xx and not a retryable 429 — fail terminal.
        break

    duration_ms = int((time.monotonic() - started_monotonic) * 1000)
    error_message = (
        json.dumps(last_payload)[:500] if last_payload else f"litellm status {last_status}"
    )
    _emit_cost(
        last_payload,
        customer_id=customer_id,
        task_id=task_id,
        retry_count=retry_count,
        duration_ms=duration_ms,
        success=False,
        error_message=error_message,
        cost_sink=cost_sink,
    )
    if last_status == 429:
        raise LiteLLMRateLimitExhaustedError(
            f"litellm 429 after {max_retries} retries: {error_message}"
        )
    raise LiteLLMRouterError(f"litellm status {last_status}: {error_message}")


def _emit_cost(
    response_body: dict[str, Any],
    *,
    customer_id: str,
    task_id: str,
    retry_count: int,
    duration_ms: int,
    success: bool,
    error_message: str | None,
    cost_sink: CostSink | None,
) -> None:
    """Build a CostEvent and hand it to ``cost_sink``. Sink failures are
    swallowed — the router must not propagate ledger problems back to the
    caller whose request actually completed."""
    if cost_sink is None:
        return
    model, input_tokens, output_tokens, cost_aud = _extract_usage(response_body)
    event = CostEvent(
        customer_id=customer_id,
        task_id=task_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_aud=cost_aud,
        retry_count=retry_count,
        duration_ms=duration_ms,
        success=success,
        error_message=error_message,
    )
    try:
        cost_sink(event)
    except Exception as exc:  # noqa: BLE001 — sink is consumer-owned; must isolate
        logger.warning(
            "cost_sink raised for task %s (customer %s): %s",
            task_id,
            customer_id,
            exc,
        )
