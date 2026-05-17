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

import json
import logging
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("indexer_base")

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8090")
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"

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
