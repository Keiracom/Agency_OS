#!/usr/bin/env python3
"""KEI-75 PR2 — add source_id property to Sessions class + backfill.

infra/weaviate/schema.py picks the property up for fresh installs (it's now
in MANDATORY_PROPERTIES). This script handles the live cluster:

    1. Issue POST /v1/schema/Sessions/properties to add source_id text
       column. Idempotent — HTTP 422 on already-present is treated as
       success.
    2. Iterate existing Sessions objects in chunks of 200. For each row,
       compute source_id from the chunk_id metadata Aiden's Wave 4 indexer
       wrote into the LlamaIndex node store. Fall back to the Weaviate
       object UUID prefixed with sessions: when chunk_id is absent.
    3. PATCH each row with the new property. Skip rows that already have
       a non-empty source_id so re-runs are idempotent.

Dry-run by default — prints projected updates + sample. Pass --apply to
commit changes. Pass --limit N to scope a smoke run.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

import weaviate

WEAVIATE_HOST = "127.0.0.1"
WEAVIATE_PORT_HTTP = 8090
WEAVIATE_PORT_GRPC = 50051
SESSIONS_CLASS = "Sessions"
PROPERTY_NAME = "source_id"
SAMPLE_LIMIT = 3


def _add_property(base_url: str) -> str:
    body = json.dumps({"name": PROPERTY_NAME, "dataType": ["text"]}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/v1/schema/{SESSIONS_CLASS}/properties",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:  # noqa: S310
            resp.read()
        return "added"
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            return "already_present"
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"property add failed: HTTP {exc.code} body={body_text[:200]}") from exc


def _iter_sessions(client: Any, limit: int | None) -> Iterator[Any]:
    collection = client.collections.get(SESSIONS_CLASS)
    cursor = None
    yielded = 0
    while True:
        result = collection.query.fetch_objects(limit=200, after=cursor, include_vector=False)
        if not result.objects:
            return
        for obj in result.objects:
            if limit is not None and yielded >= limit:
                return
            yield obj
            yielded += 1
        cursor = result.objects[-1].uuid


def _resolve_source_id(obj: Any) -> str:
    props = obj.properties or {}
    existing = props.get(PROPERTY_NAME)
    if existing and isinstance(existing, str) and existing.strip():
        return ""  # signal "skip; already has source_id"
    md = props.get("metadata") or {}
    if isinstance(md, str):
        with contextlib.suppress(Exception):
            md = json.loads(md)
    chunk_id = md.get("chunk_id") if isinstance(md, dict) else None
    if chunk_id and isinstance(chunk_id, str) and chunk_id.strip():
        return chunk_id
    return f"sessions:{obj.uuid}"


def run(host: str, port: int, apply: bool, limit: int | None) -> dict:
    base_url = f"http://{host}:{port}"  # NOSONAR python:S5332 loopback-only
    schema_action = _add_property(base_url)
    client = weaviate.connect_to_local(host=host, port=port, grpc_port=WEAVIATE_PORT_GRPC)
    collection = client.collections.get(SESSIONS_CLASS)
    would_update = 0
    skipped = 0
    sample_updates: list[tuple[str, str]] = []
    started = time.monotonic()
    try:
        for obj in _iter_sessions(client, limit):
            resolved = _resolve_source_id(obj)
            if not resolved:
                skipped += 1
                continue
            if apply:
                collection.data.update(uuid=obj.uuid, properties={PROPERTY_NAME: resolved})
            would_update += 1
            if len(sample_updates) < SAMPLE_LIMIT:
                sample_updates.append((str(obj.uuid), resolved))
    finally:
        with contextlib.suppress(Exception):
            client.close()
    return {
        "schema_action": schema_action,
        "would_update": would_update,
        "skipped_already_set": skipped,
        "applied": apply,
        "sample_updates": sample_updates,
        "elapsed_sec": round(time.monotonic() - started, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="KEI-75 PR2 Sessions source_id backfill")
    parser.add_argument("--host", default=WEAVIATE_HOST)
    parser.add_argument("--port", type=int, default=WEAVIATE_PORT_HTTP)
    parser.add_argument("--apply", action="store_true", help="commit changes (default dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="cap iteration at N rows (smoke)")
    args = parser.parse_args()
    report = run(args.host, args.port, apply=args.apply, limit=args.limit)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
