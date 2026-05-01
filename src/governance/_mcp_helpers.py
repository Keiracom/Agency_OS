"""Central MCP / event-emission helpers for governance modules.

GOV-PHASE1-COMPREHENSIVE-FIX-AIDEN-SCOPE — D5.

Every governance MCP supabase call goes through these helpers so:
  1. project_id is injected once, not duplicated at every call site.
  2. The arg-construction surface is testable (no inline `json.dumps({...})`
     spread across modules).
  3. Adding required server args later means one edit, not N.

Public surface:
  supabase_mcp_args(query, **extra) -> dict
      Build the JSON arg dict for `node mcp-bridge.js call supabase
      execute_sql <args>`. Always includes project_id (env-driven,
      defaults to the Agency OS Supabase project).

  supabase_mcp_execute_sql(sql, *, mcp_dir=None, timeout_s=30) -> list[dict]
      Run a SQL statement through the MCP bridge subprocess and return
      rows as dicts. Uses supabase_mcp_args() under the hood.

  governance_event_emit(callsign, event_type, *, event_data=None,
                        tool_name=None, file_path=None,
                        directive_id=None) -> bool
      Write one row to public.governance_events. Used by Router cost-cap
      fallbacks, hook fallbacks, and any other governance signal path.
      Returns True on success, False on failure (logged, never raised —
      governance event writes must NEVER block the calling assistant).
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Env-driven project_id with a sane default. Other governance modules
# (e.g. ATLAS-owned freeze.py) hard-code the same value; this helper is
# the consolidation target.
_DEFAULT_PROJECT_ID = "jatzvazlbusedwsnqxzr"
_MCP_BRIDGE_DIR = os.environ.get(
    "MCP_BRIDGE_DIR", "/home/elliotbot/clawd/skills/mcp-bridge",
)
_MCP_BRIDGE_SCRIPT = "scripts/mcp-bridge.js"
_DEFAULT_TIMEOUT_S = 30


def supabase_mcp_args(query: str, **extra: Any) -> dict[str, Any]:
    """Build the supabase MCP execute_sql arg dict.

    Always includes:
      - query:      the SQL statement
      - project_id: env SUPABASE_PROJECT_ID, default Agency OS project

    Extra kwargs are merged in. Caller-provided project_id wins (rare
    test path); otherwise the env value is used.
    """
    project_id = os.environ.get("SUPABASE_PROJECT_ID", _DEFAULT_PROJECT_ID)
    args: dict[str, Any] = {"query": query, "project_id": project_id}
    args.update(extra)
    # Re-pin project_id from caller if they provided one explicitly.
    if "project_id" in extra:
        args["project_id"] = extra["project_id"]
    return args


def supabase_mcp_execute_sql(
    sql: str,
    *,
    mcp_dir: str | None = None,
    timeout_s: int = _DEFAULT_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """Run SQL via the MCP bridge subprocess. Returns rows as dicts.

    Raises RuntimeError on non-zero exit. Empty result returns [].
    """
    args = supabase_mcp_args(sql)
    cwd = mcp_dir or _MCP_BRIDGE_DIR
    proc = subprocess.run(
        [
            "node",
            _MCP_BRIDGE_SCRIPT,
            "call",
            "supabase",
            "execute_sql",
            json.dumps(args),
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "mcp-bridge supabase execute_sql failed: "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    out = proc.stdout.strip()
    if not out:
        return []
    parsed = json.loads(out)
    # mcp-bridge can return the result wrapped in a guard-rail string with
    # `<untrusted-data-...>...</untrusted-data-...>` boundaries. The inner
    # JSON between those tags is the actual row payload — extract it when
    # `parsed` is a string.
    if isinstance(parsed, str):
        match = re.search(
            r"<untrusted-data-[^>]+>\s*(?P<inner>[\[{].*?[\]}])\s*"
            r"</untrusted-data-[^>]+>",
            parsed, flags=re.DOTALL,
        )
        if match:
            try:
                parsed = json.loads(match.group("inner"))
            except json.JSONDecodeError:
                parsed = []
        else:
            parsed = []
    if isinstance(parsed, dict):
        rows = parsed.get("rows") or parsed.get("data") or []
    elif isinstance(parsed, list):
        rows = parsed
    else:
        rows = []
    return list(rows) if isinstance(rows, list) else []


def _quote(value: str) -> str:
    """SQL string literal escape — single-quote doubled, no full validator."""
    return value.replace("'", "''")


def governance_event_emit(
    callsign: str,
    event_type: str,
    *,
    event_data: dict[str, Any] | None = None,
    tool_name: str | None = None,
    file_path: str | None = None,
    directive_id: str | None = None,
) -> bool:
    """Write one row to public.governance_events.

    Schema (from production introspection):
      id (uuid, default gen_random_uuid())
      callsign (text), event_type (text), event_data (jsonb)
      tool_name (text), file_path (text), timestamp (tz)
      directive_id (text)

    Returns True on success, False on any failure. Failures are logged
    but NEVER raised — governance events must not block the caller.
    """
    payload_json = json.dumps(event_data or {})
    cols = ["callsign", "event_type", "event_data"]
    vals = [
        f"'{_quote(callsign)}'",
        f"'{_quote(event_type)}'",
        f"'{_quote(payload_json)}'::jsonb",
    ]
    if tool_name is not None:
        cols.append("tool_name")
        vals.append(f"'{_quote(tool_name)}'")
    if file_path is not None:
        cols.append("file_path")
        vals.append(f"'{_quote(file_path)}'")
    if directive_id is not None:
        cols.append("directive_id")
        vals.append(f"'{_quote(directive_id)}'")
    sql = (
        "INSERT INTO public.governance_events "
        f"({', '.join(cols)}) VALUES ({', '.join(vals)});"
    )
    try:
        supabase_mcp_execute_sql(sql)
        return True
    except Exception as exc:  # pragma: no cover - logged not raised
        logger.warning("governance_event_emit failed: %s", exc)
        return False
