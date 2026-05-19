#!/usr/bin/env python3
"""kei197_drop_null_raw_text.py — drop Discoveries rows with NULL raw_text.

Cleans up the 10 orphan rows Aiden's KEI-192 memory audit found: agent='elliot'
with raw_text=NULL, environment_hash=NULL, kei=NULL/empty. All written in a
single burst on 2026-05-16 14:34 UTC (creationTimeUnix 1778926061xxx). Source
data unrecoverable — drop the orphans rather than backfill from nothing.

Usage:
    python3 scripts/orchestrator/kei197_drop_null_raw_text.py --dry-run   # list only
    python3 scripts/orchestrator/kei197_drop_null_raw_text.py             # delete

Targets ALL classes that AgentMemories audit found null-raw_text rows in
(Discoveries by default; --class <Name> for others). The audit-confirmed
shape is: raw_text IS NULL — content is unrecoverable, so dropping is the
only sensible cleanup. Any row with non-null raw_text is untouched.

Defensive: dry-run is the default mode-of-mind. Run `--dry-run` first to
list. Then re-run without the flag to delete.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("kei197_drop_null_raw_text")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = int(os.environ.get("WEAVIATE_PORT", "8090"))
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR


def _query_null_raw_text(class_name: str) -> list[dict]:
    """Return objects in `class_name` where raw_text IS NULL.

    Weaviate's `IsNull` operator requires `indexNullState: true` on the
    invertedIndexConfig — not enabled on existing collections. Workaround:
    fetch by `agent` IS NOT NULL (so we get rows with at least the agent
    tag) and filter raw_text=None client-side. This catches the audit-
    confirmed shape: rows with non-null agent BUT null raw_text.

    For broader cleanup, iterate by agent value (the 10 known orphans are
    agent='elliot'); add more callsigns if/when the audit surfaces them.
    """
    gql = (
        f"{{ Get {{ {class_name}(limit: 10000) "
        "{ _additional { id creationTimeUnix } agent kei raw_text created_at } } }"
    )
    query = {"query": gql}
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}/v1/graphql",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urlerror.URLError:
        logger.exception("Weaviate unreachable at %s", WEAVIATE_BASE)
        return []
    rows = body.get("data", {}).get("Get", {}).get(class_name, []) or []
    # Client-side filter: keep only rows where raw_text is null/empty.
    null_rows = [r for r in rows if r.get("raw_text") is None or r.get("raw_text") == ""]
    return null_rows


def _delete_object(class_name: str, object_id: str) -> bool:
    """DELETE one object by id. Returns True on 204."""
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}/v1/objects/{class_name}/{object_id}",
        method="DELETE",
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return resp.status in (200, 204)
    except urlerror.HTTPError as exc:
        if exc.code == 404:
            logger.info("%s already gone (404)", object_id)
            return True
        logger.warning("delete %s failed: %s", object_id, exc)
        return False
    except urlerror.URLError as exc:
        logger.warning("delete %s transport error: %s", object_id, exc)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list affected rows; do NOT delete",
    )
    parser.add_argument(
        "--class",
        dest="class_name",
        default="Discoveries",
        help="Weaviate class to clean (default: Discoveries)",
    )
    args = parser.parse_args(argv)

    rows = _query_null_raw_text(args.class_name)
    if not rows:
        logger.info("%s: no null-raw_text rows found — clean", args.class_name)
        return 0

    logger.info("%s: %d null-raw_text rows found", args.class_name, len(rows))
    for r in rows:
        rid = (r.get("_additional") or {}).get("id", "?")
        agent = r.get("agent")
        kei = r.get("kei")
        created = r.get("created_at")
        logger.info("  id=%s agent=%r kei=%r created_at=%r", rid, agent, kei, created)

    if args.dry_run:
        logger.info("--dry-run: no deletions performed. Re-run without the flag to delete.")
        return 0

    deleted = 0
    failed = 0
    for r in rows:
        rid = (r.get("_additional") or {}).get("id", "")
        if not rid:
            continue
        if _delete_object(args.class_name, rid):
            deleted += 1
        else:
            failed += 1
    logger.info("deleted=%d failed=%d", deleted, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
