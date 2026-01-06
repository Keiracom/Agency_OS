"""
FILE: src/services/reply_analyzer.py
PURPOSE: AI-powered reply analysis for sentiment, objections, and questions
PHASE: 24D (Conversation Threading)
TASK: THREAD-004
DEPENDENCIES:
  - src/integrations/anthropic.py (for AI analysis)
LAYER: 3 (services)
CONSUMERS: orchestration, closer engine, thread service

This service analyzes incoming replies to extract:
- Sentiment (positive, neutral, negative, mixed)
- Intent (interested, question, objection, not_interested, etc.)
- Objection type (timing, budget, authority, need, competitor, trust)
- Questions asked
- Topics mentioned
"""

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ValidationError


# Objection keywords for rule-based fallback
OBJECTION_PATTERNS = {
    "timing": [
        "not now", "not the right time", "maybe later", "reach out later",
        "in a few months", "next quarter", "next year", "too busy right now",
        "swamped", "slammed", "crazy time"
    ],
    "budget": [
        "budget", "expensive", "can't afford", "no budget", "cost",
        "pricing", "too much", "cheaper", "don't have the funds"
    ],
    "authority": [
        "not my decision", "not the decision maker", "need to ask",
        "check with my", "run it by", "get approval", "my boss",
        "the team decides", "not my call"
    ],
    "need": [
        "don't need", "already have", "not looking", "not interested",
        "satisfied with", "happy with current", "no need"
    ],
    "competitor": [
        "using another", "working with", "signed with", "contract with",
        "already partnered", "competitor", "different provider"
    ],
    "trust": [
        "never heard of", "not familiar", "don't know you",
        "who are you", "is this legit", "spam", "scam"
    ],
}

# Intent patterns
INTENT_PATTERNS = {
    "interested": [
        "sounds interesting", "tell me more", "i'd like to learn",
        "how does it work", "can you explain", "curious about",
        "yes", "definitely", "absolutely", "love to"
    ],
    "meeting_request": [
        "let's meet", "schedule a call", "book a time", "calendar",
        "set up a meeting", "let's talk", "when are you free"
    ],
    "question": [
        "what", "how", "why", "when", "where", "who", "which",
        "can you", "could you", "would you", "is it", "are you", "do you"
    ],
    "not_interested": [
        "not interested", "no thanks", "no thank you", "pass",
        "remove me", "unsubscribe", "stop", "don't contact"
    ],
}

# Sentiment keywords
SENTIMENT_KEYWORDS = {
    "positive": [
        "great", "awesome", "excellent", "love", "perfect", "wonderful",
        "fantastic", "amazing", "thanks", "thank you", "appreciate",
        "helpful", "useful", "interested", "excited"
    ],
    "negative": [
        "annoying", "frustrated", "angry", "upset", "disappointed",
        "terrible", "awful", "horrible", "hate", "spam", "stop",
        "remove", "unsubscribe", "leave me alone"
    ],
}


