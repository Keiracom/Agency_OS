"""Cache metrics emitter — Phase A7 sub-task 4.

Better Stack instrumentation hook for cache layer metrics. Provides a
MetricEmitter callable matching ValkeyClient's injection signature.

CANONICAL DESIGN — docs/architecture/design/a7_cache_architecture.md §4
(Valkey lookup metric) + §13 CB-5 (Anthropic prompt cache rate metric).

METRIC NAMES (per design + CB-5):
  - keiracom.cache.valkey.lookup{tenant_id, tool_name, outcome=hit|miss}
  - keiracom.cache.anthropic.input_tokens{type=create|read|standard, tenant_id, model}

CARDINALITY FLAG (per CB-5): tenant_id × tool_name × outcome at scale
(200+ tenants × 50 tools × 2 outcomes = 20K series) is a Better Stack
billing concern. V1 (Dave N=1) is unaffected; Phase 2 follow-up bd for
pre-aggregation hook.

DEPENDENCY INJECTION: caller provides http_post + base_url + auth_token so
the emitter is testable without a live Better Stack endpoint. Default
http_post uses stdlib urllib (no httpx dependency).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

# Better Stack telemetry HTTP API base. Env var override at construction time.
DEFAULT_BETTERSTACK_INGEST_URL: str = "https://in.logs.betterstack.com/metrics"
DEFAULT_TIMEOUT_SECONDS: float = 5.0


HTTPPostFn = Callable[[str, dict[str, Any], dict[str, str], float], int]


def _default_http_post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> int:
    """Stdlib urllib POST returning HTTP status code. Fail-open on transport error.

    Cache metrics are fire-and-forget — failing the LLM call because Better
    Stack is unreachable would be worse than dropping a metric.
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.URLError as exc:
        log.warning("better_stack_metric_emitter: %s", exc)
        return 0


def make_better_stack_emitter(
    *,
    ingest_url: str = DEFAULT_BETTERSTACK_INGEST_URL,
    source_token: str,
    http_post: HTTPPostFn | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Callable[[str, dict[str, str]], None]:
    """Build a MetricEmitter that POSTs one metric per call to Better Stack.

    Returned signature matches ValkeyClient's `metric_emitter` parameter:
        (metric_name: str, tags: dict[str, str]) -> None

    Phase 2 follow-up: buffer + flush to reduce per-call HTTP overhead +
    address the cardinality flag from CB-5. V1 (N=1 Dave) is single-emit fine.
    """
    poster = http_post or _default_http_post
    headers = {"Authorization": f"Bearer {source_token}"}

    def emit(metric_name: str, tags: dict[str, str]) -> None:
        payload = {
            "metric": metric_name,
            "tags": tags,
            "value": 1,
        }
        poster(ingest_url, payload, headers, timeout_seconds)

    return emit


def emit_anthropic_cache_tokens(
    emitter: Callable[[str, dict[str, str]], None] | None,
    *,
    tenant_id: str,
    model: str,
    cache_creation_input_tokens: int,
    cache_read_input_tokens: int,
    standard_input_tokens: int,
) -> None:
    """Emit one metric per category from an Anthropic API response usage block.

    Caller extracts the three token counts from `response.usage.*` and passes
    them in. Metric shape per CB-5:
        keiracom.cache.anthropic.input_tokens{type, tenant_id, model}

    No-op when emitter is None (e.g. in tests / pre-Better-Stack envs).
    """
    if emitter is None:
        return
    for token_type, token_count in (
        ("create", cache_creation_input_tokens),
        ("read", cache_read_input_tokens),
        ("standard", standard_input_tokens),
    ):
        if token_count > 0:
            emitter(
                "keiracom.cache.anthropic.input_tokens",
                {
                    "type": token_type,
                    "tenant_id": tenant_id,
                    "model": model,
                    "count": str(token_count),
                },
            )
