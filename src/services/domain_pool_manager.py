"""
Contract: src/services/domain_pool_manager.py
Purpose: Manage the Salesforge burner domain pool lifecycle
Layer: services
Imports: stdlib, src.models, src.integrations
Consumers: orchestration flows, assignment hooks

Pool lifecycle:
  candidate -> approved -> purchasing -> dns_configuring ->
  warming -> ready -> assigned -> (quarantined | retired)

All purchase operations are dry_run=True by default.
Set dry_run=False only after Dave explicitly approves first batch.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.burner_domain import (
    BurnerDomain,
    BurnerDomainStatus,
    BurnerMailbox,
    BurnerMailboxStatus,
    DomainNamingPattern,
)
from src.services.domain_name_generator import DomainNameGenerator

logger = logging.getLogger(__name__)

# Target number of ready domains to keep in the pool
POOL_TARGET_SIZE = 10
# Quarantine period after a domain is released
QUARANTINE_DAYS = 14


class DomainPoolManager:
    """
    Manages the lifecycle of burner sending domains.

    Responsibilities:
    - Generate and approve domain candidates
    - Coordinate purchases (dry_run by default)
    - Track warmup status via Salesforge
    - Assign/release domains to clients
    - Process quarantine expiry
    - Retire exhausted domains
    """

    def __init__(self, db: AsyncSession, dry_run: bool = True):
        self.db = db
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # 1. Pool size check
    # ------------------------------------------------------------------

    async def pool_size(self) -> dict[str, int]:
        """Return counts by status for operational visibility."""
        result = await self.db.execute(select(BurnerDomain))
        all_domains = result.scalars().all()

        counts: dict[str, int] = {}
        for domain in all_domains:
            counts[domain.status] = counts.get(domain.status, 0) + 1

        ready = counts.get(BurnerDomainStatus.READY, 0)
        counts["_total"] = len(all_domains)
        counts["_ready"] = ready
        counts["_needs_replenishment"] = max(0, POOL_TARGET_SIZE - ready)
        return counts

    # ------------------------------------------------------------------
    # 2. Generate candidates from approved patterns
    # ------------------------------------------------------------------

    async def generate_candidates(self, count: int = 20, tld: str = ".com.au") -> list[dict]:
        """
        Generate domain name candidates from approved naming patterns.

        Does NOT persist to DB — returns raw candidates for review.
        """
        result = await self.db.execute(
            select(DomainNamingPattern).where(DomainNamingPattern.approved == True)  # noqa: E712
        )
        patterns = result.scalars().all()

        if not patterns:
            logger.warning("No approved naming patterns found in domain_naming_patterns table")
            return []

        pattern_dicts = [
            {
                "pattern_type": p.pattern_type,
                "seeds": p.seeds,
                "suffixes": p.suffixes,
            }
            for p in patterns
        ]

        generator = DomainNameGenerator(pattern_dicts)
        candidates = generator.generate_batch(count=count, tld=tld)
        logger.info(f"Generated {len(candidates)} domain candidates (tld={tld})")
        return candidates

    # ------------------------------------------------------------------
    # 3. Approve a candidate (persist to DB)
    # ------------------------------------------------------------------

    async def approve_candidate(
        self, domain_name: str, pattern_type: str | None = None
    ) -> BurnerDomain:
        """
        Approve a generated candidate and persist it with status=approved.

        Args:
            domain_name: Full domain name (e.g. northgateadvisory.com.au)
            pattern_type: Pattern used to generate this domain
        """
        tld = domain_name.split(".", 1)[1] if "." in domain_name else "com.au"
        domain = BurnerDomain(
            domain_name=domain_name,
            tld=tld,
            status=BurnerDomainStatus.APPROVED,
            pattern_type=pattern_type,
            dry_run=self.dry_run,
        )
        self.db.add(domain)
        await self.db.flush()
        logger.info(f"Approved domain candidate: {domain_name} (id={domain.id})")
        return domain

    # ------------------------------------------------------------------
    # 4. Purchase approved domains
    # ------------------------------------------------------------------

    async def purchase_approved(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Trigger purchase for approved domains.

        In dry_run mode: logs intent only, does not call Salesforge.
        In live mode: calls Salesforge domain purchase API.
        """
        result = await self.db.execute(
            select(BurnerDomain)
            .where(BurnerDomain.status == BurnerDomainStatus.APPROVED)
            .limit(limit)
        )
        domains = result.scalars().all()
        outcomes: list[dict[str, Any]] = []

        for domain in domains:
            if self.dry_run or domain.dry_run:
                logger.info(f"[DRY RUN] Would purchase domain: {domain.domain_name}")
                await self.db.execute(
                    update(BurnerDomain)
                    .where(BurnerDomain.id == domain.id)
                    .values(
                        status=BurnerDomainStatus.PURCHASING,
                        notes="[dry_run] purchase simulated",
                        updated_at=datetime.now(UTC),
                    )
                )
                outcomes.append(
                    {"domain": domain.domain_name, "dry_run": True, "status": "purchasing"}
                )
            else:
                # Live purchase path — Salesforge API call goes here
                # TODO: integrate salesforge.purchase_domain() when Dave approves
                logger.warning(f"Live purchase not yet wired for {domain.domain_name}")
                outcomes.append(
                    {"domain": domain.domain_name, "dry_run": False, "status": "skipped_not_wired"}
                )

        await self.db.flush()
        return outcomes

    # ------------------------------------------------------------------
    # 5. Sync warmup status from Salesforge
    # ------------------------------------------------------------------

    async def sync_warmup_status(self) -> list[dict[str, Any]]:
        """
        Pull warmup status from Salesforge for all warming/dns_configuring domains.

        In dry_run mode: advances status deterministically for testing.
        """
        result = await self.db.execute(
            select(BurnerDomain).where(
                BurnerDomain.status.in_(
                    [
                        BurnerDomainStatus.DNS_CONFIGURING,
                        BurnerDomainStatus.WARMING,
                    ]
                )
            )
        )
        domains = result.scalars().all()
        updates: list[dict[str, Any]] = []

        for domain in domains:
            if self.dry_run or domain.dry_run:
                # Dry-run: simulate transition after 2+ hours in current status
                age = datetime.now(UTC) - domain.updated_at.replace(tzinfo=UTC)
                if age > timedelta(hours=2):
                    next_status = (
                        BurnerDomainStatus.WARMING
                        if domain.status == BurnerDomainStatus.DNS_CONFIGURING
                        else BurnerDomainStatus.READY
                    )
                    values: dict[str, Any] = {
                        "status": next_status,
                        "updated_at": datetime.now(UTC),
                    }
                    if next_status == BurnerDomainStatus.WARMING:
                        values["warmup_started_at"] = datetime.now(UTC)
                    elif next_status == BurnerDomainStatus.READY:
                        values["ready_at"] = datetime.now(UTC)
                    await self.db.execute(
                        update(BurnerDomain).where(BurnerDomain.id == domain.id).values(**values)
                    )
                    updates.append(
                        {"domain": domain.domain_name, "new_status": next_status, "dry_run": True}
                    )
                else:
                    updates.append(
                        {
                            "domain": domain.domain_name,
                            "new_status": domain.status,
                            "unchanged": True,
                        }
                    )
            else:
                # Live: call Salesforge get_warmup_status
                # TODO: wire salesforge.get_warmup_status(domain.salesforge_domain_id)
                logger.info(f"Live warmup sync not yet wired for {domain.domain_name}")
                updates.append({"domain": domain.domain_name, "skipped": True})

        await self.db.flush()
        return updates

    # ------------------------------------------------------------------
    # 6. Assign domain to client
    # ------------------------------------------------------------------

    async def assign_to_client(self, client_id: UUID) -> BurnerDomain | None:
        """
        Assign the next available ready domain to a client.

        Returns the assigned domain, or None if pool is empty.
        """
        result = await self.db.execute(
            select(BurnerDomain)
            .where(BurnerDomain.status == BurnerDomainStatus.READY)
            .order_by(BurnerDomain.ready_at.asc().nullsfirst())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        domain = result.scalar_one_or_none()

        if domain is None:
            logger.warning(f"Domain pool empty — cannot assign to client {client_id}")
            return None

        await self.db.execute(
            update(BurnerDomain)
            .where(BurnerDomain.id == domain.id)
            .values(
                status=BurnerDomainStatus.ASSIGNED,
                assigned_to_client_id=client_id,
                assigned_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        # Mark mailboxes as assigned
        await self.db.execute(
            update(BurnerMailbox)
            .where(BurnerMailbox.domain_id == domain.id)
            .values(status=BurnerMailboxStatus.ASSIGNED)
        )
        await self.db.flush()
        logger.info(f"Assigned domain {domain.domain_name} to client {client_id}")
        return domain

    # ------------------------------------------------------------------
    # 7. Release domain from client -> quarantine
    # ------------------------------------------------------------------

    async def release_from_client(self, domain_id: UUID) -> BurnerDomain:
        """
        Release an assigned domain. Moves it to quarantine for QUARANTINE_DAYS.
        """
        result = await self.db.execute(select(BurnerDomain).where(BurnerDomain.id == domain_id))
        domain = result.scalar_one()
        quarantine_until = datetime.now(UTC) + timedelta(days=QUARANTINE_DAYS)

        await self.db.execute(
            update(BurnerDomain)
            .where(BurnerDomain.id == domain_id)
            .values(
                status=BurnerDomainStatus.QUARANTINED,
                released_at=datetime.now(UTC),
                quarantine_until=quarantine_until,
                assigned_to_client_id=None,
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.execute(
            update(BurnerMailbox)
            .where(BurnerMailbox.domain_id == domain_id)
            .values(status=BurnerMailboxStatus.WARMING)
        )
        await self.db.flush()
        logger.info(
            f"Released domain {domain.domain_name} to quarantine until {quarantine_until.date()}"
        )
        return domain

    # ------------------------------------------------------------------
    # 8. Process quarantine expiry
    # ------------------------------------------------------------------

    async def process_quarantine(self) -> list[str]:
        """
        Move quarantined domains back to ready if quarantine_until has passed.

        Returns list of domain names that were released from quarantine.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(BurnerDomain).where(
                and_(
                    BurnerDomain.status == BurnerDomainStatus.QUARANTINED,
                    BurnerDomain.quarantine_until <= now,
                )
            )
        )
        domains = result.scalars().all()
        released: list[str] = []

        for domain in domains:
            await self.db.execute(
                update(BurnerDomain)
                .where(BurnerDomain.id == domain.id)
                .values(
                    status=BurnerDomainStatus.READY,
                    quarantine_until=None,
                    updated_at=now,
                )
            )
            await self.db.execute(
                update(BurnerMailbox)
                .where(BurnerMailbox.domain_id == domain.id)
                .values(status=BurnerMailboxStatus.READY)
            )
            released.append(domain.domain_name)

        if released:
            await self.db.flush()
            logger.info(f"Released {len(released)} domains from quarantine: {released}")

        return released

    # ------------------------------------------------------------------
    # 9. Retire domain
    # ------------------------------------------------------------------

    async def retire_domain(self, domain_id: UUID, reason: str = "") -> BurnerDomain:
        """
        Permanently retire a domain. No further use.
        """
        result = await self.db.execute(select(BurnerDomain).where(BurnerDomain.id == domain_id))
        domain = result.scalar_one()

        await self.db.execute(
            update(BurnerDomain)
            .where(BurnerDomain.id == domain_id)
            .values(
                status=BurnerDomainStatus.RETIRED,
                notes=reason or "Retired by pool manager",
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.execute(
            update(BurnerMailbox)
            .where(BurnerMailbox.domain_id == domain_id)
            .values(status=BurnerMailboxStatus.RETIRED)
        )
        await self.db.flush()
        logger.info(f"Retired domain {domain.domain_name}: {reason}")
        return domain
