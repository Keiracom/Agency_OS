"""
FILE: src/agents/base_agent.py
PURPOSE: Pydantic AI base agent with shared functionality
PHASE: 6 (Agents)
TASK: AGT-001
DEPENDENCIES:
  - src/config/settings.py
  - src/integrations/anthropic.py
  - src/integrations/redis.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument (DI pattern)
  - Rule 15: AI spend limiter via Anthropic integration
  - Pydantic AI for type-safe validation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.integrations.anthropic import get_anthropic_client
from src.integrations.redis import ai_spend_tracker


# Type variable for agent result data
T = TypeVar("T")


class AgentContext(BaseModel):
    """
    Context passed to all agents.

    Contains database session, client info, and other shared data.
    """

    client_id: UUID | None = None
    campaign_id: UUID | None = None
    lead_id: UUID | None = None
    user_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


@dataclass
class AgentResult(Generic[T]):
    """
    Standardized result wrapper for all agent outputs.

    Similar to EngineResult but specific to agents.
    """

    success: bool
    data: T | None = None
    error: str | None = None
    reasoning: str | None = None
    confidence: float = 0.0
    tokens_used: int = 0
    cost_aud: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data: T,
        reasoning: str | None = None,
        confidence: float = 1.0,
        tokens_used: int = 0,
        cost_aud: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentResult[T]":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            reasoning=reasoning,
            confidence=confidence,
            tokens_used=tokens_used,
            cost_aud=cost_aud,
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentResult[T]":
        """Create a failed result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {},
        )


class BaseAgent(ABC):
    """
    Abstract base class for all Pydantic AI agents.

    Provides:
    - Anthropic model integration with spend limiting
    - Shared context handling
    - Result standardization
    - Token/cost tracking
    - Type-safe inputs/outputs
    """

    # Anthropic model configuration
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 0.7

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """
        Initialize base agent with configuration.

        Args:
            model: Model to use (defaults to Claude 3 Sonnet)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
        """
        self.model_name = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self.temperature = temperature or self.DEFAULT_TEMPERATURE

        # Create Anthropic model for Pydantic AI
        # Note: AnthropicModel reads api_key from ANTHROPIC_API_KEY env var
        self._model = AnthropicModel(self.model_name)

        # Reference to spend limiter
        self._spend_tracker = ai_spend_tracker

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and tracking."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining agent behavior."""
        pass

    @property
    def model(self) -> AnthropicModel:
        """Get the Anthropic model instance."""
        return self._model

    async def check_budget(self, estimated_tokens: int = 1000) -> bool:
        """
        Check if there's budget for an AI call.

        Args:
            estimated_tokens: Estimated tokens for the call

        Returns:
            True if budget available, False otherwise
        """
        # Estimate cost (using Claude 3 Sonnet rates)
        estimated_cost = (estimated_tokens / 1_000_000) * 18.0  # ~$18/M tokens avg
        remaining = await self._spend_tracker.get_remaining()
        return remaining >= estimated_cost

    async def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Record token usage and cost.

        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens used

        Returns:
            Cost in AUD
        """
        # Calculate cost (Claude 3 Sonnet rates in AUD)
        cost = (
            (input_tokens / 1_000_000) * 3.0  # $3/M input
            + (output_tokens / 1_000_000) * 15.0  # $15/M output
        )
        await self._spend_tracker.add_spend(cost)
        return cost

    async def get_spend_status(self) -> dict[str, Any]:
        """
        Get current AI spend status.

        Returns:
            Spend status with remaining budget
        """
        client = get_anthropic_client()
        return await client.get_spend_status()

    def create_agent(
        self,
        result_type: type[BaseModel] | None = None,
        deps_type: type | None = None,
    ) -> Agent:
        """
        Create a Pydantic AI agent instance.

        Args:
            result_type: Optional Pydantic model for structured output
            deps_type: Optional dependencies type

        Returns:
            Configured Agent instance
        """
        kwargs = {
            "model": self.model,
            "system_prompt": self.system_prompt,
        }

        if result_type:
            kwargs["result_type"] = result_type

        if deps_type:
            kwargs["deps_type"] = deps_type

        return Agent(**kwargs)

    async def validate_context(
        self,
        db: AsyncSession,
        context: AgentContext,
    ) -> tuple[bool, str | None]:
        """
        Validate agent context before execution.

        Args:
            db: Database session
            context: Agent context

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check budget
        if not await self.check_budget():
            return False, "AI spend limit exceeded"

        return True, None


class AgentDependencies(BaseModel):
    """
    Dependencies injected into agents.

    Contains database session and context for agent execution.
    """

    db: Any  # AsyncSession - using Any to avoid serialization issues
    context: AgentContext
    anthropic_client: Any = None  # Optional Anthropic client override

    class Config:
        arbitrary_types_allowed = True


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Pydantic AI integration (Agent, AnthropicModel)
# [x] Type-safe AgentContext and AgentResult
# [x] Abstract base class pattern
# [x] Budget checking via spend tracker (Rule 15)
# [x] Token/cost tracking
# [x] Agent factory method (create_agent)
# [x] Context validation
# [x] Dependency injection support
# [x] All functions have type hints
# [x] All functions have docstrings
