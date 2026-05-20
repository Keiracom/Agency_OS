#!/usr/bin/env python3
"""ingest_strategic_docs.py — load ceo_memory strategic_doc:* into memory.

Dave directive 2026-05-20. The StrategicDocuments Weaviate class exists but
is empty — the drive-strategic-indexer never filled it (Drive 403). Dave
fetched the 5 strategic docs and wrote them to public.ceo_memory under
`strategic_doc:*` keys. This script promotes those entries into BOTH memory
stores so they are queryable end-to-end:
  - Weaviate StrategicDocuments class — first-class objects (direct query).
  - Cognee knowledge graph — so cognee_recall surfaces them.

Re-runnable: each doc gets a deterministic UUID (uuid5 of its drive_id), so
a re-run upserts (delete + recreate) — safe to wire to a timer if the
ceo_memory snapshot is refreshed.

Usage:
    python3 scripts/orchestrator/ingest_strategic_docs.py            # dry-run
    python3 scripts/orchestrator/ingest_strategic_docs.py --apply    # write Weaviate

Exit codes:
  0  clean (dry-run, or every doc upserted)
  1  one or more docs failed
  2  config error (no DSN) / Weaviate unreachable
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

logger = logging.getLogger("ingest_strategic_docs")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_WEAVIATE_BASE = f"http://{os.environ.get('WEAVIATE_HOST', '127.0.0.1')}:{os.environ.get('WEAVIATE_PORT', '8090')}"
_CLASS = "StrategicDocuments"
_UUID_NS = uuid.UUID("6f4a1d2e-0000-5000-a000-5337a7e9d0c5")  # fixed namespace


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def fetch_strategic_docs(conn: Any) -> list[dict[str, Any]]:
    """Read ceo_memory strategic_doc:* entries → [{key,title,content,drive_id}]."""
    out: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT key, value FROM public.ceo_memory WHERE key LIKE 'strategic_doc:%' ORDER BY key"
        )
        for key, value in cur.fetchall():
            v = value if isinstance(value, dict) else json.loads(value)
            out.append(
                {
                    "key": key,
                    "title": v.get("title", key),
                    "content": v.get("content", ""),
                    "drive_id": v.get("drive_id", key),
                }
            )
    return out


def _weaviate(method: str, path: str, body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 — fixed loopback Weaviate endpoint
        f"{_WEAVIATE_BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def upsert_doc(doc: dict[str, Any]) -> None:
    """Delete-then-create the StrategicDocuments object (deterministic UUID
    upsert). Raises RuntimeError on failure."""
    obj_id = str(uuid.uuid5(_UUID_NS, doc["drive_id"]))
    _weaviate("DELETE", f"/v1/objects/{_CLASS}/{obj_id}")  # ignore 404 — fresh
    payload = {
        "class": _CLASS,
        "id": obj_id,
        "properties": {
            "doc_id": doc["drive_id"],
            "doc_url": f"https://docs.google.com/document/d/{doc['drive_id']}",
            "title": doc["title"],
            "section": "(full document)",
            "content": doc["content"],
            "ratified_by": "dave",
        },
    }
    status, resptext = _weaviate("POST", "/v1/objects", payload)
    if status not in (200, 201):
        raise RuntimeError(f"Weaviate POST {status}: {resptext[:200]}")


def cognee_ingest_doc(doc: dict[str, Any]) -> None:
    """Ingest the doc's content into Cognee so cognee_recall surfaces it.
    Raises RuntimeError on failure."""
    sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS/scripts")
    from cognee_http_client import ingest  # noqa: PLC0415 — deferred optional import

    text = f"# {doc['title']}\n\n{doc['content']}"
    result = ingest(text, source_path=f"strategic_doc/{doc['key']}")
    if result is None:
        raise RuntimeError("cognee ingest returned no token")
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"cognee ingest error: {result['error']}")


def run(*, apply: bool) -> int:
    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed")
        return 2
    try:
        dsn = _dsn()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 2

    with psycopg.connect(dsn, prepare_threshold=None) as conn:
        docs = fetch_strategic_docs(conn)
    if not docs:
        logger.error("no strategic_doc:* entries in ceo_memory")
        return 1
    logger.info("found %d strategic docs in ceo_memory", len(docs))

    failed = 0
    for doc in docs:
        if not apply:
            logger.info("[dry-run] would upsert %s — %s", doc["key"], doc["title"])
            continue
        try:
            upsert_doc(doc)
            cognee_ingest_doc(doc)
            logger.info("ingested %s → Weaviate StrategicDocuments + Cognee", doc["key"])
        except (RuntimeError, OSError, ImportError) as exc:
            logger.error("ingest failed for %s: %s", doc["key"], exc)
            failed += 1
    print(f"docs: {len(docs)}  failed: {failed}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write Weaviate (default dry-run)")
    args = parser.parse_args(argv)
    return run(apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
