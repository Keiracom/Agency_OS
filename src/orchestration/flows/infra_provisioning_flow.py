"""
FILE: src/orchestration/flows/infra_provisioning_flow.py
PURPOSE: Automated email infrastructure provisioning via Mailforge/InfraForge
PHASE: FCO-001 (Fixed-Cost Fortress)
TASK: Mailforge pivot - automated domain + mailbox provisioning
DEPENDENCIES:
  - src/integrations/infraforge.py
  - src/integrations/warmforge.py
  - src/integrations/salesforge.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Cost tracking in $AUD only

GOVERNANCE EVENT: MAILFORGE_PIVOT
DESCRIPTION: Pivot from Titan/Neo to Mailforge for automated DNS + warmup integration
COST TARGET: $111 AUD/month (20 mailboxes + 10 domains)
MARGIN IMPACT: Maintains 65.6% → 70.1% target achievable
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.integrations.infraforge import get_infraforge_client
from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS
# ============================================

# Cost constants (AUD)
MAILFORGE_COST_PER_MAILBOX_AUD = 4.65  # $3 USD × 1.55
DOMAIN_COST_PER_YEAR_AUD = 21.70  # $14 USD × 1.55
DOMAIN_COST_PER_MONTH_AUD = DOMAIN_COST_PER_YEAR_AUD / 12  # ~$1.81

# Default configuration
DEFAULT_MAILBOXES_PER_DOMAIN = 2
DEFAULT_DOMAINS_COUNT = 10
DEFAULT_MAILBOX_COUNT = 20

# Workspace IDs (from settings)
WORKSPACE_IDS = {
    "infraforge": None,  # Set from settings
    "salesforge": None,
    "warmforge": None,
}


# ============================================
# TASKS
# ============================================

@task(name="check_domain_availability", retries=2, retry_delay_seconds=5)
async def check_domain_availability_task(
    base_name: str,
    count: int = 10,
) -> list[dict]:
    """
    Generate and check availability of alternative domains.
    
    Args:
        base_name: Base company name for domain generation
        count: Number of alternatives to generate
    
    Returns:
        List of available domains with pricing
    """
    client = get_infraforge_client()
    
    try:
        # Generate alternatives
        alternatives = await client.generate_alternative_domains(base_name, count * 2)
        
        available = []
        for domain in alternatives.get("domains", []):
            # Check availability
            availability = await client.check_domain_availability(domain["name"])
            if availability.get("available"):
                available.append({
                    "domain": domain["name"],
                    "price_usd": availability.get("price", 14),
                    "price_aud": availability.get("price", 14) * 1.55,
                })
            
            if len(available) >= count:
                break
        
        logger.info(f"Found {len(available)} available domains for base: {base_name}")
        return available
        
    except Exception as e:
        logger.error(f"Domain availability check failed: {e}")
        raise


@task(name="purchase_domains", retries=1)
async def purchase_domains_task(
    domains: list[dict],
    client_id: UUID,
) -> dict:
    """
    Purchase domains via InfraForge/Mailforge.
    
    Args:
        domains: List of domain dicts with 'domain' key
        client_id: Client UUID for tracking
    
    Returns:
        Purchase result with domain IDs
    """
    client = get_infraforge_client()
    
    try:
        # Format for API
        domain_list = [{"domain": d["domain"]} for d in domains]
        
        result = await client.buy_domains(domain_list)
        
        # Calculate cost
        total_cost_aud = len(domains) * DOMAIN_COST_PER_YEAR_AUD
        
        logger.info(
            f"Purchased {len(domains)} domains for client {client_id}. "
            f"Cost: ${total_cost_aud:.2f} AUD/year"
        )
        
        return {
            "success": True,
            "domains_purchased": len(domains),
            "cost_aud_year": total_cost_aud,
            "cost_aud_month": total_cost_aud / 12,
            "domain_ids": result.get("domainIds", []),
        }
        
    except Exception as e:
        logger.error(f"Domain purchase failed: {e}")
        raise


@task(name="create_mailboxes", retries=2, retry_delay_seconds=10)
async def create_mailboxes_task(
    domains: list[str],
    mailboxes_per_domain: int = 2,
    client_id: UUID = None,
) -> dict:
    """
    Create mailboxes on purchased domains.
    
    Automatically configures:
    - DKIM, SPF, DMARC (via InfraForge)
    - Mailbox credentials
    
    Args:
        domains: List of domain names
        mailboxes_per_domain: Number of mailboxes per domain
        client_id: Client UUID for tracking
    
    Returns:
        Mailbox creation result
    """
    client = get_infraforge_client()
    
    try:
        mailboxes = []
        for domain in domains:
            for i in range(mailboxes_per_domain):
                # Generate professional email prefixes
                prefixes = ["outreach", "hello", "contact", "team", "sales"]
                prefix = prefixes[i % len(prefixes)]
                
                mailboxes.append({
                    "email": f"{prefix}{i+1}@{domain}",
                    "firstName": "Agency",
                    "lastName": "Outreach",
                })
        
        result = await client.create_mailboxes(mailboxes)
        
        # Calculate cost
        total_mailboxes = len(mailboxes)
        monthly_cost_aud = total_mailboxes * MAILFORGE_COST_PER_MAILBOX_AUD
        
        logger.info(
            f"Created {total_mailboxes} mailboxes across {len(domains)} domains. "
            f"Cost: ${monthly_cost_aud:.2f} AUD/month"
        )
        
        return {
            "success": True,
            "mailboxes_created": total_mailboxes,
            "domains_used": len(domains),
            "cost_aud_month": monthly_cost_aud,
            "mailbox_ids": result.get("mailboxIds", []),
        }
        
    except Exception as e:
        logger.error(f"Mailbox creation failed: {e}")
        raise


@task(name="export_to_warmup", retries=2, retry_delay_seconds=5)
async def export_to_warmup_task(
    from_workspace_id: str,
    to_salesforge_workspace_id: str,
    to_warmforge_workspace_id: str,
    tag_name: str,
) -> dict:
    """
    Export mailboxes to Salesforge + WarmForge for warmup.
    
    This is the key automation that saves 15+ hours vs manual setup.
    
    Args:
        from_workspace_id: InfraForge/Mailforge workspace
        to_salesforge_workspace_id: Target Salesforge workspace
        to_warmforge_workspace_id: Target WarmForge workspace
        tag_name: Tag for organizing mailboxes
    
    Returns:
        Export result
    """
    client = get_infraforge_client()
    
    try:
        result = await client.export_to_salesforge(
            from_workspace_id=from_workspace_id,
            to_workspace_id=to_salesforge_workspace_id,
            to_warmforge_workspace_id=to_warmforge_workspace_id,
            tag_name=tag_name,
            warmup_activated=True,  # Auto-start warmup
        )
        
        logger.info(f"Exported mailboxes to Salesforge/WarmForge with tag: {tag_name}")
        
        return {
            "success": True,
            "exported": True,
            "warmup_activated": True,
            "tag": tag_name,
        }
        
    except Exception as e:
        logger.error(f"Export to warmup failed: {e}")
        raise


@task(name="log_provisioning_cost")
async def log_provisioning_cost_task(
    client_id: UUID,
    domains_purchased: int,
    mailboxes_created: int,
    domain_cost_aud: float,
    mailbox_cost_aud: float,
) -> None:
    """Log infrastructure provisioning costs to database."""
    async with get_db_session() as db:
        # Log to audit_logs
        await db.execute(
            """
            INSERT INTO audit_logs (id, action, entity_type, entity_id, changes, performed_by, created_at)
            VALUES (
                gen_random_uuid(),
                'INFRA_PROVISIONING',
                'email_infrastructure',
                :client_id,
                :changes,
                'infra_provisioning_flow',
                NOW()
            )
            """,
            {
                "client_id": str(client_id),
                "changes": {
                    "domains_purchased": domains_purchased,
                    "mailboxes_created": mailboxes_created,
                    "domain_cost_aud_month": domain_cost_aud,
                    "mailbox_cost_aud_month": mailbox_cost_aud,
                    "total_cost_aud_month": domain_cost_aud + mailbox_cost_aud,
                    "provider": "mailforge",
                },
            },
        )
        await db.commit()


# ============================================
# MAIN FLOW
# ============================================

@flow(
    name="infra_provisioning_flow",
    description="Provision email infrastructure via Mailforge (domains + mailboxes + warmup)",
    task_runner=ConcurrentTaskRunner(),
    tags=["tier:bulk", "infra:spot"],  # FCO-001: Run on spot instances
)
async def infra_provisioning_flow(
    client_id: UUID,
    company_name: str,
    domain_count: int = DEFAULT_DOMAINS_COUNT,
    mailboxes_per_domain: int = DEFAULT_MAILBOXES_PER_DOMAIN,
    salesforge_workspace_id: str = None,
    warmforge_workspace_id: str = None,
) -> dict:
    """
    Main flow: Provision complete email infrastructure for a client.
    
    Steps:
    1. Generate and check domain availability
    2. Purchase domains
    3. Create mailboxes (DNS auto-configured)
    4. Export to Salesforge + WarmForge
    5. Log costs
    
    Args:
        client_id: Client UUID
        company_name: Base name for domain generation
        domain_count: Number of domains to purchase
        mailboxes_per_domain: Mailboxes per domain
        salesforge_workspace_id: Target Salesforge workspace
        warmforge_workspace_id: Target WarmForge workspace
    
    Returns:
        Complete provisioning result with costs
    """
    logger.info(f"Starting infrastructure provisioning for client {client_id}")
    
    start_time = datetime.utcnow()
    
    # Step 1: Find available domains
    available_domains = await check_domain_availability_task(
        base_name=company_name,
        count=domain_count,
    )
    
    if len(available_domains) < domain_count:
        logger.warning(
            f"Only {len(available_domains)} domains available, "
            f"requested {domain_count}"
        )
    
    # Step 2: Purchase domains
    purchase_result = await purchase_domains_task(
        domains=available_domains[:domain_count],
        client_id=client_id,
    )
    
    # Step 3: Create mailboxes
    domain_names = [d["domain"] for d in available_domains[:domain_count]]
    mailbox_result = await create_mailboxes_task(
        domains=domain_names,
        mailboxes_per_domain=mailboxes_per_domain,
        client_id=client_id,
    )
    
    # Step 4: Export to warmup (if workspace IDs provided)
    export_result = {"success": False, "skipped": True}
    if salesforge_workspace_id and warmforge_workspace_id:
        infraforge_workspace = await get_infraforge_client().list_workspaces()
        workspace_id = infraforge_workspace.get("workspaces", [{}])[0].get("id")
        
        if workspace_id:
            export_result = await export_to_warmup_task(
                from_workspace_id=workspace_id,
                to_salesforge_workspace_id=salesforge_workspace_id,
                to_warmforge_workspace_id=warmforge_workspace_id,
                tag_name=f"client_{client_id}",
            )
    
    # Step 5: Log costs
    await log_provisioning_cost_task(
        client_id=client_id,
        domains_purchased=purchase_result["domains_purchased"],
        mailboxes_created=mailbox_result["mailboxes_created"],
        domain_cost_aud=purchase_result["cost_aud_month"],
        mailbox_cost_aud=mailbox_result["cost_aud_month"],
    )
    
    # Calculate totals
    total_cost_month = (
        purchase_result["cost_aud_month"] + 
        mailbox_result["cost_aud_month"]
    )
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    result = {
        "success": True,
        "client_id": str(client_id),
        "domains": {
            "count": purchase_result["domains_purchased"],
            "cost_aud_month": purchase_result["cost_aud_month"],
            "names": domain_names,
        },
        "mailboxes": {
            "count": mailbox_result["mailboxes_created"],
            "cost_aud_month": mailbox_result["cost_aud_month"],
        },
        "warmup": {
            "activated": export_result.get("warmup_activated", False),
            "exported": export_result.get("exported", False),
        },
        "total_cost_aud_month": total_cost_month,
        "duration_seconds": duration,
        "automation_time_saved_hours": 15,  # vs manual Titan/Neo setup
    }
    
    logger.info(
        f"Infrastructure provisioning complete for client {client_id}. "
        f"Cost: ${total_cost_month:.2f} AUD/month. "
        f"Duration: {duration:.1f}s (saved ~15 hours vs manual)"
    )
    
    return result


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Uses existing infraforge.py integration
# [x] Domain availability check
# [x] Domain purchase
# [x] Mailbox creation with auto-DNS
# [x] Export to Salesforge + WarmForge
# [x] Cost tracking in AUD
# [x] Audit logging
# [x] Tagged for spot instances (FCO-001)
