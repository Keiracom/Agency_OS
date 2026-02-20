"""
Enrichment package for Agency OS Waterfall v2 Pipeline

This package contains the discovery modes and enrichment pipeline
for the Siege Waterfall v2 implementation.

Created: 2026-02-16 (CEO Directive #023)
"""

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

__all__ = [
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
]
