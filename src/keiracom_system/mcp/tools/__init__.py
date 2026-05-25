"""MAL primitive tools exposed via MCP.

Each tool delegates to the Hindsight wrappers from PR #1134. The MCP server
(`server.py`) registers all six + applies tier gating via `tier_router`
before dispatch.

The dispatch contract per the wrappers: `tenant_id` is required for every
tool, and `TenantExtensionProtocol.get_bank_id(tenant_id)` routes the
request to the right Hindsight memory bank.
"""

from .delete import delete_memory
from .ingest import ingest_memory
from .recall import recall_memories
from .supersede import supersede_memory
from .synthesize import synthesize_bank
from .trace import trace_audit

__all__ = [
    "delete_memory",
    "ingest_memory",
    "recall_memories",
    "supersede_memory",
    "synthesize_bank",
    "trace_audit",
]
