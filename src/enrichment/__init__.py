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
- signal_config: Signal configuration repository (Directive #256)
"""

from .campaign_trigger import CampaignDiscoveryTrigger
from .discovery_filters import DiscoveryFilters
from .discovery_modes import (
    CampaignConfig,
    DiscoveryMode,
    DiscoveryRecord,
    MapsFirstDiscovery,
)
from .signal_config import (
    ServiceSignal,
    SignalConfig,
    SignalConfigRepository,
    VerticalNotFoundError,
)
from .waterfall_v2 import (
    LeadRecord,
    WaterfallV2,
)

__all__ = [
    # Discovery filters
    "DiscoveryFilters",
    # Discovery modes
    "DiscoveryMode",
    "CampaignConfig",
    "DiscoveryRecord",
    # ABNFirstDiscovery removed per Waterfall v3 Decision #1
    # ParallelDiscovery removed per Directive #170 Step 3
    "MapsFirstDiscovery",
    # Waterfall pipeline
    "LeadRecord",
    "WaterfallV2",
    # Campaign trigger
    "CampaignDiscoveryTrigger",
    # Signal configuration (Directive #256)
    "ServiceSignal",
    "SignalConfig",
    "SignalConfigRepository",
    "VerticalNotFoundError",
]
