"""
P6 — Sandbox isolation: per-sub-agent tool allowlists.

Pure-Python config module. No I/O, no network, no external deps. Defines
which Claude Code tools each agent type may invoke and provides two
helpers for the dispatcher / hook layer to consult before forwarding a
tool call.

Public surface
--------------
    AGENT_ALLOWLISTS   : dict[str, frozenset[str]]   canonical map
    get_tool_allowlist(agent_type) -> frozenset[str]
    validate_tool_access(agent_type, tool_name) -> bool

Design notes
------------
- Allowlists are FROZEN sets so callers can't mutate them by accident.
- Unknown agent_type → empty set (deny-by-default). validate_tool_access
  returns False rather than raising; callers decide how to surface the
  refusal.
- The MCP-tool namespace prefix `mcp__<server>__<tool>` is allowed via
  category wildcards: an agent that lists `"mcp__supabase__*"` in its
  allowlist gets every tool exported by the supabase MCP server. Other
  wildcard prefixes are rejected — this is the ONLY pattern.
- WebSearch / WebFetch are gated separately because they cross the
  network boundary; only research-1 + general-purpose get them by default.
- The Bash tool is the broadest privilege we hand out — kept off review,
  test, and research roles to bound blast radius.

Per-agent rationale (matches CLAUDE.md agent registry):

    architect-0   architecture decisions only — read-heavy, no writes
    research-1    research / docs / web reads — never edits
    build-2       primary build — full read+write+exec surface
    build-3       secondary build — same surface as build-2 (parallel work)
    test-4        test writing + verification — read+write+test runner only
    review-5      code review / PR checks — read-only inspection
    devops-6      deploys + infra — read+exec, NO arbitrary write
    general-purpose  broad fallback for ad-hoc spawns
"""
from __future__ import annotations

from collections.abc import Iterable

# ── Canonical Claude Code tool names ───────────────────────────────────────
# Mirrors the tool list the agent harness exposes. Used here only as
# referent strings; this module never imports tool implementations.
_READ      = "Read"
_WRITE     = "Write"
_EDIT      = "Edit"
_NB_EDIT   = "NotebookEdit"
_BASH      = "Bash"
_GREP      = "Grep"
_GLOB      = "Glob"
_WEB_FETCH = "WebFetch"
_WEB_SEARCH = "WebSearch"
_TASK      = "Task"
_SKILL     = "Skill"
_TODO      = "TodoWrite"

# ── Per-agent allowlists ───────────────────────────────────────────────────

AGENT_ALLOWLISTS: dict[str, frozenset[str]] = {
    # Architecture — pure planning + reading. No writes, no shell.
    "architect-0": frozenset({
        _READ, _GREP, _GLOB, _WEB_FETCH, _WEB_SEARCH, _TASK, _SKILL, _TODO,
    }),

    # Research — read + web only. No writes, no shell.
    "research-1": frozenset({
        _READ, _WEB_SEARCH, _WEB_FETCH, _GREP, _GLOB, _SKILL, _TODO,
    }),

    # Primary build — full read+write+exec surface (the workhorse).
    "build-2": frozenset({
        _READ, _WRITE, _EDIT, _NB_EDIT, _BASH, _GREP, _GLOB,
        _WEB_FETCH, _WEB_SEARCH, _TASK, _SKILL, _TODO,
    }),

    # Secondary build — same as build-2 so parallel work is symmetric.
    "build-3": frozenset({
        _READ, _WRITE, _EDIT, _NB_EDIT, _BASH, _GREP, _GLOB,
        _WEB_FETCH, _WEB_SEARCH, _TASK, _SKILL, _TODO,
    }),

    # Test — read + write tests + run pytest. No NotebookEdit (test files
    # are *.py, not notebooks).
    "test-4": frozenset({
        _READ, _WRITE, _EDIT, _BASH, _GREP, _GLOB, _SKILL, _TODO,
    }),

    # Review — strictly read-only inspection. NO Bash, NO Write, NO Edit.
    # The whole point of a review pass is "look, don't change."
    "review-5": frozenset({
        _READ, _GREP, _GLOB, _SKILL, _TODO,
    }),

    # DevOps — read + exec for deploys/infra. NO arbitrary file Write so
    # an infra agent can't silently rewrite source code on its way to
    # `railway up`. Edits to deploy configs go through Edit (precise).
    "devops-6": frozenset({
        _READ, _EDIT, _BASH, _GREP, _GLOB, _SKILL, _TODO,
    }),

    # General-purpose — broad fallback. Mirrors build-2.
    "general-purpose": frozenset({
        _READ, _WRITE, _EDIT, _NB_EDIT, _BASH, _GREP, _GLOB,
        _WEB_FETCH, _WEB_SEARCH, _TASK, _SKILL, _TODO,
    }),
}


# ── Public surface ─────────────────────────────────────────────────────────

def get_tool_allowlist(agent_type: str) -> frozenset[str]:
    """Return the frozen allowlist for `agent_type`. Unknown agents get
    an EMPTY frozenset (deny-by-default); callers can detect that and
    refuse to spawn rather than silently widening the surface."""
    if not isinstance(agent_type, str):
        return frozenset()
    return AGENT_ALLOWLISTS.get(agent_type, frozenset())


def validate_tool_access(agent_type: str, tool_name: str) -> bool:
    """Return True iff `agent_type` is allowed to invoke `tool_name`.

    MCP tools (prefix `mcp__<server>__<tool>`) match against any
    allowlist entry of the form `mcp__<server>__*`. No other wildcard
    pattern is supported.

    Returns False on any invalid input (non-str, empty), unknown agent,
    or non-listed tool. Never raises.
    """
    if not isinstance(agent_type, str) or not isinstance(tool_name, str):
        return False
    if not agent_type or not tool_name:
        return False
    allow = AGENT_ALLOWLISTS.get(agent_type)
    if allow is None:
        return False

    if tool_name in allow:
        return True

    # MCP-tool wildcard: mcp__server__tool matches mcp__server__* in allow
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3 and parts[0] == "mcp" and parts[1]:
            wildcard = f"mcp__{parts[1]}__*"
            if wildcard in allow:
                return True
    return False


def list_known_agents() -> Iterable[str]:
    """Iter agent_types covered by the allowlist registry — convenience
    for ops scripts that need to enumerate sandbox roles."""
    return tuple(AGENT_ALLOWLISTS.keys())
