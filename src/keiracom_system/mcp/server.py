"""server.py — MCP server entrypoint.

Receives tool-call requests, gates by tier, dispatches to the appropriate
tool from the tools/ subpackage. Loose-coupled to the actual MCP framework
(FastMCP, mcp.server, etc) so tests run without protocol dependencies — a
production wrapper imports MCPServer and registers its `invoke` method as
the dispatch backend.

Aiden Gate E parity: the same `invoke` surface works against any client
implementing the wrapper Protocols (Hindsight + NoOp/InMemory both proven
via the test suite).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from src.keiracom_system.memory.wrappers._base import (
    HindsightClient,
    TenantExtensionProtocol,
)

from .tier_router import (
    TOOL_DELETE,
    TOOL_INGEST,
    TOOL_RECALL,
    TOOL_SUPERSEDE,
    TOOL_SYNTHESIZE,
    TOOL_TRACE,
    assert_tool_allowed,
)
from .tools import (
    delete_memory,
    ingest_memory,
    recall_memories,
    supersede_memory,
    synthesize_bank,
    trace_audit,
)

log = logging.getLogger(__name__)


class _TierLookupProtocol(Protocol):
    """Reads the tenant's tier from the control-plane tenants table (PR #1131).
    The MCP server only needs the tier — Orion's KeiracomTenantExtension
    already covers the richer config-field gating layer."""

    def get_tier(self, tenant_id: str) -> str: ...


class ToolInvocationError(RuntimeError):
    """Raised for malformed tool invocations the server cannot dispatch."""


_DISPATCH = {
    TOOL_INGEST: ingest_memory,
    TOOL_RECALL: recall_memories,
    TOOL_SYNTHESIZE: synthesize_bank,
    TOOL_SUPERSEDE: supersede_memory,
    TOOL_TRACE: trace_audit,
    TOOL_DELETE: delete_memory,
}


class MCPServer:
    """Thin tool-dispatch surface. Stateless beyond the injected collaborators."""

    def __init__(
        self,
        *,
        client: HindsightClient,
        tenant_extension: TenantExtensionProtocol,
        tier_lookup: _TierLookupProtocol,
    ) -> None:
        self.client = client
        self.tenant_extension = tenant_extension
        self.tier_lookup = tier_lookup

    def list_tools(self, tenant_id: str) -> list[str]:
        """Return the tool names this tenant's tier may invoke."""
        from .tier_router import tools_for_tier  # local import — avoids cycle on init

        tier = self.tier_lookup.get_tier(tenant_id)
        return sorted(tools_for_tier(tier))

    def invoke(self, *, tool_name: str, tenant_id: str, **kwargs: Any) -> Any:
        """Dispatch a tool call after tier-gating + tenant validation."""
        if not tenant_id:
            raise ToolInvocationError("tenant_id required for every MCP tool invocation")
        if tool_name not in _DISPATCH:
            raise ToolInvocationError(
                f"unknown tool {tool_name!r}; registered: {sorted(_DISPATCH)}"
            )
        tier = self.tier_lookup.get_tier(tenant_id)
        assert_tool_allowed(tier, tool_name, tenant_id=tenant_id)
        func = _DISPATCH[tool_name]
        log.info(
            "mcp.invoke: tool=%s tenant=%s tier=%s",
            tool_name,
            tenant_id,
            tier,
        )
        return func(
            client=self.client,
            tenant_extension=self.tenant_extension,
            tenant_id=tenant_id,
            **kwargs,
        )
