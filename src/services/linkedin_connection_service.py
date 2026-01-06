"""
Contract: src/services/linkedin_connection_service.py
Purpose: Manage LinkedIn credential storage and HeyReach connection
Layer: 3 - services
Imports: models, integrations, utils
Consumers: API routes

Phase: 24H - LinkedIn Credential Connection
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.linkedin_credential import LinkedInCredential
from src.utils.encryption import decrypt_credential, encrypt_credential
from src.integrations.heyreach import get_heyreach_client

logger = logging.getLogger(__name__)


class LinkedInConnectionService:
    """
    Manages LinkedIn credential storage and HeyReach connection.

    Handles:
    - Encrypting and storing LinkedIn credentials
    - Initiating connection to HeyReach
    - 2FA flow handling
    - Connection status management
    - Disconnection
    """

    async def start_connection(
        self,
        db: AsyncSession,
        client_id: UUID,
        linkedin_email: str,
        linkedin_password: str,
    ) -> dict:
        """
        Start LinkedIn connection process.

        1. Encrypt and store credentials
        2. Call HeyReach API to add sender
        3. Return status (connected, awaiting_2fa, or error)

        Args:
            db: Database session
            client_id: Client UUID
            linkedin_email: LinkedIn account email
            linkedin_password: LinkedIn account password

        Returns:
            Dict with status and relevant data
        """
        # Encrypt credentials
        email_encrypted = encrypt_credential(linkedin_email)
        password_encrypted = encrypt_credential(linkedin_password)

        # Check if record exists
        existing = await self.get_credential(db, client_id)

        if existing:
            # Update existing record
            existing.linkedin_email_encrypted = email_encrypted
            existing.linkedin_password_encrypted = password_encrypted
            existing.connection_status = "connecting"
            existing.last_error = None
            existing.error_count = 0
            credential = existing
        else:
            # Create new record
            credential = LinkedInCredential(
                client_id=client_id,
                linkedin_email_encrypted=email_encrypted,
                linkedin_password_encrypted=password_encrypted,
                connection_status="connecting",
            )
            db.add(credential)

        await db.commit()
        await db.refresh(credential)

        # Attempt HeyReach connection
        try:
            heyreach = get_heyreach_client()
            result = await heyreach.add_linkedin_account(
                email=linkedin_email,
                password=linkedin_password,
            )

            if result.get("requires_2fa"):
                credential.connection_status = "awaiting_2fa"
                credential.two_fa_method = result.get("2fa_method", "unknown")
                credential.two_fa_requested_at = datetime.utcnow()
                await db.commit()

                logger.info(f"LinkedIn 2FA required for client {client_id}")
                return {
                    "status": "awaiting_2fa",
                    "method": result.get("2fa_method"),
                    "message": "Please enter the verification code sent to you",
                }

            elif result.get("success"):
                await self._mark_connected(db, credential, result)

                logger.info(f"LinkedIn connected for client {client_id}")
                return {
                    "status": "connected",
                    "profile_url": result.get("profile_url"),
                    "profile_name": result.get("profile_name"),
                }

            else:
                credential.connection_status = "failed"
                credential.last_error = result.get("error", "Unknown error")
                credential.error_count += 1
                credential.last_error_at = datetime.utcnow()
                await db.commit()

                logger.warning(
                    f"LinkedIn connection failed for client {client_id}: {credential.last_error}"
                )
                return {
                    "status": "failed",
                    "error": result.get("error"),
                }

        except Exception as e:
            credential.connection_status = "failed"
            credential.last_error = str(e)
            credential.error_count += 1
            credential.last_error_at = datetime.utcnow()
            await db.commit()

            logger.exception(f"LinkedIn connection error for client {client_id}")
            raise

    async def submit_2fa_code(
        self,
        db: AsyncSession,
        client_id: UUID,
        code: str,
    ) -> dict:
        """
        Submit 2FA verification code.

        Args:
            db: Database session
            client_id: Client UUID
            code: 2FA verification code

        Returns:
            Dict with status

        Raises:
            ValueError: If no pending 2FA verification
        """
        credential = await self.get_credential(db, client_id)

        if not credential or credential.connection_status != "awaiting_2fa":
            raise ValueError("No pending 2FA verification")

        # Decrypt credentials to resubmit with 2FA
        email = decrypt_credential(credential.linkedin_email_encrypted)
        password = decrypt_credential(credential.linkedin_password_encrypted)

        try:
            heyreach = get_heyreach_client()
            result = await heyreach.verify_2fa(
                email=email,
                password=password,
                code=code,
            )

            if result.get("success"):
                await self._mark_connected(db, credential, result)

                logger.info(f"LinkedIn 2FA verified for client {client_id}")
                return {"status": "connected"}

            else:
                credential.last_error = result.get("error", "Invalid code")
                credential.error_count += 1
                credential.last_error_at = datetime.utcnow()
                await db.commit()

                logger.warning(
                    f"LinkedIn 2FA verification failed for client {client_id}"
                )
                return {
                    "status": "failed",
                    "error": result.get("error", "Invalid verification code"),
                }

        except Exception as e:
            credential.last_error = str(e)
            credential.error_count += 1
            credential.last_error_at = datetime.utcnow()
            await db.commit()

            logger.exception(f"LinkedIn 2FA error for client {client_id}")
            raise

    async def _mark_connected(
        self,
        db: AsyncSession,
        credential: LinkedInCredential,
        result: dict,
    ) -> None:
        """
        Mark credential as connected with HeyReach data.

        Args:
            db: Database session
            credential: LinkedInCredential instance
            result: HeyReach API response with connection data
        """
        credential.connection_status = "connected"
        credential.heyreach_sender_id = result.get("sender_id")
        credential.heyreach_account_id = result.get("account_id")
        credential.linkedin_profile_url = result.get("profile_url")
        credential.linkedin_profile_name = result.get("profile_name")
        credential.linkedin_headline = result.get("headline")
        credential.linkedin_connection_count = result.get("connection_count")
        credential.connected_at = datetime.utcnow()
        credential.last_error = None
        credential.two_fa_method = None
        credential.two_fa_requested_at = None
        await db.commit()

    async def get_credential(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> Optional[LinkedInCredential]:
        """
        Get LinkedIn credential for client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            LinkedInCredential or None
        """
        stmt = select(LinkedInCredential).where(
            LinkedInCredential.client_id == client_id
        )
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
            "profile_url": credential.linkedin_profile_url,
            "profile_name": credential.linkedin_profile_name,
            "headline": credential.linkedin_headline,
            "connection_count": credential.linkedin_connection_count,
            "connected_at": (
                credential.connected_at.isoformat()
                if credential.connected_at
                else None
            ),
            "error": (
                credential.last_error
                if credential.connection_status == "failed"
                else None
            ),
            "two_fa_method": (
                credential.two_fa_method
                if credential.connection_status == "awaiting_2fa"
                else None
            ),
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

        # Remove from HeyReach if connected
        if credential.heyreach_sender_id:
            try:
                heyreach = get_heyreach_client()
                await heyreach.remove_sender(credential.heyreach_sender_id)
                logger.info(
                    f"Removed LinkedIn sender {credential.heyreach_sender_id} from HeyReach"
                )
            except Exception as e:
                # Log but don't fail - still disconnect locally
                logger.warning(f"Failed to remove from HeyReach: {e}")

        credential.connection_status = "disconnected"
        credential.heyreach_sender_id = None
        credential.heyreach_account_id = None
        credential.disconnected_at = datetime.utcnow()
        await db.commit()

        logger.info(f"LinkedIn disconnected for client {client_id}")
        return {"status": "disconnected"}

    async def get_sender_id(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> Optional[str]:
        """
        Get HeyReach sender ID for a connected client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            HeyReach sender ID or None if not connected
        """
        credential = await self.get_credential(db, client_id)

        if credential and credential.is_connected:
            return credential.heyreach_sender_id

        return None


# Singleton instance
linkedin_connection_service = LinkedInConnectionService()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Credential encryption on save
# [x] Credential decryption for HeyReach
# [x] HeyReach connection flow
# [x] 2FA handling
# [x] Mark connected helper
# [x] Get status method
# [x] Disconnect method
# [x] Error tracking
# [x] Logging throughout
# [x] Type hints on all methods
# [x] Docstrings on all methods
