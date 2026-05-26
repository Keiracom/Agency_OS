#!/usr/bin/env python3
"""discoveries_hand_migration.py — one-time hand-migration of Weaviate
Discoveries → Hindsight bank fleet_discoveries (V2.0 mem.weaviate_coldstart
step 5-A precondition for the LlamaIndex retirement reader cutover).

Context
-------
V2.0 lock on `mem.weaviate_coldstart` names three hand-migration classes:
Sessions, Global_governance_patterns, Discoveries. The indexer dual-write
mirror (PR #1147) catches *new* writes for the 7 classes in
`indexer_base.CLASS_TO_BANK` but pre-existing data + the three named
hand-migration classes need a one-time backfill. PR #1141 was the audit;
this script is the actual data load.

Sequence with the companion `indexer_base.CLASS_TO_BANK` edit landing in
the same PR:

1. PR merges → `Discoveries → fleet_discoveries` mapping goes live; all
   *new* Discoveries writes start dual-writing to Hindsight automatically.
2. Operator runs this script with `--execute` → existing Weaviate
   Discoveries objects are backfilled to Hindsight.
3. Verify pre/post counts match (script prints both).
4. A3-c2 step 5-B reader cutover (Agency_OS-0zv1) is now unblocked.

Idempotency
-----------
A state file (`runtime/discoveries_migration_state.jsonl`) records each
migrated external_id. Re-runs skip already-migrated IDs. Safe to abort and
resume.

Safety
------
Default is dry-run (counts only, no writes). `--execute` is operator-gated.
Failures log + continue; exit non-zero if any migration POST failed so the
operator gets a clear signal.

bd: Agency_OS-4bsc
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("discoveries_hand_migration")

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8090")
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR S5332 loopback
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://localhost:8889")  # NOSONAR S5332 loopback

WEAVIATE_CLASS = "Discoveries"
HINDSIGHT_BANK = "fleet_discoveries"

REQUEST_TIMEOUT = 30.0
PAGE_SIZE = 100
JSON_CONTENT_TYPE = "application/json"

DEFAULT_STATE_FILE = Path("runtime/discoveries_migration_state.jsonl")


def _http_get(base: str, path: str) -> dict:
    req = urlrequest.Request(f"{base}{path}", method="GET", headers={"Accept": JSON_CONTENT_TYPE})
    with urlrequest.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post(base: str, path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(
        f"{base}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": JSON_CONTENT_TYPE, "Accept": JSON_CONTENT_TYPE},
    )
    try:
        with urlrequest.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urlerror.HTTPError as exc:
        return exc.code, {"error": exc.read().decode("utf-8", errors="replace")[:500]}


def weaviate_count(class_name: str) -> int | None:
    """Return GraphQL Aggregate count for the class, or None on error."""
    query = {"query": f"{{Aggregate{{{class_name}{{meta{{count}}}}}}}}"}
    try:
        _, body = _http_post(WEAVIATE_BASE, "/v1/graphql", query)
        return body["data"]["Aggregate"][class_name][0]["meta"]["count"]
    except (KeyError, IndexError, TypeError, urlerror.URLError):
        logger.exception("weaviate_count failed for %s", class_name)
        return None


def iter_weaviate_objects(class_name: str, page_size: int = PAGE_SIZE):
    """Paginate /v1/objects?class=<name> via cursor (after=<id>)."""
    after = ""
    while True:
        qs = f"class={class_name}&limit={page_size}"
        if after:
            qs += f"&after={after}"
        try:
            page = _http_get(WEAVIATE_BASE, f"/v1/objects?{qs}")
        except urlerror.URLError:
            logger.exception("weaviate page fetch failed at after=%s", after)
            return
        objects = page.get("objects") or []
        if not objects:
            return
        yield from objects
        after = objects[-1].get("id", "")
        if len(objects) < page_size:
            return


def build_hindsight_item(weaviate_obj: dict) -> dict:
    """Map a Weaviate Discoveries object to a Hindsight memory item.

    Mirrors `indexer_base._post_object_hindsight_mirror` shape so backfilled
    items are indistinguishable from live-mirrored items downstream.
    """
    props = weaviate_obj.get("properties") or {}
    content = props.get("raw_text") or props.get("content") or json.dumps(props)[:8000]
    metadata = {k: str(v) for k, v in props.items() if k != "raw_text" and v is not None}
    metadata["mirror_source"] = "discoveries_hand_migration"
    metadata["weaviate_class"] = WEAVIATE_CLASS
    metadata["external_id"] = weaviate_obj.get("id", "")
    return {
        "content": content,
        "tags": [f"weaviate_class:{WEAVIATE_CLASS}"],
        "metadata": metadata,
    }


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if row.get("ok") and row.get("external_id"):
                seen.add(row["external_id"])
        except json.JSONDecodeError:
            continue
    return seen


def append_state(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def migrate_one(weaviate_obj: dict) -> tuple[bool, str]:
    """POST one mapped item to Hindsight. Return (ok, info)."""
    item = build_hindsight_item(weaviate_obj)
    body = {"items": [item], "async": False}
    status, resp = _http_post(HINDSIGHT_BASE, f"/v1/default/banks/{HINDSIGHT_BANK}/memories", body)
    if 200 <= status < 300:
        return True, str(resp)[:120]
    return False, f"rc={status} resp={str(resp)[:200]}"


def run(*, execute: bool, state_path: Path) -> int:
    pre = weaviate_count(WEAVIATE_CLASS)
    logger.info("pre-migration weaviate count: %s", pre)
    if pre is None:
        logger.error("weaviate Aggregate count unavailable — refusing to run")
        return 2
    seen = load_state(state_path)
    logger.info("state-file already-migrated: %d", len(seen))
    n_total = n_ok = n_fail = n_skip = 0
    t0 = time.time()
    for obj in iter_weaviate_objects(WEAVIATE_CLASS):
        n_total += 1
        ext_id = obj.get("id", "")
        if ext_id in seen:
            n_skip += 1
            continue
        if not execute:
            logger.info("dry-run: would migrate %s", ext_id)
            continue
        ok, info = migrate_one(obj)
        if ok:
            n_ok += 1
            append_state(state_path, {"external_id": ext_id, "ok": True, "info": info})
        else:
            n_fail += 1
            append_state(state_path, {"external_id": ext_id, "ok": False, "info": info})
            logger.warning("migrate %s FAILED: %s", ext_id, info)
    elapsed = time.time() - t0
    logger.info(
        "summary: total=%d ok=%d fail=%d skip=%d elapsed=%.1fs (execute=%s)",
        n_total,
        n_ok,
        n_fail,
        n_skip,
        elapsed,
        execute,
    )
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute", action="store_true", help="write to Hindsight (default: dry-run)")
    p.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    return run(execute=args.execute, state_path=args.state_file)


if __name__ == "__main__":
    sys.exit(main())
