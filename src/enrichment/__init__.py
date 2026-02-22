"""
Enrichment Module — Query Translation and Discovery

Contains modules for:
- Campaign configuration to discovery query translation
- Industry keyword expansion
- Location/suburb expansion
- Discovery result filtering
"""

from .query_translator import QueryTranslator, CampaignConfig, DiscoveryResult, DiscoveryMode
from .keyword_expander import KeywordExpander
from .location_expander import LocationExpander
from .discovery_filters import DiscoveryFilters

__all__ = [
    'QueryTranslator',
    'CampaignConfig', 
    'DiscoveryResult',
    'DiscoveryMode',
    'KeywordExpander',
    'LocationExpander',
    'DiscoveryFilters'
]