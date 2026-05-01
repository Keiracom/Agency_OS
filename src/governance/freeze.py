"""
Frozen-state registry helpers — Phase 1 Track A — A3.

Wraps `public.frozen_artifacts` (see migration
supabase/migrations/20260501_frozen_artifacts.sql). All Supabase calls
go through the MCP bridge per LAW VI to keep the integration path
consistent with the rest of the codebase.

Public surface:

    freeze_artifact(path, frozen_by, reason=None) -> dict
    unfreeze_artifact(path) -> dict
    is_frozen(path) -> bool
    list_frozen_paths() -> list[str]
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

MCP_BRIDGE_DIR = os.environ.get(
    "MCP_BRIDGE_DIR", "/home/elliotbot/clawd/skills/mcp-bridge",
)
MCP_BRIDGE_SCRIPT = "scripts/mcp-bridge.js"
MCP_TIMEOUT_S = 30


def _mcp_execute_sql(sql: str) -> list[dict[str, Any]]:
    """Run SQL through the supabase MCP bridge, return rows as dicts."""
    args_json = json.dumps({"query": sql, "project_id": "jatzvazlbusedwsnqxzr"})
    proc = subprocess.run(
        ["node", MCP_BRIDGE_SCRIPT, "call", "supabase", "execute_sql", args_json],
        cwd=MCP_BRIDGE_DIR,
        capture_output=True,
        text=True,
        timeout=MCP_TIMEOUT_S,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"mcp-bridge supabase.execute_sql failed: {proc.stderr.strip()}"
        )
    out = proc.stdout.strip()
    if not out:
        return []
    parsed = json.loads(out)
    if isinstance(parsed, dict):
        rows = parsed.get("rows") or parsed.get("data") or []
    elif isinstance(parsed, list):
        rows = parsed
    else:
        rows = []
    return list(rows) if isinstance(rows, list) else []


def _quote(s: str) -> str:
    return s.replace("'", "''")


def freeze_artifact(
    artifact_path: str,
    frozen_by: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Freeze a path. Idempotent — re-freezing an already-frozen path is a no-op."""
    reason_sql = f"'{_quote(reason)}'" if reason else "NULL"
    sql = (
        "INSERT INTO public.frozen_artifacts "
        "(artifact_path, frozen_by, reason) VALUES "
        f"('{_quote(artifact_path)}', '{_quote(frozen_by)}', {reason_sql}) "
        "ON CONFLICT (artifact_path) DO UPDATE "
        "SET unfrozen_at = NULL, frozen_by = EXCLUDED.frozen_by, "
        "    reason = COALESCE(EXCLUDED.reason, public.frozen_artifacts.reason), "
        "    frozen_at = now() "
        "RETURNING id, artifact_path, frozen_by, frozen_at, reason;"
    )
    rows = _mcp_execute_sql(sql)
    return rows[0] if rows else {"artifact_path": artifact_path}


def unfreeze_artifact(artifact_path: str) -> dict[str, Any]:
    """Set unfrozen_at on the active row for this path. No-op if not frozen."""
    sql = (
        "UPDATE public.frozen_artifacts SET unfrozen_at = now() "
        f"WHERE artifact_path = '{_quote(artifact_path)}' AND unfrozen_at IS NULL "
        "RETURNING id, artifact_path, unfrozen_at;"
    )
    rows = _mcp_execute_sql(sql)
    return rows[0] if rows else {"artifact_path": artifact_path, "unfrozen_at": None}


def is_frozen(artifact_path: str) -> bool:
    """True if an active freeze row exists for this exact path."""
    sql = (
        "SELECT 1 FROM public.frozen_artifacts "
        f"WHERE artifact_path = '{_quote(artifact_path)}' AND unfrozen_at IS NULL "
        "LIMIT 1;"
    )
    try:
        return bool(_mcp_execute_sql(sql))
    except RuntimeError as exc:
        logger.warning("is_frozen mcp call failed: %s", exc)
        return False


def list_frozen_paths() -> list[str]:
    """Return all currently-frozen artifact paths (for OPA input)."""
    sql = (
        "SELECT artifact_path FROM public.frozen_artifacts "
        "WHERE unfrozen_at IS NULL ORDER BY frozen_at DESC;"
    )
    try:
        return [str(r["artifact_path"]) for r in _mcp_execute_sql(sql) if "artifact_path" in r]
    except RuntimeError as exc:
        logger.warning("list_frozen_paths mcp call failed: %s", exc)
        return []
