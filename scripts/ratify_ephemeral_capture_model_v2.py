#!/usr/bin/env python3
"""Ratify ceo:ephemeral_capture_model_v1 -> v2 (direct-write).

LAW XIII currency update for Agency_OS-9goi. Dave ratified Path 1 (direct-write
exit_cycle -> Hindsight fleet_decisions, two-step retired) on 2026-05-29. The
canonical key still described the v1 two-step (agent -> ceo_memory -> atomiser);
this rewrites its value so downstream agents (Nova backfill #1278, future John
spawns) inherit the ratified model.

Idempotent: re-running upserts the same value. Must be run by an allowlisted
callsign (elliot|dave|john) per the KEI-87 ceo_memory write-guard — orion is
NOT allowlisted, so this ships in the PR and Elliot applies it.

    DATABASE_URL=... python3 scripts/ratify_ephemeral_capture_model_v2.py --callsign elliot
"""

from __future__ import annotations

import argparse
import json
import sys

from src.governance.ceo_memory_writer import upsert_ceo_memory_key

KEY = "ceo:ephemeral_capture_model_v1"

NEW_VALUE = {
    "date": "2026-05-29",
    "version": 2,
    "description": "How decisions are captured and persist in the ephemeral model (direct-write).",
    "ratified_by": "dave (2026-05-29) — supersedes the viktor+dave two-step v1 (2026-05-28)",
    "capture_loop": [
        "Decision happens in #ceo or agent work",
        "Agent (John) writes the decision DIRECTLY to the Hindsight fleet_decisions bank as "
        "an AtomV1 atom on spawn exit (src.keiracom_system.chat.exit_cycle.classify_and_save)",
        "Future spawn: Hindsight Layer 2 recall retrieves atoms from fleet_decisions",
    ],
    "retired": (
        "Two-step (agent -> ceo_memory -> atomiser -> fleet_decisions) is decommissioned. "
        "exit_cycle no longer writes ceo_memory."
    ),
    "critical_rule": (
        "Nothing writes automatically. John MUST call classify_and_save at every conversation "
        "exit; the Gemini classifier (confidence > 0.8, max 3) is the precision gate. If the "
        "agent exits without calling it, the next spawn has no knowledge. Write discipline is "
        "the gate."
    ),
    "supersedes": "v1 two-step model (2026-05-28)",
    "anchor": "Agency_OS-9goi (Orion) — LAW XIII currency update shipped with the live-writer PR",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--callsign", default="elliot", help="allowlisted writer (elliot|dave|john)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the value, do not write")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({KEY: NEW_VALUE}, indent=2))
        return 0
    upsert_ceo_memory_key(args.callsign, KEY, NEW_VALUE)
    print(f"ratified {KEY} -> v2 (direct-write) as callsign={args.callsign}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
