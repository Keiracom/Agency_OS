"""Pure-mock tests for src/config/sandbox.py — no I/O, no fixtures.

Covers:
  * known agents return their canonical allowlists
  * unknown / non-string agents return empty (deny-by-default)
  * validate_tool_access matches direct tool names
  * MCP wildcard pattern (mcp__server__*) matches namespaced tools
  * Explicitly-denied tools (review-5 cannot Bash, devops-6 cannot Write…)
  * Frozenset immutability — callers cannot mutate the registry
  * list_known_agents enumerates the eight registered roles
"""

from __future__ import annotations

import pytest

from src.config.sandbox import (
    AGENT_ALLOWLISTS,
    get_tool_allowlist,
    list_known_agents,
    validate_tool_access,
)

EXPECTED_AGENTS = {
    "architect-0",
    "research-1",
    "build-2",
    "build-3",
    "test-4",
    "review-5",
    "devops-6",
    "general-purpose",
}


# ── Registry shape ────────────────────────────────────────────────────────


def test_registry_covers_canonical_agent_set():
    assert set(AGENT_ALLOWLISTS.keys()) == EXPECTED_AGENTS


def test_list_known_agents_returns_all_roles():
    assert set(list_known_agents()) == EXPECTED_AGENTS


def test_all_allowlists_are_frozen():
    for agent, allow in AGENT_ALLOWLISTS.items():
        assert isinstance(allow, frozenset), f"{agent} allowlist must be frozenset"


# ── get_tool_allowlist ────────────────────────────────────────────────────


@pytest.mark.parametrize("agent", sorted(EXPECTED_AGENTS))
def test_get_tool_allowlist_known_agent_non_empty(agent):
    allow = get_tool_allowlist(agent)
    assert isinstance(allow, frozenset)
    assert len(allow) > 0


def test_get_tool_allowlist_unknown_agent_returns_empty():
    assert get_tool_allowlist("ghost-99") == frozenset()


@pytest.mark.parametrize("bad", [None, 123, [], {}, object()])
def test_get_tool_allowlist_non_string_returns_empty(bad):
    assert get_tool_allowlist(bad) == frozenset()


def test_returned_allowlist_cannot_mutate_registry():
    allow = get_tool_allowlist("build-2")
    with pytest.raises(AttributeError):
        allow.add("EvilTool")  # frozenset has no .add
    # Original registry must remain unaffected.
    assert "EvilTool" not in AGENT_ALLOWLISTS["build-2"]


# ── validate_tool_access — positive cases ─────────────────────────────────


@pytest.mark.parametrize(
    "agent,tool",
    [
        ("architect-0", "Read"),
        ("architect-0", "WebSearch"),
        ("research-1", "WebFetch"),
        ("research-1", "Read"),
        ("build-2", "Write"),
        ("build-2", "Bash"),
        ("build-3", "Edit"),
        ("test-4", "Bash"),
        ("test-4", "Write"),
        ("review-5", "Read"),
        ("review-5", "Grep"),
        ("devops-6", "Bash"),
        ("devops-6", "Edit"),
        ("general-purpose", "Bash"),
    ],
)
def test_validate_tool_access_allows_expected(agent, tool):
    assert validate_tool_access(agent, tool) is True


# ── validate_tool_access — explicit denials ───────────────────────────────


@pytest.mark.parametrize(
    "agent,tool",
    [
        # architect-0: planning only — no shell, no writes
        ("architect-0", "Bash"),
        ("architect-0", "Write"),
        ("architect-0", "Edit"),
        # research-1: read + web only
        ("research-1", "Bash"),
        ("research-1", "Write"),
        ("research-1", "Edit"),
        # test-4: no NotebookEdit (tests are .py), no web
        ("test-4", "NotebookEdit"),
        ("test-4", "WebSearch"),
        # review-5: strictly read-only
        ("review-5", "Bash"),
        ("review-5", "Write"),
        ("review-5", "Edit"),
        # devops-6: no arbitrary file Write (Edit is the precise channel)
        ("devops-6", "Write"),
        ("devops-6", "NotebookEdit"),
    ],
)
def test_validate_tool_access_denies_off_role_tools(agent, tool):
    assert validate_tool_access(agent, tool) is False


# ── validate_tool_access — invalid input contracts ────────────────────────


@pytest.mark.parametrize(
    "agent,tool",
    [
        ("", "Read"),
        ("build-2", ""),
        (None, "Read"),
        ("build-2", None),
        (123, "Read"),
        ("build-2", 123),
        ("ghost-99", "Read"),
    ],
)
def test_validate_tool_access_invalid_input_returns_false(agent, tool):
    assert validate_tool_access(agent, tool) is False


# ── MCP wildcard matching ─────────────────────────────────────────────────


def _patched(agent: str, extra: set[str]):
    """Build a one-off allowlist with extra entries so we can exercise
    the wildcard path without mutating the canonical registry."""
    return AGENT_ALLOWLISTS[agent] | frozenset(extra)


def test_mcp_wildcard_matches_namespaced_tool(monkeypatch):
    patched = {**AGENT_ALLOWLISTS, "build-2": _patched("build-2", {"mcp__supabase__*"})}
    monkeypatch.setattr("src.config.sandbox.AGENT_ALLOWLISTS", patched)
    assert validate_tool_access("build-2", "mcp__supabase__execute_sql") is True
    assert validate_tool_access("build-2", "mcp__supabase__list_tables") is True


def test_mcp_wildcard_does_not_cross_servers(monkeypatch):
    patched = {**AGENT_ALLOWLISTS, "build-2": _patched("build-2", {"mcp__supabase__*"})}
    monkeypatch.setattr("src.config.sandbox.AGENT_ALLOWLISTS", patched)
    # Supabase wildcard must NOT authorise a different MCP server.
    assert validate_tool_access("build-2", "mcp__redis__database_create_new") is False


def test_mcp_tool_without_wildcard_in_allowlist_is_denied():
    # No agent has any mcp__*__* by default.
    assert validate_tool_access("build-2", "mcp__supabase__execute_sql") is False


def test_mcp_malformed_namespace_is_denied(monkeypatch):
    patched = {**AGENT_ALLOWLISTS, "build-2": _patched("build-2", {"mcp__supabase__*"})}
    monkeypatch.setattr("src.config.sandbox.AGENT_ALLOWLISTS", patched)
    # Missing server segment → not a real MCP tool name.
    assert validate_tool_access("build-2", "mcp__") is False
    assert validate_tool_access("build-2", "mcp____tool") is False


def test_exact_mcp_tool_name_in_allowlist_also_works(monkeypatch):
    # An allowlist may pin a single MCP tool instead of a wildcard.
    patched = {
        **AGENT_ALLOWLISTS,
        "build-2": _patched("build-2", {"mcp__supabase__execute_sql"}),
    }
    monkeypatch.setattr("src.config.sandbox.AGENT_ALLOWLISTS", patched)
    assert validate_tool_access("build-2", "mcp__supabase__execute_sql") is True
    # Sibling tool from same server NOT allowed without the wildcard.
    assert validate_tool_access("build-2", "mcp__supabase__list_tables") is False


# ── Never raises ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "args",
    [
        (None, None),
        (object(), object()),
        ("", ""),
        ("build-2", "Read"),  # happy path also shouldn't raise
    ],
)
def test_validate_tool_access_never_raises(args):
    # Pure assertion: the call returns a bool no matter the input.
    result = validate_tool_access(*args)
    assert isinstance(result, bool)
