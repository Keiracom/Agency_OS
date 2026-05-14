"""indexing_queue_writer.py — KEI-61 Phase A capture-layer write API.

Minimal SDK module for webhook receivers + capture-layer callers to write
events to the public.indexing_queue staging buffer. Decouples webhook
ingestion (fast, always 200) from indexing-into-Weaviate (heavy, may fail)
by inserting a durable queue between them.

Usage:
    from scripts.orchestrator.indexing_queue_writer import queue_event

    row_id = queue_event(
        source='git',
        payload={'event': 'push', 'commit': 'abc123', 'files': [...]},
    )

Contract:
- write returns the row uuid (str) on success, raises on failure.
- Webhook receivers should wrap in try/except and respond 200 even on
  failure (don't ask upstream to retry; surface via alerting).
- <5ms typical insert latency assumes managed Supabase + same-region call.
- sanitise() integration with KEI-57 secret-redaction is a follow-up.

Phase B (gated on Atlas-KEI-48 Weaviate landing): worker that consumes
pending rows + retries failed + writes to Weaviate.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any, Callable

logger = logging.getLogger("indexing_queue_writer")

VALID_SOURCES: frozenset[str] = frozenset({
    "git", "slack", "linear", "ceo_memory", "tool_log",
})

DEFAULT_PROJECT_ID = os.environ.get("SUPABASE_PROJECT_ID", "jatzvazlbusedwsnqxzr")
DEFAULT_MCP_BRIDGE = os.environ.get(
    "AGENCY_OS_MCP_BRIDGE", "/home/elliotbot/clawd/skills/mcp-bridge"
)


class IndexingQueueError(RuntimeError):
    """Raised when the queue write fails. Callers should log + return 200 to
    upstream webhook (don't ask upstream to retry; surface via failed-row alert)."""


def queue_event(
    source: str,
    payload: dict[str, Any],
    *,
    write_fn: Callable[[str, dict[str, Any]], str] | None = None,
) -> str:
    """Insert a webhook event into public.indexing_queue. Returns row uuid."""
    if source not in VALID_SOURCES:
        raise IndexingQueueError(
            f"invalid source {source!r}; must be one of {sorted(VALID_SOURCES)}"
        )

    if write_fn is None:
        write_fn = _default_write_fn

    try:
        return write_fn(source, payload)
    except Exception as exc:  # noqa: BLE001 — bound to typed re-raise
        logger.warning("indexing_queue insert failed: %s", exc)
        raise IndexingQueueError(f"queue write failed: {exc}") from exc


def _default_write_fn(source: str, payload: dict[str, Any]) -> str:
    """Default Supabase insert via MCP bridge. Production code path."""
    payload_json = json.dumps(payload).replace("'", "''")
    sql = (
        "INSERT INTO public.indexing_queue (source, payload) "
        f"VALUES ('{source}', '{payload_json}'::jsonb) RETURNING id"
    )
    mcp_args = {"project_id": DEFAULT_PROJECT_ID, "query": sql}
    proc = subprocess.run(  # noqa: S603 — controlled args, no shell
        [
            "node",
            os.path.join(DEFAULT_MCP_BRIDGE, "scripts", "mcp-bridge.js"),
            "call",
            "supabase",
            "execute_sql",
            json.dumps(mcp_args),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        raise IndexingQueueError(
            f"mcp-bridge returncode={proc.returncode} stderr={proc.stderr[:200]}"
        )
    for token in proc.stdout.split('"'):
        if len(token) == 36 and token.count("-") == 4:
            return token
    raise IndexingQueueError(f"could not parse row uuid from response: {proc.stdout[:200]}")