class ReplyAnalyzer:
    """
    Service for analyzing reply content using AI and rule-based methods.

    Extracts sentiment, intent, objections, and questions from replies
    to help CIS learn from conversation patterns.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Reply Analyzer.

        Args:
            session: Async database session
        """
        self.session = session

    async def analyze(
        self,
        content: str,
        context: dict[str, Any] | None = None,
        use_ai: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze a reply for sentiment, intent, objections, and questions.

        Args:
            content: Reply content to analyze
            context: Optional context (lead info, previous messages)
            use_ai: Whether to use AI analysis (falls back to rules if False)

        Returns:
            Analysis results including sentiment, intent, objections, questions
        """
        if not content or not content.strip():
            return self._empty_analysis()

        content_lower = content.lower().strip()

        # Try AI analysis first if enabled
        if use_ai:
            try:
                ai_result = await self._analyze_with_ai(content, context)
                if ai_result:
                    return ai_result
            except Exception:
                pass  # Fall back to rule-based

        # Rule-based analysis as fallback
        return self._analyze_with_rules(content_lower)

    async def _analyze_with_ai(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Analyze reply using AI (Claude).

        Args:
            content: Reply content
            context: Optional context

        Returns:
            AI analysis results or None if failed
        """
        try:
            from src.integrations.anthropic import get_anthropic_client

            client = get_anthropic_client()

            context_str = ""
            if context:
                if context.get("lead_name"):
                    context_str += f"Lead: {context['lead_name']}\n"
                if context.get("company"):
                    context_str += f"Company: {context['company']}\n"
                if context.get("previous_message"):
                    context_str += f"Our previous message: {context['previous_message'][:200]}\n"

            # Build context section separately to avoid f-string backslash issues
            context_section = f"Context:\n{context_str}" if context_str else ""

            prompt = f"""Analyze this email/message reply and extract the following in JSON format:

Reply to analyze:
"{content}"

{context_section}

Return a JSON object with these fields:
- sentiment: "positive", "neutral", "negative", or "mixed"
- sentiment_score: float from -1 (very negative) to 1 (very positive)
- intent: one of "interested", "question", "objection", "not_interested", "meeting_request", "referral", "out_of_office", "unclear"
- objection_type: if intent is "objection", one of "timing", "budget", "authority", "need", "competitor", "trust", "other" or null
- question_extracted: if they asked a question, extract the main question as a string, else null
- topics_mentioned: array of key topics mentioned (max 5)
- requires_response: boolean, whether this needs a follow-up response
- suggested_action: brief suggestion for next step

Return ONLY valid JSON, no other text."""

            response = await client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1,  # Low temperature for consistent analysis
            )

            # Parse JSON from response
            response_text = response.get("content", "")

            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "sentiment": result.get("sentiment", "neutral"),
                    "sentiment_score": float(result.get("sentiment_score", 0)),
                    "intent": result.get("intent", "unclear"),
                    "objection_type": result.get("objection_type"),
                    "question_extracted": result.get("question_extracted"),
                    "topics_mentioned": result.get("topics_mentioned", []),
                    "requires_response": result.get("requires_response", True),
                    "suggested_action": result.get("suggested_action"),
                    "analysis_method": "ai",
                }

        except Exception:
            return None

        return None

    def _analyze_with_rules(self, content_lower: str) -> dict[str, Any]:
        """
        Analyze reply using rule-based patterns.

        Args:
            content_lower: Lowercase reply content

        Returns:
            Analysis results
        """
        # Detect sentiment
        sentiment, sentiment_score = self._detect_sentiment(content_lower)

        # Detect intent
        intent = self._detect_intent(content_lower)

        # Detect objection type
        objection_type = None
        if intent == "objection" or intent == "not_interested":
            objection_type = self._detect_objection_type(content_lower)

        # Extract question
        question = self._extract_question(content_lower)
        if question and intent == "unclear":
            intent = "question"

        # Extract topics (simple noun extraction)
        topics = self._extract_topics(content_lower)

        return {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "intent": intent,
            "objection_type": objection_type,
            "question_extracted": question,
            "topics_mentioned": topics,
            "requires_response": intent not in ("not_interested", "out_of_office"),
            "suggested_action": self._suggest_action(intent, objection_type),
            "analysis_method": "rules",
        }

    def _detect_sentiment(self, content: str) -> tuple[str, float]:
        """Detect sentiment from content."""
        positive_count = sum(1 for kw in SENTIMENT_KEYWORDS["positive"] if kw in content)
        negative_count = sum(1 for kw in SENTIMENT_KEYWORDS["negative"] if kw in content)

        if positive_count > 0 and negative_count > 0:
            return "mixed", 0.0
        elif positive_count > negative_count:
            score = min(1.0, positive_count * 0.3)
            return "positive", score
        elif negative_count > positive_count:
            score = max(-1.0, -negative_count * 0.3)
            return "negative", score
        else:
            return "neutral", 0.0

    def _detect_intent(self, content: str) -> str:
        """Detect intent from content."""
        # Check each intent pattern
        intent_scores = {}
        for intent, patterns in INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in content)
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return "unclear"

        # Check for objection patterns
        for objection_type, patterns in OBJECTION_PATTERNS.items():
            if any(p in content for p in patterns):
                return "objection"

        # Return highest scoring intent
        return max(intent_scores, key=intent_scores.get)

    def _detect_objection_type(self, content: str) -> str | None:
        """Detect specific objection type."""
        for objection_type, patterns in OBJECTION_PATTERNS.items():
            if any(p in content for p in patterns):
                return objection_type
        return "other"

    def _extract_question(self, content: str) -> str | None:
        """Extract the main question from content."""
        # Find sentences ending with ?
        questions = re.findall(r'[^.!?]*\?', content)
        if questions:
            # Return the longest question (likely the main one)
            return max(questions, key=len).strip()
        return None

    def _extract_topics(self, content: str) -> list[str]:
        """Extract key topics from content."""
        # Simple extraction - in production, use NLP
        # Remove common words and extract key terms
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "i", "you",
            "we", "they", "it", "this", "that", "these", "those", "my",
            "your", "our", "their", "its", "to", "of", "in", "for", "on",
            "with", "at", "by", "from", "as", "into", "through", "during",
            "and", "or", "but", "if", "then", "else", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "not", "only", "same",
            "so", "than", "too", "very", "just", "also", "now", "here",
            "there", "up", "down", "out", "about", "over", "again", "hi",
            "hello", "hey", "thanks", "thank", "please", "yes", "no"
        }

        words = re.findall(r'\b[a-z]+\b', content)
        topics = []
        for word in words:
            if word not in stop_words and len(word) > 3:
                if word not in topics:
                    topics.append(word)
                if len(topics) >= 5:
                    break

        return topics

    def _suggest_action(self, intent: str, objection_type: str | None) -> str:
        """Suggest next action based on analysis."""
        actions = {
            "interested": "Schedule a call or provide more information",
            "meeting_request": "Send calendar link immediately",
            "question": "Answer the question directly",
            "objection": self._get_objection_action(objection_type),
            "not_interested": "Mark as not interested, consider nurture sequence",
            "out_of_office": "Wait and follow up when they return",
            "unclear": "Ask clarifying question",
        }
        return actions.get(intent, "Review manually")

    def _get_objection_action(self, objection_type: str | None) -> str:
        """Get specific action for objection type."""
        actions = {
            "timing": "Acknowledge timing, offer to reconnect later",
            "budget": "Highlight ROI or offer flexible options",
            "authority": "Ask to be connected to decision maker",
            "need": "Share relevant case study or use case",
            "competitor": "Differentiate with unique value prop",
            "trust": "Share credentials, testimonials, or case studies",
            "other": "Address their specific concern",
        }
        return actions.get(objection_type, "Address their concern")

    def _empty_analysis(self) -> dict[str, Any]:
        """Return empty analysis result."""
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "intent": "unclear",
            "objection_type": None,
            "question_extracted": None,
            "topics_mentioned": [],
            "requires_response": True,
            "suggested_action": "Review manually",
            "analysis_method": "none",
        }

    async def analyze_and_save(
        self,
        reply_id: UUID,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a reply and save results to database.

        Args:
            reply_id: Reply UUID to update
            content: Reply content
            context: Optional context

        Returns:
            Analysis results
        """
        analysis = await self.analyze(content, context)

        # Update reply with analysis
        query = text("""
            UPDATE replies
            SET sentiment = :sentiment,
                sentiment_score = :sentiment_score,
                objection_type = :objection_type,
                question_extracted = :question_extracted,
                topics_mentioned = :topics_mentioned,
                ai_analysis_at = NOW()
            WHERE id = :reply_id
            RETURNING *
        """)

        await self.session.execute(query, {
            "reply_id": reply_id,
            "sentiment": analysis["sentiment"],
            "sentiment_score": analysis["sentiment_score"],
            "objection_type": analysis.get("objection_type"),
            "question_extracted": analysis.get("question_extracted"),
            "topics_mentioned": analysis.get("topics_mentioned", []),
        })

        await self.session.commit()

        return analysis

    async def classify_rejection(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Classify a rejection reason from reply content.

        Args:
            content: Reply content
            context: Optional context

        Returns:
            Rejection classification
        """
        analysis = await self.analyze(content, context, use_ai=True)

        # Map objection types to rejection reasons
        objection_to_rejection = {
            "timing": "timing_not_now",
            "budget": "budget_constraints",
            "authority": "not_decision_maker",
            "need": "no_need",
            "competitor": "using_competitor",
            "trust": "other",
            "other": "not_interested_generic",
        }

        rejection_reason = None
        if analysis.get("intent") == "not_interested":
            objection = analysis.get("objection_type")
            rejection_reason = objection_to_rejection.get(objection, "not_interested_generic")

            # Check for specific patterns
            content_lower = content.lower()
            if "stop" in content_lower or "unsubscribe" in content_lower or "remove" in content_lower:
                rejection_reason = "do_not_contact"
            elif "wrong" in content_lower and ("person" in content_lower or "contact" in content_lower):
                rejection_reason = "wrong_contact"

        return {
            "is_rejection": analysis.get("intent") == "not_interested",
            "rejection_reason": rejection_reason,
            "confidence": 0.8 if analysis.get("analysis_method") == "ai" else 0.6,
            "analysis": analysis,
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] AI-powered analysis with Claude
# [x] Rule-based fallback analysis
# [x] Sentiment detection (positive, neutral, negative, mixed)
# [x] Intent classification
# [x] Objection type detection
# [x] Question extraction
# [x] Topic extraction
# [x] Suggested action generation
# [x] Rejection classification (THREAD-005)
# [x] Save analysis to database
# [x] All functions have type hints
# [x] All functions have docstrings
