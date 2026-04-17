"""
agent_coord — primitives layer for multi-agent parallel work.

Provides:
- File-claim system (claims.py): prevent sub-agents stepping on each other's files.
- Status broadcasting (status.py): each bot can see what the other's sub-agents are doing.
- Cleanup CLI (cleanup.py): remove stale claims on startup.

Public API:
    from agent_coord import claim, release, is_claimed, scan_stale
    from agent_coord import set_status, get_peer_status
"""

from .claims import claim, release, is_claimed, scan_stale
from .status import set_status, get_peer_status

__all__ = [
    "claim",
    "release",
    "is_claimed",
    "scan_stale",
    "set_status",
    "get_peer_status",
]
