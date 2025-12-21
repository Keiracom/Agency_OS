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
"""

from src.agents.base_agent import AgentContext, AgentResult, BaseAgent
from src.agents.cmo_agent import (
    CampaignAnalysis,
    ChannelRecommendation,
    CMOAgent,
    LeadPrioritization,
    TimingRecommendation,
    get_cmo_agent,
)
from src.agents.content_agent import (
    ContentAgent,
    EmailContent,
    LinkedInContent,
    SMSContent,
    VoiceScript,
    get_content_agent,
)
from src.agents.reply_agent import (
    ExtractedEntities,
    IntentClassification,
    ReplyAgent,
    ResponseSuggestion,
    SentimentAnalysis,
    get_reply_agent,
)

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
]
