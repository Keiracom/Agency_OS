"""
Contract: src/pipeline/discovery.py
Purpose: Multi-category discovery flow for service-first campaign model.
         Sweeps DFS domain_metrics_by_categories across all category codes
         matching an agency's services, deduplicates, and feeds the pipeline.
Directive: #298

Usage:
    discovery = MultiCategoryDiscovery(dfs_client)
    domains = await discovery.discover_prospects(
        category_codes=[10514, 13462, 11295],
        location="Australia",
        exclude_domains=already_claimed_set,
    )

The discover_prospects function is the entry point for run_parallel.
It pre-fetches all domains across categories before the worker pool starts,
so workers process enrichment in parallel without DFS rate-limit contention.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from src.config.category_registry import MAX_CATEGORIES_PER_CALL

logger = logging.getLogger(__name__)


class MultiCategoryDiscovery:
    """
    Service-first multi-category discovery.
    Batches category codes (max 20/call), deduplicates, and returns
    a flat list of domain dicts ready for the pipeline worker pool.
    """

    def __init__(self, dfs_client) -> None:
        """
        Args:
            dfs_client: DFSLabsClient instance with domain_metrics_by_categories().
        """
        self._dfs = dfs_client

    async def discover_prospects(
        self,
        category_codes: list[int],
        location: str = "Australia",
        service_area: str = "national",
        exclude_domains: set[str] | None = None,
        etv_min: float = 200.0,
        etv_max: float = 5000.0,
        batch_callback: Callable[[list[dict]], None] | None = None,
    ) -> list[dict]:
        """
        Discover domains across multiple DFS categories.

        Batches category codes at MAX_CATEGORIES_PER_CALL (20) per API call.
        Deduplicates against exclude_domains (already in BU or claimed).
        Fires batch_callback(batch_results) after each API call for progress.

        Args:
            category_codes: List of DFS category codes to sweep.
            location: DFS location_name string (e.g. "Australia", "New South Wales").
            service_area: "national" | "state:<state>" | "metro:<city>" (future use).
            exclude_domains: Set of domains to skip (already claimed/in BU).
            etv_min: Minimum organic ETV filter (SMB sweet spot lower bound).
            etv_max: Maximum organic ETV filter (SMB sweet spot upper bound).
            batch_callback: Optional callable fired after each category batch.
                            Receives list[dict] of that batch's results.

        Returns:
            Deduplicated list of {"domain": str, "organic_etv": float,
            "category_codes": list[int]} dicts.
        """
        if not category_codes:
            logger.warning("discover_prospects: empty category_codes, returning empty list")
            return []

        exclude: set[str] = set(exclude_domains or [])
        seen: set[str] = set()
        results: list[dict] = []

        # Process one category at a time (pagination needed per category)
        # Batching multiple codes per call cannot be combined with offset pagination
        # because the total_count varies per category.
        for code in category_codes:
            offset = 0
            batch_size = 100
            total_count: int | None = None
            code_done = False

            while not code_done:
                try:
                    raw = await self._dfs.domain_metrics_by_categories(
                        category_codes=[code],
                        location_name=location,
                        paid_etv_min=0.0,
                        limit=batch_size,
                        offset=offset,
                    )
                except Exception as exc:
                    logger.error(
                        "discover_prospects: DFS error code=%s offset=%d: %s",
                        code, offset, exc,
                    )
                    break

                if not raw:
                    break

                # Extract total_count from first item (propagated from API response)
                if total_count is None and raw:
                    total_count = raw[0].get("_total_count", 0)

                etvs = [item.get("organic_etv", 0) or 0 for item in raw]
                min_etv_in_batch = min(etvs) if etvs else 0

                batch_results: list[dict] = []
                for item in raw:
                    domain = item.get("domain", "")
                    if not domain:
                        continue
                    organic_etv = item.get("organic_etv", 0.0) or 0.0
                    if not (etv_min <= organic_etv <= etv_max):
                        continue
                    if domain in exclude or domain in seen:
                        continue
                    seen.add(domain)
                    batch_results.append({
                        "domain": domain,
                        "organic_etv": organic_etv,
                        "paid_etv": item.get("paid_etv", 0.0) or 0.0,
                        "category_codes": [code],
                    })

                results.extend(batch_results)

                logger.info(
                    "discover_prospects: code=%s offset=%d → %d new domains (total=%d)",
                    code, offset, len(batch_results), len(results),
                )

                if batch_callback is not None:
                    try:
                        batch_callback(batch_results)
                    except Exception as exc:
                        logger.warning("batch_callback error: %s", exc)

                offset += batch_size

                # Stop conditions:
                # 1. Min ETV in this batch dropped below etv_min (we're past SMB tail)
                # 2. We've paginated past total_count
                # 3. Batch returned fewer items than requested (last page)
                if min_etv_in_batch < etv_min:
                    code_done = True
                elif total_count and offset >= total_count:
                    code_done = True
                elif len(raw) < batch_size:
                    code_done = True

        logger.info(
            "discover_prospects: complete codes=%d domains=%d",
            len(category_codes), len(results),
        )
        return results

    async def pull_batch(
        self,
        category_code: str | int,
        location_name: str = "Australia",
        limit: int = 50,
        offset: int = 0,
        etv_min: float = 200.0,
        etv_max: float = 5000.0,
    ) -> list[dict]:
        """
        Stateless single-category batch pull.
        Compatible with PipelineOrchestrator.run_parallel() worker interface.
        """
        try:
            code_int = int(category_code)
        except (ValueError, TypeError):
            logger.warning("pull_batch: invalid category_code %r", category_code)
            return []

        try:
            raw = await self._dfs.domain_metrics_by_categories(
                category_codes=[code_int],
                location_name=location_name,
                paid_etv_min=0.0,
            )
        except Exception as exc:
            logger.error("pull_batch: DFS error category=%s offset=%d: %s", category_code, offset, exc)
            return []

        filtered = [
            {
                "domain": r["domain"],
                "organic_etv": r.get("organic_etv", 0.0),
                "category_codes": [code_int],
            }
            for r in raw
            if etv_min <= (r.get("organic_etv") or 0.0) <= etv_max
        ]
        return filtered[offset: offset + limit]
