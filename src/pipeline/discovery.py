"""
Contract: src/pipeline/discovery.py
Purpose: Multi-category discovery flow for service-first campaign model.
         Sweeps DFS domain_metrics_by_categories across all category codes
         matching an agency's services, deduplicates, and feeds the pipeline.
Directive: #298, #300a (on-demand batching)

Usage:
    discovery = MultiCategoryDiscovery(dfs_client)

    # On-demand: pull one batch at a time (run_parallel refill loop)
    batch = await discovery.next_batch(
        category_codes=[10514, 13462, 11295],
        location="Australia",
        batch_size=100,
        exclude_domains=already_claimed_set,
    )

    # Full sweep (legacy — fetches entire pool upfront)
    domains = await discovery.discover_prospects(
        category_codes=[10514, 13462, 11295],
        location="Australia",
        exclude_domains=already_claimed_set,
    )

On-demand model: run_parallel calls next_batch() as the queue drains.
Discovery stops as soon as target_reached fires — DFS cost tracks actual need.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class MultiCategoryDiscovery:
    """
    Service-first multi-category discovery.

    Supports two modes:
    1. On-demand (run_parallel): next_batch() returns one page at a time.
       State (offsets, exhausted flags) is tracked on the instance.
       Call reset() to start a fresh sweep.
    2. Full sweep (legacy): discover_prospects() fetches the entire pool.
    """

    def __init__(self, dfs_client) -> None:
        """
        Args:
            dfs_client: DFSLabsClient instance with domain_metrics_by_categories().
        """
        self._dfs = dfs_client
        # On-demand state — reset per run_parallel call via reset()
        self._offsets: dict[int, int] = {}
        self._exhausted: set[int] = set()
        self._total_counts: dict[int, int] = {}

    def reset(self, category_codes: list[int]) -> None:
        """Reset pagination state for a new sweep."""
        self._offsets = dict.fromkeys(category_codes, 0)
        self._exhausted = set()
        self._total_counts = {}

    async def next_batch(
        self,
        category_codes: list[int],
        location: str = "Australia",
        batch_size: int = 100,
        exclude_domains: set[str] | None = None,
        etv_min: float | None = None,
        etv_max: float | None = None,
    ) -> list[dict]:
        """
        Pull the next batch of domains across category codes (on-demand model).

        Maintains internal offset state — each call returns the next page.
        Skips exhausted categories (min_etv < etv_min or offset >= total_count).
        Returns empty list when all categories are exhausted.

        Args:
            category_codes: DFS category codes to sweep.
            location: DFS location_name string.
            batch_size: Domains per DFS API call (max 100).
            exclude_domains: Domains to skip.
            etv_min: Required. Use get_etv_window() from
                src.config.category_etv_windows for calibrated per-category values.
            etv_max: Required. Use get_etv_window() from
                src.config.category_etv_windows for calibrated per-category values.
        """
        if etv_min is None or etv_max is None:
            raise ValueError(
                "ETV window required. Use get_etv_window(category_code) from "
                "src.config.category_etv_windows to look up the canonical window."
            )
        exclude: set[str] = set(exclude_domains or [])

        # Initialise offsets on first call
        for code in category_codes:
            if code not in self._offsets:
                self._offsets[code] = 0

        results: list[dict] = []

        # Round-robin through non-exhausted categories until we have batch_size domains
        active_codes = [c for c in category_codes if c not in self._exhausted]
        if not active_codes:
            return []

        for code in active_codes:
            if len(results) >= batch_size:
                break

            offset = self._offsets.get(code, 0)
            total_count = self._total_counts.get(code)

            # Skip if already past total_count
            if total_count is not None and offset >= total_count:
                self._exhausted.add(code)
                continue

            try:
                raw = await self._dfs.domain_metrics_by_categories(
                    category_codes=[code],
                    location_name=location,
                    paid_etv_min=0.0,
                    limit=batch_size,
                    offset=offset,
                )
            except Exception as exc:
                logger.error("next_batch: DFS error code=%s offset=%d: %s", code, offset, exc)
                self._exhausted.add(code)
                continue

            if not raw:
                self._exhausted.add(code)
                continue

            # Record total_count from first item
            if code not in self._total_counts and raw:
                tc = raw[0].get("_total_count", 0)
                if tc:
                    self._total_counts[code] = tc

            etvs = [item.get("organic_etv", 0) or 0 for item in raw]
            min_etv_in_batch = min(etvs) if etvs else 0

            for item in raw:
                domain = item.get("domain", "")
                if not domain or domain in exclude:
                    continue
                organic_etv = item.get("organic_etv", 0.0) or 0.0
                if not (etv_min <= organic_etv <= etv_max):
                    continue
                results.append(
                    {
                        "domain": domain,
                        "organic_etv": organic_etv,
                        "paid_etv": item.get("paid_etv", 0.0) or 0.0,
                        "category_codes": [code],
                    }
                )

            # Advance offset
            self._offsets[code] = offset + len(raw)

            # Mark exhausted if past SMB tail or last page
            if min_etv_in_batch < etv_min or len(raw) < batch_size:
                self._exhausted.add(code)

        logger.info(
            "next_batch: returned %d domains (active_cats=%d, exhausted=%d)",
            len(results),
            len(active_codes),
            len(self._exhausted),
        )
        return results

    @property
    def all_exhausted(self) -> bool:
        """True when all category codes have been fully paginated."""
        return len(self._exhausted) >= len(self._offsets)

    async def discover_prospects(
        self,
        category_codes: list[int],
        location: str = "Australia",
        service_area: str = "national",
        exclude_domains: set[str] | None = None,
        etv_min: float | None = None,
        etv_max: float | None = None,
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
            etv_min: Required. Use get_etv_window() from src.config.category_etv_windows.
            etv_max: Required. Use get_etv_window() from src.config.category_etv_windows.
            batch_callback: Optional callable fired after each category batch.
                            Receives list[dict] of that batch's results.

        Returns:
            Deduplicated list of {"domain": str, "organic_etv": float,
            "category_codes": list[int]} dicts.
        """
        if etv_min is None or etv_max is None:
            raise ValueError(
                "ETV window required. Use get_etv_window(category_code) from "
                "src.config.category_etv_windows to look up the canonical window."
            )
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
                        code,
                        offset,
                        exc,
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
                    batch_results.append(
                        {
                            "domain": domain,
                            "organic_etv": organic_etv,
                            "paid_etv": item.get("paid_etv", 0.0) or 0.0,
                            "category_codes": [code],
                        }
                    )

                results.extend(batch_results)

                logger.info(
                    "discover_prospects: code=%s offset=%d → %d new domains (total=%d)",
                    code,
                    offset,
                    len(batch_results),
                    len(results),
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
                if (
                    min_etv_in_batch < etv_min
                    or total_count
                    and offset >= total_count
                    or len(raw) < batch_size
                ):
                    code_done = True

        logger.info(
            "discover_prospects: complete codes=%d domains=%d",
            len(category_codes),
            len(results),
        )
        return results

    async def pull_batch(
        self,
        category_code: str | int,
        location_name: str = "Australia",
        limit: int = 50,
        offset: int = 0,
        etv_min: float | None = None,
        etv_max: float | None = None,
    ) -> list[dict]:
        """
        Stateless single-category batch pull.
        Compatible with PipelineOrchestrator.run_parallel() worker interface.
        etv_min/etv_max required — use get_etv_window() from
        src.config.category_etv_windows.
        """
        if etv_min is None or etv_max is None:
            raise ValueError(
                "ETV window required. Use get_etv_window(category_code) from "
                "src.config.category_etv_windows to look up the canonical window."
            )
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
            logger.error(
                "pull_batch: DFS error category=%s offset=%d: %s", category_code, offset, exc
            )
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
        return filtered[offset : offset + limit]
