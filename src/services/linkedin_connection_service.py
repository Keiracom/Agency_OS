"""
Contract: src/services/linkedin_connection_service.py
Purpose: Manage LinkedIn connection via Unipile hosted auth
Layer: 3 - services
Imports: models, integrations
Consumers: API routes

Phase: Unipile Migration - Hosted Auth (replaces HeyReach)

Key Changes from HeyReach:
- No credential storage (Unipile handles auth)
- No 2FA handling (Unipile hosted flow manages this)
- OAuth-style redirect flow instead of email/password
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.integrations.unipile import get_unipile_client
from src.models.linkedin_credential import LinkedInCredential

logger = logging.getLogger(__name__)


class LinkedInConnectionService:
    """
    Manages LinkedIn connection via Unipile hosted auth.

    Key Benefits over HeyReach:
    - No credential storage (improved security)
    - No 2FA handling (Unipile manages this)
    - Higher rate limits (80-100 vs 17/day)
    - 70-85% cost reduction

    Flow:
    1. User clicks "Connect LinkedIn"
    2. Generate Unipile hosted auth URL
    3. Redirect user to Unipile
    4. Unipile sends webhook with account_id
    5. Store account_id (no credentials!)
    """

    def __init__(self):
        """Initialize with Unipile client."""
        self._unipile = None

    @property
    def unipile(self):
        """Get Unipile client lazily."""
        if self._unipile is None:
            self._unipile = get_unipile_client()
        return self._unipile

    async def get_connect_url(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict:
        """
        Generate Unipile hosted auth URL for LinkedIn connection.

        This replaces the email/password flow. User is redirected to
        Unipile's hosted login page, which handles all auth including 2FA.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Dict with auth_url for redirect
        """
        # Create or update credential record with pending status
        credential = await self.get_credential(db, client_id)

        if not credential:
            credential = LinkedInCredential(
                client_id=client_id,
                connection_status="pending",
                auth_method="hosted",
            )
            db.add(credential)
        else:
            credential.connection_status = "pending"
            credential.auth_method = "hosted"
            credential.last_error = None

        await db.commit()
        await db.refresh(credential)

        # Determine redirect URLs based on environment
        frontend_url = settings.frontend_url
        api_url = settings.base_url

        try:
            # Generate hosted auth URL from Unipile
            result = await self.unipile.create_hosted_auth_link(
                providers=["LINKEDIN"],
                success_redirect_url=f"{frontend_url}/onboarding/linkedin/success",
                failure_redirect_url=f"{frontend_url}/onboarding/linkedin/failed",
                notify_url=f"{api_url}/api/v1/webhooks/unipile/account",
                name=str(client_id),  # Used to match webhook callback
                expiresOn=24 * 60,  # 24 hours in minutes
            )

            auth_url = result.get("url")
            if not auth_url:
                raise ValueError("Failed to generate auth URL from Unipile")

            logger.info(f"Generated Unipile auth URL for client {client_id}")
            return {
                "auth_url": auth_url,
                "status": "pending",
                "message": "Redirect user to auth_url to connect LinkedIn",
            }

        except Exception as e:
            credential.connection_status = "failed"
            credential.last_error = str(e)
            credential.error_count = (credential.error_count or 0) + 1
            credential.last_error_at = datetime.utcnow()
            await db.commit()

            logger.exception(f"Failed to generate Unipile auth URL for client {client_id}")
            raise

    async def handle_connection_webhook(
        self,
        db: AsyncSession,
        payload: dict,
    ) -> dict:
        """
        Handle Unipile account connection webhook.

        Called when user completes LinkedIn auth via Unipile hosted flow.

        Args:
            db: Database session
            payload: Unipile webhook payload

        Returns:
            Dict with processing result
        """
        # Extract data from webhook
        status = payload.get("status")
        account_id = payload.get("account_id")
        client_id_str = payload.get("name")  # We passed client_id as name

        if not client_id_str:
            logger.warning("Unipile webhook missing client_id (name field)")
            return {"status": "ignored", "reason": "missing_client_id"}

        try:
            client_id = UUID(client_id_str)
        except ValueError:
            logger.warning(f"Invalid client_id in Unipile webhook: {client_id_str}")
            return {"status": "ignored", "reason": "invalid_client_id"}

        # Get credential record
        credential = await self.get_credential(db, client_id)
        if not credential:
            logger.warning(f"No credential record for client {client_id}")
            return {"status": "ignored", "reason": "credential_not_found"}

        if status == "CREATION_SUCCESS":
            # Get account details from Unipile
            try:
                account_info = await self.unipile.get_account(account_id)

                credential.connection_status = "connected"
                credential.unipile_account_id = account_id
                credential.auth_method = "hosted"
                credential.linkedin_profile_url = account_info.get("identifier")
                credential.linkedin_profile_name = account_info.get("name")
                credential.connected_at = datetime.utcnow()
                credential.last_error = None
                credential.error_count = 0

                await db.commit()

                logger.info(f"LinkedIn connected via Unipile for client {client_id}")
                return {
                    "status": "connected",
                    "account_id": account_id,
                    "client_id": str(client_id),
                }

            except Exception as e:
                logger.exception(f"Failed to get Unipile account details: {e}")
                # Still mark as connected since webhook said success
                credential.connection_status = "connected"
                credential.unipile_account_id = account_id
                credential.auth_method = "hosted"
                credential.connected_at = datetime.utcnow()
                await db.commit()

                return {
                    "status": "connected",
                    "account_id": account_id,
                    "warning": "Could not fetch account details",
                }

        elif status in ("CREATION_FAILED", "DISCONNECTED"):
            credential.connection_status = (
                "failed" if status == "CREATION_FAILED" else "disconnected"
            )
            credential.last_error = payload.get("error") or payload.get("reason") or status
            credential.last_error_at = datetime.utcnow()
            await db.commit()

            logger.warning(f"LinkedIn connection {status.lower()} for client {client_id}")
            return {
                "status": status.lower(),
                "client_id": str(client_id),
                "error": credential.last_error,
            }

        else:
            logger.info(f"Unipile webhook with status {status} for client {client_id}")
            return {"status": "acknowledged", "webhook_status": status}

    async def _mark_connected(
        self,
        db: AsyncSession,
        credential: LinkedInCredential,
        result: dict,
    ) -> None:
        """
        Mark credential as connected with Unipile data.

        Args:
            db: Database session
            credential: LinkedInCredential instance
            result: Unipile API response with connection data
        """
        credential.connection_status = "connected"
        credential.unipile_account_id = result.get("account_id")
        credential.auth_method = "hosted"
        credential.linkedin_profile_url = result.get("profile_url") or result.get("identifier")
        credential.linkedin_profile_name = result.get("profile_name") or result.get("name")
        credential.linkedin_headline = result.get("headline")
        credential.linkedin_connection_count = result.get("connection_count")
        credential.connected_at = datetime.utcnow()
        credential.last_error = None
        await db.commit()

    async def get_credential(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> LinkedInCredential | None:
        """
        Get LinkedIn credential for client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            LinkedInCredential or None
        """
        stmt = select(LinkedInCredential).where(LinkedInCredential.client_id == client_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_status(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict:
        """
        Get connection status for client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Status dict with connection info
        """
        credential = await self.get_credential(db, client_id)

        if not credential:
            return {"status": "not_connected"}

        return {
            "status": credential.connection_status,
            "auth_method": credential.auth_method or "hosted",
            "profile_url": credential.linkedin_profile_url,
            "profile_name": credential.linkedin_profile_name,
            "headline": credential.linkedin_headline,
            "connection_count": credential.linkedin_connection_count,
            "connected_at": (
                credential.connected_at.isoformat() if credential.connected_at else None
            ),
            "error": (credential.last_error if credential.connection_status == "failed" else None),
        }

    async def disconnect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict:
        """
        Disconnect LinkedIn account.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Status dict

        Raises:
            ValueError: If no LinkedIn connection found
        """
        credential = await self.get_credential(db, client_id)

        if not credential:
            raise ValueError("No LinkedIn connection found")

        # Remove from Unipile if connected
        if credential.unipile_account_id:
            try:
                await self.unipile.disconnect_account(credential.unipile_account_id)
                logger.info(
                    f"Disconnected LinkedIn account {credential.unipile_account_id} from Unipile"
                )
            except Exception as e:
                # Log but don't fail - still disconnect locally
                logger.warning(f"Failed to disconnect from Unipile: {e}")

        credential.connection_status = "disconnected"
        credential.unipile_account_id = None
        credential.disconnected_at = datetime.utcnow()
        await db.commit()

        logger.info(f"LinkedIn disconnected for client {client_id}")
        return {"status": "disconnected"}

    async def get_account_id(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> str | None:
        """
        Get Unipile account ID for a connected client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Unipile account ID or None if not connected
        """
        credential = await self.get_credential(db, client_id)

        if credential and credential.is_connected:
            return credential.unipile_account_id

        return None

    async def refresh_account_status(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict:
        """
        Refresh LinkedIn account status from Unipile.

        Useful to check if account needs re-authentication.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Updated status dict
        """
        credential = await self.get_credential(db, client_id)

        if not credential or not credential.unipile_account_id:
            return {"status": "not_connected"}

        try:
            account_info = await self.unipile.get_account(credential.unipile_account_id)
            account_status = account_info.get("status", "").upper()

            # Map Unipile status to our status
            if account_status == "OK":
                credential.connection_status = "connected"
            elif account_status == "CREDENTIALS_REQUIRED":
                credential.connection_status = "credentials_required"
            elif account_status == "DISCONNECTED":
                credential.connection_status = "disconnected"
            else:
                # Unknown status, keep current
                pass

            # Update profile info if available
            if account_info.get("name"):
                credential.linkedin_profile_name = account_info["name"]
            if account_info.get("identifier"):
                credential.linkedin_profile_url = account_info["identifier"]

            await db.commit()

            return await self.get_status(db, client_id)

        except Exception as e:
            logger.exception(f"Failed to refresh account status: {e}")
            return {
                "status": credential.connection_status,
                "error": f"Failed to refresh: {str(e)}",
            }


# Singleton instance
linkedin_connection_service = LinkedInConnectionService()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Unipile hosted auth flow (no credentials stored)
# [x] No 2FA handling (Unipile manages this)
# [x] Webhook handler for connection callbacks
# [x] Mark connected helper
# [x] Get status method
# [x] Disconnect method (removes from Unipile)
# [x] Get account ID method
# [x] Refresh account status method
# [x] Error tracking
# [x] Logging throughout
# [x] Type hints on all methods
# [x] Docstrings on all methods
