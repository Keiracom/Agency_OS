"""physical_ceiling.py — box RAM-based hard spawn ceiling (Agency_OS-cuit).

A PHYSICAL max-concurrent-spawns ceiling sized to available box RAM — separate
from the tenant tier ceiling (which can be uncapped for the operator per #1285).
This layer refuses a spawn if it would OOM the box, regardless of tenant tier.

Priority order for ceiling resolution:
  1. DISPATCHER_PHYSICAL_MAX_SPAWNS env — explicit operator-configured ceiling
  2. Computed: MemAvailable // DISPATCHER_AGENT_FOOTPRINT_MB  (live /proc/meminfo)
  3. DEFAULT_PHYSICAL_CEILING — conservative fallback when /proc/meminfo absent

Fail-safe: if the RAM read fails AND no explicit ceiling is set, the fallback
DEFAULT_PHYSICAL_CEILING (4) is used — never fail-open to "unlimited".
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_MEMINFO_PATH = Path("/proc/meminfo")
_PHYSICAL_CEILING_ENV = "DISPATCHER_PHYSICAL_MAX_SPAWNS"
_AGENT_FOOTPRINT_MB_ENV = "DISPATCHER_AGENT_FOOTPRINT_MB"

DEFAULT_AGENT_FOOTPRINT_MB = 256
# Conservative box-safe default when /proc/meminfo is unavailable and no
# explicit ceiling is configured. Sized for ~1GB free / 256MB per agent.
DEFAULT_PHYSICAL_CEILING = 4


def _read_available_mb() -> int | None:
    """Read MemAvailable from /proc/meminfo. Returns None on any error."""
    try:
        for line in _MEMINFO_PATH.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except Exception:  # noqa: BLE001
        pass
    return None


def get_physical_ceiling() -> int:
    """Resolve the physical max-concurrent-spawns ceiling for this box."""
    explicit = os.environ.get(_PHYSICAL_CEILING_ENV, "").strip()
    if explicit:
        try:
            return max(1, int(explicit))
        except ValueError:
            logger.warning(
                "invalid %s=%r — ignoring, computing from RAM", _PHYSICAL_CEILING_ENV, explicit
            )

    footprint_mb = DEFAULT_AGENT_FOOTPRINT_MB
    raw = os.environ.get(_AGENT_FOOTPRINT_MB_ENV, "").strip()
    if raw:
        try:
            footprint_mb = max(1, int(raw))
        except ValueError:
            logger.warning(
                "invalid %s=%r — using default %dMB",
                _AGENT_FOOTPRINT_MB_ENV,
                raw,
                DEFAULT_AGENT_FOOTPRINT_MB,
            )

    available_mb = _read_available_mb()
    if available_mb is not None:
        ceiling = max(1, available_mb // footprint_mb)
        logger.debug(
            "physical ceiling: %dMB available / %dMB per agent = %d concurrent",
            available_mb,
            footprint_mb,
            ceiling,
        )
        return ceiling

    logger.warning(
        "physical ceiling: /proc/meminfo unavailable, using conservative default %d",
        DEFAULT_PHYSICAL_CEILING,
    )
    return DEFAULT_PHYSICAL_CEILING


def check_physical_ceiling(active_count: int) -> tuple[bool, str]:
    """Return (can_spawn, reason). False means the spawn must be refused.

    Called at spawn admission with the current count of active spawns.
    The ceiling is re-read on every call so it adapts to live RAM pressure.
    Applies regardless of tenant tier — even the uncapped operator is bounded
    by what the box can physically hold without OOM.
    """
    ceiling = get_physical_ceiling()
    if active_count >= ceiling:
        return False, (
            f"physical RAM ceiling reached: {active_count}/{ceiling} active spawns "
            f"(box OOM guard — set {_PHYSICAL_CEILING_ENV} or free RAM to raise)"
        )
    return True, ""
