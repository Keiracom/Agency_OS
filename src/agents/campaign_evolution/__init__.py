"""
Contract: src/agents/campaign_evolution/__init__.py
Purpose: Campaign evolution agent exports
Layer: 3 - agents
Phase: Phase D - Item 18
"""

from src.agents.campaign_evolution.campaign_orchestrator_agent import (
    CampaignSuggestionOutput,
    generate_campaign_suggestions,
    run_campaign_orchestrator,
)
from src.agents.campaign_evolution.how_analyzer_agent import (
    HOWAnalysis,
    run_how_analyzer,
)
from src.agents.campaign_evolution.what_analyzer_agent import (
    WHATAnalysis,
    run_what_analyzer,
)
from src.agents.campaign_evolution.who_analyzer_agent import (
    WHOAnalysis,
    run_who_analyzer,
)

__all__ = [
    # WHO Analyzer
    "WHOAnalysis",
    "run_who_analyzer",
    # WHAT Analyzer
    "WHATAnalysis",
    "run_what_analyzer",
    # HOW Analyzer
    "HOWAnalysis",
    "run_how_analyzer",
    # Orchestrator
    "CampaignSuggestionOutput",
    "run_campaign_orchestrator",
    "generate_campaign_suggestions",
]
