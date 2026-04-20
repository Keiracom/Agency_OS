"""
FILE: scripts/session_end_capture.py
PURPOSE: Capture session learnings into agent_memories before context exhaustion.
         Session continuity — what this session did, patterns surfaced, decisions made.
         Writes as tentative rows (ingest gate); promoted later via retrieval reinforcement
         or explicit Dave-confirm.

USAGE:
    python scripts/session_end_capture.py \
        --summary "Session ran L2 discernment build + 10-PR slate split..." \
        --patterns "coordination drift on file claims, scout utilisation pattern" \
        --decisions "L2 over L3 listener; 15 total PRs; post-pipeline scope added"

All three args optional but at least one required. Each is stored as its own agent_memories
row — summary as daily_log, patterns as pattern type, decisions as decision type.
All rows default to state='tentative' (ingest gate — diagnostic FM-2).

Designed to be called by an agent (us) near end-of-session — voluntary trigger, not a hook.
If context exhausts before calling, the learnings are lost — run it regularly.

Exit codes: 0 on success, 1 on any write failure (reported via stderr).
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

# Add repo root so src.memory imports resolve when invoked as a script
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.memory.store import store  # type: ignore


def _session_id() -> str:
    """Generate a session id for this capture event — UUID-based + timestamp."""
    return f"session_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _capture_item(
    callsign: str,
    session_id: str,
    source_type: str,
    content: str,
) -> tuple[bool, str]:
    """Write one row. Returns (success, id_or_error)."""
    try:
        memory_id = store(
            callsign=callsign,
            source_type=source_type,
            content=content,
            tags=["session_end_capture", session_id],
            typed_metadata={
                "session_id": session_id,
                "capture_event": "session_end",
                "captured_at": datetime.now(timezone.utc).isoformat(),
            },
            state="tentative",
        )
        return True, str(memory_id)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture session learnings to agent_memories at session end."
    )
    parser.add_argument("--summary", help="Session summary (→ daily_log row)")
    parser.add_argument(
        "--patterns",
        help="Comma-separated patterns surfaced (each → pattern row)",
    )
    parser.add_argument(
        "--decisions",
        help="Comma-separated decisions made (each → decision row)",
    )
    parser.add_argument(
        "--callsign",
        default=os.environ.get("CALLSIGN", "unknown"),
        help="Callsign attribution (default: env CALLSIGN)",
    )
    args = parser.parse_args()

    if not (args.summary or args.patterns or args.decisions):
        print(
            "ERROR: provide at least one of --summary, --patterns, --decisions",
            file=sys.stderr,
        )
        return 1

    session_id = _session_id()
    print(f"[session_end_capture] session_id={session_id} callsign={args.callsign}")

    errors: list[str] = []
    written: list[str] = []

    if args.summary:
        ok, result = _capture_item(
            args.callsign, session_id, "daily_log", args.summary
        )
        (written if ok else errors).append(
            f"daily_log {'→ ' + result if ok else ': ' + result}"
        )

    if args.patterns:
        for p in [s.strip() for s in args.patterns.split(",") if s.strip()]:
            ok, result = _capture_item(args.callsign, session_id, "pattern", p)
            (written if ok else errors).append(
                f"pattern {'→ ' + result if ok else ': ' + result}"
            )

    if args.decisions:
        for d in [s.strip() for s in args.decisions.split(",") if s.strip()]:
            ok, result = _capture_item(args.callsign, session_id, "decision", d)
            (written if ok else errors).append(
                f"decision {'→ ' + result if ok else ': ' + result}"
            )

    for line in written:
        print(f"  OK {line}")
    for line in errors:
        print(f"  ERR {line}", file=sys.stderr)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
