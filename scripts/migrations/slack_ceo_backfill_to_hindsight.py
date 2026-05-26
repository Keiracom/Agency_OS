#!/usr/bin/env python3
"""slack_ceo_backfill_to_hindsight.py — Phase A5 piece 4.

Ingests 2-month Slack #ceo channel archive into Hindsight under Dave's
fleet tenant_id via TaskContextWrapper. Per Path (C) dual-store + Viktor
2026-05-25 gap closure (A3 dual-write mirror covers FORWARD writes only;
historical Slack #ceo never re-ingested into Hindsight).

Input shape — JSONL file(s); each line is one Slack message. Operator
pre-exports #ceo via one of:
- scripts/orchestrator/slack_history_ingest.py with --dry-run → captures
  the same conversations.history payload + filter/classifier outputs
- Slack API conversations.history directly (`curl ... | jq -c '.messages[]'`)
- aiden_slack_mirror processed-dir archive (per-message JSON files)

JSONL line schema (subset Slack conversations.history shape we depend on):
  {"ts": "1779747400.123456",      # Slack ts is the canonical message id
   "user": "U091TGTPB9U",          # Slack user id (may be absent for bot/system)
   "text": "the message body",     # may be empty for files-only / threading-only msgs
   "channel": "ceo"                # informational; not required for routing
  }

Viktor gap (2026-05-25) — some historical messages lack user, text, or
both. This script does NOT skip them silently; instead each ingested
memory tracks `viktor_gap` flags in metadata so downstream recall can
filter on intact vs incomplete entries. Aggregate counts logged at end.

Chunking — one Slack message = one Hindsight memory. Granularity matches
how operators recall by ts. No aggregation across messages.

bd: Agency_OS-ygxz
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("slack_ceo_backfill_to_hindsight")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from keiracom_system.fleet.hindsight.smoke_wrappers import (  # noqa: E402
    FLEET_TENANT_ID,
    FleetHindsightClient,
    FleetTenantExtension,
)
from src.keiracom_system.memory.wrappers import TaskContextWrapper  # noqa: E402

DEFAULT_STATE_FILE = Path("runtime/a5_piece_4_slack_ceo_state.jsonl")


def load_messages_from_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            logger.warning("skipping malformed JSON line in %s: %s", path, exc)
    return rows


def detect_viktor_gaps(msg: dict[str, Any]) -> list[str]:
    """Return list of gap flags per Viktor 2026-05-25 gap classification."""
    gaps: list[str] = []
    if not msg.get("user"):
        gaps.append("missing_user")
    if not msg.get("text"):
        gaps.append("missing_text")
    if not msg.get("ts"):
        gaps.append("missing_ts")
    return gaps


def format_content(msg: dict[str, Any]) -> str:
    user = msg.get("user") or "?"
    text = msg.get("text") or ""
    return f"[{user}] {text}".strip()


def build_metadata(msg: dict[str, Any], source_file: Path) -> dict[str, Any]:
    gaps = detect_viktor_gaps(msg)
    return {
        "source": "a5_piece_4_slack_ceo_backfill",
        "source_file": str(source_file),
        "slack_ts": msg.get("ts", ""),
        "slack_user": msg.get("user", ""),
        "slack_channel": msg.get("channel", "ceo"),
        "viktor_gaps": ",".join(gaps),  # stringified per PR #1130 G2 metadata-all-string
        "external_id": f"slack-ceo:{msg.get('ts', '')}",
    }


def ingest_message(
    msg: dict[str, Any],
    source_file: Path,
    *,
    taskcontext_wrapper: TaskContextWrapper,
) -> tuple[bool, str]:
    content = format_content(msg)
    metadata = build_metadata(msg, source_file)
    try:
        resp = taskcontext_wrapper.ingest(
            tenant_id=FLEET_TENANT_ID,
            content=content,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"exception: {type(exc).__name__}: {exc}"
    if isinstance(resp, dict) and "error" in resp:
        return False, f"hindsight_error: {str(resp)[:200]}"
    return True, str(resp)[:120]


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


def run(
    *,
    input_files: list[Path],
    execute: bool,
    state_path: Path,
    wrapper_factory: Any | None = None,
) -> int:
    if not input_files:
        logger.error("no input files provided")
        return 2
    missing = [p for p in input_files if not p.exists()]
    if missing:
        for p in missing:
            logger.error("input file not found: %s", p)
        return 2
    seen = load_state(state_path)
    wrapper = (
        (
            wrapper_factory
            or (lambda: TaskContextWrapper(FleetHindsightClient(), FleetTenantExtension()))
        )()
        if execute
        else None
    )
    n_total = n_ok = n_fail = n_skip = 0
    gap_counts: dict[str, int] = {}
    for file_path in input_files:
        messages = load_messages_from_jsonl(file_path)
        logger.info("file=%s messages=%d", file_path, len(messages))
        for msg in messages:
            n_total += 1
            ts = msg.get("ts", "")
            ext_id = f"slack-ceo:{ts}"
            for gap in detect_viktor_gaps(msg):
                gap_counts[gap] = gap_counts.get(gap, 0) + 1
            if not ts:
                # No ts means no idempotency key — skip the message rather than
                # generate a synthetic id that may collide on re-run.
                n_fail += 1
                logger.warning("message missing ts — cannot idempotency-key; skipping")
                continue
            if ext_id in seen:
                n_skip += 1
                continue
            if not execute:
                logger.info("dry-run: would ingest %s", ext_id)
                continue
            ok, info = ingest_message(msg, file_path, taskcontext_wrapper=wrapper)
            entry = {"external_id": ext_id, "ok": ok, "info": info}
            append_state(state_path, entry)
            if ok:
                n_ok += 1
            else:
                n_fail += 1
                logger.warning("ingest %s FAILED: %s", ext_id, info)
    logger.info(
        "summary: total=%d ok=%d fail=%d skip=%d gaps=%s (execute=%s)",
        n_total,
        n_ok,
        n_fail,
        n_skip,
        gap_counts,
        execute,
    )
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        action="append",
        type=Path,
        required=True,
        help="JSONL file with Slack #ceo messages (repeatable)",
    )
    p.add_argument("--execute", action="store_true", help="write to Hindsight (default: dry-run)")
    p.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    return run(input_files=args.input, execute=args.execute, state_path=args.state_file)


if __name__ == "__main__":
    sys.exit(main())
