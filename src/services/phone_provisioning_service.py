"""
Contract: src/services/phone_provisioning_service.py
Purpose: Automated phone number provisioning via Twilio API
Layer: 3 - services
Imports: models, integrations
Consumers: orchestration flows, API routes, campaign creation
Spec: docs/architecture/distribution/VOICE.md
TODO.md: #13 (P3 Medium - Voice Engine)

Handles:
- Search available Australian phone numbers from Twilio
- Purchase numbers with regulatory bundle
- Configure webhooks for voice/SMS
- Add to resource pool
- Assign to clients/campaigns
- Release numbers back to pool
- Track warmup for new numbers (1-week ramp)
"""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError
from src.models.base import ChannelType
from src.models.campaign import CampaignResource
from src.models.resource_pool import (
    ClientResource,
    ResourcePool,
    ResourceStatus,
    ResourceType,
)

logger = logging.getLogger(__name__)


# ============================================
# VOICE WARMUP SCHEDULE (from VOICE.md)
# ============================================

VOICE_WARMUP_SCHEDULE = [
    (0, 2, 20),  # Days 0-2: 20 calls/day
    (3, 4, 30),  # Days 3-4: 30 calls/day
    (5, 6, 40),  # Days 5-6: 40 calls/day
    (7, 999, 50),  # Days 7+: 50 calls/day (full capacity)
]


def get_voice_daily_limit(number_created_at: datetime) -> int:
    """
    Get daily call limit based on number age (warmup schedule).

    Args:
        number_created_at: When the number was provisioned

    Returns:
        Daily call limit (20-50)
    """
    days_active = (datetime.utcnow() - number_created_at).days
    for start, end, limit in VOICE_WARMUP_SCHEDULE:
        if start <= days_active <= end:
            return limit
    return 50  # Default full capacity


# ============================================
# PHONE PROVISIONING SERVICE
# ============================================


