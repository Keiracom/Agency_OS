"""
Contract: src/services/persona_service.py
Purpose: Generate AI personas, allocate to clients, manage lifecycle
Layer: 3 - services (uses models, integrations)
Imports: models, integrations
Consumers: orchestration flows, API routes
Spec: Persona pool allocation by tier (ignition: 2, velocity: 3, dominance: 4)
"""

import logging
import random
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.persona import (
    PERSONA_TIER_ALLOCATIONS,
    Persona,
    PersonaStatus,
)

logger = logging.getLogger(__name__)


# ============================================
# PERSONA GENERATION DATA
# ============================================

# Realistic professional first names
FIRST_NAMES = [
    "James", "Sarah", "Michael", "Emma", "David", "Rachel", "Daniel", "Jessica",
    "Christopher", "Emily", "Matthew", "Lauren", "Andrew", "Nicole", "William",
    "Megan", "Joshua", "Samantha", "Ryan", "Ashley", "Brandon", "Taylor",
    "Nathan", "Victoria", "Justin", "Amanda", "Benjamin", "Brittany", "Zachary",
    "Stephanie", "Kevin", "Rebecca", "Thomas", "Chelsea", "Timothy", "Melissa",
    "Scott", "Jennifer", "Brian", "Heather", "Aaron", "Katherine", "Patrick",
    "Alexandra", "Jonathan", "Christina", "Eric", "Michelle", "Adam", "Allison",
]

# Professional last names
LAST_NAMES = [
    "Anderson", "Bennett", "Campbell", "Davidson", "Edwards", "Foster",
    "Graham", "Harrison", "Ingram", "Jensen", "Kennedy", "Lawrence",
    "Mitchell", "Newman", "O'Brien", "Parker", "Quinn", "Reynolds",
    "Sullivan", "Thompson", "Underwood", "Vaughn", "Watson", "Xu",
    "Young", "Zimmerman", "Hayes", "Morrison", "Crawford", "Henderson",
    "Brooks", "Griffin", "Cooper", "Richardson", "Walsh", "Hunter",
    "Palmer", "Spencer", "Mason", "Porter", "Russell", "Gibson",
]

# Professional titles
PROFESSIONAL_TITLES = [
    "Growth Consultant",
    "Business Development Manager",
    "Partnership Director",
    "Client Success Manager",
    "Strategic Advisor",
    "Engagement Manager",
    "Solutions Consultant",
    "Development Executive",
    "Account Director",
    "Revenue Strategist",
    "Market Development Lead",
    "Business Strategist",
]

# Generic professional company names
COMPANY_NAMES = [
    "Growth Partners",
    "Scale Advisory",
    "Momentum Consulting",
    "Catalyst Group",
    "Apex Strategy",
    "Elevation Partners",
    "Horizon Advisory",
    "Summit Consulting",
    "Vanguard Partners",
    "Pinnacle Advisory",
    "Nexus Consulting",
    "Velocity Partners",
    "Bridge Strategy",
    "Keystone Advisory",
    "Milestone Partners",
]

# Bio templates
BIO_TEMPLATES = [
    "Passionate about helping businesses scale through strategic partnerships. "
    "{years}+ years of experience driving growth across diverse industries.",
    
    "Dedicated to building lasting business relationships that deliver measurable results. "
    "Specializing in {specialty} with a track record of exceeding targets.",
    
    "Results-driven professional focused on identifying and capturing growth opportunities. "
    "Known for a consultative approach that puts client success first.",
    
    "Strategic thinker with expertise in {specialty}. "
    "Committed to understanding unique business challenges and delivering tailored solutions.",
    
    "Experienced in driving revenue growth through relationship-based strategies. "
    "{years}+ years helping organizations achieve their full potential.",
]

SPECIALTIES = [
    "B2B partnerships",
    "market expansion",
    "client acquisition",
    "strategic growth",
    "business development",
]


# ============================================
# PERSONA GENERATION
# ============================================


