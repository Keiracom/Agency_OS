"""
CLI entrypoint for startup cleanup of stale agent claims.

Usage:
    python -m agent_coord.cleanup
    python src/agent_coord/cleanup.py
"""

import os
import sys

from .claims import scan_stale


def main() -> int:
    """Remove all stale claims and print a summary. Returns 0 always."""
    stale = scan_stale()
    n = 0
    for item in stale:
        claim_file = item.get("_claim_file", "")
        if claim_file and os.path.exists(claim_file):
            try:
                os.unlink(claim_file)
                print(f"  Removed stale claim: {item['path']} (held by {item['callsign']})")
                n += 1
            except FileNotFoundError:
                pass  # Already gone — race is fine

    print(f"Cleared {n} stale claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
