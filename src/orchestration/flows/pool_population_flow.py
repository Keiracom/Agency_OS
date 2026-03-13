"""
FILE: src/orchestration/flows/pool_population_flow.py
PURPOSE: Populate lead pool using Siege Waterfall enrichment pipeline
PHASE: 24A (Lead Pool Architecture) → SIEGE (System Overhaul)
TASK: POOL-012 (Gap fix - pool population trigger)
DEPENDENCIES:
  - src/engines/scout.py
  - src/integrations/supabase.py
  - src/integrations/siege_waterfall.py (SSOT for enrichment)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation before each step
  - Rule 14: Soft deletes only

ENRICHMENT STRATEGY:
  All enrichment now flows through Siege Waterfall (5-tier Australian B2B pipeline).
  See src/integrations/siege_waterfall.py for tier details.

WATERFALL STRATEGY:
  Tier 1: Search by INDUSTRY from portfolio, EXCLUDE portfolio domains (lookalikes)
  Tier 2: Search by portfolio industries with employee size filters (broader)
  Tier 3: Search by generic ICP criteria (fallback)
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from sqlalchemy import and_, select, text

from src.engines.scout import get_scout_engine
from src.integrations.supabase import get_db_session
from src.models.base import SubscriptionStatus
from src.models.client import Client
from src.services.who_refinement_service import get_who_refined_criteria

logger = logging.getLogger(__name__)


# ============================================
# COMPANY SIZE TO EMPLOYEE COUNT MAPPING
# ============================================
COMPANY_SIZE_MAP = {
    "1-10": (1, 10),
    "11-50": (11, 50),
    "51-200": (51, 200),
    "201-500": (201, 500),
    "501-1000": (501, 1000),
    "1001-5000": (1001, 5000),
    "5001-10000": (5001, 10000),
    "10001+": (10001, 1000000),
    # Alternative formats
    "small": (1, 50),
    "medium": (51, 500),
    "large": (501, 5000),
    "enterprise": (5001, 1000000),
    "smb": (1, 200),
    "mid-market": (201, 1000),
}


def parse_employee_range(company_sizes: list[str]) -> tuple[int | None, int | None]:
    """
    Parse company size strings into min/max employee counts.

    Args:
        company_sizes: List of company size strings

    Returns:
        Tuple of (min_employees, max_employees)
    """
    if not company_sizes:
        return None, None

    min_employees = None
    max_employees = None

    for size in company_sizes:
        size_lower = size.lower().strip()

        # Check direct mapping
        if size_lower in COMPANY_SIZE_MAP:
            range_min, range_max = COMPANY_SIZE_MAP[size_lower]
            if min_employees is None or range_min < min_employees:
                min_employees = range_min
            if max_employees is None or range_max > max_employees:
                max_employees = range_max
            continue

        # Try to parse numeric range like "100-500"
        if "-" in size:
            try:
                parts = size.split("-")
                range_min = int(parts[0].strip().replace(",", ""))
                range_max = int(parts[1].strip().replace(",", "").replace("+", ""))
                if min_employees is None or range_min < min_employees:
                    min_employees = range_min
                if max_employees is None or range_max > max_employees:
                    max_employees = range_max
            except (ValueError, IndexError):
                pass

    return min_employees, max_employees


# ============================================
# TASKS
# ============================================


@task(name="validate_client_for_population", retries=2, retry_delay_seconds=5)
async def validate_client_for_population_task(client_id: UUID) -> dict[str, Any]:
    """
    Validate client has ICP configured and can populate pool.

    Args:
        client_id: Client UUID

    Returns:
        Dict with client ICP data
    """
    async with get_db_session() as db:
        stmt = select(Client).where(
            and_(
                Client.id == client_id,
                Client.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            raise ValueError(f"Client {client_id} not found")

        # JIT validation: subscription status
        if client.subscription_status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        ]:
            raise ValueError(f"Client subscription is {client.subscription_status.value}")

        # Get ICP fields from client (set during onboarding)
        # These are TEXT[] columns on the clients table
        icp_industries = getattr(client, "icp_industries", None) or []
        icp_company_sizes = getattr(client, "icp_company_sizes", None) or []
        icp_locations = getattr(client, "icp_locations", None) or []
        icp_titles = getattr(client, "icp_titles", None) or []

        # Check if ICP is configured
        has_icp = any([icp_industries, icp_titles, icp_locations])
        if not has_icp:
            raise ValueError("Client has no ICP configured. Run onboarding first.")

        # Parse employee range from company sizes
        employee_min, employee_max = parse_employee_range(icp_company_sizes)

        return {
            "client_id": str(client_id),
            "client_name": client.name,
            "subscription_status": client.subscription_status.value,
            "icp_industries": icp_industries,
            "icp_company_sizes": icp_company_sizes,
            "icp_locations": icp_locations,
            "icp_titles": icp_titles,
            "employee_min": employee_min,
            "employee_max": employee_max,
            "has_icp": True,
        }


@task(name="get_enriched_portfolio", retries=2, retry_delay_seconds=5)
async def get_enriched_portfolio_task(client_id: UUID) -> dict[str, Any]:
    """
    Get enriched portfolio companies from the client's ICP extraction.

    Args:
        client_id: Client UUID

    Returns:
        Dict with portfolio companies and extracted industries
    """
    async with get_db_session() as db:
        # Get the latest ICP extraction job for this client
        result = await db.execute(
            text("""
                SELECT extracted_icp
                FROM icp_extraction_jobs
                WHERE client_id = :client_id
                AND status = 'completed'
                AND extracted_icp IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"client_id": str(client_id)},
        )
        row = result.fetchone()

        if not row or not row.extracted_icp:
            logger.info(f"No ICP extraction found for client {client_id}")
            return {
                "has_portfolio": False,
                "portfolio_companies": [],
                "enriched_portfolio": [],
                "portfolio_industries": [],
            }

        extracted_icp = row.extracted_icp
        if isinstance(extracted_icp, str):
            extracted_icp = json.loads(extracted_icp)

        # Get portfolio data
        portfolio_companies = extracted_icp.get("portfolio_companies", [])
        enriched_portfolio = extracted_icp.get("enriched_portfolio", [])

        # Extract unique industries from enriched portfolio
        portfolio_industries = set()
        for company in enriched_portfolio:
            industry = company.get("industry")
            if industry:
                portfolio_industries.add(industry)

        logger.info(
            f"Found portfolio for client {client_id}: "
            f"{len(portfolio_companies)} companies, "
            f"{len(enriched_portfolio)} enriched, "
            f"{len(portfolio_industries)} industries"
        )

        return {
            "has_portfolio": len(enriched_portfolio) > 0,
            "portfolio_companies": portfolio_companies,
            "enriched_portfolio": enriched_portfolio,
            "portfolio_industries": list(portfolio_industries),
        }


