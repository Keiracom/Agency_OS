"""
Contract: src/integrations/sdk_brain.py
Purpose: Claude Agent SDK wrapper with cost control and caching
Layer: 2 - integrations
Imports: models ONLY
Consumers: sdk_agents

This is the core wrapper around Claude's Agent SDK that provides:
- Tool execution with cost tracking
- Per-call and daily spend limits
- Automatic prompt caching
- Structured output enforcement
- Turn limiting to prevent runaway loops

COPY THIS FILE TO: src/integrations/sdk_brain.py
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TypeVar
from uuid import UUID

from anthropic import Anthropic, AsyncAnthropic
from pydantic import BaseModel

# These imports will work when file is in src/integrations/
# from src.config.settings import settings
# from src.exceptions import AISpendLimitError
# from src.integrations.redis import ai_spend_tracker

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ============================================
# CONFIGURATION
# ============================================


@dataclass
class SDKBrainConfig:
    """Configuration for SDK Brain instance."""

    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 10
    max_cost_aud: float = 2.0
    timeout_seconds: int = 120
    enable_caching: bool = True
    enable_logging: bool = True

    # Model-specific overrides
    classification_model: str = "claude-3-5-haiku-20241022"
    complex_model: str = "claude-sonnet-4-20250514"


@dataclass
class SDKBrainResult:
    """Result from SDK Brain execution."""

    success: bool
    data: dict | BaseModel | None = None
    error: str | None = None
    cost_aud: float = 0.0
    turns_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    model_used: str = ""
    duration_ms: int = 0
    tool_calls: list[dict] = field(default_factory=list)


# ============================================
# PRICING (AUD as of Jan 2026)
# ============================================

MODEL_PRICING = {
    "claude-sonnet-4-20250514": {
        "input": 4.65,      # $3 USD × 1.55
        "output": 23.25,    # $15 USD × 1.55
        "cached": 0.465,    # 90% discount on cached
    },
    "claude-3-5-haiku-20241022": {
        "input": 1.24,      # $0.80 USD × 1.55
        "output": 6.20,     # $4 USD × 1.55
        "cached": 0.124,
    },
    "claude-opus-4-5-20251101": {
        "input": 7.75,      # $5 USD × 1.55
        "output": 38.75,    # $25 USD × 1.55
        "cached": 0.775,
    },
}


# ============================================
# SDK BRAIN CORE
# ============================================


class SDKBrain:
    """
    Claude Agent SDK wrapper with cost control.

    Provides autonomous agent execution with:
    - Tool use (web search, web fetch, etc.)
    - Multi-turn conversation loops
    - Cost tracking and limits
    - Prompt caching
    - Structured output enforcement

    Example usage:
        config = SDKBrainConfig(max_cost_aud=1.50, max_turns=10)
        brain = SDKBrain(config=config)

        result = await brain.run(
            prompt="Research this company and find pain points",
            tools=[WEB_SEARCH_TOOL, WEB_FETCH_TOOL],
            output_schema=EnrichmentOutput,
            system="You are a research assistant...",
        )

        if result.success:
            enrichment = result.data
            print(f"Cost: ${result.cost_aud:.4f} AUD")
    """

    def __init__(
        self,
        config: SDKBrainConfig | None = None,
        api_key: str | None = None,
        spend_tracker: Any | None = None,
    ):
        """
        Initialize SDK Brain.

        Args:
            config: Configuration for this instance
            api_key: Anthropic API key (uses settings if not provided)
            spend_tracker: Redis spend tracker for daily limits
        """
        self.config = config or SDKBrainConfig()

        # In production, get from settings:
        # api_key = api_key or settings.anthropic_api_key
        self._api_key = api_key

        # Sync client for tool execution
        self._client: Anthropic | None = None

        # Async client for async operations
        self._async_client: AsyncAnthropic | None = None

        # Spend tracker (Redis-based in production)
        self._spend_tracker = spend_tracker

        # Tracking for current run
        self._total_cost = 0.0
        self._turns = 0
        self._tool_calls: list[dict] = []

    @property
    def client(self) -> Anthropic:
        """Get or create sync Anthropic client."""
        if self._client is None:
            self._client = Anthropic(api_key=self._api_key)
        return self._client

    @property
    def async_client(self) -> AsyncAnthropic:
        """Get or create async Anthropic client."""
        if self._async_client is None:
            self._async_client = AsyncAnthropic(api_key=self._api_key)
        return self._async_client

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        model: str | None = None,
    ) -> float:
        """Calculate cost from token usage."""
        model = model or self.config.model
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-20250514"])

        # Regular input tokens (minus cached)
        regular_input = max(0, input_tokens - cached_tokens)

        input_cost = (regular_input / 1_000_000) * pricing["input"]
        cached_cost = (cached_tokens / 1_000_000) * pricing["cached"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + cached_cost + output_cost

    async def _check_daily_budget(self, estimated_cost: float = 0.10) -> bool:
        """Check if daily budget allows this request."""
        if self._spend_tracker is None:
            return True  # No tracker = no limit

        remaining = await self._spend_tracker.get_remaining()
        return remaining >= estimated_cost

    async def _record_spend(self, cost: float) -> None:
        """Record spend to daily tracker."""
        if self._spend_tracker is not None:
            await self._spend_tracker.add_spend(cost)

    def _reset_tracking(self) -> None:
        """Reset tracking for new run."""
        self._total_cost = 0.0
        self._turns = 0
        self._tool_calls = []

    async def run(
        self,
        prompt: str,
        tools: list[dict],
        output_schema: type[T],
        system: str | None = None,
        context: str | None = None,
        cache_context: bool = True,
    ) -> SDKBrainResult:
        """
        Run SDK agent with tools until completion or limit.

        Args:
            prompt: User prompt / goal
            tools: List of tool definitions (see sdk_tools.py)
            output_schema: Pydantic model for structured output
            system: System prompt
            context: Additional context (will be cached if cache_context=True)
            cache_context: Whether to cache the context

        Returns:
            SDKBrainResult with data, cost, and metadata

        Raises:
            Does not raise - errors returned in result
        """
        start_time = datetime.now()
        self._reset_tracking()

        # Check daily budget
        if not await self._check_daily_budget():
            return SDKBrainResult(
                success=False,
                error="Daily AI budget exhausted",
                cost_aud=0.0,
            )

        # Build messages
        messages = self._build_messages(prompt, context, cache_context)

        total_input_tokens = 0
        total_output_tokens = 0
        total_cached_tokens = 0

        try:
            while self._turns < self.config.max_turns:
                self._turns += 1

                # Make API call
                response = await self._make_request(
                    messages=messages,
                    tools=tools,
                    system=system,
                )

                # Track tokens
                usage = response.usage
                total_input_tokens += usage.input_tokens
                total_output_tokens += usage.output_tokens

                # Check for cached tokens
                if hasattr(usage, "cache_read_input_tokens"):
                    total_cached_tokens += usage.cache_read_input_tokens

                # Calculate and track cost
                turn_cost = self._calculate_cost(
                    usage.input_tokens,
                    usage.output_tokens,
                    getattr(usage, "cache_read_input_tokens", 0),
                )
                self._total_cost += turn_cost

                # Check per-call cost limit
                if self._total_cost > self.config.max_cost_aud:
                    await self._record_spend(self._total_cost)
                    return SDKBrainResult(
                        success=False,
                        error=f"Cost limit exceeded: ${self._total_cost:.4f} > ${self.config.max_cost_aud:.4f}",
                        cost_aud=self._total_cost,
                        turns_used=self._turns,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        model_used=self.config.model,
                        tool_calls=self._tool_calls,
                    )

                # Handle tool use
                if response.stop_reason == "tool_use":
                    tool_results = await self._execute_tools(response.content)
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                    continue

                # Handle completion
                if response.stop_reason == "end_turn":
                    try:
                        result_data = self._parse_output(response.content, output_schema)
                        await self._record_spend(self._total_cost)

                        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                        return SDKBrainResult(
                            success=True,
                            data=result_data,
                            cost_aud=self._total_cost,
                            turns_used=self._turns,
                            input_tokens=total_input_tokens,
                            output_tokens=total_output_tokens,
                            cached_tokens=total_cached_tokens,
                            model_used=self.config.model,
                            duration_ms=duration_ms,
                            tool_calls=self._tool_calls,
                        )
                    except Exception as e:
                        logger.warning(f"Output parsing failed: {e}")
                        # Try one more turn asking for proper format
                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": f"Please format your response as valid JSON matching this schema:\n{output_schema.model_json_schema()}"
                        })
                        continue

            # Turn limit reached
            await self._record_spend(self._total_cost)
            return SDKBrainResult(
                success=False,
                error=f"Turn limit reached: {self.config.max_turns}",
                cost_aud=self._total_cost,
                turns_used=self._turns,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                model_used=self.config.model,
                tool_calls=self._tool_calls,
            )

        except Exception as e:
            logger.error(f"SDK Brain error: {e}", exc_info=True)
            await self._record_spend(self._total_cost)
            return SDKBrainResult(
                success=False,
                error=f"Execution error: {str(e)}",
                cost_aud=self._total_cost,
                turns_used=self._turns,
                model_used=self.config.model,
            )

    def _build_messages(
        self,
        prompt: str,
        context: str | None,
        cache_context: bool,
    ) -> list[dict]:
        """Build messages list with optional caching."""
        if context and cache_context and self.config.enable_caching:
            # Use cache_control for context
            return [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": context,
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        elif context:
            return [{
                "role": "user",
                "content": f"{context}\n\n---\n\n{prompt}"
            }]
        else:
            return [{"role": "user", "content": prompt}]

    async def _make_request(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None,
    ):
        """Make API request to Claude."""
        kwargs = {
            "model": self.config.model,
            "max_tokens": 4096,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        if system:
            kwargs["system"] = system

        return await self.async_client.messages.create(**kwargs)

    async def _execute_tools(self, content: list) -> list[dict]:
        """Execute tool calls and return results."""
        results = []

        for block in content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                # Track tool call
                self._tool_calls.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "timestamp": datetime.now().isoformat(),
                })

                # Execute tool
                try:
                    result = await self._run_tool(tool_name, tool_input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                except Exception as e:
                    logger.error(f"Tool execution error: {tool_name}: {e}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {str(e)}",
                        "is_error": True,
                    })

        return results

    async def _run_tool(self, name: str, input_data: dict) -> str:
        """Run a specific tool by name."""
        # Import tool registry (circular import protection)
        from sdk_tools import TOOL_REGISTRY

        if name not in TOOL_REGISTRY:
            return f"Error: Unknown tool '{name}'"

        tool_fn = TOOL_REGISTRY[name]
        return await tool_fn(**input_data)

    def _parse_output(
        self,
        content: list,
        schema: type[T],
    ) -> T:
        """Parse response into structured output."""
        for block in content:
            if hasattr(block, "text"):
                text = block.text

                # Try to extract JSON
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]

                # Parse and validate
                data = json.loads(text.strip())
                return schema(**data)

        raise ValueError("No parseable output found in response")


# ============================================
# SIMPLE COMPLETION (Non-Agentic)
# ============================================


class SDKSimpleClient:
    """
    Simple Claude client for non-agentic tasks.

    Use this for:
    - Intent classification
    - Simple Q&A
    - Template filling

    Does NOT support tools or multi-turn loops.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-haiku-20241022",
        spend_tracker: Any | None = None,
    ):
        self._api_key = api_key
        self.model = model
        self._client: AsyncAnthropic | None = None
        self._spend_tracker = spend_tracker

    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Simple completion without tools.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Max output tokens
            temperature: Sampling temperature

        Returns:
            Dict with content, cost, tokens
        """
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )

        # Calculate cost
        pricing = MODEL_PRICING.get(self.model, MODEL_PRICING["claude-3-5-haiku-20241022"])
        cost = (
            (response.usage.input_tokens / 1_000_000) * pricing["input"]
            + (response.usage.output_tokens / 1_000_000) * pricing["output"]
        )

        # Track spend
        if self._spend_tracker:
            await self._spend_tracker.add_spend(cost)

        content = ""
        if response.content and len(response.content) > 0:
            content = response.content[0].text

        return {
            "content": content,
            "cost_aud": cost,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": self.model,
        }


# ============================================
# FACTORY FUNCTIONS
# ============================================


def create_sdk_brain(
    agent_type: str,
    api_key: str | None = None,
    spend_tracker: Any | None = None,
) -> SDKBrain:
    """
    Factory function to create SDK Brain with agent-specific config.

    Args:
        agent_type: Type of agent (enrichment, email, voice_kb, objection)
        api_key: Anthropic API key
        spend_tracker: Redis spend tracker

    Returns:
        Configured SDKBrain instance
    """
    configs = {
        "enrichment": SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=10,
            max_cost_aud=1.50,
            timeout_seconds=120,
        ),
        "email": SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=5,
            max_cost_aud=0.50,
            timeout_seconds=60,
        ),
        "voice_kb": SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=15,
            max_cost_aud=2.00,
            timeout_seconds=180,
        ),
        "objection": SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=5,
            max_cost_aud=0.50,
            timeout_seconds=60,
        ),
        "classification": SDKBrainConfig(
            model="claude-3-5-haiku-20241022",
            max_turns=1,
            max_cost_aud=0.10,
            timeout_seconds=30,
        ),
    }

    config = configs.get(agent_type, SDKBrainConfig())

    return SDKBrain(
        config=config,
        api_key=api_key,
        spend_tracker=spend_tracker,
    )


def create_simple_client(
    task_type: str = "classification",
    api_key: str | None = None,
    spend_tracker: Any | None = None,
) -> SDKSimpleClient:
    """
    Factory function to create simple client for non-agentic tasks.

    Args:
        task_type: Type of task (determines model)
        api_key: Anthropic API key
        spend_tracker: Redis spend tracker

    Returns:
        Configured SDKSimpleClient instance
    """
    # Route to appropriate model
    haiku_tasks = ["classification", "sentiment", "extraction", "template_selection"]

    if task_type in haiku_tasks:
        model = "claude-3-5-haiku-20241022"
    else:
        model = "claude-sonnet-4-20250514"

    return SDKSimpleClient(
        api_key=api_key,
        model=model,
        spend_tracker=spend_tracker,
    )
