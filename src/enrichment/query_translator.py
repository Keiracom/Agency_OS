"""
Query Translator — Campaign to Discovery Bridge

Converts campaign configuration (industry, location, lead_volume) into
discovery queries for Mode A (ABN-first), Mode B (Maps-first), or Mode C (Parallel).
"""
import asyncio
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from enrichment.discovery_filters import DiscoveryFilters
from enrichment.keyword_expander import KeywordExpander
from enrichment.location_expander import LocationExpander
from integrations.abn_client import ABNClient
from integrations.bright_data_client import BrightDataClient

logger = structlog.get_logger()


class DiscoveryMode(Enum):
    ABN_FIRST = "abn"
    MAPS_FIRST = "maps"
    PARALLEL = "parallel"


@dataclass
class CampaignConfig:
    campaign_id: str
    industry_slug: str
    location: str  # City or state
    state: str
    lead_volume: int
    filters: dict[str, Any] = field(default_factory=dict)
    discovery_mode: DiscoveryMode | None = None  # Auto-detect if None


@dataclass
class DiscoveryResult:
    abn: str | None
    business_name: str
    trading_name: str | None
    source: str  # 'abn_api' or 'maps_serp'
    raw_data: dict[str, Any]
    dedup_hash: str
    passed_filters: bool = True
    filter_reason: str | None = None


