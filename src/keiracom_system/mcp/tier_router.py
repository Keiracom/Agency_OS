"""tier_router.py — tier-driven MCP tool gating.

Implements the tier surface decided in the dispatch:
  - Solo  → Ingest + Recall  (2 tools — get-data-in, get-data-out only)
  - Pro   → adds Synthesize + Supersede (4 tools — explicit consolidation +
            supersession edges; the "compounding-earned" inflection per
            eleven_agreed_positions #4)
  - Scale → all six (adds Trace + Delete — Trace for regulated verticals
            per five_converged_decisions_locked.trace_primitive; Delete for
            GDPR + tenant-controlled erasure)

Separate from Orion's `KeiracomTenantExtension.get_allowed_config_fields()`
which gates HINDSIGHT CONFIG FIELDS per tier. This module gates MCP TOOL
SURFACE per tier. Two complementary layers — wrappers are tier-aware at the
config layer (Orion), the MCP server is tier-aware at the tool layer (here).
"""

from __future__ import annotations

from typing import Final

# Canonical tool names — keep in lockstep with the six MAL primitives from
# eleven_agreed_positions #3 ("Ingest, Recall, Synthesize, Supersede, Trace, Delete").
TOOL_INGEST: Final = "ingest"
TOOL_RECALL: Final = "recall"
TOOL_SYNTHESIZE: Final = "synthesize"
TOOL_SUPERSEDE: Final = "supersede"
TOOL_TRACE: Final = "trace"
TOOL_DELETE: Final = "delete"

ALL_TOOLS: Final[tuple[str, ...]] = (
    TOOL_INGEST,
    TOOL_RECALL,
    TOOL_SYNTHESIZE,
    TOOL_SUPERSEDE,
    TOOL_TRACE,
    TOOL_DELETE,
)

_SOLO_TOOLS: Final[frozenset[str]] = frozenset({TOOL_INGEST, TOOL_RECALL})
_PRO_TOOLS: Final[frozenset[str]] = _SOLO_TOOLS | {TOOL_SYNTHESIZE, TOOL_SUPERSEDE}
_SCALE_TOOLS: Final[frozenset[str]] = frozenset(ALL_TOOLS)

_TIER_TOOLS: Final[dict[str, frozenset[str]]] = {
    "solo": _SOLO_TOOLS,
    "pro": _PRO_TOOLS,
    "scale": _SCALE_TOOLS,
}


class TierGateError(PermissionError):
    """Raised when a tenant's tier does not include the requested tool."""


def tools_for_tier(tier: str) -> frozenset[str]:
    """Return the tool set a tier may invoke. Raises ValueError on unknown tier
    (fail-loud — silent fallback would defeat the gating purpose)."""
    if tier not in _TIER_TOOLS:
        raise ValueError(f"unknown tier {tier!r}; allowed: {sorted(_TIER_TOOLS)}")
    return _TIER_TOOLS[tier]


def is_tool_allowed(tier: str, tool_name: str) -> bool:
    """Pure predicate — True iff `tool_name` is in the tier's tool set.
    Unknown tier raises ValueError (consistent with tools_for_tier)."""
    return tool_name in tools_for_tier(tier)


def assert_tool_allowed(tier: str, tool_name: str, *, tenant_id: str = "") -> None:
    """Raises TierGateError if not allowed. Use at MCP tool dispatch entry —
    the tenant_id appears in the error message for ops/audit traceability."""
    if tool_name not in ALL_TOOLS:
        raise ValueError(f"unknown tool {tool_name!r}; allowed: {sorted(ALL_TOOLS)}")
    if not is_tool_allowed(tier, tool_name):
        tenant_hint = f" tenant={tenant_id}" if tenant_id else ""
        raise TierGateError(
            f"tier {tier!r} does not include tool {tool_name!r};{tenant_hint} "
            f"available for tier: {sorted(tools_for_tier(tier))}"
        )
