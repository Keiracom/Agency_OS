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
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from anthropic import Anthropic, AsyncAnthropic
from pydantic import BaseModel

from src.config.settings import settings

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
        "input": 4.65,  # $3 USD × 1.55
        "output": 23.25,  # $15 USD × 1.55
        "cached": 0.465,  # 90% discount on cached
    },
    "claude-3-5-haiku-20241022": {
        "input": 1.24,  # $0.80 USD × 1.55
        "output": 6.20,  # $4 USD × 1.55
        "cached": 0.124,
    },
    "claude-opus-4-5-20251101": {
        "input": 7.75,  # $5 USD × 1.55
        "output": 38.75,  # $25 USD × 1.55
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

        # Get API key from settings if not provided
        self._api_key = api_key or settings.anthropic_api_key

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
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Please format your response as valid JSON matching this schema:\n{output_schema.model_json_schema()}",
                            }
                        )
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
            return [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        elif context:
            return [{"role": "user", "content": f"{context}\n\n---\n\n{prompt}"}]
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
                self._tool_calls.append(
                    {
                        "tool": tool_name,
                        "input": tool_input,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                # Execute tool
                try:
                    result = await self._run_tool(tool_name, tool_input)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
                except Exception as e:
                    logger.error(f"Tool execution error: {tool_name}: {e}")
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True,
                        }
                    )

        return results

    async def _run_tool(self, name: str, input_data: dict) -> str:
        """Run a specific tool by name."""
        # Import tool registry (avoid circular import)
        from src.agents.sdk_agents.sdk_tools import TOOL_REGISTRY

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
        self._api_key = api_key or settings.anthropic_api_key
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
        cost = (response.usage.input_tokens / 1_000_000) * pricing["input"] + (
            response.usage.output_tokens / 1_000_000
        ) * pricing["output"]

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
        agent_type: Type of agent (icp_extraction, enrichment, email, voice_kb, objection)
        api_key: Anthropic API key
        spend_tracker: Redis spend tracker

    Returns:
        Configured SDKBrain instance
    """
    configs = {
        "icp_extraction": SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=12,
            max_cost_aud=1.00,
            timeout_seconds=180,
        ),
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


# ============================================
# SIEGE SDK INTELLIGENCE (Directive #144)
# ============================================


class SiegeSDKIntelligence:
    """
    Siege Waterfall v3 SDK Intelligence layer (Directive #144).

    Five decision points requiring Claude intelligence:
    1. ABN-GMB name resolution (~20% leads, Sonnet 4)
    2. ICP edge case classification (~15% leads, Sonnet 4)
    3. Post hook scoring (Prop ≥70, Sonnet 4)
    4. Batch quality gate (per batch, Sonnet 4)
    5. Reply classification (all replies, Haiku)

    Cost limits:
    - MAX_COST_PER_CALL: $2.00 AUD
    - MAX_DAILY_COST: $50.00 AUD per Ignition customer
    """

    MAX_COST_PER_CALL = 2.00  # AUD
    MAX_DAILY_COST = 50.00  # AUD per Ignition customer

    # Reply intent categories (10 total)
    REPLY_INTENT_CATEGORIES = [
        "positive_interest",
        "meeting_request",
        "information_request",
        "objection_price",
        "objection_timing",
        "objection_competitor",
        "not_decision_maker",
        "unsubscribe",
        "out_of_office",
        "negative_response",
    ]

    def __init__(
        self,
        spend_tracker=None,
        api_key: str | None = None,
    ):
        """
        Initialize Siege SDK Intelligence.

        Args:
            spend_tracker: Redis spend tracker for daily limits
            api_key: Anthropic API key (uses settings if not provided)
        """
        self._spend_tracker = spend_tracker
        self._api_key = api_key or settings.anthropic_api_key

        # Sonnet 4 for complex decisions
        self._sonnet_config = SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=1,
            max_cost_aud=self.MAX_COST_PER_CALL,
            timeout_seconds=60,
        )

        # Haiku for classification
        self._haiku_config = SDKBrainConfig(
            model="claude-3-5-haiku-20241022",
            max_turns=1,
            max_cost_aud=0.10,
            timeout_seconds=30,
        )

    async def abn_gmb_name_resolution(
        self,
        abn_name: str,
        gmb_results: list[dict],
    ) -> str:
        """
        Decision Point 1: ABN-GMB name resolution.

        ~20% of leads require disambiguation between ABN trading names
        and GMB business names.

        Uses: Sonnet 4

        Args:
            abn_name: Business name from ABN registry
            gmb_results: List of GMB search results to match against

        Returns:
            Best matching GMB place_id or empty string if no match
        """
        if not gmb_results:
            return ""

        brain = SDKBrain(config=self._sonnet_config, api_key=self._api_key, spend_tracker=self._spend_tracker)

        prompt = f"""You are matching Australian business names between the ABN registry and Google Maps Business.

ABN Registry Name: "{abn_name}"

GMB Search Results:
{json.dumps([{"place_id": r.get("place_id"), "name": r.get("name"), "category": r.get("category")} for r in gmb_results[:10]], indent=2)}

Task: Identify which GMB result (if any) matches the ABN business. Consider:
- Trading names vs legal names (e.g., "Joe's Plumbing" vs "Smith Plumbing Pty Ltd")
- Common abbreviations and variations
- Industry/category alignment

Return ONLY the place_id of the best match, or "NO_MATCH" if none are confident matches.
Do not explain. Just the place_id or "NO_MATCH"."""

        try:
            response = await brain.async_client.messages.create(
                model=self._sonnet_config.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )

            result = response.content[0].text.strip()
            if result == "NO_MATCH":
                return ""
            return result

        except Exception as e:
            logger.warning(f"[SiegeSDK] ABN-GMB resolution failed: {e}")
            return ""

    async def icp_edge_case_classification(
        self,
        lead_data: dict,
        icp_config: dict,
    ) -> bool:
        """
        Decision Point 2: ICP edge case classification.

        ~15% of leads have ambiguous industry categories requiring
        SDK classification.

        Uses: Sonnet 4

        Args:
            lead_data: Lead data with company info
            icp_config: ICP configuration with target criteria

        Returns:
            True if lead passes ICP, False otherwise
        """
        brain = SDKBrain(config=self._sonnet_config, api_key=self._api_key, spend_tracker=self._spend_tracker)

        prompt = f"""You are an ICP (Ideal Customer Profile) classifier for B2B lead qualification.

Lead Data:
- Company: {lead_data.get("company_name")}
- Industry: {lead_data.get("company_industry")}
- Category: {lead_data.get("category") or lead_data.get("gmb_category")}
- Employee Count: {lead_data.get("company_employee_count")}
- Country: {lead_data.get("company_country")}

ICP Criteria:
- Target Industries: {icp_config.get("industries", [])}
- Employee Range: {icp_config.get("employee_range", {})}
- Target Countries: {icp_config.get("countries", [])}

Task: Determine if this lead matches the ICP. Consider:
- Industry variations (e.g., "IT Services" could match "Technology")
- Related industries that would benefit from the service
- Company size fit with some flexibility

Return ONLY "PASS" or "FAIL". Do not explain."""

        try:
            response = await brain.async_client.messages.create(
                model=self._sonnet_config.model,
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )

            result = response.content[0].text.strip().upper()
            return result == "PASS"

        except Exception as e:
            logger.warning(f"[SiegeSDK] ICP classification failed: {e}")
            return False  # Fail safe

    async def post_hook_scoring(
        self,
        lead_data: dict,
        post_streams: dict[str, list[dict]],
    ) -> tuple[str, str]:
        """
        Decision Point 3: Post hook scoring.

        For leads with Propensity ≥70, score all 4 post streams and
        identify the best hook for personalized outreach.

        Uses: Sonnet 4

        Args:
            lead_data: Lead data with company/person info
            post_streams: Dict with keys: dm_linkedin_posts, company_linkedin_posts,
                         gmb_reviews, x_posts

        Returns:
            Tuple of (best_hook: str, source: str)
        """
        # Build prompt with all post streams
        streams_text = ""
        for source, posts in post_streams.items():
            if posts:
                streams_text += f"\n{source.upper()}:\n"
                for i, post in enumerate(posts[:5]):  # Max 5 per stream
                    content = post.get("text") or post.get("content") or post.get("review_text", "")[:200]
                    streams_text += f"  {i+1}. {content[:200]}...\n"

        if not streams_text.strip():
            return "", "none"

        brain = SDKBrain(config=self._sonnet_config, api_key=self._api_key, spend_tracker=self._spend_tracker)

        prompt = f"""You are a sales hook generator for personalized B2B outreach.

Lead Info:
- Name: {lead_data.get("first_name")} {lead_data.get("last_name")}
- Title: {lead_data.get("title")}
- Company: {lead_data.get("company_name")}

Recent Activity Streams:
{streams_text}

Task: Identify the SINGLE BEST hook from the posts/reviews above for personalized outreach.
The hook should be:
- Specific and recent (not generic)
- Something they'd be proud of or interested in discussing
- Natural conversation starter

Return in this exact format:
HOOK: <one sentence hook>
SOURCE: <dm_linkedin_posts|company_linkedin_posts|gmb_reviews|x_posts>"""

        try:
            response = await brain.async_client.messages.create(
                model=self._sonnet_config.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            result = response.content[0].text.strip()
            lines = result.split("\n")

            hook = ""
            source = "none"

            for line in lines:
                if line.startswith("HOOK:"):
                    hook = line.replace("HOOK:", "").strip()
                elif line.startswith("SOURCE:"):
                    source = line.replace("SOURCE:", "").strip().lower()

            return hook, source

        except Exception as e:
            logger.warning(f"[SiegeSDK] Post hook scoring failed: {e}")
            return "", "none"

    async def batch_quality_gate(
        self,
        batch_leads: list[dict],
        campaign_config: dict,
    ) -> tuple[bool, str]:
        """
        Decision Point 4: Batch quality gate.

        Per batch, evaluate if the distribution of leads is sufficient
        for the agency guarantee (e.g., enough hot leads, coverage).

        Uses: Sonnet 4

        Args:
            batch_leads: List of leads with scores
            campaign_config: Campaign configuration with guarantees

        Returns:
            Tuple of (passes_gate: bool, reason: str)
        """
        # Calculate distribution
        tier_counts = {"hot": 0, "warm": 0, "cool": 0, "cold": 0, "dead": 0}
        for lead in batch_leads:
            tier = lead.get("als_tier") or lead.get("tier") or "cold"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        avg_reachability = sum(l.get("reachability", 0) for l in batch_leads) / len(batch_leads) if batch_leads else 0
        avg_propensity = sum(l.get("propensity", 0) for l in batch_leads) / len(batch_leads) if batch_leads else 0

        brain = SDKBrain(config=self._sonnet_config, api_key=self._api_key, spend_tracker=self._spend_tracker)

        prompt = f"""You are evaluating a batch of leads for agency guarantee compliance.

Batch Statistics:
- Total Leads: {len(batch_leads)}
- Tier Distribution: {json.dumps(tier_counts)}
- Average Reachability: {avg_reachability:.1f}
- Average Propensity: {avg_propensity:.1f}

Campaign Requirements:
- Target Lead Count: {campaign_config.get("target_lead_count", 100)}
- Minimum Qualified %: {campaign_config.get("min_qualified_pct", 70)}%
- Required Hot Leads: {campaign_config.get("min_hot_leads", 10)}

Task: Evaluate if this batch meets the quality threshold for delivery.
Consider:
- Is there sufficient hot/warm lead coverage?
- Are reachability scores adequate for outreach?
- Does the batch meet minimum qualified percentage?

Return in this exact format:
VERDICT: <PASS|FAIL>
REASON: <one sentence explanation>"""

        try:
            response = await brain.async_client.messages.create(
                model=self._sonnet_config.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )

            result = response.content[0].text.strip()
            lines = result.split("\n")

            passes = False
            reason = "Unable to evaluate batch quality"

            for line in lines:
                if line.startswith("VERDICT:"):
                    verdict = line.replace("VERDICT:", "").strip().upper()
                    passes = verdict == "PASS"
                elif line.startswith("REASON:"):
                    reason = line.replace("REASON:", "").strip()

            return passes, reason

        except Exception as e:
            logger.warning(f"[SiegeSDK] Batch quality gate failed: {e}")
            return False, f"Evaluation error: {str(e)}"

    async def reply_classification(
        self,
        reply_text: str,
    ) -> str:
        """
        Decision Point 5: Reply classification.

        Classify all replies into one of 10 intent categories for
        automation routing.

        Uses: Haiku (fast and cheap)

        Args:
            reply_text: The reply text to classify

        Returns:
            One of REPLY_INTENT_CATEGORIES
        """
        simple_client = SDKSimpleClient(
            api_key=self._api_key,
            model=self._haiku_config.model,
            spend_tracker=self._spend_tracker,
        )

        prompt = f"""Classify this email/message reply into exactly one category.

Reply:
"{reply_text[:500]}"

Categories:
- positive_interest: Shows interest, wants to learn more
- meeting_request: Explicitly asks for or agrees to a meeting
- information_request: Asks for more info, pricing, details
- objection_price: Objects due to cost/budget concerns
- objection_timing: Objects due to timing (not now, later)
- objection_competitor: Already using a competitor
- not_decision_maker: Says they're not the right person
- unsubscribe: Requests removal from list
- out_of_office: Auto-reply, vacation, OOO message
- negative_response: Clear rejection, not interested

Return ONLY the category name. Nothing else."""

        try:
            result = await simple_client.complete(prompt=prompt, max_tokens=30)
            category = result["content"].strip().lower().replace(" ", "_")

            # Validate category
            if category in self.REPLY_INTENT_CATEGORIES:
                return category

            # Fuzzy match
            for valid_cat in self.REPLY_INTENT_CATEGORIES:
                if valid_cat in category or category in valid_cat:
                    return valid_cat

            return "negative_response"  # Default fallback

        except Exception as e:
            logger.warning(f"[SiegeSDK] Reply classification failed: {e}")
            return "negative_response"

    # =========================================================================
    # CIS LEARNING ENGINE (Directive #147)
    # =========================================================================

    async def analyze_cis_outcomes(
        self,
        outcomes: list[dict],
        current_weights: dict,
    ) -> dict:
        """
        Directive #147: CIS Learning Engine analysis.

        Analyze outcome data to recommend propensity weight adjustments.
        This is the core of the continuous improvement system — the moat.

        Cost cap: $2 AUD per run.

        Args:
            outcomes: List of outcome records with signals_active
            current_weights: Current weights from ceo:propensity_weights_v3

        Returns:
            {
                "adjustments": {
                    "signal_name": {"delta": int, "confidence": float, "reasoning": str}
                },
                "total_outcomes": int,
                "meeting_booked_count": int,
                "analysis_summary": str
            }
        """
        # Segment outcomes by type
        meeting_outcomes = [o for o in outcomes if o.get("outcome_type") == "booked"]
        non_converting = [o for o in outcomes if o.get("outcome_type") in ("no_response", "bounced")]
        
        # Gap 2 fix (Directive #157): Include negative signals for CIS learning
        # These indicate what NOT to do and should inform weight DECREASES
        data_quality_failures = [o for o in outcomes if o.get("final_outcome") == "data_quality_failure"]
        targeting_failures = [o for o in outcomes if o.get("final_outcome") == "targeting_failure"]
        soft_rejections = [o for o in outcomes if o.get("final_outcome") == "soft_rejection"]
        
        # Total negative signals for analysis
        total_negative = len(data_quality_failures) + len(targeting_failures) + len(soft_rejections)

        prompt = f"""You are the CIS (Continuous Improvement System) analyst for Agency OS.

TASK: Analyze outcome data to recommend propensity weight adjustments.

CURRENT WEIGHTS:
{json.dumps(current_weights, indent=2)}

MEETING_BOOKED OUTCOMES ({len(meeting_outcomes)} total):
{json.dumps([{"signals_active": o.get("signals_active"), "propensity_at_send": o.get("propensity_at_send")} for o in meeting_outcomes[:50]], indent=2)}

NON-CONVERTING OUTCOMES (sample of {min(50, len(non_converting))}):
{json.dumps([{"signals_active": o.get("signals_active"), "propensity_at_send": o.get("propensity_at_send")} for o in non_converting[:50]], indent=2)}

NEGATIVE SIGNAL OUTCOMES (Gap 2 - IMPORTANT FOR LEARNING):
These outcomes indicate what NOT to target. Signals present here should have weights DECREASED.

Data Quality Failures ({len(data_quality_failures)} bounced emails - bad enrichment data):
{json.dumps([{"signals_active": o.get("signals_active"), "propensity_at_send": o.get("propensity_at_send")} for o in data_quality_failures[:20]], indent=2)}

Targeting Failures ({len(targeting_failures)} spam complaints - wrong ICP or message):
{json.dumps([{"signals_active": o.get("signals_active"), "propensity_at_send": o.get("propensity_at_send")} for o in targeting_failures[:20]], indent=2)}

Soft Rejections ({len(soft_rejections)} unsubscribes - low fit):
{json.dumps([{"signals_active": o.get("signals_active"), "propensity_at_send": o.get("propensity_at_send")} for o in soft_rejections[:20]], indent=2)}

ANALYSIS REQUIRED:
1. Which signals in signals_active appeared frequently in MEETING_BOOKED outcomes? → INCREASE weights
2. Which signals appeared frequently in non-converting leads? → Consider decreasing weights
3. Which signals appeared frequently in NEGATIVE SIGNAL outcomes (bounced/spam/unsub)? → DECREASE weights
   - Targeting failures (spam) are the strongest negative signal - leads with these signals should be avoided
   - Soft rejections (unsubs) indicate lower fit - moderate weight decrease
   - Data quality failures indicate enrichment issues, not necessarily targeting issues

CONSTRAINTS:
- Max delta: ±5 points per signal
- Only recommend adjustments with confidence >= 0.7
- If insufficient data for a signal, skip it
- Preserve relative balance of weights
- NEGATIVE SIGNALS MUST DECREASE WEIGHTS - they indicate what NOT to do

RESPONSE FORMAT (JSON only):
{{
    "adjustments": {{
        "signal_name": {{"delta": -3, "confidence": 0.85, "reasoning": "Appeared in 80% of spam complaints (targeting_failure)"}}
    }},
    "analysis_summary": "Brief summary of patterns found",
    "negative_signal_insights": "What we learned from bounces/spam/unsubs"
}}

Respond with JSON only, no markdown."""

        try:
            # Call Claude Sonnet 4 with cost cap
            response = await self._call_claude_with_cost_cap(
                prompt=prompt,
                model="claude-sonnet-4-20250514",
                max_cost_usd=2.0,
                max_tokens=2000,
            )

            result = json.loads(response)

            # Add metadata
            result["total_outcomes"] = len(outcomes)
            result["meeting_booked_count"] = len(meeting_outcomes)
            # Gap 2 fix: Include negative signal counts
            result["negative_signal_counts"] = {
                "data_quality_failure": len(data_quality_failures),
                "targeting_failure": len(targeting_failures),
                "soft_rejection": len(soft_rejections),
                "total": total_negative,
            }

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[SiegeSDK] CIS analysis returned invalid JSON: {e}")
            return {
                "adjustments": {},
                "total_outcomes": len(outcomes),
                "meeting_booked_count": len(meeting_outcomes),
                "negative_signal_counts": {
                    "data_quality_failure": len(data_quality_failures),
                    "targeting_failure": len(targeting_failures),
                    "soft_rejection": len(soft_rejections),
                    "total": total_negative,
                },
                "analysis_summary": f"Analysis failed: invalid JSON response - {str(e)}",
            }
        except Exception as e:
            logger.error(f"[SiegeSDK] CIS outcome analysis failed: {e}")
            return {
                "adjustments": {},
                "total_outcomes": len(outcomes),
                "meeting_booked_count": len(meeting_outcomes),
                "negative_signal_counts": {
                    "data_quality_failure": len(data_quality_failures),
                    "targeting_failure": len(targeting_failures),
                    "soft_rejection": len(soft_rejections),
                    "total": total_negative,
                },
                "analysis_summary": f"Analysis failed: {str(e)}",
            }

    async def _call_claude_with_cost_cap(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        max_cost_usd: float = 2.0,
        max_tokens: int = 2000,
    ) -> str:
        """
        Call Claude with a cost cap.

        Converts USD cost cap to AUD and enforces limits.

        Args:
            prompt: The prompt to send
            model: Model to use
            max_cost_usd: Maximum cost in USD
            max_tokens: Maximum output tokens

        Returns:
            Response text content

        Raises:
            ValueError: If cost would exceed cap
        """
        # Convert USD to AUD (approx 1.55 conversion rate)
        max_cost_aud = max_cost_usd * 1.55

        # Check daily budget first
        if self._spend_tracker:
            remaining = await self._spend_tracker.get_remaining()
            if remaining < max_cost_aud:
                raise ValueError(f"Insufficient daily budget: ${remaining:.2f} AUD remaining")

        # Create brain with cost limit
        config = SDKBrainConfig(
            model=model,
            max_turns=1,
            max_cost_aud=max_cost_aud,
            timeout_seconds=120,
        )

        brain = SDKBrain(
            config=config,
            api_key=self._api_key,
            spend_tracker=self._spend_tracker,
        )

        # Make the request
        response = await brain.async_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        # Calculate and track cost
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-20250514"])
        cost = (
            (response.usage.input_tokens / 1_000_000) * pricing["input"]
            + (response.usage.output_tokens / 1_000_000) * pricing["output"]
        )

        if self._spend_tracker:
            await self._spend_tracker.add_spend(cost)

        logger.info(
            f"[SiegeSDK] CIS analysis cost: ${cost:.4f} AUD "
            f"(in: {response.usage.input_tokens}, out: {response.usage.output_tokens})"
        )

        # Extract text content
        if response.content and len(response.content) > 0:
            return response.content[0].text

        raise ValueError("Empty response from Claude")


# Singleton instances
_sdk_brain: SDKBrain | None = None
_simple_client: SDKSimpleClient | None = None
_siege_intelligence: SiegeSDKIntelligence | None = None


def get_sdk_brain(agent_type: str = "enrichment") -> SDKBrain:
    """Get or create SDK Brain singleton."""
    global _sdk_brain
    if _sdk_brain is None:
        _sdk_brain = create_sdk_brain(agent_type)
    return _sdk_brain


def get_simple_client(task_type: str = "classification") -> SDKSimpleClient:
    """Get or create simple client singleton."""
    global _simple_client
    if _simple_client is None:
        _simple_client = create_simple_client(task_type)
    return _simple_client


def get_siege_intelligence(spend_tracker=None) -> SiegeSDKIntelligence:
    """
    Get or create Siege SDK Intelligence singleton.

    Siege Waterfall v3 (Directive #144).

    Args:
        spend_tracker: Optional Redis spend tracker

    Returns:
        SiegeSDKIntelligence instance
    """
    global _siege_intelligence
    if _siege_intelligence is None:
        _siege_intelligence = SiegeSDKIntelligence(spend_tracker=spend_tracker)
    return _siege_intelligence
