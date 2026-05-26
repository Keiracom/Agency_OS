#!/usr/bin/env python3
"""ceo_memory_hindsight_executor.py — Phase A5 piece 1b HTTP executor.

Consumes the per-row `_carve`-annotated JSONL emitted by piece 1a
(`scripts/migrations/ceo_memory_carving_classifier.py`) and writes each
MEMORY-tagged row to Hindsight via `DecisionWrapper.ingest` under Dave's
fleet tenant_id. POLICY-tagged rows are left in Supabase ceo_memory as
canonical policy SSOT per the dual-store resolution.

Reuses `FleetHindsightClient` + `FleetTenantExtension` from
`keiracom_system/fleet/hindsight/smoke_wrappers.py` (PR #1145).

Idempotent: state file at `runtime/ceo_memory_executor_state.jsonl`
tracks each completed `key`. Re-runs skip already-completed rows.

Default is dry-run (counts only, no ingest). `--execute` is
operator-gated. Refuses to run if input is empty (safety guard against
running against a stale or unfiltered file).

bd: Agency_OS-oq3c
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("ceo_memory_hindsight_executor")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from keiracom_system.fleet.hindsight.smoke_wrappers import (  # noqa: E402
    FLEET_TENANT_ID,
    FleetHindsightClient,
    FleetTenantExtension,
)
from src.keiracom_system.memory.wrappers import DecisionWrapper  # noqa: E402

MEMORY_CARVE_VALUE = "MEMORY"
DEFAULT_STATE_FILE = Path("runtime/ceo_memory_executor_state.jsonl")


def serialize_content(key: str, value: Any) -> str:
    """Turn a ceo_memory (key, value) into a single-string content payload
    Hindsight can index. Format: `<key>: <jsonified value>`. JSON keeps
    nested structure recall-able under tag queries downstream."""
    if isinstance(value, str):
        value_repr = value
    else:
        value_repr = json.dumps(value, default=str, sort_keys=True)
    return f"{key}: {value_repr}"


def build_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """Metadata block keyed on ceo_memory row identity. Hindsight stores
    metadata stringified per PR #1130 G2 finding; the wrappers handle the
    stringification but we keep types loose here."""
    return {
        "ceo_memory_key": row.get("key", ""),
        "source": "a5_piece_1b_backfill",
        "carve": MEMORY_CARVE_VALUE,
        "original_updated_at": row.get("updated_at", ""),
    }


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("ok") and entry.get("key"):
                seen.add(entry["key"])
        except json.JSONDecodeError:
            continue
    return seen


def append_state(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def filter_memory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("_carve") == MEMORY_CARVE_VALUE]


def execute_one(
    row: dict[str, Any],
    *,
    decision_wrapper: DecisionWrapper,
) -> tuple[bool, str]:
    """Ingest one MEMORY row via DecisionWrapper. Return (ok, info)."""
    content = serialize_content(row.get("key", ""), row.get("value"))
    metadata = build_metadata(row)
    try:
        resp = decision_wrapper.ingest(
            tenant_id=FLEET_TENANT_ID,
            content=content,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"exception: {type(exc).__name__}: {exc}"
    if isinstance(resp, dict) and "error" in resp:
        return False, f"hindsight_error: {str(resp)[:200]}"
    return True, str(resp)[:120]


def run(
    *,
    input_path: Path,
    execute: bool,
    state_path: Path,
    wrapper_factory: Any | None = None,
) -> int:
    """Read classified JSONL → filter to MEMORY → ingest each via wrapper."""
    if not input_path.exists():
        logger.error("input file not found: %s", input_path)
        return 2
    all_rows = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    memory_rows = filter_memory_rows(all_rows)
    if not memory_rows:
        logger.error(
            "no MEMORY-tagged rows in input — refusing to run (rerun piece 1a or "
            "verify --input path)"
        )
        return 2
    seen = load_state(state_path)
    logger.info(
        "input: total=%d memory=%d (skip %d non-MEMORY); state already-completed: %d",
        len(all_rows),
        len(memory_rows),
        len(all_rows) - len(memory_rows),
        len(seen),
    )

    if wrapper_factory is None:

        def wrapper_factory():  # noqa: E306
            client = FleetHindsightClient()
            tenants = FleetTenantExtension()
            return DecisionWrapper(client, tenants)

    decision_wrapper = wrapper_factory() if execute else None
    n_ok = n_fail = n_skip = 0
    for row in memory_rows:
        key = row.get("key", "")
        if key in seen:
            n_skip += 1
            continue
        if not execute:
            logger.info("dry-run: would ingest %s", key)
            continue
        ok, info = execute_one(row, decision_wrapper=decision_wrapper)
        if ok:
            n_ok += 1
            append_state(state_path, {"key": key, "ok": True, "info": info})
        else:
            n_fail += 1
            append_state(state_path, {"key": key, "ok": False, "info": info})
            logger.warning("ingest %s FAILED: %s", key, info)
    logger.info(
        "summary: memory_total=%d ok=%d fail=%d skip=%d (execute=%s)",
        len(memory_rows),
        n_ok,
        n_fail,
        n_skip,
        execute,
    )
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        required=True,
        help="JSONL emitted by ceo_memory_carving_classifier.py --export-classifications",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="write to Hindsight (default: dry-run)",
    )
    p.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    return run(input_path=args.input, execute=args.execute, state_path=args.state_file)


if __name__ == "__main__":
    sys.exit(main())
