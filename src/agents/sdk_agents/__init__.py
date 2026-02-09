"""
Contract: src/agents/sdk_agents/__init__.py
Purpose: SDK agent exports
Layer: Agents
Consumers: engines, orchestration

SDK Agents use Claude Agent SDK with tools for:
- ICP extraction (client onboarding)

NOTE: email_agent, enrichment_agent, voice_kb_agent deprecated per FCO-002.
These functions now handled by Siege Waterfall pipeline.
"""

from src.agents.sdk_agents.icp_agent import (
    ICPAgent,
    ICPInput,
    ICPOutput,
    extract_icp,
    get_icp_agent,
)
from src.agents.sdk_agents.sdk_eligibility import (
    COMPLETENESS_THRESHOLD,
    ENTERPRISE_THRESHOLD,
    EXECUTIVE_TITLES,
    HOT_THRESHOLD,
    calculate_data_completeness,
    get_sdk_coverage_estimate,
    is_executive_title,
    should_use_sdk_email,
    should_use_sdk_enrichment,
    should_use_sdk_voice_kb,
)
from src.agents.sdk_agents.sdk_tools import (
    ALL_TOOLS,
    ENRICHMENT_TOOLS,
    ICP_TOOLS,
    LINKEDIN_POSTS_TOOL,
    TOOL_REGISTRY,
    WEB_FETCH_TOOL,
    WEB_SEARCH_TOOL,
    execute_tool,
    get_tools_for_agent,
)

__all__ = [
    # Tools
    "WEB_SEARCH_TOOL",
    "WEB_FETCH_TOOL",
    "LINKEDIN_POSTS_TOOL",
    "ALL_TOOLS",
    "ENRICHMENT_TOOLS",
    "ICP_TOOLS",
    "get_tools_for_agent",
    "execute_tool",
    "TOOL_REGISTRY",
    # ICP Agent
    "ICPAgent",
    "ICPInput",
    "ICPOutput",
    "get_icp_agent",
    "extract_icp",
    # SDK Eligibility (Phase 4: Tiered Enrichment)
    "should_use_sdk_enrichment",
    "should_use_sdk_email",
    "should_use_sdk_voice_kb",
    "get_sdk_coverage_estimate",
    "calculate_data_completeness",
    "is_executive_title",
    "HOT_THRESHOLD",
    "ENTERPRISE_THRESHOLD",
    "COMPLETENESS_THRESHOLD",
    "EXECUTIVE_TITLES",
]
