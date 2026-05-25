"""tier_router tests — pure-function gating predicates."""

from __future__ import annotations

import pytest

from src.keiracom_system.mcp.tier_router import (
    ALL_TOOLS,
    TOOL_DELETE,
    TOOL_INGEST,
    TOOL_RECALL,
    TOOL_SUPERSEDE,
    TOOL_SYNTHESIZE,
    TOOL_TRACE,
    TierGateError,
    assert_tool_allowed,
    is_tool_allowed,
    tools_for_tier,
)


def test_all_six_mal_primitives_present():
    """Drift-lock — the six tool names must match eleven_agreed_positions #3."""
    assert set(ALL_TOOLS) == {
        TOOL_INGEST,
        TOOL_RECALL,
        TOOL_SYNTHESIZE,
        TOOL_SUPERSEDE,
        TOOL_TRACE,
        TOOL_DELETE,
    }


def test_solo_tier_gets_ingest_and_recall_only():
    assert tools_for_tier("solo") == {TOOL_INGEST, TOOL_RECALL}


def test_pro_tier_adds_synthesize_and_supersede():
    pro = tools_for_tier("pro")
    assert TOOL_INGEST in pro and TOOL_RECALL in pro
    assert TOOL_SYNTHESIZE in pro and TOOL_SUPERSEDE in pro
    assert TOOL_TRACE not in pro and TOOL_DELETE not in pro


def test_scale_tier_gets_all_six():
    assert tools_for_tier("scale") == set(ALL_TOOLS)


def test_pro_tier_is_superset_of_solo():
    """Tier ladder invariant — higher tiers never lose tools."""
    assert tools_for_tier("solo") <= tools_for_tier("pro")


def test_scale_tier_is_superset_of_pro():
    assert tools_for_tier("pro") <= tools_for_tier("scale")


def test_unknown_tier_rejected_fail_loud():
    with pytest.raises(ValueError, match="unknown tier"):
        tools_for_tier("enterprise")


def test_is_tool_allowed_solo_can_ingest():
    assert is_tool_allowed("solo", TOOL_INGEST) is True


def test_is_tool_allowed_solo_cannot_trace():
    assert is_tool_allowed("solo", TOOL_TRACE) is False


def test_is_tool_allowed_pro_cannot_delete():
    assert is_tool_allowed("pro", TOOL_DELETE) is False


def test_is_tool_allowed_scale_can_delete():
    assert is_tool_allowed("scale", TOOL_DELETE) is True


def test_assert_tool_allowed_raises_tier_gate_error_with_tenant_in_message():
    with pytest.raises(TierGateError, match="tenant=acme") as exc:
        assert_tool_allowed("solo", TOOL_TRACE, tenant_id="acme")
    assert "trace" in str(exc.value)
    assert "solo" in str(exc.value)


def test_assert_tool_allowed_raises_value_error_on_unknown_tool():
    with pytest.raises(ValueError, match="unknown tool"):
        assert_tool_allowed("scale", "exfiltrate", tenant_id="acme")


def test_assert_tool_allowed_silent_when_allowed():
    # Returns None, no exception
    assert assert_tool_allowed("scale", TOOL_DELETE, tenant_id="acme") is None
