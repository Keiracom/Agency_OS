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
  Mode A: ABN_FIRST - Query ABN API first, then enrich with external data
  Mode B: MAPS_FIRST - Query Google Maps first, then verify with ABN
  Mode C: PARALLEL - Run both modes in parallel, deduplicate results

Created: 2026-02-16 by subagent (CEO Directive #023)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


class DiscoveryMode(Enum):
    """Discovery modes for lead generation campaigns"""

    ABN_FIRST = "mode_a"  # Universal B2B - ABN API first
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


class ABNFirstDiscovery:
    """Mode A: Query ABN API first, then enrich with external data"""

    def __init__(self, abn_client=None):
        """Initialize with ABN client dependency"""
        self.abn_client = abn_client
        if not abn_client:
            logger.warning("ABNFirstDiscovery: No ABN client provided - will fail at runtime")

    async def discover(self, config: CampaignConfig) -> list[DiscoveryRecord]:
        """
        Discovery flow for Mode A:
        1. Build ABN search query from campaign config
        2. Call ABN API SearchByNameAdvanced2017
        3. Apply hard filters (discard trusts, cancelled, no GST)
        4. Return qualified ABN records for enrichment
        """
        logger.info(
            f"Starting ABN-first discovery for industry='{config.industry}', location='{config.location}'"
        )

        try:
            # Build search query for ABN API
            search_query = self._build_abn_search_query(config)

            # Query ABN API
            abn_results = await self._query_abn_api(search_query, config)

            # Apply hard filters
            filtered_results = self._apply_abn_filters(abn_results, config)

            # Convert to unified format
            discovery_records = self._convert_abn_to_records(filtered_results)

            logger.info(
                f"ABN-first discovery completed: {len(discovery_records)} qualified records"
            )
            return discovery_records

        except Exception as e:
            logger.error(f"ABN-first discovery failed: {str(e)}")
            return []

    def _build_abn_search_query(self, config: CampaignConfig) -> dict:
        """Build ABN API search parameters"""
        query = {
            "name": config.industry,
            "postcode": None,  # Extract from config.location if available
            "state": config.state,
            "isCurrentIndicator": "Y" if config.abn_only_active else None,
        }

        # Extract postcode from location if format is "City, State Postcode"
        if config.location and any(char.isdigit() for char in config.location):
            parts = config.location.split()
            if len(parts) > 0 and parts[-1].isdigit():
                query["postcode"] = parts[-1]

        return {k: v for k, v in query.items() if v is not None}

    async def _query_abn_api(self, query: dict, config: CampaignConfig) -> list[dict]:
        """Query ABN API with search parameters"""
        if not self.abn_client:
            raise ValueError("ABN client not configured")

        # Call ABN API SearchByNameAdvanced2017
        # This would integrate with existing abn_client.py
        results = await self.abn_client.search_by_name_advanced(
            **query, max_results=config.max_results
        )

        return results or []

    def _apply_abn_filters(self, results: list[dict], config: CampaignConfig) -> list[dict]:
        """Apply hard filters to ABN results"""
        filtered = []

        for record in results:
            # Filter out trusts if configured
            if config.exclude_trusts and record.get("entityType", "").upper() in ["TRUST"]:
                continue

            # Filter GST registration if configured
            if config.abn_only_gst and not record.get("gstRegistered", False):
                continue

            # Filter cancelled ABNs
            if record.get("abnStatus", "").upper() in ["CANCELLED", "INACTIVE"]:
                continue

            filtered.append(record)

        return filtered

    def _convert_abn_to_records(self, abn_results: list[dict]) -> list[DiscoveryRecord]:
        """Convert ABN API results to unified DiscoveryRecord format"""
        records = []

        for result in abn_results:
            record = DiscoveryRecord(
                business_name=result.get("businessName", "").strip(),
                abn=result.get("abn", "").strip(),
                acn=result.get("acn", "").strip(),
                legal_name=result.get("legalName", "").strip(),
                entity_type=result.get("entityType", "").strip(),
                gst_registered=result.get("gstRegistered", False),
                state=result.get("state", "").strip(),
                discovery_source="abn_api",
                confidence_score=0.85,  # ABN API is high-confidence
                discovered_at=result.get("timestamp") or "now",
            )

            records.append(record)

        return records


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


class ParallelDiscovery:
    """Mode C: Run both modes in parallel, deduplicate on ABN + fuzzy name match"""

    def __init__(self, abn_client=None, bright_data_client=None):
        """Initialize with both discovery modes"""
        self.abn_discovery = ABNFirstDiscovery(abn_client=abn_client)
        self.maps_discovery = MapsFirstDiscovery(
            bright_data_client=bright_data_client, abn_client=abn_client
        )

    async def discover(self, config: CampaignConfig) -> list[DiscoveryRecord]:
        """
        Discovery flow for Mode C:
        1. Run both ABN-first and Maps-first in parallel
        2. Deduplicate results on ABN + fuzzy name matching
        3. Return merged records with highest confidence scores
        """
        logger.info(
            f"Starting parallel discovery for industry='{config.industry}', location='{config.location}'"
        )

        try:
            # Run both discovery modes in parallel
            abn_task = asyncio.create_task(self.abn_discovery.discover(config))
            maps_task = asyncio.create_task(self.maps_discovery.discover(config))

            abn_results, maps_results = await asyncio.gather(abn_task, maps_task)

            # Deduplicate and merge
            merged_records = self._deduplicate_and_merge(abn_results, maps_results, config)

            logger.info(f"Parallel discovery completed: {len(merged_records)} deduplicated records")
            return merged_records

        except Exception as e:
            logger.error(f"Parallel discovery failed: {str(e)}")
            return []

    def _deduplicate_and_merge(
        self,
        abn_results: list[DiscoveryRecord],
        maps_results: list[DiscoveryRecord],
        config: CampaignConfig,
    ) -> list[DiscoveryRecord]:
        """Deduplicate records on ABN + fuzzy name matching"""
        merged = {}

        # Process ABN results first (higher confidence for business data)
        for record in abn_results:
            key = self._generate_dedup_key(record, config)
            merged[key] = record

        # Process Maps results, merging with ABN data where possible
        for record in maps_results:
            key = self._generate_dedup_key(record, config)

            if key in merged:
                # Merge GMB data into existing ABN record
                existing = merged[key]
                merged[key] = self._merge_records(existing, record)
            else:
                # Add new Maps-only record
                merged[key] = record

        return list(merged.values())

    def _generate_dedup_key(self, record: DiscoveryRecord, config: CampaignConfig) -> str:
        """Generate deduplication key for record matching"""
        # Use ABN as primary key if available
        if record.abn and record.abn.strip():
            return f"abn_{record.abn.strip()}"

        # Fall back to fuzzy business name matching
        clean_name = record.business_name.lower().strip()
        # Remove common business suffixes for better matching
        suffixes = ["pty ltd", "pty. ltd.", "proprietary limited", "limited", "ltd", "corp", "inc"]
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, "").strip()

        return f"name_{clean_name}"

    def _merge_records(
        self, abn_record: DiscoveryRecord, maps_record: DiscoveryRecord
    ) -> DiscoveryRecord:
        """Merge ABN and Maps records, preferring non-empty values"""
        # Start with ABN record as base
        merged = abn_record

        # Add GMB-specific fields from Maps record
        if not merged.phone and maps_record.phone:
            merged.phone = maps_record.phone
        if not merged.website and maps_record.website:
            merged.website = maps_record.website
        if not merged.address and maps_record.address:
            merged.address = maps_record.address
        if maps_record.rating:
            merged.rating = maps_record.rating
        if maps_record.reviews_count:
            merged.reviews_count = maps_record.reviews_count
        if maps_record.category:
            merged.category = maps_record.category
        if maps_record.gmb_place_id:
            merged.gmb_place_id = maps_record.gmb_place_id

        # Update metadata
        merged.discovery_source = "both"
        merged.confidence_score = max(abn_record.confidence_score, maps_record.confidence_score)

        return merged
