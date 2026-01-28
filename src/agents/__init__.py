"""
FILE: src/agents/__init__.py
PURPOSE: Pydantic AI agents package - Intelligent automation layer
PHASE: 6 (Agents)
TASK: AGT-001
DEPENDENCIES:
  - src/engines/*
  - src/integrations/*
  - src/models/*
RULES APPLIED:
  - Rule 12: LAYER 5 - Top layer, can import from everything below
  - Pydantic AI for type-safe agent framework

This package contains all AI agents for Agency OS:
- base_agent: Abstract base with shared functionality
- cmo_agent: Chief Marketing Officer agent for orchestration decisions
- content_agent: Content generation agent for personalized copy
- reply_agent: Reply handling agent for intent classification
- skills/: Modular AI skills (loaded independently)
"""

# Lazy imports to avoid loading pydantic_ai unless agents are used
# This allows skills subpackage to be imported independently

__all__ = [
    # Base
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    # CMO Agent
    "CMOAgent",
    "get_cmo_agent",
    "CampaignAnalysis",
    "ChannelRecommendation",
    "LeadPrioritization",
    "TimingRecommendation",
    # Content Agent
    "ContentAgent",
    "get_content_agent",
    "EmailContent",
    "SMSContent",
    "LinkedInContent",
    "VoiceScript",
    # Reply Agent
    "ReplyAgent",
    "get_reply_agent",
    "IntentClassification",
    "ResponseSuggestion",
    "SentimentAnalysis",
    "ExtractedEntities",
    # ICP Discovery Agent
    "ICPDiscoveryAgent",
    "get_icp_discovery_agent",
    "ICPProfile",
    "ICPExtractionResult",
    # Campaign Generation Agent
    "CampaignGenerationAgent",
    "get_campaign_generation_agent",
    "GeneratedCampaign",
    "CampaignGenerationResult",
]


def __getattr__(name: str):
    """Lazy import to avoid loading pydantic_ai on package import."""
    if name in ("BaseAgent", "AgentContext", "AgentResult"):
        from src.agents.base_agent import AgentContext, AgentResult, BaseAgent

        return {"BaseAgent": BaseAgent, "AgentContext": AgentContext, "AgentResult": AgentResult}[
            name
        ]

    if name in (
        "CMOAgent",
        "get_cmo_agent",
        "CampaignAnalysis",
        "ChannelRecommendation",
        "LeadPrioritization",
        "TimingRecommendation",
    ):
        from src.agents.cmo_agent import (
            CampaignAnalysis,
            ChannelRecommendation,
            CMOAgent,
            LeadPrioritization,
            TimingRecommendation,
            get_cmo_agent,
        )

        return {
            "CMOAgent": CMOAgent,
            "get_cmo_agent": get_cmo_agent,
            "CampaignAnalysis": CampaignAnalysis,
            "ChannelRecommendation": ChannelRecommendation,
            "LeadPrioritization": LeadPrioritization,
            "TimingRecommendation": TimingRecommendation,
        }[name]

    if name in (
        "ContentAgent",
        "get_content_agent",
        "EmailContent",
        "SMSContent",
        "LinkedInContent",
        "VoiceScript",
    ):
        from src.agents.content_agent import (
            ContentAgent,
            EmailContent,
            LinkedInContent,
            SMSContent,
            VoiceScript,
            get_content_agent,
        )

        return {
            "ContentAgent": ContentAgent,
            "get_content_agent": get_content_agent,
            "EmailContent": EmailContent,
            "SMSContent": SMSContent,
            "LinkedInContent": LinkedInContent,
            "VoiceScript": VoiceScript,
        }[name]

    if name in (
        "ReplyAgent",
        "get_reply_agent",
        "IntentClassification",
        "ResponseSuggestion",
        "SentimentAnalysis",
        "ExtractedEntities",
    ):
        from src.agents.reply_agent import (
            ExtractedEntities,
            IntentClassification,
            ReplyAgent,
            ResponseSuggestion,
            SentimentAnalysis,
            get_reply_agent,
        )

        return {
            "ReplyAgent": ReplyAgent,
            "get_reply_agent": get_reply_agent,
            "IntentClassification": IntentClassification,
            "ResponseSuggestion": ResponseSuggestion,
            "SentimentAnalysis": SentimentAnalysis,
            "ExtractedEntities": ExtractedEntities,
        }[name]

    if name in (
        "ICPDiscoveryAgent",
        "get_icp_discovery_agent",
        "ICPProfile",
        "ICPExtractionResult",
    ):
        from src.agents.icp_discovery_agent import (
            ICPDiscoveryAgent,
            ICPExtractionResult,
            ICPProfile,
            get_icp_discovery_agent,
        )

        return {
            "ICPDiscoveryAgent": ICPDiscoveryAgent,
            "get_icp_discovery_agent": get_icp_discovery_agent,
            "ICPProfile": ICPProfile,
            "ICPExtractionResult": ICPExtractionResult,
        }[name]

    if name in (
        "CampaignGenerationAgent",
        "get_campaign_generation_agent",
        "GeneratedCampaign",
        "CampaignGenerationResult",
    ):
        from src.agents.campaign_generation_agent import (
            CampaignGenerationAgent,
            CampaignGenerationResult,
            GeneratedCampaign,
            get_campaign_generation_agent,
        )

        return {
            "CampaignGenerationAgent": CampaignGenerationAgent,
            "get_campaign_generation_agent": get_campaign_generation_agent,
            "GeneratedCampaign": GeneratedCampaign,
            "CampaignGenerationResult": CampaignGenerationResult,
        }[name]

    raise AttributeError(f"module 'src.agents' has no attribute {name!r}")
