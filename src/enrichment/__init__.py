"""
Enrichment package for Agency OS Waterfall v2 Pipeline

This package contains the discovery modes and enrichment pipeline
for the Siege Waterfall v2 implementation.

Created: 2026-02-16 (CEO Directive #023)

Key components:
- query_translator: Campaign → Discovery query orchestration
- keyword_expander: Industry → ABN search keywords
- location_expander: City → Suburb expansion for Maps SERP
- discovery_filters: Hard/soft filtering rules
- discovery_modes: Mode A/B/C discovery logic
- waterfall_v2: Full enrichment pipeline
- campaign_trigger: Auto-triggers discovery on campaign activation
"""

from .discovery_filters import DiscoveryFilters
from .discovery_modes import (
    ABNFirstDiscovery,
    CampaignConfig,
    DiscoveryMode,
    DiscoveryRecord,
    MapsFirstDiscovery,
    ParallelDiscovery,
)
from .waterfall_v2 import (
    LeadRecord,
    WaterfallV2,
)
from .campaign_trigger import CampaignDiscoveryTrigger

__all__ = [
    # Discovery filters
    "DiscoveryFilters",
    # Discovery modes
    "DiscoveryMode",
    "CampaignConfig",
    "DiscoveryRecord",
    "ABNFirstDiscovery",
    "MapsFirstDiscovery",
    "ParallelDiscovery",
    # Waterfall pipeline
    "LeadRecord",
    "WaterfallV2",
    # Campaign trigger
    "CampaignDiscoveryTrigger",
]
