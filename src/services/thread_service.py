"""
Contract: src/services/thread_service.py
Purpose: Service for managing conversation threads
Layer: 3 - services
Imports: models, exceptions
Consumers: orchestration, API routes, closer engine

FILE: src/services/thread_service.py
PURPOSE: Service for managing conversation threads
PHASE: 24D (Conversation Threading)
TASK: THREAD-002
DEPENDENCIES:
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes, closer engine

This service manages conversation threads between the platform
and leads, tracking messages, sentiment, objections, and outcomes.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError


class ThreadService:
    """
    Service for managing conversation threads.

    Tracks all back-and-forth communication with leads,
    enabling CIS to learn from conversation patterns.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Thread service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create_thread(
        self,
        client_id: UUID,
        lead_id: UUID,
        channel: str,
        campaign_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Create a new conversation thread.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID
            channel: Channel type (email, sms, linkedin)
            campaign_id: Optional campaign UUID

        Returns:
            Created thread record
        """
        query = text("""
            INSERT INTO conversation_threads (
                client_id, lead_id, campaign_id, channel,
                status, started_at, created_at, updated_at
            ) VALUES (
                :client_id, :lead_id, :campaign_id, :channel,
                'active', NOW(), NOW(), NOW()
            )
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "lead_id": lead_id,
            "campaign_id": campaign_id,
            "channel": channel,
        })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}
        return dict(row._mapping)

    async def get_by_id(self, thread_id: UUID) -> dict[str, Any] | None:
        """
        Get a thread by ID.

        Args:
            thread_id: Thread UUID

        Returns:
            Thread record or None if not found
        """
        query = text("""
            SELECT * FROM conversation_threads WHERE id = :thread_id
        """)

        result = await self.session.execute(query, {"thread_id": thread_id})
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def get_or_create_for_lead(
        self,
        client_id: UUID,
        lead_id: UUID,
        channel: str,
        campaign_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Get existing active thread or create a new one.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID
            channel: Channel type
            campaign_id: Optional campaign UUID

        Returns:
            Thread record
        """
        # Look for active thread
        query = text("""
            SELECT * FROM conversation_threads
            WHERE client_id = :client_id
            AND lead_id = :lead_id
            AND channel = :channel
            AND status IN ('active', 'stale')
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "lead_id": lead_id,
            "channel": channel,
        })
        row = result.fetchone()

        if row:
            # Reactivate if stale
            thread = dict(row._mapping)
            if thread["status"] == "stale":
                await self.update_status(thread["id"], "active")
                thread["status"] = "active"
            return thread

        # Create new thread
        return await self.create_thread(
            client_id=client_id,
            lead_id=lead_id,
            channel=channel,
            campaign_id=campaign_id,
        )

    async def add_message(
        self,
        thread_id: UUID,
        direction: str,
        content: str,
        sent_at: datetime | None = None,
        activity_id: UUID | None = None,
        reply_id: UUID | None = None,
        sentiment: str | None = None,
        sentiment_score: float | None = None,
        intent: str | None = None,
        objection_type: str | None = None,
        question_extracted: str | None = None,
        topics_mentioned: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Add a message to a thread.

        Args:
            thread_id: Thread UUID
            direction: 'outbound' (us) or 'inbound' (them)
            content: Message content
            sent_at: When message was sent
            activity_id: Link to activity (for outbound)
            reply_id: Link to reply (for inbound)
            sentiment: Message sentiment
            sentiment_score: Sentiment score (-1 to 1)
            intent: Detected intent
            objection_type: Type of objection raised
            question_extracted: Question asked
            topics_mentioned: Topics in the message

        Returns:
            Created message record
        """
        if direction not in ("outbound", "inbound"):
            raise ValidationError(message="Direction must be 'outbound' or 'inbound'")

        # Get next position
        pos_query = text("""
            SELECT COALESCE(MAX(position), 0) + 1 as next_pos
            FROM thread_messages WHERE thread_id = :thread_id
        """)
        pos_result = await self.session.execute(pos_query, {"thread_id": thread_id})
        pos_row = pos_result.fetchone()
        next_position = pos_row.next_pos if pos_row else 1

        query = text("""
            INSERT INTO thread_messages (
                thread_id, activity_id, reply_id, direction,
                content, content_preview, sent_at, position,
                sentiment, sentiment_score, intent,
                objection_type, question_extracted, topics_mentioned,
                created_at
            ) VALUES (
                :thread_id, :activity_id, :reply_id, :direction,
                :content, :content_preview, :sent_at, :position,
                :sentiment, :sentiment_score, :intent,
                :objection_type, :question_extracted, :topics_mentioned,
                NOW()
            )
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "thread_id": thread_id,
            "activity_id": activity_id,
            "reply_id": reply_id,
            "direction": direction,
            "content": content,
            "content_preview": content[:200] if len(content) > 200 else content,
            "sent_at": sent_at or datetime.utcnow(),
            "position": next_position,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "intent": intent,
            "objection_type": objection_type,
            "question_extracted": question_extracted,
            "topics_mentioned": topics_mentioned,
        })

        row = result.fetchone()
        await self.session.commit()

        if not row:
            return {}
        return dict(row._mapping)

    async def update_status(
        self,
        thread_id: UUID,
        status: str,
    ) -> dict[str, Any]:
        """
        Update thread status.

        Args:
            thread_id: Thread UUID
            status: New status (active, resolved, stale, converted, dead)

        Returns:
            Updated thread record
        """
        valid_statuses = ["active", "resolved", "stale", "converted", "dead"]
        if status not in valid_statuses:
            raise ValidationError(message=f"Invalid status. Must be one of: {valid_statuses}")

        query = text("""
            UPDATE conversation_threads
            SET status = :status, updated_at = NOW()
            WHERE id = :thread_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "thread_id": thread_id,
            "status": status,
        })

        row = result.fetchone()
        if not row:
            raise NotFoundError(resource_type="thread", resource_id=str(thread_id))

        await self.session.commit()
        return dict(row._mapping)

    async def set_outcome(
        self,
        thread_id: UUID,
        outcome: str,
        outcome_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Set the outcome of a thread.

        Args:
            thread_id: Thread UUID
            outcome: Outcome type
            outcome_reason: Optional reason details

        Returns:
            Updated thread record
        """
        valid_outcomes = [
            "converted", "rejected", "no_response", "ongoing",
            "meeting_booked", "referral", "future_interest"
        ]
        if outcome not in valid_outcomes:
            raise ValidationError(message=f"Invalid outcome. Must be one of: {valid_outcomes}")

        # Determine status based on outcome
        status = "resolved" if outcome in ("converted", "rejected", "meeting_booked") else "active"
        if outcome == "converted" or outcome == "meeting_booked":
            status = "converted"

        query = text("""
            UPDATE conversation_threads
            SET outcome = :outcome,
                outcome_at = NOW(),
                outcome_reason = :outcome_reason,
                status = :status,
                updated_at = NOW()
            WHERE id = :thread_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "thread_id": thread_id,
            "outcome": outcome,
            "outcome_reason": outcome_reason,
            "status": status,
        })

        row = result.fetchone()
        if not row:
            raise NotFoundError(resource_type="thread", resource_id=str(thread_id))

        await self.session.commit()
        return dict(row._mapping)

    async def mark_escalated(
        self,
        thread_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """
        Mark a thread as escalated to human.

        Args:
            thread_id: Thread UUID
            reason: Reason for escalation

        Returns:
            Updated thread record
        """
        query = text("""
            UPDATE conversation_threads
            SET escalated_to_human = TRUE,
                escalated_at = NOW(),
                escalation_reason = :reason,
                updated_at = NOW()
            WHERE id = :thread_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "thread_id": thread_id,
            "reason": reason,
        })

        row = result.fetchone()
        if not row:
            raise NotFoundError(resource_type="thread", resource_id=str(thread_id))

        await self.session.commit()
        return dict(row._mapping)

    async def get_thread_messages(
        self,
        thread_id: UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get all messages in a thread.

        Args:
            thread_id: Thread UUID
            limit: Max messages to return

        Returns:
            List of message records ordered by position
        """
        query = text("""
            SELECT * FROM thread_messages
            WHERE thread_id = :thread_id
            ORDER BY position ASC
            LIMIT :limit
        """)

        result = await self.session.execute(query, {
            "thread_id": thread_id,
            "limit": limit,
        })

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def get_lead_threads(
        self,
        lead_id: UUID,
        client_id: UUID | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get all threads for a lead.

        Args:
            lead_id: Lead UUID
            client_id: Optional client filter
            limit: Max threads to return

        Returns:
            List of thread records
        """
        if client_id:
            query = text("""
                SELECT * FROM conversation_threads
                WHERE lead_id = :lead_id AND client_id = :client_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            result = await self.session.execute(query, {
                "lead_id": lead_id,
                "client_id": client_id,
                "limit": limit,
            })
        else:
            query = text("""
                SELECT * FROM conversation_threads
                WHERE lead_id = :lead_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            result = await self.session.execute(query, {
                "lead_id": lead_id,
                "limit": limit,
            })

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def get_client_threads(
        self,
        client_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get threads for a client.

        Args:
            client_id: Client UUID
            status: Optional status filter
            limit: Max threads to return
            offset: Pagination offset

        Returns:
            List of thread records
        """
        if status:
            query = text("""
                SELECT * FROM conversation_threads
                WHERE client_id = :client_id AND status = :status
                ORDER BY last_message_at DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
            result = await self.session.execute(query, {
                "client_id": client_id,
                "status": status,
                "limit": limit,
                "offset": offset,
            })
        else:
            query = text("""
                SELECT * FROM conversation_threads
                WHERE client_id = :client_id
                ORDER BY last_message_at DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
            result = await self.session.execute(query, {
                "client_id": client_id,
                "limit": limit,
                "offset": offset,
            })

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def get_analytics(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get conversation analytics for a client.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Analytics data
        """
        query = text("""
            SELECT * FROM get_conversation_analytics(:client_id, :days)
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
        })

        row = result.fetchone()
        if not row:
            return {
                "total_threads": 0,
                "active_threads": 0,
                "converted_threads": 0,
                "rejected_threads": 0,
                "avg_messages_per_thread": 0,
                "avg_our_response_minutes": 0,
                "avg_their_response_minutes": 0,
                "conversion_rate": 0,
                "top_objections": {},
                "sentiment_distribution": {},
            }

        return dict(row._mapping)

    async def get_common_questions(
        self,
        client_id: UUID,
        days: int = 90,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get common questions asked by leads.

        Args:
            client_id: Client UUID
            days: Number of days to analyze
            limit: Max questions to return

        Returns:
            List of common questions with frequency
        """
        query = text("""
            SELECT * FROM get_common_questions(:client_id, :days, :limit)
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
            "limit": limit,
        })

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] No imports from engines/integrations/orchestration
# [x] Thread CRUD operations
# [x] Message management
# [x] Status and outcome tracking
# [x] Escalation tracking
# [x] Thread retrieval by lead/client
# [x] Analytics integration
# [x] Common questions retrieval
# [x] All functions have type hints
# [x] All functions have docstrings
