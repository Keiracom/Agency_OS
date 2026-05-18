#!/usr/bin/env python3
"""kei196_reingest_with_vectorizer.py — re-ingest Weaviate collections with text2vec.

KEI-192 audit found vectorizer=none on all 5 retrieval-path collections:
Discoveries, Keis, AgentMemories, Decisions, Codebase. With no embeddings,
agent_query similarity scores return 0.0, the default min_score=0.50 filter
drops every result, and 12/14 retrieval_events end up with top_citation_id=NULL.

This script:
  1. Backs up each target collection's objects to a JSON file under
     /home/elliotbot/clawd/logs/kei196_backup/<class>.jsonl
  2. (Operator-gated) Drops the existing collection
  3. (Operator-gated) Recreates with vectorizer=text2vec-transformers
  4. (Operator-gated) Re-POSTs all backed-up objects (vectorizer auto-embeds)
  5. Runs the score validation: agent_query returns score > 0.0 on a probe

Prerequisites (operator must verify before --execute):
  - t2v-transformers inference container reachable from Weaviate
    (typical: docker run semitechnologies/transformers-inference:<MODEL>)
  - Weaviate config has the text2vec-transformers module enabled
  - Backup directory writable: /home/elliotbot/clawd/logs/kei196_backup/

Steps are independent + idempotent:
  --step backup    only back up; safe to run repeatedly
  --step recreate  DROPS + recreates schema (destructive — needs operator gate)
  --step restore   POSTs backed-up objects (idempotent via deterministic UUID
                   where source pipelines used uuid5; new randomised UUIDs
                   otherwise — safe but produces duplicates if rerun without
                   recreate)
  --step validate  agent_query probe — asserts score > 0.0
  --step all       backup → recreate → restore → validate (full cutover)

Default: dry-run with summary counts. --execute required to actually mutate
Weaviate state. The --execute flag is mandatory for any destructive step.

Rollback: if recreate succeeds but restore fails partway, the .jsonl backups
let the operator re-run --step restore manually or with the
--source-backup-dir override.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("kei196_reingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = int(os.environ.get("WEAVIATE_PORT", "8090"))
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR

BACKUP_DIR_DEFAULT = Path(
    os.environ.get("KEI196_BACKUP_DIR", "/home/elliotbot/clawd/logs/kei196_backup")
)

TARGET_COLLECTIONS: tuple[str, ...] = (
    "Discoveries",
    "Keis",
    "AgentMemories",
    "Decisions",
    "Codebase",
)

NEW_VECTORIZER = "text2vec-transformers"
NEW_MODULE_CONFIG = {
    "text2vec-transformers": {
        "vectorizeClassName": False,
        "poolingStrategy": "masked_mean",
    }
}


def _http_get(path: str) -> dict:
    req = urlrequest.Request(f"{WEAVIATE_BASE}{path}", method="GET")
    with urlrequest.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _http_request(method: str, path: str, body: dict | None = None) -> dict | None:
    data = json.dumps(body).encode() if body is not None else None
    req = urlrequest.Request(f"{WEAVIATE_BASE}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urlrequest.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


def fetch_class_schema(class_name: str) -> dict | None:
    """Return the existing class schema dict, or None if absent."""
    try:
        return _http_get(f"/v1/schema/{class_name}")
    except urlerror.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def backup_class(class_name: str, backup_dir: Path) -> int:
    """Page through the class and write each object as one JSONL line.

    Returns the count of backed-up objects. Uses Weaviate's cursor pagination
    via /v1/objects?class=<name>&limit=N&after=<id> for stable iteration.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    out_path = backup_dir / f"{class_name}.jsonl"
    n = 0
    after = ""
    page_size = 100
    with out_path.open("w", encoding="utf-8") as fh:
        while True:
            qs = f"class={class_name}&limit={page_size}"
            if after:
                qs += f"&after={after}"
            page = _http_get(f"/v1/objects?{qs}")
            objects = page.get("objects", []) or []
            if not objects:
                break
            for obj in objects:
                fh.write(json.dumps(obj) + "\n")
                n += 1
            after = objects[-1].get("id", "")
            if len(objects) < page_size:
                break
    logger.info("backup %s -> %s (%d objects)", class_name, out_path, n)
    return n


