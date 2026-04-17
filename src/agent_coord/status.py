"""
Status-broadcasting for multi-agent coordination.

Each callsign writes its active agent roster to STATUS_DIR/{callsign}.json.
Peers read each other's status files to understand what's in-flight.
"""

import json
import os
import uuid
from datetime import datetime, timezone

STATUS_DIR = "/tmp/agent-status"

os.makedirs(STATUS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _atomic_write(path: str, payload: dict) -> None:
    """Write JSON to path.tmp.<uuid4> then rename into place."""
    tmp_path = f"{path}.tmp.{uuid.uuid4().hex}"
    with open(tmp_path, "w") as f:
        json.dump(payload, f)
    os.rename(tmp_path, path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def set_status(callsign: str, active_agents: list[dict]) -> None:
    """
    Broadcast this callsign's active agent roster.

    active_agents items must have keys: name, task, file, started_at.
    Writes atomically to STATUS_DIR/{callsign}.json.
    """
    payload = {
        "callsign": callsign,
        "active_agents": active_agents,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    status_file = os.path.join(STATUS_DIR, f"{callsign}.json")
    _atomic_write(status_file, payload)


def get_peer_status(peer_callsign: str) -> dict | None:
    """
    Read a peer's status file.

    Returns parsed dict or None if missing / unreadable / malformed JSON.
    Does not raise on JSON decode error (peer may be mid-write).
    """
    status_file = os.path.join(STATUS_DIR, f"{peer_callsign}.json")
    try:
        with open(status_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
