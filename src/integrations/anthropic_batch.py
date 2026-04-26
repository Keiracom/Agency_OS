"""
P4 — Anthropic Message Batches API integration (300K output beta).

Wrapper around POST /v1/messages/batches and the related GET endpoints.
Designed for bulk sub-agent work where the 50% pricing discount + the
new 300K-output token ceiling make synchronous /messages calls
economically + technically wrong.

Public surface
--------------
    create_batch(messages, model, ...) -> str      # returns batch_id
    poll_batch(batch_id) -> dict                   # raw status payload
    get_results(batch_id) -> list[dict]            # per-request results
    cancel_batch(batch_id) -> dict
    wait_for_batch(batch_id, ...) -> dict          # convenience polling loop

`messages` is a list[BatchRequest], where BatchRequest is either
  - a list[ {"role": ..., "content": ...} ]   — convenience shape
  - a {"custom_id": str, "params": {...}}     — full Anthropic shape

The convenience shape is wrapped automatically:
    custom_id = f"req-{i}"
    params    = {"model": model, "max_tokens": 4096, "messages": [...]}

Beta headers used (see Anthropic batch + 300K-output beta docs):
  anthropic-beta: message-batches-2024-09-24,output-300k-2026-03-24

Security
  - No subprocess. No URL following from caller-supplied input.
  - The only HTTP target is the constant ANTHROPIC_API_BASE.
  - batch_id is matched against an allow-list regex before being
    interpolated into a URL path.
  - Caller-supplied `messages` are JSON-serialised by httpx; never
    shell-quoted, never written to disk.
  - Every error path raises a typed exception OR returns a
    well-formed dict — the caller decides whether to retry.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION  = "2023-06-01"
# Two beta headers, comma-separated, per Anthropic docs:
#   message-batches-2024-09-24 — Batches API surface
#   output-300k-2026-03-24     — 300K output-token ceiling (P4 ask)
BATCH_BETA_HEADER = "message-batches-2024-09-24,output-300k-2026-03-24"

DEFAULT_MAX_TOKENS = 4_096
HTTP_TIMEOUT_S     = 30.0
POLL_INTERVAL_S    = 5.0
POLL_MAX_S         = 60 * 60 * 4   # 4 hour safety cap on wait_for_batch

_BATCH_ID_RE = re.compile(r"^msgbatch_[A-Za-z0-9_-]{1,128}$")


class AnthropicBatchError(RuntimeError):
    """Typed exception so callers can distinguish batch failures from
    generic httpx/JSON errors."""


# ── Helpers ────────────────────────────────────────────────────────────────

def _api_key() -> str:
    key = (getattr(settings, "anthropic_api_key", "") or "").strip()
    if not key:
        raise AnthropicBatchError("ANTHROPIC_API_KEY unset")
    return key


def _headers() -> dict[str, str]:
    return {
        "x-api-key":         _api_key(),
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta":    BATCH_BETA_HEADER,
        "content-type":      "application/json",
    }


def _validate_batch_id(batch_id: str) -> str:
    if not isinstance(batch_id, str) or not _BATCH_ID_RE.match(batch_id):
        raise AnthropicBatchError(f"invalid batch_id: {batch_id!r}")
    return batch_id


def _normalise_requests(
    messages: list[Any], model: str, max_tokens: int,
) -> list[dict]:
    """Accept either:
      - list[ list[{"role":..., "content":...}] ]   convenience shape
      - list[ {"custom_id": str, "params": {...}} ] full shape
    Return the full Anthropic shape in both cases.
    """
    if not isinstance(messages, list) or not messages:
        raise AnthropicBatchError("messages must be a non-empty list")

    out: list[dict] = []
    for i, item in enumerate(messages):
        if isinstance(item, dict) and "params" in item and "custom_id" in item:
            # Already in full shape — accept verbatim.
            out.append(item)
            continue
        if isinstance(item, list):
            out.append({
                "custom_id": f"req-{i}",
                "params": {
                    "model":      model,
                    "max_tokens": max_tokens,
                    "messages":   item,
                },
            })
            continue
        raise AnthropicBatchError(
            f"messages[{i}] must be a list of message dicts or a full request "
            f"dict with custom_id+params; got {type(item).__name__}"
        )
    return out


# ── Public API ─────────────────────────────────────────────────────────────

def create_batch(
    messages: list[Any],
    model: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = HTTP_TIMEOUT_S,
) -> str:
    """POST a new batch. Returns the batch_id."""
    if not isinstance(model, str) or not model:
        raise AnthropicBatchError("model must be a non-empty string")
    requests_payload = _normalise_requests(messages, model, max_tokens)
    body = {"requests": requests_payload}

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{ANTHROPIC_API_BASE}/messages/batches",
            json=body, headers=_headers(),
        )
    if resp.status_code >= 400:
        raise AnthropicBatchError(
            f"create_batch HTTP {resp.status_code}: {resp.text[:500]}"
        )

    data = resp.json()
    batch_id = data.get("id")
    if not isinstance(batch_id, str):
        raise AnthropicBatchError(f"create_batch: missing 'id' in response: {data!r}")
    logger.info(
        "anthropic_batch.create batch_id=%s requests=%d model=%s",
        batch_id, len(requests_payload), model,
    )
    return batch_id


def poll_batch(batch_id: str, *, timeout: float = HTTP_TIMEOUT_S) -> dict:
    """GET batch status. Returns the full payload (processing_status,
    request_counts, etc.). Raises on HTTP/JSON failures."""
    bid = _validate_batch_id(batch_id)
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(
            f"{ANTHROPIC_API_BASE}/messages/batches/{bid}",
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise AnthropicBatchError(
            f"poll_batch HTTP {resp.status_code}: {resp.text[:500]}"
        )
    return resp.json()


def get_results(batch_id: str, *, timeout: float = HTTP_TIMEOUT_S) -> list[dict]:
    """GET batch results. Returns a list of per-request result dicts
    (each has custom_id + result). Only valid AFTER the batch has
    processing_status='ended'."""
    bid = _validate_batch_id(batch_id)
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(
            f"{ANTHROPIC_API_BASE}/messages/batches/{bid}/results",
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise AnthropicBatchError(
            f"get_results HTTP {resp.status_code}: {resp.text[:500]}"
        )
    # Anthropic returns JSONL — one result object per line.
    out: list[dict] = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            import json
            out.append(json.loads(line))
        except (ValueError, TypeError) as exc:
            logger.warning("get_results: skip un-parseable line: %s", exc)
    logger.info("anthropic_batch.results batch_id=%s n=%d", bid, len(out))
    return out


def cancel_batch(batch_id: str, *, timeout: float = HTTP_TIMEOUT_S) -> dict:
    """POST cancel. Returns the updated batch payload."""
    bid = _validate_batch_id(batch_id)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{ANTHROPIC_API_BASE}/messages/batches/{bid}/cancel",
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise AnthropicBatchError(
            f"cancel_batch HTTP {resp.status_code}: {resp.text[:500]}"
        )
    return resp.json()


def wait_for_batch(
    batch_id: str,
    *,
    interval: float = POLL_INTERVAL_S,
    max_wait_s: float = POLL_MAX_S,
) -> dict:
    """Convenience polling loop. Returns the final payload when
    processing_status reaches a terminal state ('ended' / 'canceled' /
    'expired'). Raises on timeout or HTTP failure."""
    if interval <= 0:
        raise AnthropicBatchError("interval must be > 0")
    deadline = time.monotonic() + max_wait_s
    terminal = {"ended", "canceled", "expired", "failed"}
    while True:
        payload = poll_batch(batch_id)
        status = payload.get("processing_status")
        if status in terminal:
            logger.info(
                "anthropic_batch.wait batch_id=%s terminal=%s counts=%s",
                batch_id, status, payload.get("request_counts"),
            )
            return payload
        if time.monotonic() > deadline:
            raise AnthropicBatchError(
                f"wait_for_batch timed out (>{max_wait_s}s) — last status={status!r}",
            )
        time.sleep(interval)
