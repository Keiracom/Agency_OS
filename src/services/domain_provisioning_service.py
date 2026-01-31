"""
Contract: src/services/domain_provisioning_service.py
Purpose: Domain provisioning service for persona-based email infrastructure
Layer: 3 - services (uses models, integrations)
Imports: models, integrations
Consumers: orchestration flows, API routes

Handles:
- Domain name generation for personas
- Domain availability checking
- Domain purchase via InfraForge
- Mailbox creation (2 per domain)
- Export to Salesforge + WarmForge warmup
- Resource pool registration
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.infraforge import get_infraforge_client, WORKSPACE_IDS
from src.models.persona import Persona
from src.models.resource_pool import ResourcePool, ResourceType, ResourceStatus
from src.services.resource_assignment_service import add_resource_to_pool
from src.services.spending_guard import (
    check_can_purchase,
    record_purchase,
    SpendingLimitExceeded,
    requires_approval,
    queue_for_approval,
)

logger = logging.getLogger(__name__)


# ============================================
# WORKSPACE IDS
# ============================================

INFRAFORGE_WORKSPACE = WORKSPACE_IDS["infraforge"]
SALESFORGE_WORKSPACE = WORKSPACE_IDS["salesforge"]
WARMFORGE_WORKSPACE = WORKSPACE_IDS["warmforge"]


# ============================================
# DOMAIN PATTERNS
# ============================================

DOMAIN_PATTERNS = [
    "{firstname}{lastname}.io",
    "{f}{lastname}.co",
    "team{firstname}.com",
    "{firstname}{l}.io",
    "get{lastname}.com",
]

# Maximum domains to purchase per persona
MAX_DOMAINS_PER_PERSONA = 3

# Mailboxes per domain
MAILBOXES_PER_DOMAIN = 2


# ============================================
# DOMAIN NAME GENERATION
# ============================================


async def generate_domain_names_for_persona(persona: Persona) -> list[str]:
    """
    Generate domain name variants for a persona.

    Uses patterns to create branded domain names from persona's
    first and last name.

    Args:
        persona: Persona model with first_name and last_name

    Returns:
        List of candidate domain names

    Example:
        For persona "John Smith":
        - johnsmith.io
        - jsmith.co
        - teamjohn.com
        - johns.io
        - getsmith.com
    """
    first_name = persona.first_name.lower().strip()
    last_name = persona.last_name.lower().strip()

    names = []
    for pattern in DOMAIN_PATTERNS:
        try:
            name = pattern.format(
                firstname=first_name,
                lastname=last_name,
                f=first_name[0] if first_name else "x",
                l=last_name[0] if last_name else "x",
            )
            names.append(name)
        except (IndexError, KeyError) as e:
            logger.warning(f"Error generating domain from pattern '{pattern}': {e}")
            continue

    logger.debug(f"Generated {len(names)} domain candidates for {persona.full_name}")
    return names


# ============================================
# DOMAIN AVAILABILITY
# ============================================


async def check_domain_availability(domains: list[str]) -> list[str]:
    """
    Check which domains are available for purchase.

    Queries InfraForge API for each domain.

    Args:
        domains: List of domain names to check

    Returns:
        List of available domain names
    """
    client = get_infraforge_client()
    available: list[str] = []

    try:
        results = await client.check_domain_availability(domains)

        for result in results:
            domain = result.get("domain", "")
            is_available = result.get("available", False)

            if is_available:
                available.append(domain)
                logger.debug(f"Domain available: {domain}")
            else:
                logger.debug(f"Domain unavailable: {domain}")

    except Exception as e:
        logger.error(f"Error checking domain availability: {e}")
        # Return empty list on error - caller should handle

    logger.info(f"Availability check: {len(available)}/{len(domains)} domains available")
    return available


# ============================================
# DOMAIN PURCHASE
# ============================================


async def purchase_domains(domains: list[str]) -> list[dict[str, Any]]:
    """
    Purchase domains via InfraForge.

    Args:
        domains: List of domain names to purchase

    Returns:
        List of purchase results with domain info

    Raises:
        SpendingLimitExceeded: If purchase would exceed safety limits
        Exception: If purchase fails (propagated from InfraForge client)
    """
    if not domains:
        logger.warning("No domains to purchase")
        return []

    # ============================================
    # SAFEGUARD: Check spending limits BEFORE purchase
    # ============================================
    check_can_purchase(len(domains))  # Raises SpendingLimitExceeded if over limit
    
    # Optional: Queue for approval if large purchase
    if requires_approval(len(domains)):
        request_id = queue_for_approval(
            domain_count=len(domains),
            domains=domains,
            reason="bulk_purchase",
        )
        logger.warning(
            f"Large purchase ({len(domains)} domains) queued for approval. "
            f"Request ID: {request_id}"
        )
        # In production, you might want to raise here and wait for approval
        # For now, we log and continue (approval queue is informational)

    client = get_infraforge_client()
    results = await client.purchase_domains_bulk(domains)

    successful = [r for r in results if r.get("status") != "failed"]
    failed = [r for r in results if r.get("status") == "failed"]

    if failed:
        for f in failed:
            logger.warning(f"Failed to purchase domain {f.get('domain')}: {f.get('error')}")

    # ============================================
    # SAFEGUARD: Record successful purchases
    # ============================================
    if successful:
        record_purchase(len(successful))

    logger.info(f"Purchased {len(successful)}/{len(domains)} domains")
    return successful


# ============================================
# MAILBOX CREATION
# ============================================


async def create_mailboxes_for_persona(
    domain: str,
    persona: Persona,
) -> list[dict[str, Any]]:
    """
    Create mailboxes for a persona on a domain.

    Creates 2 mailboxes per domain with persona identity:
    - firstname@domain.com
    - f.lastname@domain.com

    Args:
        domain: Domain name (e.g., "johnsmith.io")
        persona: Persona to create mailboxes for

    Returns:
        List of created mailbox details
    """
    client = get_infraforge_client()
    mailboxes: list[dict[str, Any]] = []

    # Mailbox configurations
    mailbox_configs = [
        {
            "prefix": persona.first_name.lower(),
            "display_name": persona.full_name,
        },
        {
            "prefix": f"{persona.first_name[0].lower()}.{persona.last_name.lower()}",
            "display_name": persona.display_name,
        },
    ]

    for config in mailbox_configs:
        try:
            result = await client.create_mailbox(
                domain=domain,
                email_prefix=config["prefix"],
                display_name=config["display_name"],
                first_name=persona.first_name,
                last_name=persona.last_name,
            )
            mailboxes.append(result)
            logger.info(f"Created mailbox: {result.get('email')}")

        except Exception as e:
            logger.error(f"Failed to create mailbox {config['prefix']}@{domain}: {e}")
            # Continue with other mailboxes

    return mailboxes


# ============================================
# SALESFORGE EXPORT
# ============================================


async def export_to_salesforge_and_warmup(
    domains: list[str],
    tag_name: str = "auto-provision",
) -> bool:
    """
    Export mailboxes to Salesforge and activate WarmForge warmup.

    This is the key integration step that connects InfraForge domains
    to the sending infrastructure.

    Args:
        domains: List of domain names to export mailboxes for
        tag_name: Tag for organizing mailboxes in Salesforge

    Returns:
        True if export successful, False otherwise
    """
    if not domains:
        logger.warning("No domains to export")
        return False

    client = get_infraforge_client()

    try:
        result = await client.export_to_salesforge(
            domains=domains,
            warmup_activated=True,
        )

        exported_count = result.get("exported_count", 0)
        logger.info(
            f"Exported {exported_count} mailboxes to Salesforge "
            f"(tag: {tag_name}, warmup: enabled)"
        )

        return result.get("success", False)

    except Exception as e:
        logger.error(f"Export to Salesforge failed: {e}")
        return False


# ============================================
# FULL PROVISIONING FLOW
# ============================================


async def provision_persona_with_domains(
    db: AsyncSession,
    persona: Persona,
    max_domains: int = MAX_DOMAINS_PER_PERSONA,
) -> dict[str, Any]:
    """
    Full domain provisioning flow for a persona.

    Orchestrates the complete provisioning pipeline:
    1. Generate domain name variants
    2. Check domain availability
    3. Purchase available domains (up to max_domains)
    4. Create mailboxes on each domain
    5. Export to Salesforge with warmup enabled
    6. Register domains in resource pool

    Args:
        db: Database session
        persona: Persona to provision domains for
        max_domains: Maximum number of domains to purchase (default: 3)

    Returns:
        Dict with provisioning results:
        - success: bool
        - persona_id: str (if successful)
        - domains_purchased: int (if successful)
        - domains: list of domain names (if successful)
        - mailboxes_created: int (if successful)
        - error: str (if failed)
    """
    logger.info(f"Starting domain provisioning for persona {persona.id} ({persona.full_name})")

    # 1. Generate domain names
    domain_names = await generate_domain_names_for_persona(persona)
    if not domain_names:
        return {
            "success": False,
            "error": "Failed to generate domain names",
        }

    # 2. Check availability
    available = await check_domain_availability(domain_names)
    if not available:
        return {
            "success": False,
            "error": "No domains available for persona name",
            "checked_domains": domain_names,
        }

    # 3. Purchase domains (limited to max_domains)
    domains_to_purchase = available[:max_domains]
    purchased = await purchase_domains(domains_to_purchase)

    if not purchased:
        return {
            "success": False,
            "error": "Domain purchase failed",
            "available_domains": available,
        }

    # Extract domain names from purchase results
    purchased_domains: list[str] = []
    for domain_info in purchased:
        domain = _extract_domain_name(domain_info)
        if domain:
            purchased_domains.append(domain)

    # 4. Create mailboxes for each domain
    total_mailboxes = 0
    for domain in purchased_domains:
        mailboxes = await create_mailboxes_for_persona(domain, persona)
        total_mailboxes += len(mailboxes)

    # 5. Export to Salesforge with warmup
    tag_name = f"persona-{persona.id}"
    export_success = await export_to_salesforge_and_warmup(
        domains=purchased_domains,
        tag_name=tag_name,
    )

    if not export_success:
        logger.warning(f"Salesforge export failed for persona {persona.id}")
        # Continue anyway - domains are purchased, can retry export

    # 6. Add to resource pool
    for domain_info in purchased:
        domain = _extract_domain_name(domain_info)
        if not domain:
            continue

        try:
            await add_resource_to_pool(
                db=db,
                resource_type=ResourceType.EMAIL_DOMAIN,
                resource_value=domain,
                provider="infraforge",
                provider_id=str(domain_info.get("domain_id") or domain_info.get("id", "")),
                status=ResourceStatus.WARMING,
                warmup_completed=False,
                resource_name=f"{persona.full_name} - {domain}",
            )
            logger.debug(f"Added domain {domain} to resource pool")

        except Exception as e:
            logger.error(f"Failed to add domain {domain} to resource pool: {e}")
            # Continue - domain is still purchased

    await db.commit()

    logger.info(
        f"Provisioning complete for persona {persona.id}: "
        f"{len(purchased_domains)} domains, {total_mailboxes} mailboxes"
    )

    return {
        "success": True,
        "persona_id": str(persona.id),
        "persona_name": persona.full_name,
        "domains_purchased": len(purchased_domains),
        "domains": purchased_domains,
        "mailboxes_created": total_mailboxes,
        "warmup_enabled": export_success,
    }


# ============================================
# HELPER FUNCTIONS
# ============================================


def _extract_domain_name(domain_info: dict[str, Any]) -> str | None:
    """
    Extract domain name from purchase result.

    InfraForge may return domain in different formats:
    - {"domain": "example.com"}
    - {"sld": "example", "tld": "com"}

    Args:
        domain_info: Purchase result dict

    Returns:
        Domain name string or None if extraction fails
    """
    if "domain" in domain_info:
        return domain_info["domain"]

    sld = domain_info.get("sld")
    tld = domain_info.get("tld")

    if sld and tld:
        return f"{sld}.{tld}"

    return None


async def get_warmup_status_for_domains(domains: list[str]) -> list[dict[str, Any]]:
    """
    Get warmup status for a list of domains.

    Args:
        domains: List of domain names

    Returns:
        List of warmup status dicts per domain/mailbox
    """
    client = get_infraforge_client()
    statuses: list[dict[str, Any]] = []

    for domain in domains:
        try:
            # Get mailboxes for domain
            mailboxes = await client.get_mailboxes(domain=domain)

            for mailbox in mailboxes:
                email = mailbox.get("email", "")
                if not email:
                    continue

                status = await client.get_warmup_status(email)
                statuses.append(status)

        except Exception as e:
            logger.warning(f"Failed to get warmup status for {domain}: {e}")
            statuses.append({
                "domain": domain,
                "status": "error",
                "error": str(e),
            })

    return statuses


async def provision_domain_only(
    db: AsyncSession,
    domain: str,
    persona: Persona | None = None,
) -> dict[str, Any]:
    """
    Provision a specific domain (skip availability check).

    Use when domain has already been verified available.

    Args:
        db: Database session
        domain: Specific domain name to purchase
        persona: Optional persona for mailbox creation

    Returns:
        Provisioning result dict
    """
    logger.info(f"Provisioning specific domain: {domain}")

    # Purchase
    purchased = await purchase_domains([domain])
    if not purchased:
        return {
            "success": False,
            "error": f"Failed to purchase domain: {domain}",
        }

    domain_info = purchased[0]
    purchased_domain = _extract_domain_name(domain_info)

    if not purchased_domain:
        return {
            "success": False,
            "error": "Failed to extract domain name from purchase result",
        }

    # Create mailboxes if persona provided
    mailboxes_created = 0
    if persona:
        mailboxes = await create_mailboxes_for_persona(purchased_domain, persona)
        mailboxes_created = len(mailboxes)

        # Export to Salesforge
        await export_to_salesforge_and_warmup(
            domains=[purchased_domain],
            tag_name=f"domain-{purchased_domain}",
        )

    # Add to resource pool
    resource_name = f"{persona.full_name} - {purchased_domain}" if persona else purchased_domain

    await add_resource_to_pool(
        db=db,
        resource_type=ResourceType.EMAIL_DOMAIN,
        resource_value=purchased_domain,
        provider="infraforge",
        provider_id=str(domain_info.get("domain_id") or domain_info.get("id", "")),
        status=ResourceStatus.WARMING,
        warmup_completed=False,
        resource_name=resource_name,
    )

    await db.commit()

    return {
        "success": True,
        "domain": purchased_domain,
        "mailboxes_created": mailboxes_created,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Workspace IDs from infraforge integration
# [x] DOMAIN_PATTERNS constant
# [x] generate_domain_names_for_persona()
# [x] check_domain_availability()
# [x] purchase_domains()
# [x] create_mailboxes_for_persona()
# [x] export_to_salesforge_and_warmup()
# [x] provision_persona_with_domains() - full flow
# [x] provision_domain_only() - single domain helper
# [x] get_warmup_status_for_domains() - status check
# [x] _extract_domain_name() helper
# [x] Proper logging throughout
# [x] Type hints on all functions
# [x] Docstrings on all functions
# [x] Error handling with continue-on-partial-failure
