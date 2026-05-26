#!/usr/bin/env python3
"""weaviate_to_hindsight_tenant_backfill.py — Phase A5 piece 2 generic harness.

Reads one Weaviate class via /v1/objects pagination + ingests each object
into Hindsight under Dave's fleet tenant_id via the named wrapper. One
invocation handles one class; operator runs repeatedly to backfill the
13 snapshot classes (per `live_state_snapshot.json` in the
pre-Hindsight backup at /home/elliotbot/clawd/backups/
memory_pre_hindsight_migration_20260525/).

Per `mem.weaviate_coldstart` empirical addendum (Atlas 2026-05-25):
live Weaviate is byte-identical to snapshot for unchanged data → reading
LIVE Weaviate IS reading the snapshot for backfill purposes. Snapshot
serves as the disaster-recovery audit baseline; live Weaviate is the
readable source.

Trio hand-migrations (PR #1172 Discoveries, #1174 Sessions, #1176
Global_governance_patterns) ingest into the indexer-mirror GLOBAL banks
(fleet_<class>); THIS harness ingests under Dave's TENANT bank via
wrappers for Dave-as-tenant memory recall.

Reuses FleetHindsightClient + FleetTenantExtension from
`keiracom_system/fleet/hindsight/smoke_wrappers.py` (PR #1145).

CLI:
  python3 scripts/migrations/weaviate_to_hindsight_tenant_backfill.py \\
    --class Decisions \\
    --wrapper decision \\
    [--execute]

Wrapper dispatch:
  decision    → DecisionWrapper.ingest(content, metadata)
  taskcontext → TaskContextWrapper.ingest(content, metadata)
  artifact    → ArtifactWrapper.ingest(content, author, artifact_ref, metadata)
  antipattern → AntiPatternWrapper.ingest(context, failed_path, verified_path, metadata)

bd: Agency_OS-inhl
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("weaviate_to_hindsight_tenant_backfill")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from keiracom_system.fleet.hindsight.smoke_wrappers import (  # noqa: E402
    FLEET_TENANT_ID,
    FleetHindsightClient,
    FleetTenantExtension,
)
from src.keiracom_system.memory.wrappers import (  # noqa: E402
    AntiPatternWrapper,
    ArtifactWrapper,
    DecisionWrapper,
    TaskContextWrapper,
)

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8090")
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR S5332 loopback
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30.0

DEFAULT_STATE_DIR = Path("runtime/a5_piece_2_state")

WRAPPER_NAMES = ("decision", "taskcontext", "artifact", "antipattern")


def _http_get(path: str) -> dict:
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}{path}",
        method="GET",
        headers={"Accept": "application/json"},
    )
    with urlrequest.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def iter_weaviate_objects(class_name: str, page_size: int = PAGE_SIZE):
    after = ""
    while True:
        qs = f"class={class_name}&limit={page_size}"
        if after:
            qs += f"&after={after}"
        try:
            page = _http_get(f"/v1/objects?{qs}")
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


def _content_from_props(props: dict[str, Any]) -> str:
    return props.get("raw_text") or props.get("content") or json.dumps(props)[:8000]


def _metadata_from_obj(obj: dict[str, Any], class_name: str, wrapper_name: str) -> dict[str, Any]:
    props = obj.get("properties") or {}
    meta = {k: str(v) for k, v in props.items() if k != "raw_text" and v is not None}
    meta["source"] = "a5_piece_2_snapshot_backfill"
    meta["weaviate_class"] = class_name
    meta["wrapper"] = wrapper_name
    meta["external_id"] = obj.get("id", "")
    return meta


def ingest_decision(wrapper: DecisionWrapper, obj: dict, class_name: str) -> Any:
    props = obj.get("properties") or {}
    return wrapper.ingest(
        tenant_id=FLEET_TENANT_ID,
        content=_content_from_props(props),
        metadata=_metadata_from_obj(obj, class_name, "decision"),
    )


def ingest_taskcontext(wrapper: TaskContextWrapper, obj: dict, class_name: str) -> Any:
    props = obj.get("properties") or {}
    return wrapper.ingest(
        tenant_id=FLEET_TENANT_ID,
        content=_content_from_props(props),
        metadata=_metadata_from_obj(obj, class_name, "taskcontext"),
    )


def ingest_artifact(wrapper: ArtifactWrapper, obj: dict, class_name: str) -> Any:
    props = obj.get("properties") or {}
    author = str(props.get("agent") or "unknown")
    artifact_ref = f"{class_name}/{obj.get('id', '')}"
    return wrapper.ingest(
        tenant_id=FLEET_TENANT_ID,
        content=_content_from_props(props),
        author=author,
        artifact_ref=artifact_ref,
        metadata=_metadata_from_obj(obj, class_name, "artifact"),
    )


def ingest_antipattern(wrapper: AntiPatternWrapper, obj: dict, class_name: str) -> Any:
    props = obj.get("properties") or {}
    context = str(props.get("context") or props.get("kei") or class_name)
    failed_path = str(props.get("failed_path") or props.get("raw_text") or "")
    verified_path = str(props.get("verified_path") or "")
    return wrapper.ingest(
        tenant_id=FLEET_TENANT_ID,
        context=context,
        failed_path=failed_path,
        verified_path=verified_path,
        metadata=_metadata_from_obj(obj, class_name, "antipattern"),
    )


INGESTERS = {
    "decision": (DecisionWrapper, ingest_decision),
    "taskcontext": (TaskContextWrapper, ingest_taskcontext),
    "artifact": (ArtifactWrapper, ingest_artifact),
    "antipattern": (AntiPatternWrapper, ingest_antipattern),
}


def build_wrapper(wrapper_name: str) -> Any:
    cls, _ = INGESTERS[wrapper_name]
    return cls(FleetHindsightClient(), FleetTenantExtension())


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("ok") and entry.get("external_id"):
                seen.add(entry["external_id"])
        except json.JSONDecodeError:
            continue
    return seen


def append_state(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def ingest_one(
    obj: dict,
    *,
    class_name: str,
    wrapper_name: str,
    wrapper: Any,
) -> tuple[bool, str]:
    _, ingester = INGESTERS[wrapper_name]
    try:
        resp = ingester(wrapper, obj, class_name)
    except Exception as exc:  # noqa: BLE001
        return False, f"exception: {type(exc).__name__}: {exc}"
    if isinstance(resp, dict) and "error" in resp:
        return False, f"hindsight_error: {str(resp)[:200]}"
    return True, str(resp)[:120]


def run(
    *,
    class_name: str,
    wrapper_name: str,
    execute: bool,
    state_path: Path,
    obj_iter=None,
    wrapper_factory=None,
) -> int:
    if wrapper_name not in INGESTERS:
        logger.error("unknown wrapper %r — allowed: %s", wrapper_name, sorted(INGESTERS))
        return 2
    iterator = obj_iter if obj_iter is not None else iter_weaviate_objects(class_name)
    wrapper = (wrapper_factory or (lambda: build_wrapper(wrapper_name)))() if execute else None
    seen = load_state(state_path)
    logger.info(
        "class=%s wrapper=%s execute=%s state_already_done=%d",
        class_name,
        wrapper_name,
        execute,
        len(seen),
    )
    n_total = n_ok = n_fail = n_skip = 0
    for obj in iterator:
        n_total += 1
        ext_id = obj.get("id", "")
        if ext_id in seen:
            n_skip += 1
            continue
        if not execute:
            logger.info("dry-run: would ingest %s/%s", class_name, ext_id)
            continue
        ok, info = ingest_one(
            obj,
            class_name=class_name,
            wrapper_name=wrapper_name,
            wrapper=wrapper,
        )
        if ok:
            n_ok += 1
            append_state(state_path, {"external_id": ext_id, "ok": True, "info": info})
        else:
            n_fail += 1
            append_state(state_path, {"external_id": ext_id, "ok": False, "info": info})
            logger.warning("ingest %s/%s FAILED: %s", class_name, ext_id, info)
    logger.info(
        "summary class=%s: total=%d ok=%d fail=%d skip=%d",
        class_name,
        n_total,
        n_ok,
        n_fail,
        n_skip,
    )
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--class", dest="class_name", required=True, help="Weaviate class name")
    p.add_argument("--wrapper", required=True, choices=WRAPPER_NAMES, help="Hindsight wrapper type")
    p.add_argument("--execute", action="store_true", help="write to Hindsight (default: dry-run)")
    p.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="default: runtime/a5_piece_2_state/<class>.jsonl",
    )
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    state_path = args.state_file or (DEFAULT_STATE_DIR / f"{args.class_name}.jsonl")
    return run(
        class_name=args.class_name,
        wrapper_name=args.wrapper,
        execute=args.execute,
        state_path=state_path,
    )


if __name__ == "__main__":
    sys.exit(main())
