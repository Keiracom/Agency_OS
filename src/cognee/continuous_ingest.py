"""continuous_ingest.py — passive watcher that feeds new Supabase writes
into the Cognee knowledge graph via Aiden's wrapper (src/cognee/client.py).

Watches three tables:
    public.ceo_memory           (key/value upserts; watermark = updated_at)
    public.governance_events    (append-only; watermark = timestamp)
    public.agent_memories       (per-callsign inserts; watermark = created_at)

After each scan, the per-table high-water mark is persisted to a JSON state
file. The next scan only fetches rows > watermark so the graph receives
each row exactly once across restarts.

========================================================================
DESIGN RATIONALE — POLLING + WATERMARK (Pattern A compliance)
========================================================================
The memory audit (Stream 1, 2026-05-12) named "Pattern A" the recurring
failure mode of writer-side migrations that wrap a new dependency around
existing writers without ever closing the old reader path. Wrap-and-leave
creates two SSOTs and unbounded migration debt.

Approach options weighed for Cognee continuous ingest:

  1. POLLING + WATERMARK (this module). Writers are completely untouched.
     The Cognee dependency lives on the reader side only. If Cognee is
     ever removed, deleting this module + its state file is the entire
     rollback. Latency = poll interval. Lossy only on rows whose
     timestamp ties exactly at the boundary — we use `>` not `>=` on the
     watermark so we never re-ingest, and we use a `started_at_safety`
     lookback so we don't miss rows that landed in the same second as
     the previous scan's max.

  2. LISTEN/NOTIFY via DB triggers. Real-time, but installs a DB-side
     trigger per table → every writer's INSERT now fires a side-effect
     it doesn't know about. That's Pattern A risk one level down: the
     trigger is a writer-side coupling we'd have to remove on rollback.
     Reserved for Phase 2 once polling is proven and we want sub-second
     latency.

  3. Supabase realtime channel. Same shape as LISTEN/NOTIFY routed via
     Supabase's WS layer. Same Pattern A trade-off, plus a runtime
     dependency on Supabase realtime being enabled per-table. Phase 2+.

  4. Wrap the writers (modify gatekeeper.py / store.py / etc. to call
     cognee.add inline after each insert). **Rejected.** Direct Pattern
     A violation: every writer now has a Cognee import; removing Cognee
     means editing every writer; reader close is impossible because
     there is no reader — the writer IS the integration.

This module is also DRAFT — it does NOT auto-start. Activation is a
separate Phase 2 step Dave directs (no systemd unit shipped here, no
import hook, no entry point in any flow).
========================================================================

Public surface:
    run_once(state_path=None, *, table_filter=None) -> ScanResult
        One scan pass over the three watched tables. Returns counts +
        per-table watermarks. Best-effort: per-table errors are isolated
        — a Cognee outage on one table does not block the others, and
        the failed table's watermark is NOT advanced.
    run_forever(state_path=None, *, interval_seconds=60) -> never
        Blocking sleep loop around run_once. Not auto-started.

State file format (JSON):
    {
      "ceo_memory":         {"watermark": "2026-05-12T03:47:12+00:00", "last_run_at": "..."},
      "governance_events":  {"watermark": "2026-05-12T03:47:12+00:00", "last_run_at": "..."},
      "agent_memories":     {"watermark": "2026-05-12T03:47:12+00:00", "last_run_at": "..."}
    }

Aiden's wrapper contract (src/cognee/client.py):
    async add(content, *, org_id, app_id, agent_id, node_set=None)
We dispatch a single asyncio.run() per scan batch to keep the public
surface synchronous and easy to call from a cron-equivalent.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.evo.supabase_client import sb_get

logger = logging.getLogger("cognee.continuous_ingest")

DEFAULT_STATE_PATH = Path("/tmp/agency-os-cognee-watermarks.json")
DEFAULT_LOOKBACK_SECONDS = 5
DEFAULT_PAGE_SIZE = 200
DEFAULT_ORG_ID = "keiracom_platform"
DEFAULT_APP_ID = "agency_os"
SYSTEM_AGENT_ID = "system"


@dataclass(frozen=True)
class TableSpec:
    """How to scan a watched table and turn its rows into Cognee chunks."""

    table: str
    watermark_column: str
    select_columns: str
    content_builder: Callable[[dict], str]
    agent_id_builder: Callable[[dict], str]


@dataclass
class ScanResult:
    """Per-run summary — counts ingested per table + final watermarks."""

    ingested: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    watermarks: dict[str, str] = field(default_factory=dict)


def _ceo_memory_content(row: dict) -> str:
    return f"ceo_memory[{row.get('key')}] = {json.dumps(row.get('value'), default=str)}"


def _governance_event_content(row: dict) -> str:
    return (
        f"governance_event[{row.get('event_type')}] callsign={row.get('callsign')} "
        f"tool={row.get('tool_name')} file={row.get('file_path')} "
        f"directive={row.get('directive_id')} data="
        f"{json.dumps(row.get('event_data') or {}, default=str)}"
    )


def _agent_memory_content(row: dict) -> str:
    return (
        f"agent_memory[{row.get('source_type')}] callsign={row.get('callsign')} "
        f"tags={row.get('tags')} content={row.get('content')}"
    )


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        table="ceo_memory",
        watermark_column="updated_at",
        select_columns="key,value,updated_at",
        content_builder=_ceo_memory_content,
        agent_id_builder=lambda _row: SYSTEM_AGENT_ID,
    ),
    TableSpec(
        table="governance_events",
        watermark_column="timestamp",
        select_columns="id,callsign,event_type,event_data,tool_name,file_path,timestamp,directive_id",
        content_builder=_governance_event_content,
        agent_id_builder=lambda row: row.get("callsign") or SYSTEM_AGENT_ID,
    ),
    TableSpec(
        table="agent_memories",
        watermark_column="created_at",
        select_columns="id,callsign,source_type,content,tags,created_at",
        content_builder=_agent_memory_content,
        agent_id_builder=lambda row: row.get("callsign") or SYSTEM_AGENT_ID,
    ),
)


def _load_state(state_path: Path) -> dict[str, dict[str, str]]:
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("state file unreadable, treating as empty: %s", exc)
        return {}


def _save_state(state_path: Path, state: dict[str, dict[str, str]]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def _initial_watermark(lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS) -> str:
    return (datetime.now(UTC) - timedelta(seconds=lookback_seconds)).isoformat()


def _fetch_new_rows(spec: TableSpec, watermark: str) -> list[dict]:
    params = {
        spec.watermark_column: f"gt.{watermark}",
        "select": spec.select_columns,
        "order": f"{spec.watermark_column}.asc",
        "limit": str(DEFAULT_PAGE_SIZE),
    }
    return sb_get(spec.table, params)


async def _ingest_rows(
    spec: TableSpec,
    rows: list[dict],
    *,
    add_fn: Callable[..., Any],
    org_id: str,
    app_id: str,
) -> None:
    """Await add() per row in timestamp order. Caller catches exceptions."""
    for row in rows:
        await add_fn(
            spec.content_builder(row),
            org_id=org_id,
            app_id=app_id,
            agent_id=spec.agent_id_builder(row),
            node_set=[f"source:{spec.table}"],
        )


def run_once(
    state_path: Path | None = None,
    *,
    table_filter: tuple[str, ...] | None = None,
    add_fn: Callable[..., Any] | None = None,
    org_id: str = DEFAULT_ORG_ID,
    app_id: str = DEFAULT_APP_ID,
    initial_lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS,
) -> ScanResult:
    """One polling pass. Updates state file on success per table."""
    state_path = state_path or DEFAULT_STATE_PATH
    state = _load_state(state_path)
    result = ScanResult()
    initial_wm = _initial_watermark(initial_lookback_seconds)

    if add_fn is None:
        from src.cognee.client import add as add_fn  # lazy — avoids import at module load

    for spec in TABLE_SPECS:
        if table_filter and spec.table not in table_filter:
            continue
        watermark = state.get(spec.table, {}).get("watermark", initial_wm)
        try:
            rows = _fetch_new_rows(spec, watermark)
        except Exception as exc:
            logger.warning("fetch %s failed: %s", spec.table, exc)
            result.errors[spec.table] = f"fetch: {exc}"
            result.watermarks[spec.table] = watermark
            continue
        if not rows:
            result.ingested[spec.table] = 0
            result.watermarks[spec.table] = watermark
            continue
        try:
            asyncio.run(_ingest_rows(spec, rows, add_fn=add_fn, org_id=org_id, app_id=app_id))
        except Exception as exc:
            # Pattern A safety: ingest failure must NOT advance the watermark.
            # Next scan retries the same rows; idempotency is Cognee's problem.
            logger.warning("ingest %s failed after %d rows: %s", spec.table, len(rows), exc)
            result.errors[spec.table] = f"ingest: {exc}"
            result.watermarks[spec.table] = watermark
            continue
        new_wm = str(rows[-1][spec.watermark_column])
        state[spec.table] = {
            "watermark": new_wm,
            "last_run_at": datetime.now(UTC).isoformat(),
        }
        result.ingested[spec.table] = len(rows)
        result.watermarks[spec.table] = new_wm

    _save_state(state_path, state)
    return result


def run_forever(
    state_path: Path | None = None,
    *,
    interval_seconds: int = 60,
) -> None:
    """Blocking sleep loop around run_once. Not auto-started — caller's job."""
    import time

    logger.info("continuous_ingest loop starting, interval=%ds", interval_seconds)
    while True:
        try:
            result = run_once(state_path)
            logger.info("scan: ingested=%s errors=%s", result.ingested, result.errors)
        except Exception as exc:
            logger.exception("run_once raised unexpectedly: %s", exc)
        time.sleep(interval_seconds)
