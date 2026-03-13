"""
FILE: src/enrichment/discovery_modes.py
PURPOSE: Mode A/B/C discovery logic for Waterfall v2 Pipeline
PHASE: SIEGE (CEO Directive #023)
TASK: Waterfall v2 Pipeline Implementation
DEPENDENCIES:
  - src/integrations/abn_client.py
  - src/integrations/bright_data_client.py (TBD)
  - src/config/settings.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

DISCOVERY MODES:
  Mode A: ABN_FIRST - DEPRECATED (Waterfall v3 Decision #1, 2026-03-01)
  Mode B: MAPS_FIRST - Query Google Maps first, then verify with ABN (primary)
  Mode C: PARALLEL - Both modes with deduplication

Created: 2026-02-16 by subagent (CEO Directive #023)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


class DiscoveryMode(Enum):
    """Discovery modes for lead generation campaigns"""

    # ABN_FIRST deprecated per Waterfall v3 Decision #1 (2026-03-01)
    # GMB is now primary discovery source; ABN used for verification only
    MAPS_FIRST = "mode_b"  # Local businesses with GMB - Google Maps first
    PARALLEL = "mode_c"  # Premium - both modes with deduplication


@dataclass
class CampaignConfig:
    """Configuration for discovery campaign"""

    mode: DiscoveryMode
    industry: str
    location: str
    state: str = None
    filters: dict[str, Any] = field(default_factory=dict)

    # Discovery limits
    max_results: int = 1000
    abn_only_active: bool = True
    abn_only_gst: bool = True
    exclude_trusts: bool = True

    # Quality gates
    min_confidence_score: float = 0.70
    fuzzy_match_threshold: int = 80


@dataclass
class DiscoveryRecord:
    """Unified record structure from discovery"""

    # Core identifiers
    business_name: str
    abn: str = None
    acn: str = None

    # ABN Registry fields
    legal_name: str = None
    entity_type: str = None
    gst_registered: bool = False
    state: str = None

    # Google Maps/GMB fields
    gmb_place_id: str = None
    phone: str = None
    website: str = None
    address: str = None
    rating: float = None
    reviews_count: int = None
    category: str = None

    # Discovery metadata
    discovery_source: str = None  # "abn_api", "google_maps", "both"
    confidence_score: float = 0.0
    discovered_at: str = None


class MapsFirstDiscovery:
    """Mode B: Query Google Maps first, then verify with ABN"""

    def __init__(self, bright_data_client=None, abn_client=None):
        """Initialize with Bright Data and ABN clients"""
        self.bd = bright_data_client
        self.abn_client = abn_client

        if not bright_data_client:
            logger.warning(
                "MapsFirstDiscovery: No Bright Data client provided - will fail at runtime"
            )

    async def discover(self, config: CampaignConfig) -> list[DiscoveryRecord]:
        """
        Discovery flow for Mode B:
        1. Search Google Maps via SERP API (Bright Data)
        2. For each GMB result, attempt ABN lookup by business name
        3. Return records with GMB data + ABN verification where possible
        """
        logger.info(
            f"Starting Maps-first discovery for industry='{config.industry}', location='{config.location}'"
        )

        try:
            # Search Google Maps
            gmb_results = await self._search_google_maps(config)

            # Verify with ABN API
            verified_records = await self._verify_with_abn(gmb_results, config)

            logger.info(f"Maps-first discovery completed: {len(verified_records)} records")
            return verified_records

        except Exception as e:
            logger.error(f"Maps-first discovery failed: {str(e)}")
            return []

    async def _search_google_maps(self, config: CampaignConfig) -> list[dict]:
        """Search Google Maps via Bright Data SERP API"""
        if not self.bd:
            raise ValueError("Bright Data client not configured")

        # Build search query for Google Maps
        search_query = f"{config.industry} {config.location}"

        # Use Bright Data Google Maps dataset
        # Dataset ID: gd_m8ebnr0q2qlklc02fz (from inventory)
        results = await self.bd.search_google_maps(
            query=search_query, location=config.location, max_results=config.max_results
        )

        return results or []

    async def _verify_with_abn(
        self, gmb_results: list[dict], config: CampaignConfig
    ) -> list[DiscoveryRecord]:
        """Verify GMB results with ABN API lookups"""
        verified_records = []

        for gmb_result in gmb_results:
            business_name = gmb_result.get("name", "").strip()

            if not business_name:
                continue

            # Attempt ABN lookup
            abn_match = await self._lookup_abn_by_name(business_name, config)

            # Create record with GMB data + ABN verification
            record = self._create_verified_record(gmb_result, abn_match)

            # Apply confidence scoring
            record.confidence_score = self._calculate_confidence(gmb_result, abn_match)

            if record.confidence_score >= config.min_confidence_score:
                verified_records.append(record)

        return verified_records

    async def _lookup_abn_by_name(self, business_name: str, config: CampaignConfig) -> dict | None:
        """Lookup ABN by business name"""
        if not self.abn_client:
            return None

        try:
            search_params = {
                "name": business_name,
                "state": config.state,
                "isCurrentIndicator": "Y",
            }

            results = await self.abn_client.search_by_name_advanced(**search_params)

            # Return best match based on name similarity
            if results:
                for result in results:
                    similarity = fuzz.ratio(
                        business_name.lower(), result.get("businessName", "").lower()
                    )
                    if similarity >= config.fuzzy_match_threshold:
                        return result

            return None

        except Exception as e:
            logger.warning(f"ABN lookup failed for '{business_name}': {str(e)}")
            return None

    def _create_verified_record(self, gmb_result: dict, abn_match: dict | None) -> DiscoveryRecord:
        """Create unified record from GMB + ABN data"""
        record = DiscoveryRecord(
            business_name=gmb_result.get("name", "").strip(),
            gmb_place_id=gmb_result.get("place_id", ""),
            phone=gmb_result.get("phone", ""),
            website=gmb_result.get("website", ""),
            address=gmb_result.get("address", ""),
            rating=gmb_result.get("rating"),
            reviews_count=gmb_result.get("reviews_count"),
            category=gmb_result.get("category", ""),
            discovery_source="google_maps",
            discovered_at="now",
        )

        # Add ABN data if verified
        if abn_match:
            record.abn = abn_match.get("abn", "")
            record.acn = abn_match.get("acn", "")
            record.legal_name = abn_match.get("legalName", "")
            record.entity_type = abn_match.get("entityType", "")
            record.gst_registered = abn_match.get("gstRegistered", False)
            record.state = abn_match.get("state", "")
            record.discovery_source = "both"

        return record

    def _calculate_confidence(self, gmb_result: dict, abn_match: dict | None) -> float:
        """Calculate confidence score for the record"""
        score = 0.0

        # Base GMB confidence
        if gmb_result.get("name"):
            score += 0.3
        if gmb_result.get("phone"):
            score += 0.2
        if gmb_result.get("website"):
            score += 0.2
        if gmb_result.get("address"):
            score += 0.1

        # ABN verification bonus
        if abn_match:
            score += 0.3
            if abn_match.get("gstRegistered"):
                score += 0.1

        return min(score, 1.0)


# ParallelDiscovery deleted — Directive #170 Step 3 (2026-03-10)
# Was a thin wrapper around MapsFirstDiscovery with no additional logic.
# DiscoveryMode.PARALLEL enum value retained; waterfall_v2 now routes PARALLEL → MapsFirstDiscovery directly.

# Backward-compatibility alias — Directive #188 (2026-03-13)
GMBFirstDiscovery = MapsFirstDiscovery
