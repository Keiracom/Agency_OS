#!/usr/bin/env python3
"""preflight_resources.py — KEI-56 pre-deployment resource check.

Run BEFORE starting any new resource-intensive service (Weaviate, LlamaIndex,
Cognee, additional Claude session). Verifies:

    free_mb (MemAvailable) >= PREFLIGHT_MIN_HEADROOM_MB

If insufficient: exit 1 + post warning to #ceo. The caller (operator or
systemd unit's ExecStartPre=) should fail-fast on non-zero exit to block the
new service from starting.

Usage:
    scripts/orchestrator/preflight_resources.py            # uses defaults
    scripts/orchestrator/preflight_resources.py --headroom-mb 4096
    scripts/orchestrator/preflight_resources.py --service weaviate
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Reuse the meminfo reader from resource_monitor.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from resource_monitor import _read_meminfo  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("preflight_resources")

# Default headroom = 2 GiB per Linear KEI-56 spec.
DEFAULT_MIN_HEADROOM_MB = 2 * 1024


def check_headroom(min_headroom_mb: int) -> tuple[bool, int]:
    """Return (ok, available_mb)."""
    mem = _read_meminfo()
    available = mem.get("MemAvailable", 0)
    return available >= min_headroom_mb, available


def _post_ceo_block(service: str, available_mb: int, required_mb: int) -> None:
    relay = Path(__file__).resolve().parent.parent / "slack_relay.py"
    if not relay.is_file():
        logger.warning("slack_relay.py missing — dropping block post")
        return
    msg = (
        f":no_entry: preflight BLOCK — service `{service}` start refused: "
        f"available={available_mb}MB < required={required_mb}MB headroom. "
        f"Source: preflight_resources (KEI-56)."
    )
    try:
        subprocess.run(
            ["python3", str(relay), "-c", "ceo", msg],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("slack_relay -c ceo failed: %s", exc)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--headroom-mb",
        type=int,
        default=DEFAULT_MIN_HEADROOM_MB,
        help=f"Minimum MemAvailable in MiB to allow start (default {DEFAULT_MIN_HEADROOM_MB})",
    )
    p.add_argument(
        "--service",
        default="unspecified",
        help="Service name for #ceo alert context",
    )
    args = p.parse_args(argv)

    ok, available = check_headroom(args.headroom_mb)
    if ok:
        logger.info(
            "preflight OK: %s — available=%dMB >= required=%dMB",
            args.service,
            available,
            args.headroom_mb,
        )
        return 0

    logger.error(
        "preflight BLOCK: %s — available=%dMB < required=%dMB",
        args.service,
        available,
        args.headroom_mb,
    )
    _post_ceo_block(args.service, available, args.headroom_mb)
    return 1


if __name__ == "__main__":
    sys.exit(main())
