#!/usr/bin/env python3
"""bd_challenge.py — KEI-55 CLI wrapper for discovery_validation.challenge.

Usage:
    python3 scripts/bd_challenge.py <discovery_id> --by <callsign> --counter <text...>

Example:
    python3 scripts/bd_challenge.py abc-123 --by atlas --counter this finding is outdated since KEI-57 changed the model
"""

from __future__ import annotations

import argparse
import json
import sys

from src.governance.discovery_validation import challenge


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Challenge a KEI-55 staging discovery by recording a counter finding.",
    )
    parser.add_argument("discovery_id", help="Weaviate object id of the staging discovery")
    parser.add_argument("--by", required=True, metavar="CALLSIGN", help="callsign of the challenger")
    parser.add_argument(
        "--counter",
        required=True,
        nargs="+",
        metavar="TEXT",
        help="counter finding text (no quoting needed — tokens joined with spaces)",
    )
    args = parser.parse_args(argv)

    counter_text = " ".join(args.counter)

    try:
        result = challenge(
            discovery_id=args.discovery_id,
            challenged_by_callsign=args.by,
            counter_finding_text=counter_text,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"ok": result, "discovery_id": args.discovery_id, "challenged_by": args.by}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