async def generate_persona(db: AsyncSession) -> Persona:
    """
    AI generates a professional identity.

    Creates a realistic professional persona with:
    - First name, last name (realistic, professional)
    - Title (e.g., "Growth Consultant", "Business Development")
    - Bio (2-3 sentences)
    - Company name (generic professional: "Growth Partners", "Scale Advisory")

    Returns created Persona with status='available'
    """
    # Generate identity components
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    title = random.choice(PROFESSIONAL_TITLES)
    company_name = random.choice(COMPANY_NAMES)

    # Generate bio from template
    bio_template = random.choice(BIO_TEMPLATES)
    years = random.randint(5, 15)
    specialty = random.choice(SPECIALTIES)
    bio = bio_template.format(years=years, specialty=specialty)

    # Create persona
    persona = Persona(
        first_name=first_name,
        last_name=last_name,
        title=title,
        bio=bio,
        company_name=company_name,
        status=PersonaStatus.AVAILABLE,
    )

    db.add(persona)
    await db.commit()
    await db.refresh(persona)

    logger.info(
        f"Generated new persona: {persona.full_name} - {title} at {company_name}"
    )

    return persona


async def generate_domain_names(persona: Persona) -> list[str]:
    """
    Generate domain name variants for persona.

    Patterns:
    - {firstname}{lastname}.io
    - {f}{lastname}.co
    - team{firstname}.com

    Returns list of 3 domain name options.
    """
    first = persona.first_name.lower()
    last = persona.last_name.lower()
    first_initial = first[0]

    domains = [
        f"{first}{last}.io",
        f"{first_initial}{last}.co",
        f"team{first}.com",
    ]

    logger.debug(f"Generated domain variants for {persona.full_name}: {domains}")

    return domains


# ============================================
# PERSONA ALLOCATION
# ============================================


async def allocate_personas_to_client(
    db: AsyncSession,
    client_id: UUID,
    tier: str,
) -> list[Persona]:
    """
    Allocate available personas to new client based on tier.

    Tier allocations:
    - Ignition: 2 personas
    - Velocity: 3 personas
    - Dominance: 4 personas

    Updates persona.status = 'allocated', persona.allocated_to_client_id = client_id

    Args:
        db: Database session
        client_id: New client's UUID
        tier: Pricing tier ('ignition', 'velocity', 'dominance')

    Returns:
        List of allocated Persona objects

    Raises:
        ValueError: If tier is invalid
    """
    tier_lower = tier.lower()

    if tier_lower not in PERSONA_TIER_ALLOCATIONS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(PERSONA_TIER_ALLOCATIONS.keys())}")

    count_needed = PERSONA_TIER_ALLOCATIONS[tier_lower]

    logger.info(f"Allocating {count_needed} personas to client {client_id} (tier: {tier_lower})")

    # Get available personas
    stmt = (
        select(Persona)
        .where(Persona.status == PersonaStatus.AVAILABLE)
        .order_by(Persona.created_at.asc())
        .limit(count_needed)
    )
    result = await db.execute(stmt)
    available_personas = list(result.scalars().all())

    if len(available_personas) < count_needed:
        logger.warning(
            f"Insufficient personas: need {count_needed}, have {len(available_personas)}. "
            f"Allocating {len(available_personas)} available."
        )

    allocated: list[Persona] = []

    for persona in available_personas:
        persona.status = PersonaStatus.ALLOCATED
        persona.allocated_to_client_id = client_id
        allocated.append(persona)

        logger.debug(f"Allocated persona {persona.full_name} to client {client_id}")

    await db.commit()

    logger.info(
        f"Persona allocation complete for client {client_id}: "
        f"{len(allocated)} personas allocated"
    )

    return allocated


# ============================================
# PERSONA RELEASE
# ============================================


async def release_client_personas(
    db: AsyncSession,
    client_id: UUID,
) -> int:
    """
    Release personas when client churns.

    Sets status back to 'available', clears allocated_to_client_id.

    Args:
        db: Database session
        client_id: Churning client's UUID

    Returns:
        Count of released personas
    """
    logger.info(f"Releasing personas for client {client_id}")

    # Get client's allocated personas
    stmt = (
        select(Persona)
        .where(Persona.allocated_to_client_id == client_id)
        .where(Persona.status == PersonaStatus.ALLOCATED)
    )
    result = await db.execute(stmt)
    client_personas = list(result.scalars().all())

    release_count = 0

    for persona in client_personas:
        persona.status = PersonaStatus.AVAILABLE
        persona.allocated_to_client_id = None
        release_count += 1

        logger.debug(f"Released persona {persona.full_name} from client {client_id}")

    await db.commit()

    logger.info(f"Released {release_count} personas for client {client_id}")

    return release_count


