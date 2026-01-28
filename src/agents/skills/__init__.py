"""
FILE: src/agents/skills/__init__.py
PURPOSE: Skills module for modular, testable AI capabilities
PHASE: 11-12A (ICP Discovery + Campaign Generation)
TASK: ICP-002, CAM-001-003
"""

from src.agents.skills.als_weight_suggester import ALSWeights, ALSWeightSuggesterSkill
from src.agents.skills.base_skill import (
    BaseSkill,
    SkillError,
    SkillRegistry,
    SkillResult,
)
from src.agents.skills.campaign_splitter import CampaignPlan, CampaignSplitterSkill
from src.agents.skills.company_size_estimator import CompanySizeEstimatorSkill, LinkedInData
from src.agents.skills.icp_deriver import DerivedICP, EnrichedCompany, ICPDeriverSkill
from src.agents.skills.industry_classifier import IndustryClassifierSkill, IndustryMatch
from src.agents.skills.messaging_generator import MessagingGeneratorSkill
from src.agents.skills.portfolio_extractor import PortfolioCompany, PortfolioExtractorSkill

# Import Campaign Generation skills to register them
from src.agents.skills.sequence_builder import SequenceBuilderSkill, SequenceTouch
from src.agents.skills.service_extractor import ServiceExtractorSkill, ServiceInfo
from src.agents.skills.value_prop_extractor import ValuePropExtractorSkill

# Import ICP Discovery skills to register them
from src.agents.skills.website_parser import PageContent, WebsiteParserSkill

__all__ = [
    # Base
    "BaseSkill",
    "SkillRegistry",
    "SkillResult",
    "SkillError",
    # ICP Discovery Skills
    "WebsiteParserSkill",
    "ServiceExtractorSkill",
    "ValuePropExtractorSkill",
    "PortfolioExtractorSkill",
    "IndustryClassifierSkill",
    "CompanySizeEstimatorSkill",
    "ICPDeriverSkill",
    "ALSWeightSuggesterSkill",
    # Campaign Generation Skills
    "SequenceBuilderSkill",
    "MessagingGeneratorSkill",
    "CampaignSplitterSkill",
    # Models
    "PageContent",
    "ServiceInfo",
    "PortfolioCompany",
    "IndustryMatch",
    "LinkedInData",
    "EnrichedCompany",
    "DerivedICP",
    "ALSWeights",
    "SequenceTouch",
    "CampaignPlan",
]
