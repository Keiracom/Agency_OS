"""src/integrations/smartlead_mcp.py — thin Python wrapper over the SmartLead MCP bridge.

Provides typed helpers that domain_pool_manager (and future callers) use to
dispatch SmartLead operations without writing a full Python client. Per
LAW VI hierarchy: skill (skills/smartlead/SKILL.md) > MCP > exec; this
module is the MCP-layer dispatcher.

Wraps `mcp-bridge call smartlead <tool>` subprocess invocations into typed
Python callables. The bridge entry was wired in PR #579 (smartlead-mcp-by-
leadmagic, npm package, 116+ tools).

Per LAW XII: domain_pool_manager and other callers MUST go through these
helpers — direct subprocess invocation of the bridge outside this module is
forbidden.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "SmartleadMCPError",
    "purchase_domain",
    "get_warmup_stats",
]

# Resolve mcp-bridge path. Default mirrors the convention in the rest of
# the repo (skills/mcp-bridge); env var override for staging/prod parity.
_MCP_BRIDGE_DIR = os.environ.get(
    "MCP_BRIDGE_DIR",
    "/home/elliotbot/clawd/skills/mcp-bridge",
)
_DEFAULT_TIMEOUT = 60.0  # seconds — SmartLead actions can be slow on first call


class SmartleadMCPError(RuntimeError):
    """Raised when the MCP bridge invocation fails or returns an error payload."""


async def _call(tool: str, args: dict[str, Any], *, timeout: float = _DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Invoke `mcp-bridge call smartlead <tool>` with the given JSON args.

    Returns the parsed JSON response from the MCP server. Raises
    SmartleadMCPError on non-zero exit, timeout, or unparseable output.
    """
    args_json = json.dumps(args)
    cmd = ["node", "scripts/mcp-bridge.js", "call", "smartlead", tool, args_json]
    logger.info(
        "[smartlead-mcp] %s args=%s",
        tool,
        # Truncate args for logs — some payloads are large.
        args_json if len(args_json) <= 200 else args_json[:200] + "...",
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=_MCP_BRIDGE_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError as exc:
        raise SmartleadMCPError(f"MCP bridge timeout calling {tool} after {timeout}s") from exc

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[:500]
        raise SmartleadMCPError(
            f"MCP bridge exit {proc.returncode} for {tool}: {err}"
        )

    raw = stdout.decode("utf-8", errors="replace").strip()
    if not raw:
        raise SmartleadMCPError(f"MCP bridge returned empty stdout for {tool}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # MCP bridge sometimes prefixes output with diagnostic lines.
        # Try recovering the last JSON object on the stdout.
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        raise SmartleadMCPError(
            f"MCP bridge returned non-JSON for {tool}: {raw[:500]}"
        ) from exc


# ── Typed helpers ─────────────────────────────────────────────────────────────


async def purchase_domain(
    domain_name: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Trigger SmartLead's auto-generate-mailboxes + domain purchase flow.

    SmartLead's Namecheap integration handles the domain purchase + mailbox
    generation in a single API call. Returns the SmartLead response which
    includes the new email_account_id(s) and domain status.

    Args:
        domain_name: bare domain name to purchase (e.g. "acme-outreach.com").

    Returns:
        Parsed JSON response from SmartLead. Caller persists relevant ids.

    Raises:
        SmartleadMCPError on bridge failure / timeout / non-JSON response.
        ValueError on invalid input.
    """
    if not domain_name or not isinstance(domain_name, str):
        raise ValueError(f"domain_name must be a non-empty string, got {domain_name!r}")
    domain_name = domain_name.strip().lower()
    # Light sanity filter — full validation happens server-side.
    if "/" in domain_name or " " in domain_name:
        raise ValueError(f"domain_name must be a bare domain, got {domain_name!r}")

    return await _call(
        "auto_generate_mailboxes",
        {"domain": domain_name},
        timeout=timeout,
    )


async def get_warmup_stats(
    email_account_id: int | str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Fetch warmup-status + 7-day metrics for a SmartLead email account.

    Wraps `GET /email-accounts/{id}/warmup-stats` per the SmartLead skill
    spec (skills/smartlead/SKILL.md). Returned payload includes warmup
    state, sent/opened/replied/bounced/unsubscribed counts.

    Args:
        email_account_id: SmartLead-assigned email account id.

    Returns:
        Parsed JSON response — keys per SmartLead docs.

    Raises:
        SmartleadMCPError on bridge failure / timeout.
        ValueError on missing id.
    """
    if email_account_id is None or email_account_id == "":
        raise ValueError("email_account_id must be a non-empty value")

    return await _call(
        "fetch_warmup_stats_by_email_account",
        {"email_account_id": email_account_id},
        timeout=timeout,
    )


def shell_safe_repr_for_logs(args: dict[str, Any]) -> str:
    """Helper for log lines — produces a shell-safe single-line representation
    of the args dict for diagnostic output. NOT for execution.
    """
    return shlex.quote(json.dumps(args))