# ============================================
# PERSONA QUERIES
# ============================================


async def get_available_persona_count(db: AsyncSession) -> int:
    """
    Count personas with status='available'.

    Args:
        db: Database session

    Returns:
        Count of available personas
    """
    stmt = (
        select(func.count())
        .select_from(Persona)
        .where(Persona.status == PersonaStatus.AVAILABLE)
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0

    return count


async def get_client_personas(
    db: AsyncSession,
    client_id: UUID,
) -> list[Persona]:
    """
    Get all personas allocated to a client.

    Args:
        db: Database session
        client_id: Client UUID

    Returns:
        List of Persona objects allocated to the client
    """
    stmt = (
        select(Persona)
        .where(Persona.allocated_to_client_id == client_id)
        .where(Persona.status == PersonaStatus.ALLOCATED)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_pool_stats(db: AsyncSession) -> dict:
    """
    Get persona pool statistics.

    Returns:
        Dict with pool statistics (total, available, allocated, retired)
    """
    # Total
    total_stmt = select(func.count()).select_from(Persona)
    total = (await db.execute(total_stmt)).scalar() or 0

    # Available
    available_stmt = (
        select(func.count())
        .select_from(Persona)
        .where(Persona.status == PersonaStatus.AVAILABLE)
    )
    available = (await db.execute(available_stmt)).scalar() or 0

    # Allocated
    allocated_stmt = (
        select(func.count())
        .select_from(Persona)
        .where(Persona.status == PersonaStatus.ALLOCATED)
    )
    allocated = (await db.execute(allocated_stmt)).scalar() or 0

    # Retired
    retired_stmt = (
        select(func.count())
        .select_from(Persona)
        .where(Persona.status == PersonaStatus.RETIRED)
    )
    retired = (await db.execute(retired_stmt)).scalar() or 0

    return {
        "total": total,
        "available": available,
        "allocated": allocated,
        "retired": retired,
    }


async def retire_persona(
    db: AsyncSession,
    persona_id: UUID,
    reason: str | None = None,
) -> bool:
    """
    Retire a persona from the pool.

    Args:
        db: Database session
        persona_id: Persona UUID
        reason: Optional reason for retirement

    Returns:
        True if retired, False if not found
    """
    persona = await db.get(Persona, persona_id)
    if not persona:
        return False

    persona.status = PersonaStatus.RETIRED
    persona.allocated_to_client_id = None

    await db.commit()

    logger.info(f"Retired persona {persona.full_name} ({persona_id}): {reason or 'No reason provided'}")

    return True


# ============================================
# BULK GENERATION
# ============================================


async def ensure_persona_buffer(
    db: AsyncSession,
    buffer_count: int = 10,
) -> int:
    """
    Ensure minimum available persona buffer.

    Generates new personas if available count is below buffer_count.

    Args:
        db: Database session
        buffer_count: Minimum number of available personas to maintain

    Returns:
        Number of personas generated
    """
    available = await get_available_persona_count(db)

    if available >= buffer_count:
        logger.debug(f"Persona buffer healthy: {available} available (target: {buffer_count})")
        return 0

    to_generate = buffer_count - available
    logger.info(f"Generating {to_generate} personas to meet buffer target")

    generated = 0
    for _ in range(to_generate):
        await generate_persona(db)
        generated += 1

    logger.info(f"Generated {generated} personas to replenish buffer")

    return generated


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] generate_persona function - creates AI persona
# [x] generate_domain_names function - 3 domain variants
# [x] allocate_personas_to_client function - tier-based allocation
# [x] release_client_personas function - churn handling
# [x] get_available_persona_count function - availability check
# [x] get_client_personas function - client lookup
# [x] get_pool_stats function - pool statistics
# [x] retire_persona function - lifecycle management
# [x] ensure_persona_buffer function - buffer maintenance
# [x] Proper logging
# [x] Type hints on all functions
# [x] Docstrings on all functions
