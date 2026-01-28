"""
Contract: src/services/conversation_analytics_service.py
Purpose: Conversation analytics service for CIS learning
Layer: 3 - services
Imports: models
Consumers: orchestration, API routes, CIS detectors

FILE: src/services/conversation_analytics_service.py
PURPOSE: Conversation analytics service for CIS learning
PHASE: 24D (Conversation Threading)
TASK: THREAD-007
DEPENDENCIES:
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: orchestration, API routes, CIS detectors

This service provides analytics on conversation patterns to help
CIS learn optimal conversation strategies.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ConversationAnalyticsService:
    """
    Service for analyzing conversation patterns and outcomes.

    Provides insights into:
    - Thread conversion rates
    - Common objections and their frequency
    - Response timing patterns
    - Sentiment trends
    - Question patterns from leads
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Conversation Analytics service.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_analytics(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get comprehensive conversation analytics for a client.

        Uses the database function get_conversation_analytics().

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Analytics data including totals, rates, and distributions
        """
        query = text("""
            SELECT * FROM get_conversation_analytics(:client_id, :days)
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
            },
        )

        row = result.fetchone()
        if not row:
            return self._empty_analytics()

        return dict(row._mapping)

    async def get_common_questions(
        self,
        client_id: UUID,
        days: int = 90,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get common questions asked by leads.

        Uses the database function get_common_questions().

        Args:
            client_id: Client UUID
            days: Number of days to analyze
            limit: Max questions to return

        Returns:
            List of questions with frequency and sentiment
        """
        query = text("""
            SELECT * FROM get_common_questions(:client_id, :days, :limit)
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def get_objection_breakdown(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get breakdown of objection types and their outcomes.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Objection breakdown with counts and conversion rates
        """
        query = text("""
            WITH objection_stats AS (
                SELECT
                    tm.objection_type,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE ct.outcome = 'converted' OR ct.outcome = 'meeting_booked') as converted_count,
                    COUNT(*) FILTER (WHERE ct.outcome = 'rejected') as rejected_count
                FROM thread_messages tm
                JOIN conversation_threads ct ON ct.id = tm.thread_id
                WHERE ct.client_id = :client_id
                AND tm.objection_type IS NOT NULL
                AND ct.created_at >= NOW() - (:days || ' days')::INTERVAL
                GROUP BY tm.objection_type
                ORDER BY count DESC
            )
            SELECT
                objection_type,
                count,
                converted_count,
                rejected_count,
                ROUND(converted_count::NUMERIC / NULLIF(count, 0) * 100, 2) as conversion_rate_after_objection
            FROM objection_stats
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
            },
        )

        rows = result.fetchall()
        return {
            "objections": [dict(row._mapping) for row in rows],
            "total_objections": sum(r.count for r in rows) if rows else 0,
        }

    async def get_response_timing_analysis(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Analyze response timing patterns and their correlation with outcomes.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Response timing analysis with optimal windows
        """
        query = text("""
            WITH timing_stats AS (
                SELECT
                    CASE
                        WHEN ct.avg_our_response_minutes < 5 THEN 'under_5min'
                        WHEN ct.avg_our_response_minutes < 30 THEN '5_to_30min'
                        WHEN ct.avg_our_response_minutes < 60 THEN '30_to_60min'
                        WHEN ct.avg_our_response_minutes < 240 THEN '1_to_4hr'
                        WHEN ct.avg_our_response_minutes < 1440 THEN '4_to_24hr'
                        ELSE 'over_24hr'
                    END as response_bucket,
                    COUNT(*) as thread_count,
                    COUNT(*) FILTER (WHERE outcome = 'converted' OR outcome = 'meeting_booked') as converted,
                    AVG(message_count) as avg_messages
                FROM conversation_threads ct
                WHERE ct.client_id = :client_id
                AND ct.created_at >= NOW() - (:days || ' days')::INTERVAL
                AND ct.avg_our_response_minutes IS NOT NULL
                GROUP BY 1
            )
            SELECT
                response_bucket,
                thread_count,
                converted,
                ROUND(converted::NUMERIC / NULLIF(thread_count, 0) * 100, 2) as conversion_rate,
                ROUND(avg_messages, 1) as avg_messages
            FROM timing_stats
            ORDER BY
                CASE response_bucket
                    WHEN 'under_5min' THEN 1
                    WHEN '5_to_30min' THEN 2
                    WHEN '30_to_60min' THEN 3
                    WHEN '1_to_4hr' THEN 4
                    WHEN '4_to_24hr' THEN 5
                    ELSE 6
                END
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
            },
        )

        rows = result.fetchall()

        # Find optimal response time window
        best_bucket: str | None = None
        best_rate: float = 0.0
        for row in rows:
            rate = float(row.conversion_rate or 0)
            if rate > best_rate and row.thread_count >= 5:  # Min sample size
                best_rate = rate
                best_bucket = row.response_bucket

        return {
            "timing_buckets": [dict(row._mapping) for row in rows],
            "optimal_response_window": best_bucket,
            "optimal_conversion_rate": best_rate,
        }

    async def get_sentiment_trends(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Analyze sentiment trends over conversation lifecycle.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Sentiment analysis by position in thread
        """
        query = text("""
            SELECT
                tm.position,
                tm.sentiment,
                COUNT(*) as count,
                AVG(tm.sentiment_score) as avg_score
            FROM thread_messages tm
            JOIN conversation_threads ct ON ct.id = tm.thread_id
            WHERE ct.client_id = :client_id
            AND tm.direction = 'inbound'
            AND tm.sentiment IS NOT NULL
            AND ct.created_at >= NOW() - (:days || ' days')::INTERVAL
            AND tm.position <= 10  -- First 10 messages
            GROUP BY tm.position, tm.sentiment
            ORDER BY tm.position, tm.sentiment
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
            },
        )

        rows = result.fetchall()

        # Organize by position
        by_position: dict[int, dict[str, Any]] = {}
        for row in rows:
            pos = row.position
            if pos not in by_position:
                by_position[pos] = {}
            by_position[pos][row.sentiment] = {
                "count": row.count,
                "avg_score": float(row.avg_score) if row.avg_score else 0,
            }

        return {
            "sentiment_by_position": by_position,
            "positions_analyzed": list(by_position.keys()),
        }

    async def get_conversion_patterns(
        self,
        client_id: UUID,
        days: int = 90,
    ) -> dict[str, Any]:
        """
        Analyze patterns in successful conversions vs rejections.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Patterns that differentiate converted vs rejected threads
        """
        query = text("""
            WITH thread_patterns AS (
                SELECT
                    ct.outcome,
                    ct.message_count,
                    ct.our_message_count,
                    ct.their_message_count,
                    ct.avg_our_response_minutes,
                    ct.avg_their_response_minutes,
                    (
                        SELECT COUNT(*) FROM thread_messages tm
                        WHERE tm.thread_id = ct.id AND tm.objection_type IS NOT NULL
                    ) as objection_count,
                    (
                        SELECT COUNT(*) FROM thread_messages tm
                        WHERE tm.thread_id = ct.id AND tm.question_extracted IS NOT NULL
                    ) as question_count,
                    (
                        SELECT tm.sentiment FROM thread_messages tm
                        WHERE tm.thread_id = ct.id AND tm.direction = 'inbound'
                        ORDER BY tm.position DESC LIMIT 1
                    ) as final_sentiment
                FROM conversation_threads ct
                WHERE ct.client_id = :client_id
                AND ct.outcome IS NOT NULL
                AND ct.created_at >= NOW() - (:days || ' days')::INTERVAL
            )
            SELECT
                outcome,
                COUNT(*) as count,
                ROUND(AVG(message_count), 1) as avg_messages,
                ROUND(AVG(our_message_count), 1) as avg_our_messages,
                ROUND(AVG(their_message_count), 1) as avg_their_messages,
                ROUND(AVG(avg_our_response_minutes), 0) as avg_our_response_min,
                ROUND(AVG(avg_their_response_minutes), 0) as avg_their_response_min,
                ROUND(AVG(objection_count), 1) as avg_objections,
                ROUND(AVG(question_count), 1) as avg_questions,
                MODE() WITHIN GROUP (ORDER BY final_sentiment) as most_common_final_sentiment
            FROM thread_patterns
            GROUP BY outcome
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
            },
        )

        rows = result.fetchall()

        patterns = {}
        for row in rows:
            patterns[row.outcome] = {
                "count": row.count,
                "avg_messages": float(row.avg_messages) if row.avg_messages else 0,
                "avg_our_messages": float(row.avg_our_messages) if row.avg_our_messages else 0,
                "avg_their_messages": float(row.avg_their_messages)
                if row.avg_their_messages
                else 0,
                "avg_our_response_min": int(row.avg_our_response_min)
                if row.avg_our_response_min
                else 0,
                "avg_their_response_min": int(row.avg_their_response_min)
                if row.avg_their_response_min
                else 0,
                "avg_objections": float(row.avg_objections) if row.avg_objections else 0,
                "avg_questions": float(row.avg_questions) if row.avg_questions else 0,
                "most_common_final_sentiment": row.most_common_final_sentiment,
            }

        return {
            "patterns_by_outcome": patterns,
            "outcomes_analyzed": list(patterns.keys()),
        }

    async def get_topic_effectiveness(
        self,
        client_id: UUID,
        days: int = 90,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Analyze which topics correlate with conversions.

        Args:
            client_id: Client UUID
            days: Number of days to analyze
            limit: Max topics to return

        Returns:
            Topics ranked by conversion correlation
        """
        query = text("""
            WITH topic_unnest AS (
                SELECT
                    ct.id as thread_id,
                    ct.outcome,
                    UNNEST(tm.topics_mentioned) as topic
                FROM thread_messages tm
                JOIN conversation_threads ct ON ct.id = tm.thread_id
                WHERE ct.client_id = :client_id
                AND tm.topics_mentioned IS NOT NULL
                AND array_length(tm.topics_mentioned, 1) > 0
                AND ct.created_at >= NOW() - (:days || ' days')::INTERVAL
            ),
            topic_stats AS (
                SELECT
                    topic,
                    COUNT(DISTINCT thread_id) as mention_count,
                    COUNT(DISTINCT thread_id) FILTER (
                        WHERE outcome = 'converted' OR outcome = 'meeting_booked'
                    ) as converted_count
                FROM topic_unnest
                GROUP BY topic
                HAVING COUNT(DISTINCT thread_id) >= 3  -- Min sample
            )
            SELECT
                topic,
                mention_count,
                converted_count,
                ROUND(converted_count::NUMERIC / mention_count * 100, 2) as conversion_rate
            FROM topic_stats
            ORDER BY conversion_rate DESC
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "client_id": client_id,
                "days": days,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    def _empty_analytics(self) -> dict[str, Any]:
        """Return empty analytics result."""
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


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] Uses database functions from migration 027
# [x] get_analytics() for comprehensive stats
# [x] get_common_questions() for FAQ analysis
# [x] get_objection_breakdown() for objection patterns
# [x] get_response_timing_analysis() for timing optimization
# [x] get_sentiment_trends() for sentiment lifecycle
# [x] get_conversion_patterns() for win/loss analysis
# [x] get_topic_effectiveness() for topic correlation
# [x] All functions have type hints
# [x] All functions have docstrings
