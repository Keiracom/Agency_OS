"""
P5 — Anthropic Rate Limits API integration.

Provides check_rate_limits(model, required_tokens) -> bool. Designed to
be called BEFORE spawning a batch of sub-agent work so the orchestrator
can decide whether to proceed, throttle, or defer.

How it works
------------
The Anthropic API exposes its current rate-limit posture via response
headers on every messages call:

  anthropic-ratelimit-requests-remaining          (RPM headroom)
  anthropic-ratelimit-tokens-remaining            (TPM headroom — total)
  anthropic-ratelimit-input-tokens-remaining      (input TPM headroom)
  anthropic-ratelimit-output-tokens-remaining     (output TPM headroom)
  anthropic-ratelimit-requests-reset              (ISO8601 reset)
  anthropic-ratelimit-tokens-reset                (ISO8601 reset)

There is NO standalone "rate limits" endpoint, so we probe the cheapest
available path — `/v1/messages/count_tokens` — which returns the same
ratelimit headers without consuming real tokens. Result cached per-model
for PROBE_TTL_SECONDS to avoid back-to-back probes.

The function is intentionally conservative:
  - No raises. Network / API errors return True (fail-open) so a
    Rate-Limits-API outage cannot block legitimate work.
  - No retries — this is a quick check, not a wait.
  - Boolean answer + a structured log line. Caller (the batch
    orchestrator) decides defer / proceed / split.

Security: pure HTTP via httpx, API key from settings, no shell, no URL
following from caller-supplied input.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
PROBE_TTL_SECONDS = 30
PROBE_TIMEOUT_S = 5.0

# Headers we care about — names as documented by Anthropic.
_HDR_REQ_REM = "anthropic-ratelimit-requests-remaining"
_HDR_TOK_REM = "anthropic-ratelimit-tokens-remaining"
_HDR_IN_REM = "anthropic-ratelimit-input-tokens-remaining"
_HDR_OUT_REM = "anthropic-ratelimit-output-tokens-remaining"
_HDR_REQ_RESET = "anthropic-ratelimit-requests-reset"
_HDR_TOK_RESET = "anthropic-ratelimit-tokens-reset"


@dataclass
class RateLimitSnapshot:
    """Cached headers from the most-recent probe per model."""

    model: str
    requests_remaining: int | None
    tokens_remaining: int | None
    input_tokens_remaining: int | None
    output_tokens_remaining: int | None
    requests_reset_iso: str | None
    tokens_reset_iso: str | None
    captured_at: float

    def headroom_for(self, required_tokens: int) -> tuple[bool, str]:
        """Return (has_headroom, reason). Considers the most-restrictive
        signal among the four *remaining* counters and the RPM check."""
        # RPM: refuse when zero requests remain (we'd hit the wall).
        if self.requests_remaining is not None and self.requests_remaining <= 0:
            return False, f"requests_remaining={self.requests_remaining}"

        # Token budgets — prefer the more specific headers when present.
        if (
            self.input_tokens_remaining is not None
            and self.input_tokens_remaining < required_tokens
        ):
            return False, (
                f"input_tokens_remaining={self.input_tokens_remaining} < required={required_tokens}"
            )
        if (
            self.output_tokens_remaining is not None
            and self.output_tokens_remaining < required_tokens
        ):
            return False, (
                f"output_tokens_remaining={self.output_tokens_remaining} "
                f"< required={required_tokens}"
            )
        # Total tokens fallback when per-direction headers absent.
        if self.tokens_remaining is not None and self.tokens_remaining < required_tokens:
            return False, (f"tokens_remaining={self.tokens_remaining} < required={required_tokens}")
        return True, "ok"


# Per-process snapshot cache. Keyed by model.
_SNAPSHOT_CACHE: dict[str, RateLimitSnapshot] = {}


# ── Header parsing ─────────────────────────────────────────────────────────


def _parse_int(v: str | None) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _snapshot_from_headers(model: str, headers) -> RateLimitSnapshot:
    """headers — any mapping-like (httpx Headers, dict, etc.)."""
    return RateLimitSnapshot(
        model=model,
        requests_remaining=_parse_int(headers.get(_HDR_REQ_REM)),
        tokens_remaining=_parse_int(headers.get(_HDR_TOK_REM)),
        input_tokens_remaining=_parse_int(headers.get(_HDR_IN_REM)),
        output_tokens_remaining=_parse_int(headers.get(_HDR_OUT_REM)),
        requests_reset_iso=headers.get(_HDR_REQ_RESET) or None,
        tokens_reset_iso=headers.get(_HDR_TOK_RESET) or None,
        captured_at=time.monotonic(),
    )


# ── Probe ──────────────────────────────────────────────────────────────────


def _api_key() -> str | None:
    key = getattr(settings, "anthropic_api_key", "") or ""
    return key.strip() or None


def _probe(model: str) -> RateLimitSnapshot | None:
    """POST /v1/messages/count_tokens with a 1-token payload to fetch the
    current rate-limit headers. Returns None on any HTTP failure (fail-open
    is handled by the caller)."""
    key = _api_key()
    if not key:
        logger.warning("anthropic_rate_limit: ANTHROPIC_API_KEY unset — cannot probe")
        return None

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ok"}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    try:
        with httpx.Client(timeout=PROBE_TIMEOUT_S) as client:
            resp = client.post(
                f"{ANTHROPIC_API_BASE}/messages/count_tokens",
                json=payload,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        logger.warning("anthropic_rate_limit: probe HTTP error: %s", exc)
        return None

    # Anthropic returns the rate-limit headers regardless of the body's
    # status code, but we still log non-2xx so debug surfaces are visible.
    if resp.status_code >= 400:
        logger.warning(
            "anthropic_rate_limit: probe status=%s body[:200]=%r",
            resp.status_code,
            resp.text[:200],
        )

    return _snapshot_from_headers(model, resp.headers)


def _cached_snapshot(model: str) -> RateLimitSnapshot | None:
    snap = _SNAPSHOT_CACHE.get(model)
    if snap is None:
        return None
    if (time.monotonic() - snap.captured_at) > PROBE_TTL_SECONDS:
        return None
    return snap


# ── Public surface ─────────────────────────────────────────────────────────


def check_rate_limits(model: str, required_tokens: int) -> bool:
    """Return True iff there is enough headroom on `model` for an
    operation that will consume roughly `required_tokens`.

    Cached per-model for PROBE_TTL_SECONDS (30s) so back-to-back checks
    don't probe the API every time. On any probe failure (network,
    missing API key, non-2xx) the function FAILS OPEN and returns True
    so that an integration outage cannot block legitimate work — the
    docstring on this function is the contract: a False answer means
    "we have evidence of insufficient headroom"; a True answer means
    "we have no evidence of insufficient headroom" (which includes
    "we couldn't ask").

    Side effect: emits a structured log line with the verdict and the
    raw counters so the orchestrator's logs carry the evidence.
    """
    if not isinstance(model, str) or not model:
        logger.warning("anthropic_rate_limit: invalid model arg %r — fail-open", model)
        return True
    if not isinstance(required_tokens, int) or required_tokens < 0:
        logger.warning(
            "anthropic_rate_limit: invalid required_tokens %r — fail-open",
            required_tokens,
        )
        return True

    snap = _cached_snapshot(model)
    if snap is None:
        snap = _probe(model)
        if snap is None:
            logger.info(
                "anthropic_rate_limit: no probe data for model=%s required=%d — fail-open",
                model,
                required_tokens,
            )
            return True
        _SNAPSHOT_CACHE[model] = snap

    ok, reason = snap.headroom_for(required_tokens)
    log = logger.info if ok else logger.warning
    log(
        "anthropic_rate_limit: model=%s required=%d ok=%s reason=%s "
        "rpm_rem=%s tpm_rem=%s in_rem=%s out_rem=%s",
        model,
        required_tokens,
        ok,
        reason,
        snap.requests_remaining,
        snap.tokens_remaining,
        snap.input_tokens_remaining,
        snap.output_tokens_remaining,
    )
    return ok


def reset_cache() -> None:
    """Clear the per-process snapshot cache. Tests + ops use this to
    force the next check_rate_limits() call to re-probe."""
    _SNAPSHOT_CACHE.clear()


def cached_snapshot(model: str) -> RateLimitSnapshot | None:
    """Read-only accessor for ops / tests."""
    return _cached_snapshot(model)