class PhoneProvisioningService:
    """
    Service for automated phone number provisioning via Twilio.

    Workflow:
    1. Search available AU numbers with voice+SMS capability
    2. Purchase with regulatory bundle
    3. Configure webhooks
    4. Add to resource_pool table
    5. Optionally assign to client

    Per VOICE.md specs:
    - Rate limit: 50 calls/day/number (after warmup)
    - Warmup: 1-week ramp (20->30->40->50)
    - AU regulatory bundle required
    """

    def __init__(self):
        """Initialize with Twilio credentials from settings."""
        self._client = None

    @property
    def twilio(self):
        """Lazy load Twilio client."""
        if self._client is None:
            from twilio.rest import Client as TwilioBaseClient

            if not settings.twilio_account_sid or not settings.twilio_auth_token:
                raise IntegrationError(
                    service="twilio",
                    message="Twilio credentials not configured",
                )
            self._client = TwilioBaseClient(
                settings.twilio_account_sid,
                settings.twilio_auth_token,
            )
        return self._client

    async def search_available_numbers(
        self,
        country: str = "AU",
        area_code: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search for available phone numbers in Twilio.

        Args:
            country: ISO country code (default: AU for Australia)
            area_code: Optional area code filter
            limit: Max numbers to return

        Returns:
            List of available numbers with details
        """
        try:

            def _search():
                kwargs = {
                    "limit": limit,
                    "voice_enabled": True,
                    "sms_enabled": True,
                }
                if area_code:
                    kwargs["area_code"] = area_code

                # Try mobile first (preferred for AU)
                try:
                    return self.twilio.available_phone_numbers(country).mobile.list(**kwargs)
                except Exception:
                    # Fall back to local if mobile not available
                    return self.twilio.available_phone_numbers(country).local.list(**kwargs)

            numbers = await asyncio.to_thread(_search)

            return [
                {
                    "phone_number": n.phone_number,
                    "friendly_name": n.friendly_name,
                    "locality": getattr(n, "locality", None),
                    "region": getattr(n, "region", None),
                    "capabilities": {
                        "voice": n.capabilities.get("voice", False),
                        "sms": n.capabilities.get("sms", False),
                        "mms": n.capabilities.get("mms", False),
                    },
                }
                for n in numbers
            ]

        except Exception as e:
            logger.error(f"Failed to search available numbers: {e}")
            raise APIError(
                service="twilio",
                status_code=500,
                message=f"Failed to search numbers: {str(e)}",
            )

    async def provision_number(
        self,
        db: AsyncSession,
        phone_number: str,
        client_id: UUID | None = None,
        friendly_name: str | None = None,
    ) -> ResourcePool:
        """
        Purchase and provision a phone number from Twilio.

        Args:
            db: Database session
            phone_number: E.164 phone number to purchase
            client_id: Optional client to assign to
            friendly_name: Optional friendly name

        Returns:
            Created ResourcePool record
        """
        try:
            # Build webhook URLs
            voice_webhook = f"{settings.base_url}/api/v1/webhooks/vapi/call"
            sms_webhook = f"{settings.base_url}/api/v1/webhooks/twilio/sms"

            def _purchase():
                kwargs = {
                    "phone_number": phone_number,
                    "voice_url": voice_webhook,
                    "voice_method": "POST",
                    "sms_url": sms_webhook,
                    "sms_method": "POST",
                }

                # Add friendly name if provided
                if friendly_name:
                    kwargs["friendly_name"] = friendly_name

                # Add regulatory bundle if configured (required for AU)
                if hasattr(settings, "twilio_au_bundle_sid") and settings.twilio_au_bundle_sid:
                    kwargs["bundle_sid"] = settings.twilio_au_bundle_sid

                return self.twilio.incoming_phone_numbers.create(**kwargs)

            number = await asyncio.to_thread(_purchase)

            logger.info(f"Purchased Twilio number: {phone_number} (SID: {number.sid})")

            # Add to resource pool
            resource = ResourcePool(
                resource_type=ResourceType.PHONE_NUMBER,
                resource_value=phone_number,
                resource_name=friendly_name or f"Voice {phone_number[-4:]}",
                provider="twilio",
                provider_id=number.sid,
                provider_metadata={
                    "capabilities": {
                        "voice": True,
                        "sms": True,
                    },
                    "voice_webhook": voice_webhook,
                    "sms_webhook": sms_webhook,
                    "purchased_at": datetime.utcnow().isoformat(),
                },
                status=ResourceStatus.WARMING,  # New numbers start in warmup
                max_clients=1,  # Phone numbers are exclusive
                current_clients=0,
                warmup_started_at=datetime.utcnow(),
                reputation_score=50,  # Neutral starting score
            )

            db.add(resource)
            await db.flush()
            await db.refresh(resource)

            logger.info(f"Added phone to resource pool: {resource.id}")

            # Optionally assign to client immediately
            if client_id:
                await self._assign_to_client(db, resource.id, client_id)

            await db.commit()

            return resource

        except Exception as e:
            logger.error(f"Failed to provision number {phone_number}: {e}")
            raise APIError(
                service="twilio",
                status_code=500,
                message=f"Failed to provision number: {str(e)}",
            )

    async def provision_for_campaign(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        client_id: UUID,
    ) -> dict:
        """
        Provision or assign a phone number for a voice campaign.

        Workflow:
        1. Check if client already has available phone numbers
        2. If yes, use existing from pool
        3. If no, search and provision new number

        Args:
            db: Database session
            campaign_id: Campaign to assign number to
            client_id: Client owning the campaign

        Returns:
            Dict with phone_number and provisioning details
        """
        # 1. Check for existing available numbers in client's pool
        stmt = (
            select(ClientResource)
            .join(ResourcePool)
            .where(
                and_(
                    ClientResource.client_id == client_id,
                    ClientResource.released_at.is_(None),
                    ResourcePool.resource_type == ResourceType.PHONE_NUMBER,
                    ResourcePool.status.in_(
                        [ResourceStatus.AVAILABLE, ResourceStatus.WARMING, ResourceStatus.ASSIGNED]
                    ),
                )
            )
        )
        result = await db.execute(stmt)
        client_resources = list(result.scalars().all())

        # 2. Check if any are not yet assigned to this campaign
        if client_resources:
            # Get campaign's current phone resources
            campaign_stmt = select(CampaignResource).where(
                and_(
                    CampaignResource.campaign_id == campaign_id,
                    CampaignResource.channel == ChannelType.VOICE,
                    CampaignResource.is_active,
                )
            )
            campaign_result = await db.execute(campaign_stmt)
            existing_campaign_phones = {cr.resource_id for cr in campaign_result.scalars().all()}

            # Find unassigned client phone number
            for cr in client_resources:
                if cr.resource.resource_value not in existing_campaign_phones:
                    # Assign existing number to campaign
                    await self._assign_to_campaign(
                        db=db,
                        campaign_id=campaign_id,
                        client_resource=cr,
                    )
                    await db.commit()

                    return {
                        "phone_number": cr.resource.resource_value,
                        "resource_pool_id": str(cr.resource_pool_id),
                        "client_resource_id": str(cr.id),
                        "provisioned": False,
                        "source": "existing_pool",
                        "daily_limit": get_voice_daily_limit(
                            cr.resource.warmup_started_at or datetime.utcnow()
                        ),
                    }

        # 3. Need to provision new number
        logger.info(f"No available phone numbers for client {client_id}, provisioning new")

        # Search for available numbers
        available = await self.search_available_numbers(country="AU", limit=3)

        if not available:
            raise APIError(
                service="twilio",
                status_code=503,
                message="No phone numbers available for provisioning",
            )

        # Provision the first available
        resource = await self.provision_number(
            db=db,
            phone_number=available[0]["phone_number"],
            client_id=client_id,
            friendly_name=f"Voice-{campaign_id.hex[:8]}",
        )

        # Get client resource link
        cr_stmt = select(ClientResource).where(
            and_(
                ClientResource.client_id == client_id,
                ClientResource.resource_pool_id == resource.id,
            )
        )
        cr_result = await db.execute(cr_stmt)
        client_resource = cr_result.scalar_one()

        # Assign to campaign
        await self._assign_to_campaign(
            db=db,
            campaign_id=campaign_id,
            client_resource=client_resource,
        )
        await db.commit()

        return {
            "phone_number": resource.resource_value,
            "resource_pool_id": str(resource.id),
            "client_resource_id": str(client_resource.id),
            "provisioned": True,
            "source": "newly_provisioned",
            "daily_limit": get_voice_daily_limit(datetime.utcnow()),
            "warmup_days_remaining": 7,
        }

    async def release_number(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
        delete_from_twilio: bool = False,
    ) -> bool:
        """
        Release a phone number back to available pool.

        Args:
            db: Database session
            resource_pool_id: Resource pool record ID
            delete_from_twilio: If True, also release from Twilio account

        Returns:
            True if released successfully
        """
        resource = await db.get(ResourcePool, resource_pool_id)
        if not resource:
            logger.warning(f"Resource not found: {resource_pool_id}")
            return False

        if resource.resource_type != ResourceType.PHONE_NUMBER:
            logger.warning(f"Resource is not a phone number: {resource.resource_type}")
            return False

        # Release all client assignments
        stmt = select(ClientResource).where(
            and_(
                ClientResource.resource_pool_id == resource_pool_id,
                ClientResource.released_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        client_resources = list(result.scalars().all())

        for cr in client_resources:
            cr.released_at = datetime.utcnow()
            resource.current_clients = max(0, resource.current_clients - 1)

        # Update resource status
        if resource.current_clients == 0:
            resource.status = ResourceStatus.AVAILABLE

        # Optionally delete from Twilio
        if delete_from_twilio and resource.provider_id:
            try:

                def _delete():
                    self.twilio.incoming_phone_numbers(resource.provider_id).delete()

                await asyncio.to_thread(_delete)
                resource.status = ResourceStatus.RETIRED
                logger.info(f"Released number from Twilio: {resource.resource_value}")

            except Exception as e:
                logger.error(f"Failed to release from Twilio: {e}")
                # Don't fail the whole operation

        await db.commit()

        logger.info(f"Released phone number: {resource.resource_value}")
        return True

    async def check_pool_health(
        self,
        db: AsyncSession,
        client_id: UUID,
        min_numbers: int = 1,
    ) -> dict:
        """
        Check if client has enough active phone numbers.

        Args:
            db: Database session
            client_id: Client UUID
            min_numbers: Minimum required numbers (default 1 per tier allocation)

        Returns:
            Health check result with recommendations
        """
        stmt = (
            select(ClientResource)
            .join(ResourcePool)
            .where(
                and_(
                    ClientResource.client_id == client_id,
                    ClientResource.released_at.is_(None),
                    ResourcePool.resource_type == ResourceType.PHONE_NUMBER,
                    ResourcePool.status.in_(
                        [
                            ResourceStatus.AVAILABLE,
                            ResourceStatus.WARMING,
                            ResourceStatus.ASSIGNED,
                        ]
                    ),
                )
            )
        )
        result = await db.execute(stmt)
        active_resources = list(result.scalars().all())

        active_count = len(active_resources)
        needs_provisioning = active_count < min_numbers

        # Calculate total daily capacity
        total_capacity = sum(
            get_voice_daily_limit(cr.resource.warmup_started_at or datetime.utcnow())
            for cr in active_resources
        )

        # Check warmup status
        warming_count = sum(1 for cr in active_resources if cr.resource.warmup_completed_at is None)

        return {
            "active_count": active_count,
            "min_required": min_numbers,
            "needs_provisioning": needs_provisioning,
            "shortfall": max(0, min_numbers - active_count),
            "total_daily_capacity": total_capacity,
            "numbers_warming": warming_count,
            "all_warmed": warming_count == 0,
            "health_status": "healthy" if not needs_provisioning else "needs_attention",
        }

    async def update_webhooks(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
        voice_webhook: str | None = None,
        sms_webhook: str | None = None,
    ) -> bool:
        """
        Update webhook URLs for a phone number in Twilio.

        Args:
            db: Database session
            resource_pool_id: Resource pool record ID
            voice_webhook: New voice webhook URL
            sms_webhook: New SMS webhook URL

        Returns:
            True if updated successfully
        """
        resource = await db.get(ResourcePool, resource_pool_id)
        if not resource or not resource.provider_id:
            return False

        try:

            def _update():
                kwargs = {}
                if voice_webhook:
                    kwargs["voice_url"] = voice_webhook
                    kwargs["voice_method"] = "POST"
                if sms_webhook:
                    kwargs["sms_url"] = sms_webhook
                    kwargs["sms_method"] = "POST"

                if kwargs:
                    self.twilio.incoming_phone_numbers(resource.provider_id).update(**kwargs)

            await asyncio.to_thread(_update)

            # Update metadata
            if resource.provider_metadata is None:
                resource.provider_metadata = {}
            if voice_webhook:
                resource.provider_metadata["voice_webhook"] = voice_webhook
            if sms_webhook:
                resource.provider_metadata["sms_webhook"] = sms_webhook

            await db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to update webhooks: {e}")
            return False

    async def complete_warmup(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
    ) -> bool:
        """
        Mark a phone number's warmup as complete.

        Called after 7 days or manually by ops.

        Args:
            db: Database session
            resource_pool_id: Resource pool record ID

        Returns:
            True if marked complete
        """
        resource = await db.get(ResourcePool, resource_pool_id)
        if not resource:
            return False

        resource.warmup_completed_at = datetime.utcnow()
        resource.status = ResourceStatus.AVAILABLE
        resource.reputation_score = 80  # Good starting reputation

        await db.commit()

        logger.info(f"Completed warmup for phone: {resource.resource_value}")
        return True

    # ============================================
    # PRIVATE HELPERS
    # ============================================

    async def _assign_to_client(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
        client_id: UUID,
    ) -> ClientResource:
        """Assign resource pool item to a client."""
        resource = await db.get(ResourcePool, resource_pool_id)
        if resource is None:
            raise ValueError(f"Resource pool {resource_pool_id} not found")

        client_resource = ClientResource(
            client_id=client_id,
            resource_pool_id=resource_pool_id,
            assigned_at=datetime.utcnow(),
        )
        db.add(client_resource)

        resource.current_clients += 1
        if resource.current_clients >= resource.max_clients:
            resource.status = ResourceStatus.ASSIGNED

        await db.flush()
        await db.refresh(client_resource)

        return client_resource

    async def _assign_to_campaign(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        client_resource: ClientResource,
    ) -> CampaignResource:
        """Assign client resource to a specific campaign."""
        resource = client_resource.resource

        daily_limit = get_voice_daily_limit(resource.warmup_started_at or datetime.utcnow())

        campaign_resource = CampaignResource(
            campaign_id=campaign_id,
            client_resource_id=client_resource.id,
            channel=ChannelType.VOICE,
            resource_id=resource.resource_value,
            resource_name=resource.resource_name,
            daily_limit=daily_limit,
            daily_used=0,
            is_active=True,
            is_warmed=resource.warmup_completed_at is not None,
        )
        db.add(campaign_resource)

        await db.flush()
        await db.refresh(campaign_resource)

        logger.info(
            f"Assigned phone {resource.resource_value} to campaign {campaign_id} "
            f"(limit: {daily_limit}/day)"
        )

        return campaign_resource


# ============================================
# SINGLETON INSTANCE
# ============================================

_phone_provisioning_service: PhoneProvisioningService | None = None


def get_phone_provisioning_service() -> PhoneProvisioningService:
    """Get or create PhoneProvisioningService instance."""
    global _phone_provisioning_service
    if _phone_provisioning_service is None:
        _phone_provisioning_service = PhoneProvisioningService()
    return _phone_provisioning_service


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (uses settings)
# [x] search_available_numbers() - searches Twilio
# [x] provision_number() - purchases and configures
# [x] provision_for_campaign() - assigns to campaign
# [x] release_number() - releases back to pool
# [x] check_pool_health() - monitors pool size
# [x] update_webhooks() - configures webhooks
# [x] complete_warmup() - marks warmup done
# [x] Warmup schedule per VOICE.md (20->30->40->50)
# [x] Async Twilio calls via asyncio.to_thread()
# [x] Proper logging
# [x] Error handling with custom exceptions
# [x] Type hints on all functions
# [x] Docstrings on all functions
