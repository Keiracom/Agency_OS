"""
FILE: src/orchestration/flows/pool_population_flow.py
PURPOSE: Populate lead pool from Apollo based on client ICP
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-012 (Gap fix - pool population trigger)
DEPENDENCIES:
  - src/engines/scout.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation before each step
  - Rule 14: Soft deletes only
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from sqlalchemy import and_, select

from src.engines.scout import get_scout_engine
from src.integrations.supabase import get_db_session
from src.models.base import SubscriptionStatus
from src.models.client import Client

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
            raise ValueError(
                f"Client subscription is {client.subscription_status.value}"
            )

        # Get ICP fields from client (set during onboarding)
        # These are TEXT[] columns on the clients table
        icp_industries = getattr(client, 'icp_industries', None) or []
        icp_company_sizes = getattr(client, 'icp_company_sizes', None) or []
        icp_locations = getattr(client, 'icp_locations', None) or []
        icp_titles = getattr(client, 'icp_titles', None) or []

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


@task(name="populate_pool_from_apollo", retries=2, retry_delay_seconds=10)
async def populate_pool_from_apollo_task(
    client_id: UUID,
    icp_criteria: dict[str, Any],
    limit: int = 25,
) -> dict[str, Any]:
    """
    Search Apollo and populate the lead pool.

    Args:
        client_id: Client UUID for suppression filtering
        icp_criteria: ICP criteria dict
        limit: Maximum leads to add

    Returns:
        Dict with population results
    """
    async with get_db_session() as db:
        scout = get_scout_engine()

        # Build Apollo-compatible criteria
        apollo_criteria = {
            "titles": icp_criteria.get("icp_titles", []),
            "industries": icp_criteria.get("icp_industries", []),
            "countries": icp_criteria.get("icp_locations", []),
            "employee_min": icp_criteria.get("employee_min"),
            "employee_max": icp_criteria.get("employee_max"),
            # seniorities can be inferred from titles or set defaults
            "seniorities": ["director", "vp", "c_suite", "owner", "founder"],
        }

        logger.info(
            f"Populating pool for client {client_id} with criteria: "
            f"industries={apollo_criteria['industries']}, "
            f"titles={apollo_criteria['titles']}, "
            f"limit={limit}"
        )

        result = await scout.search_and_populate_pool(
            db=db,
            icp_criteria=apollo_criteria,
            limit=limit,
            client_id=client_id,
        )

        if result.success:
            logger.info(
                f"Pool population complete: {result.data['added']} added, "
                f"{result.data['skipped']} skipped, "
                f"{result.data['suppressed']} suppressed"
            )
            return {
                "success": True,
                "added": result.data["added"],
                "skipped": result.data["skipped"],
                "suppressed": result.data["suppressed"],
                "total": result.data["total"],
            }
        else:
            logger.error(f"Pool population failed: {result.error}")
            return {
                "success": False,
                "error": result.error,
                "added": 0,
                "skipped": 0,
                "suppressed": 0,
                "total": 0,
            }


# ============================================
# FLOWS
# ============================================


@flow(
    name="pool_population",
    description="Populate lead pool from Apollo based on client ICP",
    log_prints=True,
)
async def pool_population_flow(
    client_id: str | UUID,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Populate the lead pool for a client based on their ICP.

    Steps:
    1. Validate client has ICP configured
    2. Build Apollo search criteria from ICP
    3. Search Apollo and populate pool
    4. Return summary

    Args:
        client_id: Client UUID (string or UUID)
        limit: Maximum leads to add to pool

    Returns:
        Dict with population summary
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

    # Step 2: Build ICP criteria
    icp_criteria = {
        "icp_industries": client_data["icp_industries"],
        "icp_titles": client_data["icp_titles"],
        "icp_locations": client_data["icp_locations"],
        "employee_min": client_data["employee_min"],
        "employee_max": client_data["employee_max"],
    }

    # Step 3: Populate pool from Apollo
    population_result = await populate_pool_from_apollo_task(
        client_id=client_id,
        icp_criteria=icp_criteria,
        limit=limit,
    )

    # Compile summary
    summary = {
        "client_id": str(client_id),
        "client_name": client_data["client_name"],
        "success": population_result["success"],
        "leads_added": population_result["added"],
        "leads_skipped": population_result["skipped"],
        "leads_suppressed": population_result["suppressed"],
        "leads_found": population_result["total"],
        "icp_criteria": icp_criteria,
        "completed_at": datetime.utcnow().isoformat(),
    }

    if population_result["success"]:
        logger.info(
            f"Pool population completed: {summary['leads_added']} leads added "
            f"for client {client_data['client_name']}"
        )
    else:
        logger.error(
            f"Pool population failed for client {client_data['client_name']}: "
            f"{population_result.get('error', 'Unknown error')}"
        )
        summary["error"] = population_result.get("error")

    return summary


@flow(
    name="pool_population_batch",
    description="Populate pool for multiple clients",
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
            results.append({
                "client_id": str(client_id),
                "success": False,
                "error": str(e),
            })

    return {
        "clients_processed": len(client_ids),
        "total_leads_added": total_added,
        "results": results,
        "completed_at": datetime.utcnow().isoformat(),
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] Uses ScoutEngine for Apollo search
# [x] JIT validation tasks (Rule 13)
# [x] Soft delete checks in queries (Rule 14)
# [x] @flow and @task decorators from Prefect
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Maps client ICP fields to Apollo search criteria
# [x] Filters suppressed leads via client_id parameter
