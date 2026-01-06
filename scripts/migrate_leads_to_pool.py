"""
FILE: scripts/migrate_leads_to_pool.py
PURPOSE: One-time migration of existing leads to lead_pool
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-013

This script:
1. Reads all existing leads from the leads table
2. Creates pool entries in lead_pool (deduped by email)
3. Creates assignments linking pool leads to original clients
4. Updates leads.lead_pool_id reference

Run with: python -m scripts.migrate_leads_to_pool
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from uuid import UUID

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agency_os"
)

# Convert to async URL if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


async def get_session() -> AsyncSession:
    """Create async database session."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


async def migrate_leads_to_pool():
    """
    Migrate existing leads to the lead pool.

    Strategy:
    1. For each unique email in leads, create ONE pool entry
    2. Assign that pool entry to the client of the FIRST lead with that email
    3. Link all leads with that email to the same pool entry
    """
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        logger.info("Starting lead pool migration...")

        # Step 1: Get count of existing leads
        count_result = await db.execute(
            text("SELECT COUNT(*) FROM leads WHERE deleted_at IS NULL")
        )
        total_leads = count_result.scalar() or 0
        logger.info(f"Found {total_leads} leads to migrate")

        if total_leads == 0:
            logger.info("No leads to migrate")
            return

        # Step 2: Get all unique emails with their lead data
        # We'll use the first lead (by created_at) as the source of truth
        leads_query = text("""
            SELECT DISTINCT ON (LOWER(email))
                id, email, first_name, last_name, title, company,
                linkedin_url, phone, email_verified, als_score, als_tier,
                client_id, campaign_id, status, created_at
            FROM leads
            WHERE deleted_at IS NULL
            AND email IS NOT NULL
            ORDER BY LOWER(email), created_at ASC
        """)

        result = await db.execute(leads_query)
        unique_leads = result.fetchall()
        logger.info(f"Found {len(unique_leads)} unique email addresses")

        # Step 3: Migrate each unique lead to pool
        migrated = 0
        assigned = 0
        errors = 0

        for lead in unique_leads:
            try:
                # Check if already in pool
                check_result = await db.execute(
                    text("SELECT id FROM lead_pool WHERE LOWER(email) = LOWER(:email)"),
                    {"email": lead.email}
                )
                existing = check_result.fetchone()

                if existing:
                    pool_id = existing.id
                    logger.debug(f"Lead {lead.email} already in pool")
                else:
                    # Determine email status based on email_verified
                    email_status = "verified" if lead.email_verified else "guessed"

                    # Insert into pool
                    insert_result = await db.execute(
                        text("""
                            INSERT INTO lead_pool (
                                email, email_status, first_name, last_name,
                                title, company_name, linkedin_url, phone,
                                als_score, als_tier, pool_status, created_at
                            ) VALUES (
                                :email, :email_status, :first_name, :last_name,
                                :title, :company_name, :linkedin_url, :phone,
                                :als_score, :als_tier, 'assigned', NOW()
                            )
                            ON CONFLICT (email) DO UPDATE SET
                                updated_at = NOW()
                            RETURNING id
                        """),
                        {
                            "email": lead.email.lower(),
                            "email_status": email_status,
                            "first_name": lead.first_name,
                            "last_name": lead.last_name,
                            "title": lead.title,
                            "company_name": lead.company,
                            "linkedin_url": lead.linkedin_url,
                            "phone": lead.phone,
                            "als_score": lead.als_score,
                            "als_tier": lead.als_tier,
                        }
                    )
                    pool_row = insert_result.fetchone()
                    pool_id = pool_row.id
                    migrated += 1

                # Create assignment if client_id exists
                if lead.client_id:
                    # Check if assignment already exists
                    assign_check = await db.execute(
                        text("""
                            SELECT id FROM lead_assignments
                            WHERE lead_pool_id = :pool_id
                        """),
                        {"pool_id": str(pool_id)}
                    )

                    if not assign_check.fetchone():
                        await db.execute(
                            text("""
                                INSERT INTO lead_assignments (
                                    lead_pool_id, client_id, campaign_id,
                                    status, assigned_by, assignment_reason,
                                    assigned_at
                                ) VALUES (
                                    :pool_id, :client_id, :campaign_id,
                                    'active', 'migration', 'Migrated from legacy leads table',
                                    :assigned_at
                                )
                                ON CONFLICT (lead_pool_id) DO NOTHING
                            """),
                            {
                                "pool_id": str(pool_id),
                                "client_id": str(lead.client_id),
                                "campaign_id": str(lead.campaign_id) if lead.campaign_id else None,
                                "assigned_at": lead.created_at or datetime.utcnow(),
                            }
                        )
                        assigned += 1

                # Update lead with pool reference
                await db.execute(
                    text("""
                        UPDATE leads
                        SET lead_pool_id = :pool_id, updated_at = NOW()
                        WHERE id = :lead_id
                    """),
                    {"pool_id": str(pool_id), "lead_id": str(lead.id)}
                )

                # Also update any other leads with the same email
                await db.execute(
                    text("""
                        UPDATE leads
                        SET lead_pool_id = :pool_id, updated_at = NOW()
                        WHERE LOWER(email) = LOWER(:email)
                        AND lead_pool_id IS NULL
                    """),
                    {"pool_id": str(pool_id), "email": lead.email}
                )

            except Exception as e:
                logger.error(f"Error migrating lead {lead.email}: {e}")
                errors += 1

            # Commit every 100 records
            if (migrated + errors) % 100 == 0:
                await db.commit()
                logger.info(f"Progress: {migrated} migrated, {assigned} assigned, {errors} errors")

        # Final commit
        await db.commit()

        logger.info("=" * 50)
        logger.info("Migration complete!")
        logger.info(f"Total unique emails: {len(unique_leads)}")
        logger.info(f"New pool entries created: {migrated}")
        logger.info(f"Assignments created: {assigned}")
        logger.info(f"Errors: {errors}")

        # Step 4: Update pool statistics
        stats_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN pool_status = 'available' THEN 1 END) as available,
                    COUNT(CASE WHEN pool_status = 'assigned' THEN 1 END) as assigned
                FROM lead_pool
            """)
        )
        stats = stats_result.fetchone()
        logger.info(f"Pool stats - Total: {stats.total}, Available: {stats.available}, Assigned: {stats.assigned}")


async def verify_migration():
    """Verify the migration was successful."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        logger.info("\n" + "=" * 50)
        logger.info("Verification checks...")

        # Check 1: All leads have pool reference
        orphan_check = await db.execute(
            text("""
                SELECT COUNT(*) FROM leads
                WHERE deleted_at IS NULL
                AND lead_pool_id IS NULL
                AND email IS NOT NULL
            """)
        )
        orphans = orphan_check.scalar() or 0
        logger.info(f"Leads without pool reference: {orphans}")

        # Check 2: Pool entries have unique emails
        dupe_check = await db.execute(
            text("""
                SELECT email, COUNT(*) as cnt
                FROM lead_pool
                GROUP BY email
                HAVING COUNT(*) > 1
            """)
        )
        dupes = dupe_check.fetchall()
        logger.info(f"Duplicate emails in pool: {len(dupes)}")

        # Check 3: Assignments match pool status
        status_check = await db.execute(
            text("""
                SELECT COUNT(*) FROM lead_pool lp
                JOIN lead_assignments la ON la.lead_pool_id = lp.id
                WHERE lp.pool_status = 'available'
                AND la.status = 'active'
            """)
        )
        mismatched = status_check.scalar() or 0
        logger.info(f"Status mismatches: {mismatched}")

        if orphans == 0 and len(dupes) == 0 and mismatched == 0:
            logger.info("All verification checks passed!")
        else:
            logger.warning("Some verification checks failed - review the data")


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate leads to pool")
    parser.add_argument("--verify-only", action="store_true", help="Only verify, don't migrate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    if args.verify_only:
        await verify_migration()
    elif args.dry_run:
        logger.info("DRY RUN - would migrate leads to pool")
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as db:
            count_result = await db.execute(
                text("SELECT COUNT(DISTINCT LOWER(email)) FROM leads WHERE deleted_at IS NULL AND email IS NOT NULL")
            )
            unique_emails = count_result.scalar() or 0
            logger.info(f"Would migrate {unique_emails} unique emails to pool")
    else:
        await migrate_leads_to_pool()
        await verify_migration()


if __name__ == "__main__":
    asyncio.run(main())