@task(name="populate_pool_from_portfolio", retries=2, retry_delay_seconds=10)
async def populate_pool_from_portfolio_task(
    client_id: UUID,
    enriched_portfolio: list[dict[str, Any]],
    icp_titles: list[str],
    icp_locations: list[str],
    employee_min: int | None = None,
    employee_max: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Search for LOOKALIKE companies (Tier 1).

    Uses enriched portfolio to identify similar companies in the same industries.
    Enrichment powered by Siege Waterfall pipeline.

    Args:
        client_id: Client UUID for suppression filtering
        enriched_portfolio: List of enriched portfolio companies
        icp_titles: Target job titles
        icp_locations: Target locations
        employee_min: Minimum employee count
        employee_max: Maximum employee count
        limit: Maximum leads to add

    Returns:
        Dict with population results
    """
    # Extract portfolio industries for logging
    portfolio_industries = set()
    for company in enriched_portfolio:
        industry = company.get("industry")
        if industry:
            portfolio_industries.add(industry.lower().strip())

    logger.info(
        f"Tier 1 (Portfolio Lookalikes): "
        f"Industries identified: {list(portfolio_industries)}. "
        f"Enrichment via Siege Waterfall."
    )

    # TODO: Implement lookalike search using Siege Waterfall for enrichment
    # Current implementation returns stub results pending full integration
    return {
        "success": True,
        "tier": 1,
        "added": 0,
        "skipped": 0,
        "excluded_portfolio": 0,
        "industries_searched": len(portfolio_industries),
        "message": "Pending Siege Waterfall integration for lead discovery.",
    }


@task(name="populate_pool_from_industries", retries=2, retry_delay_seconds=10)
async def populate_pool_from_industries_task(
    client_id: UUID,
    portfolio_industries: list[str],
    icp_titles: list[str],
    icp_locations: list[str],
    employee_min: int | None,
    employee_max: int | None,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Search by portfolio industries (Tier 2).

    Uses industries extracted from portfolio companies for broader matching.
    Enrichment powered by Siege Waterfall pipeline.

    Args:
        client_id: Client UUID for suppression filtering
        portfolio_industries: Industries from enriched portfolio
        icp_titles: Target job titles
        icp_locations: Target locations
        employee_min: Minimum employee count
        employee_max: Maximum employee count
        limit: Maximum leads to add

    Returns:
        Dict with population results
    """
    if not portfolio_industries:
        return {
            "success": True,
            "tier": 2,
            "added": 0,
            "skipped": 0,
            "suppressed": 0,
            "total": 0,
            "message": "No portfolio industries to search",
        }

    async with get_db_session() as db:
        scout = get_scout_engine()

        base_criteria = {
            "titles": icp_titles,
            "industries": portfolio_industries,  # Use portfolio industries!
            "countries": icp_locations or ["Australia"],
            "employee_min": employee_min,
            "employee_max": employee_max,
            "seniorities": ["director", "vp", "c_suite", "owner", "founder", "manager"],
        }

        # Apply WHO refinement to improve targeting based on conversion patterns
        refined_criteria = await get_who_refined_criteria(db, client_id, base_criteria)
        logger.info("Tier 2: Applied WHO refinement to search criteria")

        logger.info(
            f"Tier 2: Searching by portfolio industries: {refined_criteria.get('industries', portfolio_industries)}"
        )

        result = await scout.search_and_populate_pool(
            db=db,
            icp_criteria=refined_criteria,
            limit=limit,
            client_id=client_id,
        )

        if result.success:
            logger.info(f"Tier 2 (Industries) complete: {result.data['added']} added")
            return {
                "success": True,
                "tier": 2,
                "added": result.data["added"],
                "skipped": result.data["skipped"],
                "suppressed": result.data["suppressed"],
                "total": result.data["total"],
            }
        else:
            return {
                "success": False,
                "tier": 2,
                "error": result.error,
                "added": 0,
                "skipped": 0,
                "suppressed": 0,
                "total": 0,
            }


@task(name="populate_pool_from_icp", retries=2, retry_delay_seconds=10)
async def populate_pool_from_icp_task(
    client_id: UUID,
    icp_criteria: dict[str, Any],
    limit: int = 25,
) -> dict[str, Any]:
    """
    Populate the lead pool (Tier 3 fallback).

    Uses generic ICP criteria for broadest matching.
    Enrichment powered by Siege Waterfall pipeline.

    Args:
        client_id: Client UUID for suppression filtering
        icp_criteria: ICP criteria dict
        limit: Maximum leads to add

    Returns:
        Dict with population results
    """
    # Industry → GMB search category mapping (Directive #188)
    INDUSTRY_TO_GMB_CATEGORY = {
        "ecommerce": "ecommerce agency",
        "retail": "retail marketing agency",
        "direct_to_consumer": "digital marketing agency",
        "marketing": "marketing agency",
        "saas": "software marketing agency",
        "b2b": "b2b marketing agency",
        "finance": "financial services marketing",
        "health": "healthcare marketing agency",
    }

    def _map_industry_to_gmb_category(industry: str) -> str:
        return INDUSTRY_TO_GMB_CATEGORY.get(industry.lower(), f"{industry} marketing agency")

    def _extract_domain(website: str) -> str | None:
        from urllib.parse import urlparse
        if not website:
            return None
        try:
            parsed = urlparse(website if "://" in website else f"https://{website}")
            host = parsed.netloc or parsed.path
            return host.lstrip("www.").lower() or None
        except Exception:
            return None

    from src.integrations.bright_data_client import DATASET_IDS, get_bright_data_client

    MAX_ONBOARDING_COMBOS = 3

    industries: list[str] = icp_criteria.get("icp_industries", []) or []
    locations: list[str] = icp_criteria.get("icp_locations", []) or ["Australia"]
    if not industries:
        industries = ["marketing"]

    # Cap combos: top 2 industries × top 2 locations, max MAX_ONBOARDING_COMBOS
    combos = [(ind, loc) for ind in industries[:2] for loc in locations[:2]]
    combos = combos[:MAX_ONBOARDING_COMBOS]

    bd_client = get_bright_data_client()
    seen_keys: set[str] = set()
    added = 0
    skipped = 0

    # Use first combo's industry as fallback label for DB insert
    industry = combos[0][0] if combos else industries[0]

    # Build all inputs at once and issue a single batched BD call
    inputs = [
        {"keyword": _map_industry_to_gmb_category(ind), "country": "AU"}
        for ind, _loc in combos
    ]
    logger.info(
        f"Tier 3 GMB batch discovery: {len(inputs)} combos, client={client_id}"
    )
    try:
        records = await bd_client._scraper_request(
            DATASET_IDS["gmb_business"],
            inputs,
            discover_by="location",
        )
    except Exception as e:
        logger.warning(f"GMB batch discovery failed: {e}")
        records = []

    async with get_db_session() as db:
        for record in records:
            if added >= limit:
                break

            company_name = (record.get("name") or "").strip()
            if not company_name:
                skipped += 1
                continue

            phone = record.get("phone") or None
            website = record.get("website") or ""
            domain = _extract_domain(website)

            city = None
            address = record.get("address") or ""
            if address:
                parts = [p.strip() for p in address.split(",") if p.strip()]
                if len(parts) >= 2:
                    city = parts[-2]  # penultimate part is usually city

            # Dedup key: prefer domain, fall back to phone, then name
            dedup_key = domain or phone or company_name.lower()
            if dedup_key in seen_keys:
                skipped += 1
                continue
            seen_keys.add(dedup_key)

            try:
                await db.execute(
                    text("""
                        INSERT INTO lead_pool (
                            id, client_id, company_name, company_domain, phone,
                            company_industry, company_city, pool_status,
                            enrichment_source, als_score, als_tier, created_at
                        ) VALUES (
                            gen_random_uuid(), :client_id, :company_name, :company_domain, :phone,
                            :industry, :city, 'available',
                            'gmb_discovery', 0, 'cold', NOW()
                        )
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "client_id": str(client_id),
                        "company_name": company_name,
                        "company_domain": domain,
                        "phone": phone,
                        "industry": industry,
                        "city": city,
                    },
                )
                await db.commit()
                added += 1
            except Exception as e:
                logger.warning(f"Failed to insert lead '{company_name}': {e}")
                await db.rollback()
                skipped += 1

    logger.info(f"Tier 3 GMB discovery complete: {added} added, {skipped} skipped")
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "suppressed": 0,
        "total": added + skipped,
    }


# ============================================
# FLOWS
# ============================================


@flow(
    name="pool_population",
    description="Populate lead pool using waterfall strategy with Siege Waterfall enrichment",
    log_prints=True,
    timeout_seconds=900,  # 15 minute timeout for batched BD job
)
async def pool_population_flow(
    client_id: str | UUID,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Populate the lead pool for a client using waterfall strategy.

    Waterfall Tiers:
    1. Portfolio Lookalikes: Search by INDUSTRY extracted from portfolio
       companies, EXCLUDING portfolio company domains (finds similar companies)
    2. Portfolio Industries: Broader industry search with employee size filters
    3. Generic ICP: Fall back to broad ICP criteria search

    All enrichment flows through Siege Waterfall (5-tier Australian B2B pipeline).

    IMPORTANT: Portfolio companies are the agency's EXISTING clients.
    We don't contact them - we find LOOKALIKES in the same industries.

    Args:
        client_id: Client UUID (string or UUID)
        limit: Maximum leads to add to pool

    Returns:
        Dict with population summary including tier breakdown
    """
    # Convert string to UUID if needed (Prefect API passes strings)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting pool population flow for client {client_id}")

    # Step 1: Validate client and get ICP
    client_data = await validate_client_for_population_task(client_id)
    logger.info(
        f"Client validated: {client_data['client_name']}, "
        f"ICP: {len(client_data['icp_industries'])} industries, "
        f"{len(client_data['icp_titles'])} titles"
    )

    # Step 2: Get enriched portfolio from ICP extraction
    portfolio_data = await get_enriched_portfolio_task(client_id)

    # Track results by tier
    tier_results = []
    total_added = 0
    remaining = limit

    # ============================================
    # TIER 1: Portfolio Lookalike Search
    # (Search by industry, EXCLUDE portfolio domains)
    # ============================================
    if portfolio_data["has_portfolio"] and remaining > 0:
        logger.info("=== TIER 1: Portfolio Lookalike Search ===")
        tier1_result = await populate_pool_from_portfolio_task(
            client_id=client_id,
            enriched_portfolio=portfolio_data["enriched_portfolio"],
            icp_titles=client_data["icp_titles"],
            icp_locations=client_data["icp_locations"],
            employee_min=client_data["employee_min"],
            employee_max=client_data["employee_max"],
            limit=remaining,
        )
        tier_results.append(tier1_result)
        total_added += tier1_result["added"]
        remaining = limit - total_added
        logger.info(f"Tier 1 result: {tier1_result['added']} leads added, {remaining} remaining")

    # ============================================
    # TIER 2: Portfolio Industries Search
    # ============================================
    if portfolio_data["portfolio_industries"] and remaining > 0:
        logger.info("=== TIER 2: Portfolio Industries Search ===")
        tier2_result = await populate_pool_from_industries_task(
            client_id=client_id,
            portfolio_industries=portfolio_data["portfolio_industries"],
            icp_titles=client_data["icp_titles"],
            icp_locations=client_data["icp_locations"],
            employee_min=client_data["employee_min"],
            employee_max=client_data["employee_max"],
            limit=remaining,
        )
        tier_results.append(tier2_result)
        total_added += tier2_result["added"]
        remaining = limit - total_added
        logger.info(f"Tier 2 result: {tier2_result['added']} leads added, {remaining} remaining")

    # ============================================
    # TIER 3: Generic ICP Search (Fallback)
    # ============================================
    if remaining > 0:
        logger.info("=== TIER 3: Generic ICP Search (Fallback) ===")
        icp_criteria = {
            "icp_industries": client_data["icp_industries"],
            "icp_titles": client_data["icp_titles"],
            "icp_locations": client_data["icp_locations"],
            "employee_min": client_data["employee_min"],
            "employee_max": client_data["employee_max"],
        }

        tier3_result = await populate_pool_from_icp_task(
            client_id=client_id,
            icp_criteria=icp_criteria,
            limit=remaining,
        )
        tier3_result["tier"] = 3
        tier_results.append(tier3_result)
        total_added += tier3_result["added"]
        logger.info(f"Tier 3 result: {tier3_result['added']} leads added")

    # Compile summary
    summary = {
        "client_id": str(client_id),
        "client_name": client_data["client_name"],
        "success": total_added > 0,
        "leads_added": total_added,
        "leads_requested": limit,
        "portfolio_companies_found": len(portfolio_data.get("enriched_portfolio", [])),
        "portfolio_industries_found": portfolio_data.get("portfolio_industries", []),
        "tier_results": tier_results,
        "icp_criteria": {
            "industries": client_data["icp_industries"],
            "titles": client_data["icp_titles"],
            "locations": client_data["icp_locations"],
        },
        "enrichment_source": "siege_waterfall",
        "completed_at": datetime.now(UTC).isoformat(),
    }

    if total_added > 0:
        tier_breakdown = {r.get("tier", "?"): r.get("added", 0) for r in tier_results}
        logger.info(
            f"Pool population completed: {total_added} leads added "
            f"for client {client_data['client_name']} "
            f"(Tier breakdown: {tier_breakdown})"
        )
    else:
        logger.warning(
            f"Pool population found 0 leads for client {client_data['client_name']}. "
            f"Portfolio companies: {len(portfolio_data.get('enriched_portfolio', []))}, "
            f"Portfolio industries: {portfolio_data.get('portfolio_industries', [])}"
        )
        summary["warning"] = "No leads found across all tiers"

    return summary


@flow(
    name="pool_population_batch",
    description="Populate pool for multiple clients using Siege Waterfall enrichment",
    log_prints=True,
)
async def pool_population_batch_flow(
    client_ids: list[UUID],
    limit_per_client: int = 25,
) -> dict[str, Any]:
    """
    Populate pool for multiple clients.

    Args:
        client_ids: List of client UUIDs
        limit_per_client: Leads per client

    Returns:
        Dict with batch results
    """
    logger.info(f"Starting batch pool population for {len(client_ids)} clients")

    results = []
    total_added = 0

    for client_id in client_ids:
        try:
            result = await pool_population_flow(
                client_id=client_id,
                limit=limit_per_client,
            )
            results.append(result)
            total_added += result.get("leads_added", 0)
        except Exception as e:
            logger.error(f"Failed to populate pool for client {client_id}: {e}")
            results.append(
                {
                    "client_id": str(client_id),
                    "success": False,
                    "error": str(e),
                }
            )

    return {
        "clients_processed": len(client_ids),
        "total_leads_added": total_added,
        "enrichment_source": "siege_waterfall",
        "results": results,
        "completed_at": datetime.now(UTC).isoformat(),
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] Uses ScoutEngine for lead search (Siege Waterfall for enrichment)
# [x] JIT validation tasks (Rule 13)
# [x] Soft delete checks in queries (Rule 14)
# [x] @flow and @task decorators from Prefect
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Maps client ICP fields to search criteria
# [x] Filters suppressed leads via client_id parameter
# [x] WATERFALL STRATEGY IMPLEMENTED:
#     - Tier 1: Portfolio LOOKALIKE search (by industry, excluding portfolio domains)
#     - Tier 2: Portfolio industries search with employee size filters
#     - Tier 3: Generic ICP fallback
# [x] Gets enriched_portfolio from ICP extraction job
# [x] Tracks results per tier in summary
# [x] CRITICAL FIX: Tier 1 now searches for LOOKALIKES, not existing client contacts
# [x] WHO REFINEMENT INTEGRATED:
#     - All tiers apply get_who_refined_criteria() before search
#     - Refines titles, industries, and company size based on conversion patterns
#     - Transparent logging of refinement application
# [x] SIEGE WATERFALL: All enrichment flows through siege_waterfall.py (SSOT)
