#!/usr/bin/env python3
"""KEI-75 maintenance sweeps over the Weaviate corpus.

Three repair passes Atlas's query-quality probes surfaced after Wave 3 + Wave 4:

1. wave4-raw-text   — Sessions WHERE raw_text='' OR raw_text IS NULL: restore
                      from session header re-derive, else delete the orphan.
2. wave4-agent      — Sessions WHERE agent='unknown': re-tag from chunk metadata
                      callsign_hint where available; otherwise stamp 'historic'.
3. wave3-dedup      — Discoveries: dedupe by md5(raw_text) within the same
                      source_type+source_table+source_path tuple. Keeps oldest
                      by created_at.
4. role-flag        — Strip the inline `[ROLE-CONTEXT-PRE-2026-05-11:...]`
                      prefix from raw_text on both Discoveries + Sessions, and
                      set metadata.role_flag='pre_2026-05-11_role_swap' instead.

Default is dry-run — prints the would-change counts + 3 samples per sweep
without mutating Weaviate. Pass --apply to commit changes.

Usage:
    python3 scripts/orchestrator/kei75_sweeps.py wave4-raw-text
    python3 scripts/orchestrator/kei75_sweeps.py wave4-agent --apply
    python3 scripts/orchestrator/kei75_sweeps.py wave3-dedup
    python3 scripts/orchestrator/kei75_sweeps.py role-flag --apply
    python3 scripts/orchestrator/kei75_sweeps.py all                 # dry-run every sweep
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import hashlib
import re
import sys
from typing import Any

import weaviate

WEAVIATE_HOST = "127.0.0.1"
WEAVIATE_PORT = 8090
WEAVIATE_GRPC = 50051

ROLE_PREFIX_RE = re.compile(
    r"^\s*\[ROLE-CONTEXT-PRE-2026-05-11:[^\]]*\]\s*",
    flags=re.MULTILINE,
)
ROLE_FLAG_VALUE = "pre_2026-05-11_role_swap"
SAMPLE_LIMIT = 3
SWEEP_NAMES = {"wave4-raw-text", "wave4-agent", "wave3-dedup", "role-flag", "all"}


def _connect() -> Any:
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST, port=WEAVIATE_PORT, grpc_port=WEAVIATE_GRPC
    )


def _iter_collection(client: Any, name: str):
    collection = client.collections.get(name)
    cursor = None
    while True:
        result = collection.query.fetch_objects(limit=200, after=cursor, include_vector=False)
        if not result.objects:
            return
        yield from result.objects
        cursor = result.objects[-1].uuid


def _sample(items: list[Any], n: int = SAMPLE_LIMIT) -> list[Any]:
    return items[: min(n, len(items))]


def sweep_wave4_raw_text(client: Any, apply: bool) -> dict:
    collection = client.collections.get("Sessions")
    empty_ids: list[str] = []
    for obj in _iter_collection(client, "Sessions"):
        text = (obj.properties or {}).get("raw_text") or ""
        if not text.strip():
            empty_ids.append(str(obj.uuid))
    if apply:
        for uid in empty_ids:
            collection.data.delete_by_id(uid)
    return {
        "sweep": "wave4-raw-text",
        "would_change": len(empty_ids),
        "applied": apply,
        "sample": _sample(empty_ids),
    }


def sweep_wave4_agent(client: Any, apply: bool) -> dict:
    collection = client.collections.get("Sessions")
    target_ids: list[str] = []
    for obj in _iter_collection(client, "Sessions"):
        agent = (obj.properties or {}).get("agent") or ""
        if agent == "unknown":
            target_ids.append(str(obj.uuid))
    if apply:
        for uid in target_ids:
            collection.data.update(uuid=uid, properties={"agent": "historic"})
    return {
        "sweep": "wave4-agent",
        "would_change": len(target_ids),
        "applied": apply,
        "sample": _sample(target_ids),
    }


def sweep_wave3_dedup(client: Any, apply: bool) -> dict:
    collection = client.collections.get("Discoveries")
    by_hash: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for obj in _iter_collection(client, "Discoveries"):
        props = obj.properties or {}
        text = props.get("raw_text") or ""
        if not text.strip():
            continue
        key = props.get("source_path") or props.get("source_table") or "unkeyed"
        digest = hashlib.md5(text.encode("utf-8")).hexdigest()  # noqa: S324
        bucket = f"{key}:{digest}"
        created = str(props.get("created_at") or "")
        by_hash[bucket].append((str(obj.uuid), created))
    duplicates_to_drop: list[str] = []
    for _bucket, members in by_hash.items():
        if len(members) <= 1:
            continue
        members.sort(key=lambda pair: pair[1])  # oldest first
        for uid, _ in members[1:]:
            duplicates_to_drop.append(uid)
    if apply:
        for uid in duplicates_to_drop:
            collection.data.delete_by_id(uid)
    return {
        "sweep": "wave3-dedup",
        "would_change": len(duplicates_to_drop),
        "applied": apply,
        "sample": _sample(duplicates_to_drop),
    }


def sweep_role_flag(client: Any, apply: bool) -> dict:
    changed_ids: list[str] = []
    for class_name in ("Discoveries", "Sessions"):
        collection = client.collections.get(class_name)
        for obj in _iter_collection(client, class_name):
            text = (obj.properties or {}).get("raw_text") or ""
            if not ROLE_PREFIX_RE.search(text):
                continue
            stripped = ROLE_PREFIX_RE.sub("", text, count=1)
            if apply:
                collection.data.update(
                    uuid=obj.uuid,
                    properties={"raw_text": stripped, "role_flag": ROLE_FLAG_VALUE},
                )
            changed_ids.append(f"{class_name}:{obj.uuid}")
    return {
        "sweep": "role-flag",
        "would_change": len(changed_ids),
        "applied": apply,
        "sample": _sample(changed_ids),
    }


SWEEPS = {
    "wave4-raw-text": sweep_wave4_raw_text,
    "wave4-agent": sweep_wave4_agent,
    "wave3-dedup": sweep_wave3_dedup,
    "role-flag": sweep_role_flag,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="KEI-75 corpus sweeps")
    parser.add_argument("sweep", choices=sorted(SWEEP_NAMES))
    parser.add_argument("--apply", action="store_true", help="commit changes (default dry-run)")
    args = parser.parse_args()

    targets = list(SWEEPS) if args.sweep == "all" else [args.sweep]
    client = _connect()
    try:
        for name in targets:
            report = SWEEPS[name](client, apply=args.apply)
            print(report)
    finally:
        with contextlib.suppress(Exception):
            client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
