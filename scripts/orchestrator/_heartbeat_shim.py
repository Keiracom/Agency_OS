"""_heartbeat_shim.py — single shared path-resolver + import for the
KEI-91 heartbeat library.

Every long-running script that wants to emit heartbeats imports the
`heartbeat_tick` callable from this shim. The shim:

  1. Walks up the filesystem from its own location to find `src/observability/
     heartbeat.py` — depth-agnostic, so it works whether the calling script
     lives in scripts/, scripts/orchestrator/, or any other depth.
  2. Inserts the discovered `src/` directory onto sys.path (once, idempotent).
  3. Imports `observability.heartbeat.tick`. On ImportError specifically
     (NOT the broad Exception catch — Aiden's review #2), logs a warning
     and substitutes a no-op so calling services degrade gracefully without
     silent unknown failures.

Why a shim file rather than inline path-prepend:
  - One canonical site for the path-resolution logic — no copy-paste drift
    across the wired services. Aiden's review pinned that as a brittleness
    concern.
  - `suppress(ImportError)` instead of `suppress(Exception)` — surfaces non-
    import failures visibly to the caller's logger instead of swallowing
    them.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

_logger = logging.getLogger("heartbeat_shim")


def _resolve_src_dir() -> Path | None:
    """Walk up from this shim's location until `src/observability/heartbeat.py`
    is found. Returns the matching `src/` dir, or None if the layout has
    drifted.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "src" / "observability" / "heartbeat.py"
        if candidate.exists():
            return parent / "src"
    return None


_src_dir = _resolve_src_dir()
if _src_dir is not None and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

try:
    from observability.heartbeat import tick as _real_tick
except ImportError as exc:  # noqa: BLE001 — narrowed below to ImportError only
    _logger.warning(
        "_heartbeat_shim: cannot import observability.heartbeat (%s) — "
        "heartbeat_tick will be a no-op for this process",
        exc,
    )
    _real_tick = None


def heartbeat_tick(
    service_name: str,
    *,
    outcome_increment: int = 1,
    status: str = "ok",
    error_message: str | None = None,
    period_seconds: int = 300,
) -> None:
    """Forward to observability.heartbeat.tick if available; no-op otherwise.

    The signature mirrors heartbeat.tick exactly so callers don't have to
    care whether the shim resolved the import.
    """
    if _real_tick is None:
        return
    _real_tick(
        service_name,
        outcome_increment=outcome_increment,
        status=status,
        error_message=error_message,
        period_seconds=period_seconds,
    )


__all__ = ["heartbeat_tick"]


# Defensive: keep the module-level Any reference so type-checkers don't strip
# the lazy fallback. No runtime cost.
_: Any = _real_tick
