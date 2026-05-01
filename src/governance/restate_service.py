"""
Restate Governance Service — durable execution scaffold for directive lifecycle tracking.

Virtual object: "governance"
Key: directive_id (string) — one object instance per directive

Handlers:
  directive_start    — records directive start with scope
  directive_complete — validates completion evidence exists, marks complete
  get_state          — returns current directive lifecycle state

Uses Restate durable state (ctx.get/ctx.set) so state survives crashes/restarts.
"""
from __future__ import annotations

from typing import Any

# restate-sdk imports — pinned to 0.17.x. SDK 0.17 removed restate.server.app
# in favour of the top-level restate.app() factory; see requirements.txt pin.
from restate import ObjectContext, VirtualObject, app as restate_app

# ---------------------------------------------------------------------------
# State schema (stored per directive_id key in Restate durable store)
# ---------------------------------------------------------------------------
# {
#   "status": "started" | "complete" | "failed",
#   "scope": <str>,
#   "evidence": <dict | None>,
#   "started_at": <ISO timestamp str>,
#   "completed_at": <ISO timestamp str | None>,
# }

STATE_KEY = "directive_lifecycle"

governance = VirtualObject("governance")


@governance.handler()
async def directive_start(ctx: ObjectContext, payload: dict[str, Any]) -> dict[str, Any]:
    """Record directive start.

    Expected payload keys:
      directive_id: str  (also the object key — carried for logging)
      scope: str
      started_at: str (ISO 8601)
    """
    current = await ctx.get(STATE_KEY) or {}

    if current.get("status") == "complete":
        # Idempotent — already completed, do not overwrite
        return {"ok": False, "reason": "already_complete", "state": current}

    state = {
        "status": "started",
        "scope": payload.get("scope", ""),
        "directive_id": payload.get("directive_id", ""),
        "evidence": None,
        "started_at": payload.get("started_at", ""),
        "completed_at": None,
    }
    await ctx.set(STATE_KEY, state)
    return {"ok": True, "state": state}


@governance.handler()
async def directive_complete(ctx: ObjectContext, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and record directive completion.

    Expected payload keys:
      directive_id: str
      evidence: dict   — must be non-empty; presence check enforced
      completed_at: str (ISO 8601)
    """
    evidence = payload.get("evidence")
    if not evidence:
        return {"ok": False, "reason": "evidence_required"}

    current = await ctx.get(STATE_KEY) or {}

    if current.get("status") == "complete":
        # Idempotent — return existing completed state
        return {"ok": True, "idempotent": True, "state": current}

    state = {
        **current,
        "status": "complete",
        "evidence": evidence,
        "completed_at": payload.get("completed_at", ""),
    }
    await ctx.set(STATE_KEY, state)
    return {"ok": True, "state": state}


@governance.handler()
async def get_state(ctx: ObjectContext, _payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return current directive lifecycle state."""
    state = await ctx.get(STATE_KEY)
    if state is None:
        return {"status": "not_found"}
    return state


# ---------------------------------------------------------------------------
# ASGI app — register with Restate server via admin API after deploying
# ---------------------------------------------------------------------------
asgi_app = restate_app([governance])
