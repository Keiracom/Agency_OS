#!/usr/bin/env python3
"""indexer_base.py — Shared HTTP + retry primitives for source → Weaviate indexers.

Multi-source indexer pipelines (KEI-85, parent KEI-107) all share the same
shape: pull from a source (Postgres / Linear / git / Slack-relay processed
dir) → POST to Weaviate :8090 with deterministic UUID → mark source as
indexed (or advance cursor) → write audit_logs entry.

This module captures only the universal bits — HTTP retry, audit row write,
class bootstrap — so each per-source indexer stays small + reviewable.

Used by:
- ceo_memory_indexer.py  → Decisions  (KEI-85 phase A)
- linear_state_indexer.py → Keis       (KEI-85 phase B)
- slack_indexer.py        → Staging_discoveries (KEI-85 phase C)
- git_commits_indexer.py  → Codebase   (KEI-85 phase D)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("indexer_base")

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8090")
# Loopback-only by design — Weaviate binds 127.0.0.1 per scripts/orchestrator/
# weaviate_capped.sh and serves plain HTTP. TLS is terminated at the
# Cloudflare Tunnel layer (T0.3, separate KEI), never at the Weaviate process.
# Switching this to https://127.0.0.1 would break the connection — there is
# no TLS listener inside the cgroup. The NOSONAR below suppresses S5332 on
# this line only; rationale is captured in this comment block.
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 10.0

# Stable namespace for deterministic-UUID derivation across indexer runs.
# Different from random uuid4 — same source key always maps to same Weaviate id.
INDEXER_UUID_NAMESPACE = uuid.UUID("9b5b5d51-2a32-4b71-9c5f-7b6c1e3a4d11")


class IndexerError(RuntimeError):
    """Indexer-specific runtime error."""


def deterministic_uuid(source: str, key: str) -> str:
    """Same `(source, key)` → same UUID across processes + restarts.

    `source` distinguishes the indexer (e.g. `ceo_memory`, `git`).
    `key` is the source-local identity (e.g. `ceo_memory.key:vN`, git sha).
    """
    return str(uuid.uuid5(INDEXER_UUID_NAMESPACE, f"{source}:{key}"))


@contextmanager
def _http_request(method: str, path: str, body: dict | None = None) -> Iterator[Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urlrequest.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        yield resp


def ensure_class(class_name: str, schema_body: dict) -> None:
    """Idempotent class create. Returns silently if class already present."""
    try:
        with _http_request("GET", f"/v1/schema/{class_name}"):
            logger.info("class %s already exists", class_name)
            return
    except urlerror.HTTPError as exc:
        if exc.code != 404:
            raise
    logger.info("creating Weaviate class %s", class_name)
    with _http_request("POST", "/v1/schema", schema_body) as resp:
        if resp.status >= 300:
            raise IndexerError(f"class create failed: {resp.status}")


def post_object(obj: dict) -> bool:
    """POST an object with retry. Idempotent if `id` is deterministic.

    Returns True on success (including 422 already-exists, which is treated
    as a no-op for indexer convergence).
    """
    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with _http_request("POST", "/v1/objects", obj) as resp:
                if 200 <= resp.status < 300:
                    return True
                logger.warning(
                    "post_object id=%s rc=%s attempt=%d",
                    obj.get("id"),
                    resp.status,
                    attempt,
                )
        except urlerror.HTTPError as exc:
            if exc.code == 422:
                logger.debug(
                    "post_object id=%s already exists (422 idempotent no-op)", obj.get("id")
                )
                return True
            logger.warning(
                "post_object id=%s HTTPError=%s attempt=%d",
                obj.get("id"),
                exc.code,
                attempt,
            )
        except OSError as exc:
            logger.warning(
                "post_object id=%s transient %s attempt=%d",
                obj.get("id"),
                exc,
                attempt,
            )
        if attempt < MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2
    return False


def aggregate_count(class_name: str) -> int | None:
    """Return current object count via GraphQL Aggregate. Returns None on error."""
    query = {"query": f"{{Aggregate{{{class_name}{{meta{{count}}}}}}}}"}
    try:
        with _http_request("POST", "/v1/graphql", query) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["data"]["Aggregate"][class_name][0]["meta"]["count"]
    except (KeyError, ValueError, urlerror.URLError, OSError):
        return None


R = TypeVar("R")  # Source-row type (per-indexer dataclass).


@dataclass(frozen=True)
class BatchOutcome:
    selected: int
    success: int
    failed: int

    def to_dict(self) -> dict[str, int]:
        return {"selected": self.selected, "success": self.success, "failed": self.failed}


class BaseIndexer(ABC, Generic[R]):
    """Architectural contract for source → Weaviate indexers (KEI-85).

    Subclasses MUST implement:
      - source_name: stable string used as the first arg of deterministic_uuid()
      - target_class: Weaviate class name (e.g. "Decisions", "Keis")
      - class_schema: Weaviate class schema body for ensure_class()
      - identity_key(row): per-row source-local identity (used in deterministic UUID)
      - fetch_batch(batch_size): list[R] of source rows to attempt
      - build_object(row): the Weaviate POST body (must set "id" + "class" + "properties")

    The base implements ensure_class + the index_once loop so every per-source
    indexer ends up with the same convergence/idempotency story.
    """

    source_name: str
    target_class: str
    class_schema: dict

    @abstractmethod
    def fetch_batch(self, batch_size: int) -> list[R]: ...

    @abstractmethod
    def build_object(self, row: R) -> dict: ...

    def ensure_target_class(self) -> None:
        ensure_class(self.target_class, self.class_schema)

    def index_once(self, batch_size: int) -> BatchOutcome:
        rows = self.fetch_batch(batch_size)
        success = 0
        failed = 0
        for row in rows:
            if post_object(self.build_object(row)):
                success += 1
            else:
                failed += 1
        return BatchOutcome(selected=len(rows), success=success, failed=failed)


# ─── Shared DB-indexer runtime (KEI-109 dedup extraction) ────────────────────
#
# All Postgres-backed indexers (ceo_memory, elliot_memories, future schemas)
# share the same daemon/--once dispatch, signal handling, DSN resolution, and
# heartbeat reporting shape. `run_db_indexer` is the single entry point so
# each leaf indexer only defines its IndexerClass and constants.


def resolve_pg_dsn() -> str:
    """Resolve DATABASE_URL / SUPABASE_DB_URL with the psycopg-compatible
    rewrite for `postgresql+asyncpg://` DSNs.
    """
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        raise SystemExit("indexer: DATABASE_URL or SUPABASE_DB_URL must be set")
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def run_db_indexer(
    indexer_factory: Callable[[Any], BaseIndexer],
    *,
    unit_name: str,
    default_batch: int,
    poll_seconds: int,
) -> None:
    """Daemon/--once runtime for Postgres-backed indexers.

    `indexer_factory(conn)` returns a concrete BaseIndexer subclass instance.
    `unit_name` is the systemd unit (e.g. "ceo-memory-indexer") used for
    heartbeat tagging. `default_batch` + `poll_seconds` control loop cadence.

    Imports `psycopg` and the heartbeat shim lazily so unit tests can import
    indexer_base without those side-effects.
    """
    import psycopg  # noqa: PLC0415 — lazy to keep tests importable without psycopg
    from _heartbeat_shim import (  # noqa: PLC0415 — lazy: shim does sys.path mutation on import
        heartbeat_tick as _heartbeat_tick,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=default_batch)
    args = parser.parse_args()

    shutdown_flag = {"requested": False}

    def _on_signal(signum: int, _frame: Any) -> None:
        logger.info("signal %s received — shutdown", signum)
        shutdown_flag["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    # prepare_threshold=None per reference_psycopg_supabase_pgbouncer (KEI-54B
    # PR #881): Supabase pooler is pgbouncer txn-mode and drops PREPARE between
    # leases. Without this, psycopg3 auto-prepares after 5 executions and the
    # next batch hits DuplicatePreparedStatement → InvalidSqlStatementName loop
    # (root cause of KEI-70st — 20h stuck error stream after first ~200 rows).
    with psycopg.connect(resolve_pg_dsn(), autocommit=True, prepare_threshold=None) as conn:
        indexer = indexer_factory(conn)
        target_class = indexer.target_class
        logger.info(
            "indexer start source=%s class=%s batch=%d",
            indexer.source_name,
            target_class,
            args.batch,
        )
        indexer.ensure_target_class()

        def _tick_and_log(outcome: BatchOutcome, *, label: str) -> None:
            logger.info(
                "%s outcome=%s class_count=%s",
                label,
                outcome.to_dict(),
                aggregate_count(target_class),
            )
            _heartbeat_tick(
                unit_name,
                outcome_increment=outcome.success,
                status="ok" if outcome.failed == 0 else "degraded",
            )

        if args.once:
            _tick_and_log(indexer.index_once(args.batch), label="once")
            return

        while not shutdown_flag["requested"]:
            try:
                _tick_and_log(indexer.index_once(args.batch), label="batch")
            except Exception as exc:  # noqa: BLE001 — broad on purpose: any exception is a heartbeat-worthy signal
                logger.exception("batch failed — sleeping then continuing")
                _heartbeat_tick(
                    unit_name,
                    outcome_increment=0,
                    status="error",
                    error_message=str(exc)[:500],
                )
            for _ in range(poll_seconds):
                if shutdown_flag["requested"]:
                    break
                time.sleep(1)
    logger.info("indexer exiting cleanly")
