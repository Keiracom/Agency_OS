#!/usr/bin/env python3
"""LAW XVIII orchestration enforcement — PreToolUse hook.

Blocks Edit / Write / MultiEdit / NotebookEdit when the running session is a
callsign bot (elliot, aiden, max, atlas, orion, scout) and DAVE_OVERRIDE is
not set to '1'. Callsign bots must delegate write ops to sub-agents (Rule 4
ORCHESTRATE).

DAVE_OVERRIDE=1 lets the call through and appends an audit record to
logs/governance/dave_override.jsonl. Blocks append to
logs/governance/law_xviii_blocks.jsonl.

Hook protocol: reads PreToolUse JSON on stdin, prints decision JSON on
stdout, exits 0. Fail-open on any unexpected error so a hook bug cannot
paralyse a session.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

CALLSIGN_BOTS = frozenset({"elliot", "aiden", "max", "atlas", "orion", "scout"})
WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = REPO_ROOT / "logs" / "governance"
BLOCK_LOG = LOG_DIR / "law_xviii_blocks.jsonl"
OVERRIDE_LOG = LOG_DIR / "dave_override.jsonl"
BLOCK_REASON = "LAW_XVIII: callsign bots must delegate write ops to sub-agents"


def _append_jsonl(path: Path, record: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # never let logging failure paralyse the hook


def _read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _emit_block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> int:
    callsign = (os.environ.get("CALLSIGN") or "").strip().lower()
    override = os.environ.get("DAVE_OVERRIDE", "").strip() == "1"

    payload = _read_stdin()
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("notebook_path")
        or ""
    )

    if tool_name not in WRITE_TOOLS:
        return 0
    if callsign not in CALLSIGN_BOTS:
        return 0

    record = {
        "ts": int(time.time()),
        "callsign": callsign,
        "tool": tool_name,
        "file_path": file_path,
        "session_id": payload.get("session_id"),
    }

    if override:
        _append_jsonl(OVERRIDE_LOG, {**record, "event": "dave_override_pass"})
        return 0

    _append_jsonl(BLOCK_LOG, {**record, "event": "law_xviii_block"})
    _emit_block(BLOCK_REASON)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — fail-open
        sys.exit(0)
