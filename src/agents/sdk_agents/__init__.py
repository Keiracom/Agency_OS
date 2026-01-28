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

from src.agents.sdk_agents.email_agent import (
    EmailOutput,
    EmailVariants,
    generate_email_sequence,
    generate_hot_lead_email,
    run_sdk_email,
)
from src.agents.sdk_agents.enrichment_agent import (
    EnrichmentOutput,
    enrich_hot_lead,
    run_sdk_enrichment,
)
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
from src.agents.sdk_agents.voice_kb_agent import (
    VoiceKBOutput,
    generate_hot_lead_voice_kb,
    get_basic_voice_kb,
    run_sdk_voice_kb,
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
