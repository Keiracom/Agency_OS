"""Keiracom System MCP layer — Phase 2 build wave 2 item 4.

Canonical key citations (per audit-dispatch checklist):

ceo:memory_abstraction_layer_v1 — eleven_agreed_positions #9:
    "MCP swappability: agents call memory MCP tools, never SQL/Cypher;
     swap backend = rewrite DAL"

ceo:memory_abstraction_layer_v1 — aiden_six_phase_2_build_gates Gate E:
    "MCP swappability proven via dual-backend implementation (Hindsight +
     NoOp/InMemory), full agent integration suite parity"

PR #1126 G5 finding (Atlas multi-tenancy spike — control-plane gap list):
    "G5 — Tier-aware MCP server. The MCP server exposes the same six
     primitives regardless of tier. The tier-router makes the topology
     choice transparent to agents. … Honours the MCP swappability gate
     (eleven_agreed_positions item 9). The MCP server reads the tenant's
     topology flag at session start and routes to the right Hindsight
     cluster URL."

This layer:
- Registers the six MAL primitive tools (Ingest/Recall/Synthesize/Supersede/
  Trace/Delete) via the tools/ subpackage.
- Gates tool dispatch by tenant tier via tier_router (Solo: 2 tools; Pro: 4;
  Scale: 6).
- Routes per-tenant via Orion's KeiracomTenantExtension (PR #1132) — the
  same `get_bank_id(tenant_id)` boundary the wrappers (PR #1134) consume.
- Aiden Gate E parity: NoOp client variant ships with the test suite so
  agent integration is provably backend-swappable.
"""

from .server import MCPServer, ToolInvocationError
from .tier_router import (
    ALL_TOOLS,
    TOOL_DELETE,
    TOOL_INGEST,
    TOOL_RECALL,
    TOOL_SUPERSEDE,
    TOOL_SYNTHESIZE,
    TOOL_TRACE,
    TierGateError,
    assert_tool_allowed,
    is_tool_allowed,
    tools_for_tier,
)

__all__ = [
    "ALL_TOOLS",
    "MCPServer",
    "TOOL_DELETE",
    "TOOL_INGEST",
    "TOOL_RECALL",
    "TOOL_SUPERSEDE",
    "TOOL_SYNTHESIZE",
    "TOOL_TRACE",
    "TierGateError",
    "ToolInvocationError",
    "assert_tool_allowed",
    "is_tool_allowed",
    "tools_for_tier",
]
