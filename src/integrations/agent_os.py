"""
Contract: src/integrations/agent_os.py
Purpose: MS Agent OS integration boundary — advisory-only by default.
Layer: integration
Directive: agent-os-advisory-flag (GOV-12)

ADVISORY_ONLY is a runtime CODE FLAG (env-driven), not a doc note.
When True, the Agent OS evaluate() path logs + returns a verdict but
NEVER blocks or raises. Enforcement (blocking) stays 100% in the
Sidecar (src/governance/gatekeeper.py). Agent OS does not touch it.

The check at the call site is a single boolean guard (see
`evaluate()`), satisfying GOV-12 "gates as code not comments".
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def _read_advisory_only() -> bool:
    """Read AGENT_OS_ADVISORY_ONLY env var. Default: True (safe — never blocks)."""
    raw = os.environ.get("AGENT_OS_ADVISORY_ONLY", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


ADVISORY_ONLY: bool = _read_advisory_only()


@dataclass(frozen=True)
class AgentOSVerdict:
    """Result of an Agent OS evaluation. `surfaced` = logged for ops review."""

    allowed: bool
    reason: str
    surfaced: bool = True


def evaluate(action: str, context: dict[str, Any] | None = None) -> AgentOSVerdict:
    """
    Agent OS advisory evaluation at the integration boundary.

    GOV-12 enforcement: the ADVISORY_ONLY guard below is the gate. If
    True, we log + surface a verdict and return. We do NOT raise. We do
    NOT block. Sidecar (gatekeeper) owns blocking.

    Args:
        action: Action identifier being evaluated (e.g. "tool.bash.exec").
        context: Optional context dict (callsign, tool args, etc.).

    Returns:
        AgentOSVerdict — advisory only when ADVISORY_ONLY is True.
    """
    ctx = context or {}
    verdict = AgentOSVerdict(allowed=True, reason="advisory-stub:no-rules-loaded")

    if ADVISORY_ONLY:
        logger.info(
            "agent_os.advisory action=%s callsign=%s verdict=%s reason=%s",
            action,
            ctx.get("callsign", "unknown"),
            verdict.allowed,
            verdict.reason,
        )
        return verdict

    # Non-advisory path is intentionally NOT implemented here. Enforcement
    # is the Sidecar's job (src/governance/gatekeeper.py). Reaching this
    # branch means a misconfiguration — fail loud, do not silently block.
    raise RuntimeError(
        "agent_os.evaluate called with ADVISORY_ONLY=False; "
        "enforcement belongs to the Sidecar, not Agent OS"
    )