class QueryTranslator:
    """
    Orchestrates the campaign→discovery pipeline.

    Flow:
    1. Determine discovery mode based on vertical
    2. Expand industry → keywords
    3. Expand location → suburbs (for Maps)
    4. Generate query batches
    5. Execute queries with deduplication
    6. Apply filters
    7. Return results for waterfall enrichment
    """

    # Waste ratios for lead volume estimation
    ABN_WASTE_RATIO = 1.28  # 28% waste from filters
    ABN_RESULTS_PER_QUERY = 200
    MAPS_RESULTS_PER_QUERY = 20

    def __init__(
        self,
        abn_client: ABNClient,
        bright_data_client: BrightDataClient,
        keyword_expander: KeywordExpander,
        location_expander: LocationExpander,
        filters: DiscoveryFilters,
        supabase_client = None
    ):
        self.abn = abn_client
        self.bd = bright_data_client
        self.keywords = keyword_expander
        self.locations = location_expander
        self.filters = filters
        self.supabase = supabase_client
        self._seen_hashes: set = set()

    def determine_mode(self, config: CampaignConfig) -> DiscoveryMode:
        """
        Determine discovery mode based on industry vertical.

        Maps-first: Local services with physical presence
        ABN-first: Non-local B2B, professional services
        Parallel: Premium campaigns or mixed verticals
        """
        if config.discovery_mode:
            return config.discovery_mode

        # Get mode from industry_keywords table
        mode = self.keywords.get_discovery_mode(config.industry_slug)

        mode_map = {
            'maps_first': DiscoveryMode.MAPS_FIRST,
            'abn_first': DiscoveryMode.ABN_FIRST,
            'both': DiscoveryMode.PARALLEL
        }

        return mode_map.get(mode, DiscoveryMode.PARALLEL)

    def estimate_queries_needed(self, config: CampaignConfig, mode: DiscoveryMode) -> int:
        """Estimate number of queries needed to hit lead_volume target."""
        target = config.lead_volume

        if mode == DiscoveryMode.ABN_FIRST:
            # Account for waste ratio
            adjusted = target * self.ABN_WASTE_RATIO
            return max(1, int(adjusted / self.ABN_RESULTS_PER_QUERY) + 1)

        elif mode == DiscoveryMode.MAPS_FIRST:
            return max(1, int(target / self.MAPS_RESULTS_PER_QUERY) + 1)

        else:  # Parallel
            # Run both, deduplicate
            abn_queries = max(1, int((target * 0.6) / self.ABN_RESULTS_PER_QUERY) + 1)
            maps_queries = max(1, int((target * 0.6) / self.MAPS_RESULTS_PER_QUERY) + 1)
            return abn_queries + maps_queries

    def _compute_dedup_hash(self, result: dict, source: str) -> str:
        """Compute deduplication hash based on source."""
        if source == 'abn_api' and result.get('abn'):
            # ABN is the primary dedup key
            return f"abn:{result['abn']}"
        else:
            # Maps: use normalized name + address
            name = (result.get('business_name') or result.get('name') or '').lower().strip()
            addr = (result.get('address') or '').lower().strip()
            combined = f"{name}|{addr}"
            return f"maps:{hashlib.md5(combined.encode()).hexdigest()}"

    async def execute_abn_queries(
        self,
        config: CampaignConfig,
        keywords: list[str],
        max_queries: int
    ) -> list[DiscoveryResult]:
        """Execute Mode A: ABN API searches."""
        results = []
        queries_run = 0

        for keyword in keywords:
            if queries_run >= max_queries:
                break

            try:
                abn_results = await self.abn.search_by_name(
                    name=keyword,
                    state=config.state,
                    active_only=True,
                    entity_type_code=['PRV', 'PUB']  # Private + Public companies
                )

                queries_run += 1

                # Log query
                if self.supabase:
                    await self._log_query(
                        config.campaign_id,
                        'abn',
                        'abn_search',
                        {'keyword': keyword, 'state': config.state},
                        len(abn_results),
                        0.0  # ABN API is free
                    )

                for record in abn_results:
                    dedup_hash = self._compute_dedup_hash(record, 'abn_api')

                    if dedup_hash in self._seen_hashes:
                        continue
                    self._seen_hashes.add(dedup_hash)

                    # Apply filters
                    passed, reason = self.filters.apply(record, 'abn_api')

                    results.append(DiscoveryResult(
                        abn=record.get('abn'),
                        business_name=record.get('entity_name') or record.get('name'),
                        trading_name=record.get('trading_name'),
                        source='abn_api',
                        raw_data=record,
                        dedup_hash=dedup_hash,
                        passed_filters=passed,
                        filter_reason=reason
                    ))

            except Exception as e:
                logger.error("abn_query_failed", keyword=keyword, error=str(e))

        return results

    async def execute_maps_queries(
        self,
        config: CampaignConfig,
        keywords: list[str],
        suburbs: list[str],
        max_queries: int
    ) -> list[DiscoveryResult]:
        """Execute Mode B: Google Maps SERP searches."""
        results = []
        queries_run = 0

        for keyword in keywords:
            for suburb in suburbs:
                if queries_run >= max_queries:
                    break

                try:
                    maps_results = self.bd.search_google_maps(
                        query=keyword,
                        location=f"{suburb} {config.state}"
                    )

                    queries_run += 1

                    # Log query
                    if self.supabase:
                        await self._log_query(
                            config.campaign_id,
                            'maps',
                            'maps_serp',
                            {'keyword': keyword, 'suburb': suburb, 'state': config.state},
                            len(maps_results) if isinstance(maps_results, list) else 0,
                            0.0015
                        )

                    for record in (maps_results if isinstance(maps_results, list) else []):
                        dedup_hash = self._compute_dedup_hash(record, 'maps_serp')

                        if dedup_hash in self._seen_hashes:
                            continue
                        self._seen_hashes.add(dedup_hash)

                        results.append(DiscoveryResult(
                            abn=None,  # ABN lookup in enrichment
                            business_name=record.get('name') or record.get('title'),
                            trading_name=None,
                            source='maps_serp',
                            raw_data=record,
                            dedup_hash=dedup_hash,
                            passed_filters=True  # Maps results filtered later with ABN
                        ))

                except Exception as e:
                    logger.error("maps_query_failed", keyword=keyword, suburb=suburb, error=str(e))

            if queries_run >= max_queries:
                break

        return results

    async def _log_query(
        self,
        campaign_id: str,
        mode: str,
        query_type: str,
        params: dict,
        results_count: int,
        cost_aud: float
    ):
        """Log query to discovery_queries table."""
        if not self.supabase:
            return

        try:
            await self.supabase.table('discovery_queries').insert({
                'campaign_id': campaign_id,
                'mode': mode,
                'query_type': query_type,
                'query_params': params,
                'results_count': results_count,
                'cost_aud': cost_aud
            }).execute()
        except Exception as e:
            logger.warning("query_log_failed", error=str(e))

    async def run(self, config: CampaignConfig) -> list[DiscoveryResult]:
        """
        Execute the full discovery pipeline.

        Returns list of DiscoveryResults ready for waterfall enrichment.
        """
        self._seen_hashes.clear()

        # 1. Determine mode
        mode = self.determine_mode(config)
        logger.info("discovery_mode_selected", mode=mode.value, campaign_id=config.campaign_id)

        # 2. Expand keywords
        keywords = await self.keywords.expand(config.industry_slug)
        logger.info("keywords_expanded", count=len(keywords))

        # 3. Expand locations (for Maps)
        suburbs = []
        if mode in [DiscoveryMode.MAPS_FIRST, DiscoveryMode.PARALLEL]:
            suburbs = await self.locations.expand(config.location, config.state)
            logger.info("suburbs_expanded", count=len(suburbs))

        # 4. Estimate queries
        max_queries = self.estimate_queries_needed(config, mode)
        logger.info("queries_estimated", max=max_queries)

        # 5. Execute queries
        results = []

        if mode == DiscoveryMode.ABN_FIRST:
            results = await self.execute_abn_queries(config, keywords, max_queries)

        elif mode == DiscoveryMode.MAPS_FIRST:
            results = await self.execute_maps_queries(config, keywords, suburbs, max_queries)

        else:  # Parallel
            abn_results, maps_results = await asyncio.gather(
                self.execute_abn_queries(config, keywords, max_queries // 2),
                self.execute_maps_queries(config, keywords, suburbs, max_queries // 2)
            )
            results = abn_results + maps_results

        # 6. Filter to passed only (keep failed for audit)
        passed_results = [r for r in results if r.passed_filters]

        logger.info(
            "discovery_complete",
            total=len(results),
            passed=len(passed_results),
            mode=mode.value
        )

        return results