def recreate_class_with_vectorizer(class_name: str) -> bool:
    """DROP + CREATE class with text2vec-transformers. DESTRUCTIVE — operator-gated."""
    existing = fetch_class_schema(class_name)
    if existing is None:
        logger.warning("class %s does not exist — skipping recreate", class_name)
        return False
    properties = existing.get("properties", [])
    new_schema = {
        "class": class_name,
        "vectorizer": NEW_VECTORIZER,
        "moduleConfig": NEW_MODULE_CONFIG,
        "properties": properties,
    }
    _http_request("DELETE", f"/v1/schema/{class_name}")
    logger.info("dropped class %s", class_name)
    _http_request("POST", "/v1/schema", new_schema)
    logger.info("created class %s with vectorizer=%s", class_name, NEW_VECTORIZER)
    return True


def restore_class(class_name: str, backup_dir: Path) -> int:
    """Re-POST every backed-up object to the (now vectorizer-enabled) class.

    Objects are POST'd one at a time so the vectorizer module can compute
    each embedding. Returns the count of successfully restored objects.
    """
    src = backup_dir / f"{class_name}.jsonl"
    if not src.exists():
        logger.warning("no backup at %s — skipping restore", src)
        return 0
    n_ok = 0
    n_fail = 0
    with src.open() as fh:
        for line in fh:
            obj = json.loads(line)
            payload = {
                "class": class_name,
                "id": obj.get("id"),
                "properties": obj.get("properties") or {},
            }
            try:
                _http_request("POST", "/v1/objects", payload)
                n_ok += 1
            except urlerror.HTTPError as exc:
                if exc.code == 422:
                    n_ok += 1  # already exists — idempotent
                    continue
                logger.warning("restore %s/%s failed: %s", class_name, payload["id"], exc)
                n_fail += 1
    logger.info("restored %s: %d ok, %d failed", class_name, n_ok, n_fail)
    return n_ok


def validate_scores(class_name: str, probe_query: str = "memory recall") -> tuple[bool, float]:
    """Run a GraphQL nearText probe and assert top score > 0.0.

    Returns (passed, top_score). Passed=False means the vectorizer didn't
    produce non-zero similarity — either the inference container is not
    reachable or the data didn't index. Operator investigates.
    """
    gql = (
        f'{{ Get {{ {class_name}(nearText: {{concepts: ["{probe_query}"]}}, limit: 1) '
        "{ _additional { id certainty distance } } } }"
    )
    try:
        body = _http_request("POST", "/v1/graphql", {"query": gql}) or {}
    except urlerror.HTTPError as exc:
        logger.error("validate %s failed: %s", class_name, exc)
        return False, 0.0
    rows = body.get("data", {}).get("Get", {}).get(class_name, []) or []
    if not rows:
        return False, 0.0
    additional = rows[0].get("_additional", {}) or {}
    certainty = float(additional.get("certainty") or 0.0)
    return certainty > 0.0, certainty


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step",
        choices=("backup", "recreate", "restore", "validate", "all"),
        default="backup",
        help="step to run (default: backup — read-only)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="REQUIRED for any destructive step (recreate, restore, all)",
    )
    parser.add_argument(
        "--class",
        dest="class_name",
        choices=TARGET_COLLECTIONS,
        default=None,
        help="restrict to one class (default: all 5 target collections)",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(BACKUP_DIR_DEFAULT),
        help=f"backup directory (default: {BACKUP_DIR_DEFAULT})",
    )
    args = parser.parse_args(argv)

    classes = (args.class_name,) if args.class_name else TARGET_COLLECTIONS
    backup_dir = Path(args.backup_dir).resolve()

    destructive = args.step in ("recreate", "restore", "all")
    if destructive and not args.execute:
        logger.error(
            "--step %s is destructive — re-run with --execute. Dry-run note: "
            "would backup→recreate→restore %d collection(s): %s",
            args.step,
            len(classes),
            ",".join(classes),
        )
        return 1

    if args.step in ("backup", "all"):
        total = 0
        for c in classes:
            total += backup_class(c, backup_dir)
        logger.info("backup step complete: %d objects across %d classes", total, len(classes))

    if args.step in ("recreate", "all"):
        for c in classes:
            recreate_class_with_vectorizer(c)

    if args.step in ("restore", "all"):
        for c in classes:
            restore_class(c, backup_dir)

    if args.step in ("validate", "all"):
        all_pass = True
        for c in classes:
            ok, score = validate_scores(c)
            logger.info("validate %s: passed=%s top_certainty=%.3f", c, ok, score)
            if not ok:
                all_pass = False
        if not all_pass:
            logger.warning("validate failed for one or more classes — check inference container")
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
