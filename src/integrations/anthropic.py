"""
FILE: src/integrations/anthropic.py
PURPOSE: Anthropic/Claude API integration with spend limiter
PHASE: 3 (Integrations)
TASK: INT-012
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
  - src/integrations/redis.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 15: AI spend limiter (daily circuit breaker)
"""

from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from src.config.settings import settings
from src.exceptions import AISpendLimitError, APIError, IntegrationError
from src.integrations.redis import ai_spend_tracker


class AnthropicClient:
    """
    Anthropic/Claude API client with spend limiting.

    All AI calls go through this client to enforce the daily
    spend limit (Rule 15).
    """

    # Cost per 1M tokens (approximate, in AUD)
    COST_PER_M_INPUT_TOKENS = 3.00  # Claude 3 Sonnet
    COST_PER_M_OUTPUT_TOKENS = 15.00

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            raise IntegrationError(
                service="anthropic",
                message="Anthropic API key is required",
            )
        self._client = AsyncAnthropic(api_key=self.api_key)
        self.daily_limit = settings.anthropic_daily_spend_limit

    async def _check_budget(self, estimated_cost: float) -> None:
        """
        Check if there's enough budget for the request.

        Args:
            estimated_cost: Estimated cost in AUD

        Raises:
            AISpendLimitError: If budget exceeded
        """
        remaining = await ai_spend_tracker.get_remaining()
        if remaining < estimated_cost:
            spent = await ai_spend_tracker.get_spend()
            raise AISpendLimitError(
                spent=spent,
                limit=self.daily_limit,
                message=f"AI spend limit exceeded: ${spent:.2f} of ${self.daily_limit:.2f}",
            )

    async def _record_spend(self, input_tokens: int, output_tokens: int) -> float:
        """
        Record spend from API call.

        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens used

        Returns:
            Cost in AUD
        """
        cost = (
            (input_tokens / 1_000_000) * self.COST_PER_M_INPUT_TOKENS
            + (output_tokens / 1_000_000) * self.COST_PER_M_OUTPUT_TOKENS
        )
        await ai_spend_tracker.add_spend(cost)
        return cost

    def _estimate_cost(self, max_tokens: int, input_length: int) -> float:
        """
        Estimate cost for a request.

        Args:
            max_tokens: Maximum output tokens
            input_length: Approximate input character length

        Returns:
            Estimated cost in AUD
        """
        # Rough estimate: 4 chars per token
        estimated_input_tokens = input_length / 4
        return (
            (estimated_input_tokens / 1_000_000) * self.COST_PER_M_INPUT_TOKENS
            + (max_tokens / 1_000_000) * self.COST_PER_M_OUTPUT_TOKENS
        )

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: str = "claude-3-sonnet-20240229",
    ) -> dict[str, Any]:
        """
        Generate a completion.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            model: Model to use

        Returns:
            Completion result with content and usage

        Raises:
            AISpendLimitError: If daily spend limit exceeded
        """
        # Estimate and check budget
        estimated_cost = self._estimate_cost(max_tokens, len(prompt) + len(system or ""))
        await self._check_budget(estimated_cost)

        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else anthropic.NOT_GIVEN,
                messages=messages,
            )

            # Record actual spend
            cost = await self._record_spend(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            return {
                "content": response.content[0].text if response.content else "",
                "model": response.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost_aud": cost,
                "stop_reason": response.stop_reason,
            }

        except anthropic.APIError as e:
            raise APIError(
                service="anthropic",
                status_code=getattr(e, "status_code", 500),
                message=f"Anthropic API error: {str(e)}",
            )

    async def classify_intent(
        self,
        message: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """
        Classify the intent of a message (e.g., reply).

        Args:
            message: Message to classify
            context: Additional context

        Returns:
            Classification result
        """
        system = """You are an intent classifier for sales outreach replies.
Classify the reply into one of these categories:
- meeting_request: Wants to schedule a meeting
- interested: Shows interest but no meeting request
- question: Has questions about the offering
- not_interested: Politely declines
- unsubscribe: Wants to stop receiving messages
- out_of_office: Automated out of office reply
- auto_reply: Other automated reply

Return JSON with: {"intent": "category", "confidence": 0.0-1.0, "reasoning": "brief explanation"}"""

        prompt = f"Classify this reply:\n\n{message}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        result = await self.complete(
            prompt=prompt,
            system=system,
            max_tokens=200,
            temperature=0.3,
        )

        # Parse JSON from response
        import json
        try:
            content = result["content"]
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            classification = json.loads(content.strip())
            return {
                "intent": classification.get("intent"),
                "confidence": classification.get("confidence", 0.8),
                "reasoning": classification.get("reasoning"),
                "cost_aud": result["cost_aud"],
            }
        except json.JSONDecodeError:
            return {
                "intent": "question",  # Default fallback
                "confidence": 0.5,
                "reasoning": "Could not parse classification",
                "cost_aud": result["cost_aud"],
            }

    async def generate_email(
        self,
        template: str,
        lead_data: dict[str, Any],
        tone: str = "professional",
    ) -> dict[str, Any]:
        """
        Generate personalized email content.

        Args:
            template: Email template with placeholders
            lead_data: Lead data for personalization
            tone: Desired tone (professional, friendly, direct)

        Returns:
            Generated email content
        """
        system = f"""You are an expert sales copywriter. Generate personalized email content.
Tone: {tone}
Keep emails concise (under 150 words).
Use the provided lead data for personalization.
Do not include subject line unless asked."""

        prompt = f"""Generate a personalized email based on this template:

Template:
{template}

Lead Data:
- Name: {lead_data.get('first_name')} {lead_data.get('last_name')}
- Company: {lead_data.get('company')}
- Title: {lead_data.get('title')}
- Industry: {lead_data.get('organization_industry')}

Return only the email body text."""

        result = await self.complete(
            prompt=prompt,
            system=system,
            max_tokens=500,
            temperature=0.7,
        )

        return {
            "content": result["content"],
            "cost_aud": result["cost_aud"],
        }

    async def get_spend_status(self) -> dict[str, Any]:
        """
        Get current AI spend status.

        Returns:
            Spend status with remaining budget
        """
        spent = await ai_spend_tracker.get_spend()
        remaining = await ai_spend_tracker.get_remaining()

        return {
            "daily_limit": self.daily_limit,
            "spent": spent,
            "remaining": remaining,
            "percentage_used": (spent / self.daily_limit) * 100 if self.daily_limit > 0 else 0,
        }


# Singleton instance
_anthropic_client: AnthropicClient | None = None


def get_anthropic_client() -> AnthropicClient:
    """Get or create Anthropic client instance."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AnthropicClient()
    return _anthropic_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Daily spend limiter (Rule 15)
# [x] Budget check before requests
# [x] Spend tracking via Redis
# [x] Cost calculation
# [x] Message completion
# [x] Intent classification
# [x] Email generation
# [x] Spend status reporting
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
