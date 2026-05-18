#!/usr/bin/env python3
"""_strategic_collection_schema.py — Weaviate StrategicDocuments collection bootstrap.

Idempotent: if the class already exists, logs and skips.  On schema drift
(class present but with different properties), logs a WARNING and does NOT
auto-migrate destructively.  Destructive migration requires an explicit
operator action outside this script.

Vectorizer: text2vec-openai (Dave Option A, KEI-196 fix-up).
Requires OPENAI_API_KEY in env.  The Weaviate container must be configured
with the openai module (ENABLE_MODULES=text2vec-openai or equivalent).

Usage (operator, post-merge OR first --mode=full run):
    python -m scripts.orchestrator._strategic_collection_schema --create

The main indexer (drive_strategic_indexer.py) calls ensure_strategic_class()
automatically on every startup, so manual invocation is optional.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from urllib import error as urlerror
from urllib import request as urlrequest

sys.path.insert(0, __file__.rsplit("/orchestrator/", 1)[0] + "/orchestrator")

from indexer_base import WEAVIATE_BASE, IndexerError  # noqa: E402

logger = logging.getLogger("strategic_collection_schema")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STRATEGIC_DOCS_CLASS = "StrategicDocuments"

STRATEGIC_DOCS_SCHEMA: dict = {
    "class": STRATEGIC_DOCS_CLASS,
    "vectorizer": "text2vec-openai",
    "properties": [
        {"name": "doc_id", "dataType": ["text"]},
        {"name": "doc_url", "dataType": ["text"]},
        {"name": "title", "dataType": ["text"]},
        {"name": "section", "dataType": ["text"]},
        {"name": "content", "dataType": ["text"]},
        {"name": "updated_at", "dataType": ["date"]},
        {"name": "ratified_by", "dataType": ["text"]},
        {"name": "ratified_at", "dataType": ["date"]},
    ],
}

REQUEST_TIMEOUT = 10.0


def _get(path: str) -> tuple[int, dict]:
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}{path}",
        headers={"Accept": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urlerror.HTTPError as exc:
        return exc.code, {}


def _post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}{path}",
        data=data,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urlerror.HTTPError as exc:
        body_bytes = exc.read() if hasattr(exc, "read") else b""
        return exc.code, {"error": body_bytes.decode(errors="replace")}


def ensure_strategic_class() -> None:
    """Idempotent class create.  Logs warning on drift, never destructs."""
    status, existing = _get(f"/v1/schema/{STRATEGIC_DOCS_CLASS}")
    if status == 200:
        existing_props = {p["name"] for p in existing.get("properties", [])}
        expected_props = {p["name"] for p in STRATEGIC_DOCS_SCHEMA["properties"]}
        if existing_props != expected_props:
            logger.warning(
                "schema drift on %s: expected=%s got=%s — no auto-migration",
                STRATEGIC_DOCS_CLASS,
                sorted(expected_props),
                sorted(existing_props),
            )
        else:
            logger.info("class %s already exists with correct schema", STRATEGIC_DOCS_CLASS)
        return
    if status != 404:
        raise IndexerError(f"unexpected GET /v1/schema status={status}")
    logger.info("creating Weaviate class %s", STRATEGIC_DOCS_CLASS)
    rc, resp_body = _post("/v1/schema", STRATEGIC_DOCS_SCHEMA)
    if rc >= 300:
        raise IndexerError(f"class create failed: {rc} — {resp_body}")
    logger.info("created %s (rc=%s)", STRATEGIC_DOCS_CLASS, rc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap StrategicDocuments Weaviate class")
    parser.add_argument("--create", action="store_true", help="Create the class if absent")
    args = parser.parse_args()
    if args.create:
        ensure_strategic_class()
        print(f"done — {STRATEGIC_DOCS_CLASS} class ready")
    else:
        parser.print_help()
        sys.exit(1)
