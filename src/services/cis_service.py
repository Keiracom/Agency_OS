"""
Contract: src/services/cis_service.py
Purpose: CIS (Conversion Intelligence System) data collection service
Layer: 3 - services
Imports: integrations
Consumers: orchestration flows, engines

FILE: src/services/cis_service.py
PURPOSE: Wire CIS tables to live campaign data for machine learning
PHASE: Step 7/8 (CIS Tables)
TASK: STEP7-CIS
DEPENDENCIES:
  - supabase/migrations/061_cis_schema.sql (CIS tables)
  - src/integrations/supabase.py
LAYER: 3 (services)
CONSUMERS: outreach_flow.py, reply_analyzer.py, closer engine

This service captures learning data to answer: "What works and why?"
Tables fed:
  - cis_outreach_outcomes: tracks sent → delivered → opened → clicked → replied → meeting → converted
  - cis_reply_classifications: detailed intent analysis from reply_analyzer.py
  - cis_channel_performance: per-campaign channel metrics
  - cis_als_tier_conversions: ALS tier → conversion correlation
  - cis_message_patterns: which hooks/templates work
  - cis_agency_learnings: monthly per-agency summary
"""

import hashlib
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


class CISService:
    """
    Conversion Intelligence System (CIS) data collection service.

    Records campaign outcomes and learnings to CIS tables for ML analysis.
    Month 1 metrics feed CIS → Month 2 campaigns suggested with improved targeting.
    """

    def __init__(self, session: AsyncSession | None = None):
        """
        Initialize CIS Service.

        Args:
            session: Optional async database session. If not provided,
                     methods will create their own session.
        """
        self._session = session

    async def _get_session(self) -> AsyncSession:
        """Get database session (use provided or create new)."""
        if self._session:
            return self._session
        # Caller must use context manager in this case
        raise ValueError("No session provided - use async with get_db_session()")

    # =========================================================================
    # A. OUTREACH OUTCOMES - Record each message sent through funnel
    # =========================================================================

    async def record_outreach_outcome(
        self,
        activity_id: UUID | str,
        lead_id: UUID | str,
        client_id: UUID | str,
        campaign_id: UUID | str | None,
        channel: str,
        sequence_step: int | None = None,
        als_score_at_send: int | None = None,
        als_tier_at_send: str | None = None,
        subject_line: str | None = None,
        hook_type: str | None = None,
        personalization_level: str = "basic",
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Record initial outreach outcome when a message is sent.

        Creates a row in cis_outreach_outcomes with sent_at timestamp.
        Updates happen later as delivery/open/click/reply events arrive.

        Args:
            activity_id: Activity UUID (links to activities table)
            lead_id: Lead UUID
            client_id: Client UUID
            campaign_id: Campaign UUID (optional)
            channel: Channel type (email, linkedin, sms, voice)
            sequence_step: Which step in sequence (1, 2, 3, etc.)
            als_score_at_send: Lead's ALS score at time of send
            als_tier_at_send: Lead's ALS tier at time of send (hot/warm/cool/cold/dead)
            subject_line: Email subject for pattern matching
            hook_type: Content hook type (pain_point, social_proof, question, etc.)
            personalization_level: none, basic, deep, sdk_enhanced
            session: Optional database session

        Returns:
            Dict with outcome_id and success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._record_outreach_outcome_impl(
                    db,
                    activity_id,
                    lead_id,
                    client_id,
                    campaign_id,
                    channel,
                    sequence_step,
                    als_score_at_send,
                    als_tier_at_send,
                    subject_line,
                    hook_type,
                    personalization_level,
                )
        return await self._record_outreach_outcome_impl(
            db,
            activity_id,
            lead_id,
            client_id,
            campaign_id,
            channel,
            sequence_step,
            als_score_at_send,
            als_tier_at_send,
            subject_line,
            hook_type,
            personalization_level,
        )

    async def _record_outreach_outcome_impl(
        self,
        db: AsyncSession,
        activity_id: UUID | str,
        lead_id: UUID | str,
        client_id: UUID | str,
        campaign_id: UUID | str | None,
        channel: str,
        sequence_step: int | None,
        als_score_at_send: int | None,
        als_tier_at_send: str | None,
        subject_line: str | None,
        hook_type: str | None,
        personalization_level: str,
    ) -> dict[str, Any]:
        """Implementation of record_outreach_outcome."""
        try:
            # Hash subject line for pattern grouping
            subject_hash = None
            if subject_line:
                subject_hash = hashlib.md5(subject_line.lower().strip().encode()).hexdigest()[:16]

            query = text("""
                INSERT INTO cis_outreach_outcomes (
                    activity_id, lead_id, client_id, campaign_id, channel,
                    sequence_step, sent_at, als_score_at_send, als_tier_at_send,
                    subject_hash, hook_type, personalization_level,
                    created_at, updated_at
                ) VALUES (
                    :activity_id, :lead_id, :client_id, :campaign_id, :channel,
                    :sequence_step, NOW(), :als_score, :als_tier,
                    :subject_hash, :hook_type, :personalization_level,
                    NOW(), NOW()
                )
                RETURNING id
            """)

            result = await db.execute(
                query,
                {
                    "activity_id": str(activity_id),
                    "lead_id": str(lead_id),
                    "client_id": str(client_id),
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "channel": channel,
                    "sequence_step": sequence_step,
                    "als_score": als_score_at_send,
                    "als_tier": als_tier_at_send,
                    "subject_hash": subject_hash,
                    "hook_type": hook_type,
                    "personalization_level": personalization_level,
                },
            )
            row = result.fetchone()
            await db.commit()

            outcome_id = str(row.id) if row else None
            logger.info(f"CIS: Recorded outreach outcome {outcome_id} for activity {activity_id}")

            return {
                "success": True,
                "outcome_id": outcome_id,
                "activity_id": str(activity_id),
            }

        except Exception as e:
            logger.error(f"CIS: Failed to record outreach outcome: {e}")
            return {"success": False, "error": str(e)}

    async def update_outreach_outcome(
        self,
        activity_id: UUID | str,
        event_type: str,
        final_outcome: str | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Update outreach outcome when delivery/open/click/reply events occur.

        Args:
            activity_id: Activity UUID to update
            event_type: Event type (delivered, opened, clicked, replied, meeting_booked, converted)
            final_outcome: Final outcome classification (optional)
            session: Optional database session

        Returns:
            Dict with success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._update_outreach_outcome_impl(
                    db, activity_id, event_type, final_outcome
                )
        return await self._update_outreach_outcome_impl(db, activity_id, event_type, final_outcome)

    async def _update_outreach_outcome_impl(
        self,
        db: AsyncSession,
        activity_id: UUID | str,
        event_type: str,
        final_outcome: str | None,
    ) -> dict[str, Any]:
        """Implementation of update_outreach_outcome."""
        try:
            # Map event type to column
            event_column_map = {
                "delivered": "delivered_at",
                "opened": "opened_at",
                "clicked": "clicked_at",
                "replied": "replied_at",
                "meeting_booked": "meeting_booked_at",
                "converted": "converted_at",
            }

            column = event_column_map.get(event_type)
            if not column:
                return {"success": False, "error": f"Unknown event type: {event_type}"}

            # Build update query
            update_parts = [f"{column} = NOW()"]
            params: dict[str, Any] = {"activity_id": str(activity_id)}

            if final_outcome:
                update_parts.append("final_outcome = :final_outcome")
                params["final_outcome"] = final_outcome

            # Calculate time metrics for certain events
            if event_type == "opened":
                update_parts.append(
                    "time_to_open_minutes = EXTRACT(EPOCH FROM (NOW() - sent_at)) / 60"
                )
            elif event_type == "replied":
                update_parts.append(
                    "time_to_reply_minutes = EXTRACT(EPOCH FROM (NOW() - sent_at)) / 60"
                )
            elif event_type in ("meeting_booked", "converted"):
                update_parts.append("days_to_outcome = EXTRACT(DAY FROM (NOW() - sent_at))")

            update_parts.append("updated_at = NOW()")

            query = text(f"""
                UPDATE cis_outreach_outcomes
                SET {", ".join(update_parts)}
                WHERE activity_id = :activity_id
                RETURNING id
            """)

            result = await db.execute(query, params)
            row = result.fetchone()
            await db.commit()

            if row:
                logger.info(f"CIS: Updated outcome for activity {activity_id}: {event_type}")
                return {"success": True, "activity_id": str(activity_id)}
            else:
                logger.warning(f"CIS: No outcome found for activity {activity_id}")
                return {"success": False, "error": "Outcome not found"}

        except Exception as e:
            logger.error(f"CIS: Failed to update outreach outcome: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # B. REPLY CLASSIFICATIONS - Detailed intent analysis
    # =========================================================================

    async def record_reply_classification(
        self,
        reply_id: UUID | str,
        lead_id: UUID | str,
        client_id: UUID | str,
        primary_intent: str,
        intent_confidence: float = 0.0,
        objection_category: str | None = None,
        sentiment: str = "neutral",
        sentiment_score: float = 0.0,
        questions_asked: list[str] | None = None,
        topics_mentioned: list[str] | None = None,
        competitor_mentioned: str | None = None,
        timeline_mentioned: str | None = None,
        budget_mentioned: bool = False,
        is_substantive: bool = True,
        word_count: int | None = None,
        response_time_hours: float | None = None,
        classifier_version: str = "v1",
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Record detailed reply classification for CIS learning.

        Args:
            reply_id: Reply UUID
            lead_id: Lead UUID
            client_id: Client UUID
            primary_intent: Primary intent classification
            intent_confidence: Confidence score (0-1)
            objection_category: If objection, which type
            sentiment: positive, neutral, negative, mixed
            sentiment_score: -1 to 1 score
            questions_asked: List of questions in reply
            topics_mentioned: Key topics mentioned
            competitor_mentioned: Name of competitor if mentioned
            timeline_mentioned: Timeline reference (next_quarter, etc.)
            budget_mentioned: Whether budget was mentioned
            is_substantive: True if substantive (not one-word)
            word_count: Number of words in reply
            response_time_hours: Hours since our message
            classifier_version: Version of classifier used
            session: Optional database session

        Returns:
            Dict with classification_id and success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._record_reply_classification_impl(
                    db,
                    reply_id,
                    lead_id,
                    client_id,
                    primary_intent,
                    intent_confidence,
                    objection_category,
                    sentiment,
                    sentiment_score,
                    questions_asked,
                    topics_mentioned,
                    competitor_mentioned,
                    timeline_mentioned,
                    budget_mentioned,
                    is_substantive,
                    word_count,
                    response_time_hours,
                    classifier_version,
                )
        return await self._record_reply_classification_impl(
            db,
            reply_id,
            lead_id,
            client_id,
            primary_intent,
            intent_confidence,
            objection_category,
            sentiment,
            sentiment_score,
            questions_asked,
            topics_mentioned,
            competitor_mentioned,
            timeline_mentioned,
            budget_mentioned,
            is_substantive,
            word_count,
            response_time_hours,
            classifier_version,
        )

    async def _record_reply_classification_impl(
        self,
        db: AsyncSession,
        reply_id: UUID | str,
        lead_id: UUID | str,
        client_id: UUID | str,
        primary_intent: str,
        intent_confidence: float,
        objection_category: str | None,
        sentiment: str,
        sentiment_score: float,
        questions_asked: list[str] | None,
        topics_mentioned: list[str] | None,
        competitor_mentioned: str | None,
        timeline_mentioned: str | None,
        budget_mentioned: bool,
        is_substantive: bool,
        word_count: int | None,
        response_time_hours: float | None,
        classifier_version: str,
    ) -> dict[str, Any]:
        """Implementation of record_reply_classification."""
        try:
            query = text("""
                INSERT INTO cis_reply_classifications (
                    reply_id, lead_id, client_id,
                    primary_intent, intent_confidence,
                    objection_category, sentiment, sentiment_score,
                    questions_asked, topics_mentioned,
                    competitor_mentioned, timeline_mentioned, budget_mentioned,
                    is_substantive, word_count, response_time_hours,
                    classifier_version, classified_at, created_at
                ) VALUES (
                    :reply_id, :lead_id, :client_id,
                    :primary_intent, :intent_confidence,
                    :objection_category, :sentiment, :sentiment_score,
                    :questions_asked, :topics_mentioned,
                    :competitor_mentioned, :timeline_mentioned, :budget_mentioned,
                    :is_substantive, :word_count, :response_time_hours,
                    :classifier_version, NOW(), NOW()
                )
                ON CONFLICT (reply_id) DO UPDATE SET
                    primary_intent = EXCLUDED.primary_intent,
                    intent_confidence = EXCLUDED.intent_confidence,
                    objection_category = EXCLUDED.objection_category,
                    sentiment = EXCLUDED.sentiment,
                    sentiment_score = EXCLUDED.sentiment_score,
                    questions_asked = EXCLUDED.questions_asked,
                    topics_mentioned = EXCLUDED.topics_mentioned,
                    competitor_mentioned = EXCLUDED.competitor_mentioned,
                    timeline_mentioned = EXCLUDED.timeline_mentioned,
                    budget_mentioned = EXCLUDED.budget_mentioned,
                    is_substantive = EXCLUDED.is_substantive,
                    word_count = EXCLUDED.word_count,
                    response_time_hours = EXCLUDED.response_time_hours,
                    classifier_version = EXCLUDED.classifier_version,
                    classified_at = NOW()
                RETURNING id
            """)

            result = await db.execute(
                query,
                {
                    "reply_id": str(reply_id),
                    "lead_id": str(lead_id),
                    "client_id": str(client_id),
                    "primary_intent": primary_intent,
                    "intent_confidence": intent_confidence,
                    "objection_category": objection_category,
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                    "questions_asked": questions_asked or [],
                    "topics_mentioned": topics_mentioned or [],
                    "competitor_mentioned": competitor_mentioned,
                    "timeline_mentioned": timeline_mentioned,
                    "budget_mentioned": budget_mentioned,
                    "is_substantive": is_substantive,
                    "word_count": word_count,
                    "response_time_hours": response_time_hours,
                    "classifier_version": classifier_version,
                },
            )
            row = result.fetchone()
            await db.commit()

            classification_id = str(row.id) if row else None
            logger.info(
                f"CIS: Recorded reply classification {classification_id} for reply {reply_id}"
            )

            return {
                "success": True,
                "classification_id": classification_id,
                "reply_id": str(reply_id),
            }

        except Exception as e:
            logger.error(f"CIS: Failed to record reply classification: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # C. CHANNEL PERFORMANCE - Aggregated metrics
    # =========================================================================

    async def update_channel_performance(
        self,
        client_id: UUID | str,
        campaign_id: UUID | str | None,
        channel: str,
        messages_sent: int = 0,
        replies: int = 0,
        positive_replies: int = 0,
        meetings_booked: int = 0,
        conversions: int = 0,
        cost_aud: float = 0.0,
        date: datetime | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Update or insert channel performance metrics.

        Uses the existing refresh_cis_channel_performance function or
        direct upsert for real-time updates.

        Args:
            client_id: Client UUID
            campaign_id: Campaign UUID (optional)
            channel: Channel type
            messages_sent: Number of messages sent
            replies: Number of replies received
            positive_replies: Number of positive replies
            meetings_booked: Number of meetings booked
            conversions: Number of conversions
            cost_aud: Total cost in AUD
            date: Date for metrics (defaults to today)
            session: Optional database session

        Returns:
            Dict with success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._update_channel_performance_impl(
                    db,
                    client_id,
                    campaign_id,
                    channel,
                    messages_sent,
                    replies,
                    positive_replies,
                    meetings_booked,
                    conversions,
                    cost_aud,
                    date,
                )
        return await self._update_channel_performance_impl(
            db,
            client_id,
            campaign_id,
            channel,
            messages_sent,
            replies,
            positive_replies,
            meetings_booked,
            conversions,
            cost_aud,
            date,
        )

    async def _update_channel_performance_impl(
        self,
        db: AsyncSession,
        client_id: UUID | str,
        campaign_id: UUID | str | None,
        channel: str,
        messages_sent: int,
        replies: int,
        positive_replies: int,
        meetings_booked: int,
        conversions: int,
        cost_aud: float,
        date: datetime | None,
    ) -> dict[str, Any]:
        """Implementation of update_channel_performance."""
        try:
            target_date = date or datetime.utcnow()

            # Calculate rates
            delivery_rate = 1.0 if messages_sent > 0 else 0  # Assume all delivered for now
            reply_rate = replies / messages_sent if messages_sent > 0 else 0
            positive_reply_rate = positive_replies / replies if replies > 0 else 0
            meeting_rate = meetings_booked / messages_sent if messages_sent > 0 else 0
            conversion_rate = conversions / messages_sent if messages_sent > 0 else 0

            cost_per_reply = cost_aud / replies if replies > 0 else None
            cost_per_meeting = cost_aud / meetings_booked if meetings_booked > 0 else None

            query = text("""
                INSERT INTO cis_channel_performance (
                    client_id, campaign_id, channel, date,
                    sends, deliveries, replies, positive_replies,
                    meetings_booked, conversions,
                    delivery_rate, reply_rate, positive_reply_rate,
                    meeting_rate, conversion_rate,
                    total_cost_aud, cost_per_reply_aud, cost_per_meeting_aud,
                    computed_at
                ) VALUES (
                    :client_id, :campaign_id, :channel, :date,
                    :sends, :sends, :replies, :positive_replies,
                    :meetings_booked, :conversions,
                    :delivery_rate, :reply_rate, :positive_reply_rate,
                    :meeting_rate, :conversion_rate,
                    :cost_aud, :cost_per_reply, :cost_per_meeting,
                    NOW()
                )
                ON CONFLICT (client_id, campaign_id, channel, date)
                DO UPDATE SET
                    sends = cis_channel_performance.sends + EXCLUDED.sends,
                    deliveries = cis_channel_performance.deliveries + EXCLUDED.deliveries,
                    replies = cis_channel_performance.replies + EXCLUDED.replies,
                    positive_replies = cis_channel_performance.positive_replies + EXCLUDED.positive_replies,
                    meetings_booked = cis_channel_performance.meetings_booked + EXCLUDED.meetings_booked,
                    conversions = cis_channel_performance.conversions + EXCLUDED.conversions,
                    total_cost_aud = cis_channel_performance.total_cost_aud + EXCLUDED.total_cost_aud,
                    computed_at = NOW()
                RETURNING id
            """)

            result = await db.execute(
                query,
                {
                    "client_id": str(client_id),
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "channel": channel,
                    "date": target_date.date(),
                    "sends": messages_sent,
                    "replies": replies,
                    "positive_replies": positive_replies,
                    "meetings_booked": meetings_booked,
                    "conversions": conversions,
                    "delivery_rate": delivery_rate,
                    "reply_rate": reply_rate,
                    "positive_reply_rate": positive_reply_rate,
                    "meeting_rate": meeting_rate,
                    "conversion_rate": conversion_rate,
                    "cost_aud": cost_aud,
                    "cost_per_reply": cost_per_reply,
                    "cost_per_meeting": cost_per_meeting,
                },
            )
            row = result.fetchone()
            await db.commit()

            logger.info(f"CIS: Updated channel performance for {client_id}/{channel}")
            return {"success": True, "id": str(row.id) if row else None}

        except Exception as e:
            logger.error(f"CIS: Failed to update channel performance: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # D. ALS TIER CONVERSIONS - Track which tiers convert
    # =========================================================================

    async def record_als_conversion(
        self,
        lead_id: UUID | str,
        client_id: UUID | str,
        als_score: int,
        als_tier: str,
        channel_that_converted: str,
        sequence_step_that_converted: int | None = None,
        conversion_type: str = "meeting_booked",
        campaign_id: UUID | str | None = None,
        touches_before_conversion: int | None = None,
        days_in_sequence: int | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Record ALS tier conversion when a meeting is booked or deal closes.

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            als_score: Lead's ALS score at conversion
            als_tier: Lead's ALS tier at conversion
            channel_that_converted: Channel that triggered conversion
            sequence_step_that_converted: Which step in sequence
            conversion_type: meeting_booked or deal_closed
            campaign_id: Campaign UUID (optional)
            touches_before_conversion: Number of touches before conversion
            days_in_sequence: Days lead was in sequence
            session: Optional database session

        Returns:
            Dict with conversion_id and success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._record_als_conversion_impl(
                    db,
                    lead_id,
                    client_id,
                    als_score,
                    als_tier,
                    channel_that_converted,
                    sequence_step_that_converted,
                    conversion_type,
                    campaign_id,
                    touches_before_conversion,
                    days_in_sequence,
                )
        return await self._record_als_conversion_impl(
            db,
            lead_id,
            client_id,
            als_score,
            als_tier,
            channel_that_converted,
            sequence_step_that_converted,
            conversion_type,
            campaign_id,
            touches_before_conversion,
            days_in_sequence,
        )

    async def _record_als_conversion_impl(
        self,
        db: AsyncSession,
        lead_id: UUID | str,
        client_id: UUID | str,
        als_score: int,
        als_tier: str,
        channel_that_converted: str,
        sequence_step_that_converted: int | None,
        conversion_type: str,
        campaign_id: UUID | str | None,
        touches_before_conversion: int | None,
        days_in_sequence: int | None,
    ) -> dict[str, Any]:
        """Implementation of record_als_conversion."""
        try:
            query = text("""
                INSERT INTO cis_als_tier_conversions (
                    client_id, campaign_id, lead_id, als_tier,
                    als_score_at_conversion, channel_that_converted,
                    sequence_step_that_converted, conversion_type,
                    touches_before_conversion, days_in_sequence,
                    converted_at, created_at
                ) VALUES (
                    :client_id, :campaign_id, :lead_id, :als_tier,
                    :als_score, :channel, :sequence_step, :conversion_type,
                    :touches, :days, NOW(), NOW()
                )
                RETURNING id
            """)

            result = await db.execute(
                query,
                {
                    "client_id": str(client_id),
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "lead_id": str(lead_id),
                    "als_tier": als_tier,
                    "als_score": als_score,
                    "channel": channel_that_converted,
                    "sequence_step": sequence_step_that_converted,
                    "conversion_type": conversion_type,
                    "touches": touches_before_conversion,
                    "days": days_in_sequence,
                },
            )
            row = result.fetchone()
            await db.commit()

            conversion_id = str(row.id) if row else None
            logger.info(
                f"CIS: Recorded ALS conversion {conversion_id} for lead {lead_id} "
                f"(tier={als_tier}, channel={channel_that_converted})"
            )

            return {
                "success": True,
                "conversion_id": conversion_id,
                "lead_id": str(lead_id),
            }

        except Exception as e:
            logger.error(f"CIS: Failed to record ALS conversion: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # E. MESSAGE PATTERNS - Track what hooks/templates work
    # =========================================================================

    async def update_message_patterns(
        self,
        client_id: UUID | str,
        hook_type: str,
        template_id: UUID | str | None = None,
        channel: str = "email",
        subject_pattern: str | None = None,
        times_used: int = 1,
        replies_generated: int = 0,
        positive_replies: int = 0,
        meetings_generated: int = 0,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Update message pattern performance metrics.

        Args:
            client_id: Client UUID
            hook_type: Type of hook (pain_point, social_proof, question, etc.)
            template_id: Template UUID if using a template
            channel: Channel type
            subject_pattern: Subject line pattern/category
            times_used: Number of times pattern was used
            replies_generated: Number of replies generated
            positive_replies: Number of positive replies
            meetings_generated: Number of meetings generated
            session: Optional database session

        Returns:
            Dict with success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._update_message_patterns_impl(
                    db,
                    client_id,
                    hook_type,
                    template_id,
                    channel,
                    subject_pattern,
                    times_used,
                    replies_generated,
                    positive_replies,
                    meetings_generated,
                )
        return await self._update_message_patterns_impl(
            db,
            client_id,
            hook_type,
            template_id,
            channel,
            subject_pattern,
            times_used,
            replies_generated,
            positive_replies,
            meetings_generated,
        )

    async def _update_message_patterns_impl(
        self,
        db: AsyncSession,
        client_id: UUID | str,
        hook_type: str,
        template_id: UUID | str | None,
        channel: str,
        subject_pattern: str | None,
        times_used: int,
        replies_generated: int,
        positive_replies: int,
        meetings_generated: int,
    ) -> dict[str, Any]:
        """Implementation of update_message_patterns."""
        try:
            # Calculate rates
            reply_rate = replies_generated / times_used if times_used > 0 else 0
            positive_rate = positive_replies / replies_generated if replies_generated > 0 else 0
            meeting_rate = meetings_generated / times_used if times_used > 0 else 0

            query = text("""
                INSERT INTO cis_message_patterns (
                    client_id, channel, hook_type, template_id,
                    subject_pattern, times_used,
                    replies_generated, positive_replies, meetings_generated,
                    reply_rate, positive_rate, meeting_rate,
                    first_used_at, last_used_at, created_at, updated_at
                ) VALUES (
                    :client_id, :channel, :hook_type, :template_id,
                    :subject_pattern, :times_used,
                    :replies_generated, :positive_replies, :meetings_generated,
                    :reply_rate, :positive_rate, :meeting_rate,
                    NOW(), NOW(), NOW(), NOW()
                )
                ON CONFLICT (client_id, channel, hook_type, COALESCE(template_id, '00000000-0000-0000-0000-000000000000'::uuid))
                DO UPDATE SET
                    times_used = cis_message_patterns.times_used + EXCLUDED.times_used,
                    replies_generated = cis_message_patterns.replies_generated + EXCLUDED.replies_generated,
                    positive_replies = cis_message_patterns.positive_replies + EXCLUDED.positive_replies,
                    meetings_generated = cis_message_patterns.meetings_generated + EXCLUDED.meetings_generated,
                    reply_rate = (cis_message_patterns.replies_generated + EXCLUDED.replies_generated)::NUMERIC /
                                 NULLIF(cis_message_patterns.times_used + EXCLUDED.times_used, 0),
                    positive_rate = (cis_message_patterns.positive_replies + EXCLUDED.positive_replies)::NUMERIC /
                                    NULLIF(cis_message_patterns.replies_generated + EXCLUDED.replies_generated, 0),
                    meeting_rate = (cis_message_patterns.meetings_generated + EXCLUDED.meetings_generated)::NUMERIC /
                                   NULLIF(cis_message_patterns.times_used + EXCLUDED.times_used, 0),
                    last_used_at = NOW(),
                    updated_at = NOW()
                RETURNING id
            """)

            result = await db.execute(
                query,
                {
                    "client_id": str(client_id),
                    "channel": channel,
                    "hook_type": hook_type,
                    "template_id": str(template_id) if template_id else None,
                    "subject_pattern": subject_pattern,
                    "times_used": times_used,
                    "replies_generated": replies_generated,
                    "positive_replies": positive_replies,
                    "meetings_generated": meetings_generated,
                    "reply_rate": reply_rate,
                    "positive_rate": positive_rate,
                    "meeting_rate": meeting_rate,
                },
            )
            row = result.fetchone()
            await db.commit()

            logger.info(f"CIS: Updated message pattern {hook_type} for {client_id}")
            return {"success": True, "id": str(row.id) if row else None}

        except Exception as e:
            logger.error(f"CIS: Failed to update message patterns: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # F. AGENCY LEARNINGS - Monthly per-agency summary
    # =========================================================================

    async def update_agency_learnings(
        self,
        client_id: UUID | str,
        month: str,  # Format: "2024-01"
        total_leads_processed: int = 0,
        total_sends: int = 0,
        total_replies: int = 0,
        total_meetings: int = 0,
        total_conversions: int = 0,
        best_performing_channel: str | None = None,
        best_performing_hook: str | None = None,
        best_als_tier: str | None = None,
        avg_reply_rate: float | None = None,
        avg_meeting_rate: float | None = None,
        total_spend_aud: float = 0.0,
        cost_per_meeting_aud: float | None = None,
        learnings_summary: str | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Update monthly agency learnings summary.

        Args:
            client_id: Client UUID
            month: Month string (YYYY-MM format)
            total_leads_processed: Total leads processed
            total_sends: Total messages sent
            total_replies: Total replies received
            total_meetings: Total meetings booked
            total_conversions: Total conversions
            best_performing_channel: Best channel by meeting rate
            best_performing_hook: Best hook type
            best_als_tier: Best converting ALS tier
            avg_reply_rate: Average reply rate
            avg_meeting_rate: Average meeting rate
            total_spend_aud: Total spend in AUD
            cost_per_meeting_aud: Cost per meeting
            learnings_summary: AI-generated summary of learnings
            session: Optional database session

        Returns:
            Dict with success status
        """
        db = session or self._session
        if not db:
            async with get_db_session() as db:
                return await self._update_agency_learnings_impl(
                    db,
                    client_id,
                    month,
                    total_leads_processed,
                    total_sends,
                    total_replies,
                    total_meetings,
                    total_conversions,
                    best_performing_channel,
                    best_performing_hook,
                    best_als_tier,
                    avg_reply_rate,
                    avg_meeting_rate,
                    total_spend_aud,
                    cost_per_meeting_aud,
                    learnings_summary,
                )
        return await self._update_agency_learnings_impl(
            db,
            client_id,
            month,
            total_leads_processed,
            total_sends,
            total_replies,
            total_meetings,
            total_conversions,
            best_performing_channel,
            best_performing_hook,
            best_als_tier,
            avg_reply_rate,
            avg_meeting_rate,
            total_spend_aud,
            cost_per_meeting_aud,
            learnings_summary,
        )

    async def _update_agency_learnings_impl(
        self,
        db: AsyncSession,
        client_id: UUID | str,
        month: str,
        total_leads_processed: int,
        total_sends: int,
        total_replies: int,
        total_meetings: int,
        total_conversions: int,
        best_performing_channel: str | None,
        best_performing_hook: str | None,
        best_als_tier: str | None,
        avg_reply_rate: float | None,
        avg_meeting_rate: float | None,
        total_spend_aud: float,
        cost_per_meeting_aud: float | None,
        learnings_summary: str | None,
    ) -> dict[str, Any]:
        """Implementation of update_agency_learnings."""
        try:
            query = text("""
                INSERT INTO cis_agency_learnings (
                    client_id, month,
                    total_leads_processed, total_sends, total_replies,
                    total_meetings, total_conversions,
                    best_performing_channel, best_performing_hook, best_als_tier,
                    avg_reply_rate, avg_meeting_rate,
                    total_spend_aud, cost_per_meeting_aud,
                    learnings_summary,
                    computed_at, created_at, updated_at
                ) VALUES (
                    :client_id, :month,
                    :leads, :sends, :replies,
                    :meetings, :conversions,
                    :best_channel, :best_hook, :best_tier,
                    :reply_rate, :meeting_rate,
                    :spend, :cost_per_meeting,
                    :summary,
                    NOW(), NOW(), NOW()
                )
                ON CONFLICT (client_id, month)
                DO UPDATE SET
                    total_leads_processed = EXCLUDED.total_leads_processed,
                    total_sends = EXCLUDED.total_sends,
                    total_replies = EXCLUDED.total_replies,
                    total_meetings = EXCLUDED.total_meetings,
                    total_conversions = EXCLUDED.total_conversions,
                    best_performing_channel = EXCLUDED.best_performing_channel,
                    best_performing_hook = EXCLUDED.best_performing_hook,
                    best_als_tier = EXCLUDED.best_als_tier,
                    avg_reply_rate = EXCLUDED.avg_reply_rate,
                    avg_meeting_rate = EXCLUDED.avg_meeting_rate,
                    total_spend_aud = EXCLUDED.total_spend_aud,
                    cost_per_meeting_aud = EXCLUDED.cost_per_meeting_aud,
                    learnings_summary = EXCLUDED.learnings_summary,
                    computed_at = NOW(),
                    updated_at = NOW()
                RETURNING id
            """)

            result = await db.execute(
                query,
                {
                    "client_id": str(client_id),
                    "month": month,
                    "leads": total_leads_processed,
                    "sends": total_sends,
                    "replies": total_replies,
                    "meetings": total_meetings,
                    "conversions": total_conversions,
                    "best_channel": best_performing_channel,
                    "best_hook": best_performing_hook,
                    "best_tier": best_als_tier,
                    "reply_rate": avg_reply_rate,
                    "meeting_rate": avg_meeting_rate,
                    "spend": total_spend_aud,
                    "cost_per_meeting": cost_per_meeting_aud,
                    "summary": learnings_summary,
                },
            )
            row = result.fetchone()
            await db.commit()

            logger.info(f"CIS: Updated agency learnings for {client_id} / {month}")
            return {"success": True, "id": str(row.id) if row else None}

        except Exception as e:
            logger.error(f"CIS: Failed to update agency learnings: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# SINGLETON / FACTORY
# ============================================================================

_cis_service_instance: CISService | None = None


def get_cis_service(session: AsyncSession | None = None) -> CISService:
    """
    Get CIS service instance.

    Args:
        session: Optional database session

    Returns:
        CISService instance
    """
    global _cis_service_instance
    if session:
        return CISService(session)
    if _cis_service_instance is None:
        _cis_service_instance = CISService()
    return _cis_service_instance


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Contract comment at top
# [x] Session passed as argument (optional with fallback)
# [x] All CIS tables covered:
#     - cis_outreach_outcomes ✓
#     - cis_reply_classifications ✓
#     - cis_channel_performance ✓
#     - cis_als_tier_conversions ✓
#     - cis_message_patterns ✓
#     - cis_agency_learnings ✓
# [x] Upsert logic for aggregated tables
# [x] Proper logging
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Error handling with try/except
