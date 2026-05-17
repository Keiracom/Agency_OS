#!/usr/bin/env python3
"""linear_state_indexer.py — KEI-85 phase B: index Linear KEI state into Weaviate Keis.

Polls Linear's GraphQL API for KEI issues belonging to team Keiracom, captures
title + description + state name + state type + updatedAt, and POSTs one
Weaviate Keis object per (linear_issue_id, updated_at) tuple. Each state
transition produces a new Weaviate object — preserving history so agents can
recall WHY a KEI moved Todo → In Progress → Done at recall time.

Idempotent: deterministic UUID derived from `linear:{issue_id}:{updated_at}`.
Re-polling unchanged issues returns 422 from Weaviate (already-exists) and is
treated as a no-op.

Cursor: tracks the max `updatedAt` seen so far in a tiny on-disk JSON. Each
poll fetches `WHERE updatedAt > $cursor` to keep the per-poll set small.

Usage:
    python3 scripts/orchestrator/linear_state_indexer.py            # daemon loop
    python3 scripts/orchestrator/linear_state_indexer.py --once     # one batch
    python3 scripts/orchestrator/linear_state_indexer.py --batch=100
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from indexer_base import (
    BaseIndexer,
    aggregate_count,
    deterministic_uuid,
)

logger = logging.getLogger("linear_state_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

KEIS_CLASS = "Keis"
SOURCE_NAME = "linear"
# Sonar S1192: define the epoch fallback literal once and reuse.
EPOCH_ISO = "1970-01-01T00:00:00Z"
POLL_SECONDS = int(os.environ.get("LINEAR_STATE_POLL_SECONDS", "60"))
BATCH_SIZE_DEFAULT = int(os.environ.get("LINEAR_STATE_BATCH_SIZE", "100"))
TEAM_KEY = os.environ.get("LINEAR_TEAM_KEY", "KEI")
CURSOR_PATH = Path(
    os.environ.get(
        "LINEAR_STATE_CURSOR_PATH", "/home/elliotbot/clawd/logs/linear_state_indexer.cursor"
    )
)

LINEAR_API = "https://api.linear.app/graphql"

KEIS_SCHEMA = {
    "class": KEIS_CLASS,
    "vectorizer": "none",
    "properties": [
        {"name": "raw_text", "dataType": ["text"]},
        {"name": "environment_hash", "dataType": ["text"]},
        {"name": "created_at", "dataType": ["date"]},
        {"name": "agent", "dataType": ["text"]},
        {"name": "kei", "dataType": ["text"]},
    ],
}


@dataclass(frozen=True)
class LinearIssue:
    id: str
    identifier: str
    title: str
    description: str
    state_name: str
    state_type: str
    updated_at: str
    assignee: str
    priority_name: str


_shutdown_requested = False


def _signal_handler(signum: int, _frame: Any) -> None:
    global _shutdown_requested
    logger.info("signal %s received — shutdown", signum)
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def _api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY")
    if not key:
        raise SystemExit("indexer: LINEAR_API_KEY must be set")
    return key


def _read_cursor() -> str:
    if not CURSOR_PATH.exists():
        return EPOCH_ISO
    try:
        return json.loads(CURSOR_PATH.read_text()).get("updated_at", EPOCH_ISO)
    except (ValueError, OSError):
        return EPOCH_ISO


def _write_cursor(updated_at: str) -> None:
    try:
        CURSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        CURSOR_PATH.write_text(json.dumps({"updated_at": updated_at}))
    except OSError as exc:
        logger.warning("cursor persist failed (%s) — non-fatal", exc)


MAX_GRAPHQL_RETRIES = 4
INITIAL_BACKOFF_SECONDS = 1.0
MAX_PAGINATION_PAGES = int(os.environ.get("LINEAR_STATE_MAX_PAGES", "20"))


def _handle_http_error(exc: urlerror.HTTPError, attempt: int, backoff: float) -> float | None:
    """Decide retry-or-raise for an HTTPError. Returns the next backoff value if
    retryable (caller must `continue`); returns None if terminal (caller must
    re-raise). Sleeps internally on retry."""
    if exc.code == 429:
        retry_after = _parse_retry_after(exc.headers.get("Retry-After"))
        wait = retry_after if retry_after is not None else backoff
        logger.warning("linear_api 429 (attempt=%d) — sleeping %ss", attempt, wait)
        time.sleep(wait)
        return backoff * 2
    if 500 <= exc.code < 600:
        logger.warning("linear_api %d (attempt=%d) — backoff %ss", exc.code, attempt, backoff)
        time.sleep(backoff)
        return backoff * 2
    return None


def _graphql(query: str, variables: dict) -> dict:
    """Linear GraphQL POST with retry + 429 Retry-After respect.

    Mirrors the indexer_base.post_object exponential-backoff shape so the
    failure surface across Weaviate + Linear is uniform. On 429: parse
    Retry-After header (seconds or http-date). On 5xx: exponential backoff.
    On terminal failure: raise so caller surfaces the error.
    """
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    backoff = INITIAL_BACKOFF_SECONDS
    last_exc: Exception | None = None
    for attempt in range(1, MAX_GRAPHQL_RETRIES + 1):
        req = urlrequest.Request(
            LINEAR_API,
            data=body,
            method="POST",
            headers={
                "Authorization": _api_key(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlrequest.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            last_exc = exc
            next_backoff = _handle_http_error(exc, attempt, backoff)
            if next_backoff is None:
                raise
            backoff = next_backoff
        except (urlerror.URLError, OSError) as exc:
            last_exc = exc
            logger.warning(
                "linear_api transient %s (attempt=%d) — backoff %ss", exc, attempt, backoff
            )
            time.sleep(backoff)
            backoff *= 2
    raise last_exc if last_exc else RuntimeError("linear_api retries exhausted")


def _parse_retry_after(header_value: str | None) -> float | None:
    if not header_value:
        return None
    try:
        return float(header_value)
    except ValueError:
        # http-date form — give up parsing and let caller fall back to backoff
        return None


LINEAR_QUERY = """
query KeisSince($filter: IssueFilter!, $first: Int!, $after: String) {
  issues(filter: $filter, first: $first, after: $after, orderBy: updatedAt) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      identifier
      title
      description
      updatedAt
      state { name type }
      assignee { name }
      priorityLabel
    }
  }
}
"""


def _parse_nodes(nodes: list[dict]) -> list[LinearIssue]:
    return [
        LinearIssue(
            id=n["id"],
            identifier=n.get("identifier", ""),
            title=n.get("title", ""),
            description=n.get("description") or "",
            state_name=(n.get("state") or {}).get("name", ""),
            state_type=(n.get("state") or {}).get("type", ""),
            updated_at=n.get("updatedAt", ""),
            assignee=((n.get("assignee") or {}).get("name") or ""),
            priority_name=n.get("priorityLabel", ""),
        )
        for n in nodes
    ]


def _fetch_page(
    cursor: str, batch_size: int, after: str | None
) -> tuple[list[LinearIssue], str | None] | None:
    """Single GraphQL page fetch. Returns `(issues, next_after)` on success;
    `next_after` is None when this is the last page. Returns None on any
    error so the caller can drop out of the pagination loop. Extracted so
    `fetch_linear_issues` stays under SonarCloud's cognitive-complexity cap.
    """
    variables: dict[str, Any] = {
        "filter": {
            "team": {"key": {"eq": TEAM_KEY}},
            "updatedAt": {"gt": cursor},
        },
        "first": batch_size,
    }
    if after:
        variables["after"] = after
    try:
        body = _graphql(LINEAR_QUERY, variables)
    except (urlerror.URLError, OSError, ValueError):
        return None
    if body.get("errors"):
        return None
    issues_block = body.get("data", {}).get("issues", {}) or {}
    page_info = issues_block.get("pageInfo", {}) or {}
    next_after = page_info.get("endCursor") if page_info.get("hasNextPage") else None
    return _parse_nodes(issues_block.get("nodes", []) or []), next_after


def fetch_linear_issues(cursor: str, batch_size: int) -> list[LinearIssue]:
    """Fetch ALL issues with updatedAt > cursor, paginating via hasNextPage.

    Hard-capped at MAX_PAGINATION_PAGES per fetch to bound one daemon poll's
    work. Remaining issues drain on the next poll (cursor will have advanced).
    """
    collected: list[LinearIssue] = []
    after: str | None = None
    for page in range(1, MAX_PAGINATION_PAGES + 1):
        result = _fetch_page(cursor, batch_size, after)
        if result is None:
            logger.warning(
                "linear_api page %d failed — returning partial batch (%d)",
                page,
                len(collected),
            )
            return collected
        issues, after = result
        collected.extend(issues)
        if after is None:
            return collected
    logger.warning(
        "pagination cap %d reached (%d issues) — next poll drains the rest",
        MAX_PAGINATION_PAGES,
        len(collected),
    )
    return collected


class LinearStateIndexer(BaseIndexer[LinearIssue]):
    """Linear KEI state → Keis concrete indexer (KEI-85 phase B)."""

    source_name = SOURCE_NAME
    target_class = KEIS_CLASS
    class_schema = KEIS_SCHEMA

    def __init__(self, batch_size: int) -> None:
        self._batch_size = batch_size
        self._last_max_updated_at: str | None = None

    def fetch_batch(self, batch_size: int) -> list[LinearIssue]:
        cursor = _read_cursor()
        issues = fetch_linear_issues(cursor, batch_size)
        if issues:
            self._last_max_updated_at = max(i.updated_at for i in issues if i.updated_at)
        return issues

    def build_object(self, row: LinearIssue) -> dict:
        return build_keis_doc(row)

    def advance_cursor(self) -> None:
        if self._last_max_updated_at:
            _write_cursor(self._last_max_updated_at)


def build_keis_doc(issue: LinearIssue) -> dict:
    body = {
        "identifier": issue.identifier,
        "title": issue.title,
        "description": issue.description,
        "state_name": issue.state_name,
        "state_type": issue.state_type,
        "assignee": issue.assignee,
        "priority": issue.priority_name,
    }
    raw_text = json.dumps(body, sort_keys=True, default=str)
    env_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    return {
        "class": KEIS_CLASS,
        "id": deterministic_uuid(SOURCE_NAME, f"{issue.id}:{issue.updated_at}"),
        "properties": {
            "raw_text": raw_text,
            "environment_hash": env_hash,
            "created_at": issue.updated_at or EPOCH_ISO,
            "agent": "system",
            "kei": issue.identifier,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE_DEFAULT)
    args = parser.parse_args()

    indexer = LinearStateIndexer(args.batch)
    indexer.ensure_target_class()
    logger.info(
        "indexer start source=%s class=%s batch=%d team=%s",
        SOURCE_NAME,
        KEIS_CLASS,
        args.batch,
        TEAM_KEY,
    )

    if args.once:
        outcome = indexer.index_once(args.batch)
        indexer.advance_cursor()
        logger.info(
            "once outcome=%s class_count=%s cursor=%s",
            outcome.to_dict(),
            aggregate_count(KEIS_CLASS),
            _read_cursor(),
        )
        return
    while not _shutdown_requested:
        try:
            outcome = indexer.index_once(args.batch)
            indexer.advance_cursor()
            logger.info(
                "batch outcome=%s class_count=%s cursor=%s",
                outcome.to_dict(),
                aggregate_count(KEIS_CLASS),
                _read_cursor(),
            )
        except Exception:
            logger.exception("batch failed — sleeping then continuing")
        for _ in range(POLL_SECONDS):
            if _shutdown_requested:
                break
            time.sleep(1)
    logger.info("indexer exiting cleanly")


if __name__ == "__main__":
    main()
    sys.exit(0)
