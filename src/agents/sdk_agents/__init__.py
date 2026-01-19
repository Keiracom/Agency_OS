"""
Contract: src/agents/sdk_agents/__init__.py
Purpose: SDK agent exports
Layer: Agents
Consumers: engines, orchestration

SDK Agents use Claude Agent SDK with tools for:
- ICP extraction (client onboarding)
- Lead enrichment (Hot leads with signals only)
- Email personalization (all Hot leads)
- Voice KB generation (all Hot leads)
- Objection handling
"""

from src.agents.sdk_agents.sdk_tools import (
    WEB_SEARCH_TOOL,
    WEB_FETCH_TOOL,
    LINKEDIN_POSTS_TOOL,
    ALL_TOOLS,
    ENRICHMENT_TOOLS,
    ICP_TOOLS,
    get_tools_for_agent,
    execute_tool,
    TOOL_REGISTRY,
)

from src.agents.sdk_agents.icp_agent import (
    ICPAgent,
    ICPInput,
    ICPOutput,
    get_icp_agent,
    extract_icp,
)

from src.agents.sdk_agents.sdk_eligibility import (
    should_use_sdk_enrichment,
    should_use_sdk_email,
    should_use_sdk_voice_kb,
    get_sdk_coverage_estimate,
    HOT_THRESHOLD,
)

from src.agents.sdk_agents.enrichment_agent import (
    run_sdk_enrichment,
    enrich_hot_lead,
    EnrichmentOutput,
)

from src.agents.sdk_agents.email_agent import (
    run_sdk_email,
    generate_hot_lead_email,
    generate_email_sequence,
    EmailOutput,
    EmailVariants,
)

from src.agents.sdk_agents.voice_kb_agent import (
    run_sdk_voice_kb,
    generate_hot_lead_voice_kb,
    get_basic_voice_kb,
    VoiceKBOutput,
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
    # SDK Eligibility
    "should_use_sdk_enrichment",
    "should_use_sdk_email",
    "should_use_sdk_voice_kb",
    "get_sdk_coverage_estimate",
    "HOT_THRESHOLD",
    # Enrichment Agent
    "run_sdk_enrichment",
    "enrich_hot_lead",
    "EnrichmentOutput",
    # Email Agent
    "run_sdk_email",
    "generate_hot_lead_email",
    "generate_email_sequence",
    "EmailOutput",
    "EmailVariants",
    # Voice KB Agent
    "run_sdk_voice_kb",
    "generate_hot_lead_voice_kb",
    "get_basic_voice_kb",
    "VoiceKBOutput",
]
