"""
Intelligence module - Platform-wide learning and pattern aggregation.

Phase 20: Platform Intelligence
"""

from src.intelligence.website_intelligence import (
    WebsiteIntelligence,
    WebsiteIntelligenceEngine,
    get_website_intelligence_engine,
)

__all__ = [
    "WebsiteIntelligence",
    "WebsiteIntelligenceEngine",
    "get_website_intelligence_engine",
]
