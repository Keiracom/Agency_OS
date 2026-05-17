"""bd_verify.py — KEI-58 CLI for `bd verify <kei-or-discovery-id>`.

Routed via scripts/bd shim. Returns a freshness verdict on the most recent
discovery_log row matching the given KEI. Exit 0 on any verdict (FRESH /
STALE / EXPIRED) — non-zero only on missing row or hard error so the shim
can distinguish "no such discovery" from "discovery is stale".

Usage:
    bd verify KEI-50
    bd verify KEI-50 --json
"""

from __future__ import annotations

import argparse
import json
import sys

from scripts.orchestrator.discovery_log import compute_freshness, load_all_discoveries


def _latest_for_kei(kei: str) -> dict | None:
    matches = [r for r in load_all_discoveries() if r.get("kei") == kei]
    return matches[-1] if matches else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bd verify")
    parser.add_argument("kei", help="KEI id (e.g. KEI-50) or discovery row id")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of human text")
    args = parser.parse_args(argv)

    row = _latest_for_kei(args.kei)
    if row is None:
        print(f"ERROR: no discovery row with kei={args.kei!r}", file=sys.stderr)
        return 2

    f = compute_freshness(row)
    if args.json:
        print(json.dumps({"kei": args.kei, **f}))
    else:
        verdict = f["verdict"].upper()
        print(f"{verdict} — {f['reason']}")
        if f["drift"]:
            print(f"  drift: {', '.join(f['drift'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
