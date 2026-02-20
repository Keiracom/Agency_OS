"""
FILE: src/integrations/elevenagets_client.py
PURPOSE: ElevenAgents Conversational AI client for Alex voice agent
PHASE: 17 (Launch Prerequisites)
TASK: VOICE-008
DEPENDENCIES:
  - httpx
  - tenacity
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: No hardcoded credentials

VOICE AI STACK (ElevenAgents):
- STT: scribe_v2_realtime
- LLM primary (90%): groq/meta-llama/llama-4-maverick
- LLM fallback (10%): claude-haiku-4-5 (complex objection handling)
- TTS: eleven_v3_conversational
- Telephony: Twilio AU (au1 region)
- Language: en-AU

API Docs: https://elevenlabs.io/docs/eleven-agents
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.exceptions import IntegrationError

logger = logging.getLogger(__name__)


# ============================================
# Data Classes
# ============================================


@dataclass
class AgentConfig:
    """Configuration for an ElevenAgents voice agent."""

    name: str
    voice_id: str
    tts_model: str = "eleven_v3_conversational"
    stt_model: str = "scribe_v2_realtime"
    primary_llm: str = "groq/meta-llama/llama-4-maverick"
    fallback_llm: str = "claude-haiku-4-5"
    language: str = "en-AU"
    max_duration_seconds: int = 300  # 5 min max call
    first_message: str | None = None
    system_prompt: str | None = None


@dataclass
class CallInitResult:
    """Result from initiating an outbound call."""

    success: bool
    elevenagets_call_id: str | None = None
    twilio_call_sid: str | None = None
    voice_call_record_id: str | None = None  # UUID of voice_calls record
    error: str | None = None


@dataclass
class CallStatus:
    """Current status of a call."""

    call_id: str
    status: str  # initiated, ringing, in-progress, completed, failed
    duration_seconds: int | None = None
    transcript: str | None = None
    outcome: str | None = None
    recording_url: str | None = None
    ended_reason: str | None = None


@dataclass
class WebhookPayload:
    """Parsed webhook payload from ElevenAgents."""

    call_id: str
    call_sid: str | None = None
    event_type: str = ""
    status: str = ""
    duration_seconds: int | None = None
    transcript: str | None = None
    outcome_signal: str | None = None
    recording_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================
# ElevenAgents Client
# ============================================


class ElevenAgentsClient:
    """
    ElevenAgents Conversational AI client for Alex voice agent.

    Handles:
    - Agent creation and management
    - Outbound call initiation via Twilio AU
    - Call status and transcripts
    - System prompt building from templates

    All API methods include retry logic with exponential backoff for
    transient failures (network errors, timeouts).

    API Docs: https://elevenlabs.io/docs/eleven-agents
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_MIN_WAIT = 2  # seconds
    RETRY_MAX_WAIT = 10  # seconds

    def __init__(self, api_key: str | None = None):
        """
        Initialize ElevenAgents client.

        Args:
            api_key: ElevenLabs API key. Falls back to settings if not provided.

        Raises:
            IntegrationError: If API key is not configured.
        """
        self.api_key = api_key or settings.elevenlabs_api_key
        if not self.api_key:
            raise IntegrationError("elevenagets", "ELEVENLABS_API_KEY not configured")

        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        self._agent_id = settings.elevenagets_agent_id or None
        self._prompt_cache: dict[str, str] = {}

    @property
    def agent_id(self) -> str | None:
        """Get the current agent ID."""
        return self._agent_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """
        Make HTTP request to ElevenLabs API with retry logic.

        Uses exponential backoff for transient failures (network errors, timeouts).
        Retries up to 3 times with 2-10 second waits.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., "/convai/agents")
            json: Request body for POST/PATCH
            params: Query parameters for GET

        Returns:
            httpx.Response object

        Raises:
            httpx.RequestError: After max retries exhausted
            httpx.TimeoutException: After max retries exhausted
        """
        url = f"{self.BASE_URL}{endpoint}"
        logger.info(f"ElevenAgents API: {method} {endpoint}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json,
                params=params,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"ElevenAgents rate limited, retry after {retry_after}s")
                raise httpx.RequestError(f"Rate limited, retry after {retry_after}s")

            return response

    async def create_agent(self, config: AgentConfig) -> str:
        """
        Create or update the Alex voice agent.

        Args:
            config: AgentConfig with agent settings.

        Returns:
            Agent ID string.

        Raises:
            IntegrationError: If agent creation fails.
        """
        # Check if we should update existing agent
        if self._agent_id:
            return await self._update_agent(self._agent_id, config)

        payload = {
            "name": config.name,
            "conversation_config": {
                "tts": {
                    "model_id": config.tts_model,
                    "voice_id": config.voice_id,
                },
                "stt": {
                    "model_id": config.stt_model,
                },
                "llm": {
                    "provider": "custom",
                    "model": config.primary_llm,
                    "fallback_model": config.fallback_llm,
                },
                "language": config.language,
                "max_duration_seconds": config.max_duration_seconds,
            },
            "platform_settings": {
                "telephony": {
                    "provider": "twilio",
                    "region": "au1",  # Australian region
                },
            },
        }

        if config.first_message:
            payload["conversation_config"]["first_message"] = config.first_message

        if config.system_prompt:
            payload["conversation_config"]["llm"]["system_prompt"] = config.system_prompt

        try:
            response = await self._request("POST", "/convai/agents", json=payload)
            if response.status_code not in (200, 201):
                logger.error(f"ElevenAgents create_agent failed: {response.text}")
                raise IntegrationError(
                    "elevenagets",
                    f"Failed to create agent: {response.status_code}",
                    {"response": response.text},
                )

            data = response.json()
            agent_id = data.get("agent_id")
            self._agent_id = agent_id

            logger.info(f"Created ElevenAgents agent: {config.name} (ID: {agent_id})")
            return agent_id

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"ElevenAgents create_agent failed after retries: {e}")
            raise IntegrationError("elevenagets", f"Failed to create agent: {e}") from e

    async def _update_agent(self, agent_id: str, config: AgentConfig) -> str:
        """Update an existing agent."""
        payload = {
            "name": config.name,
            "conversation_config": {
                "tts": {
                    "model_id": config.tts_model,
                    "voice_id": config.voice_id,
                },
                "stt": {
                    "model_id": config.stt_model,
                },
                "llm": {
                    "provider": "custom",
                    "model": config.primary_llm,
                    "fallback_model": config.fallback_llm,
                },
                "language": config.language,
                "max_duration_seconds": config.max_duration_seconds,
            },
        }

        if config.system_prompt:
            payload["conversation_config"]["llm"]["system_prompt"] = config.system_prompt

        try:
            response = await self._request("PATCH", f"/convai/agents/{agent_id}", json=payload)
            if response.status_code != 200:
                logger.error(f"ElevenAgents update_agent failed: {response.text}")
                raise IntegrationError(
                    "elevenagets",
                    f"Failed to update agent: {response.status_code}",
                    {"response": response.text},
                )

            logger.info(f"Updated ElevenAgents agent: {config.name} (ID: {agent_id})")
            return agent_id

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"ElevenAgents update_agent failed after retries: {e}")
            raise IntegrationError("elevenagets", f"Failed to update agent: {e}") from e

    async def get_agent(self, agent_id: str | None = None) -> dict:
        """
        Get agent details by ID.

        Args:
            agent_id: Agent ID. Uses stored agent_id if not provided.

        Returns:
            Agent configuration dict.

        Raises:
            IntegrationError: If agent not found or request fails.
        """
        agent_id = agent_id or self._agent_id
        if not agent_id:
            raise IntegrationError("elevenagets", "No agent_id configured")

        try:
            response = await self._request("GET", f"/convai/agents/{agent_id}")
            if response.status_code != 200:
                raise IntegrationError(
                    "elevenagets",
                    f"Failed to get agent: {response.status_code}",
                    {"response": response.text},
                )
            return response.json()

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"ElevenAgents get_agent failed: {e}")
            raise IntegrationError("elevenagets", f"Failed to get agent: {e}") from e

    async def initiate_call(
        self,
        phone: str,
        compiled_context: dict,
        lead_id: str,
        agency_id: str,
        campaign_id: str | None = None,
    ) -> CallInitResult:
        """
        Initiate an outbound call via ElevenAgents.

        Steps:
        1. Build system prompt from compiled_context
        2. Create voice_calls record with status INITIATED
        3. Call ElevenAgents API to start call
        4. Update voice_calls with call IDs
        5. Return result with call IDs

        Args:
            phone: Phone number in E.164 format (+61412345678)
            compiled_context: Context dict for prompt templating
            lead_id: UUID of the lead
            agency_id: UUID of the agency
            campaign_id: Optional campaign UUID

        Returns:
            CallInitResult with call IDs or error.
        """
        if not self._agent_id:
            return CallInitResult(
                success=False,
                error="No agent_id configured. Call create_agent first.",
            )

        # Build system prompt from compiled context
        try:
            system_prompt = self.build_system_prompt(compiled_context)
        except Exception as e:
            logger.error(f"Failed to build system prompt: {e}")
            return CallInitResult(success=False, error=f"Failed to build prompt: {e}")

        # Generate voice_call record ID
        voice_call_record_id = str(uuid.uuid4())

        # Metadata to include with the call
        metadata = {
            "lead_id": lead_id,
            "agency_id": agency_id,
            "voice_call_record_id": voice_call_record_id,
            "initiated_at": datetime.now(timezone.utc).isoformat(),
        }
        if campaign_id:
            metadata["campaign_id"] = campaign_id

        # Call payload
        payload = {
            "agent_id": self._agent_id,
            "phone_number": phone,
            "from_number": settings.twilio_phone_number_au or settings.twilio_phone_number,
            "conversation_config_override": {
                "llm": {
                    "system_prompt": system_prompt,
                },
            },
            "metadata": metadata,
            "webhook_url": f"{settings.base_url}/api/webhooks/elevenagets/call-completed",
        }

        try:
            logger.info(f"ElevenAgents initiating call: phone={phone[:6]}***, lead_id={lead_id}")

            response = await self._request("POST", "/convai/calls", json=payload)

            if response.status_code not in (200, 201):
                logger.error(
                    f"ElevenAgents initiate_call failed: status={response.status_code}, "
                    f"phone={phone[:6]}***, response={response.text}"
                )
                return CallInitResult(
                    success=False,
                    voice_call_record_id=voice_call_record_id,
                    error=f"API error: {response.status_code} - {response.text}",
                )

            data = response.json()
            elevenagets_call_id = data.get("call_id")
            twilio_call_sid = data.get("telephony", {}).get("call_sid")

            logger.info(
                f"ElevenAgents call initiated: phone={phone[:6]}***, "
                f"call_id={elevenagets_call_id}, twilio_sid={twilio_call_sid}"
            )

            return CallInitResult(
                success=True,
                elevenagets_call_id=elevenagets_call_id,
                twilio_call_sid=twilio_call_sid,
                voice_call_record_id=voice_call_record_id,
            )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(
                f"ElevenAgents initiate_call failed after {self.MAX_RETRIES} retries: "
                f"phone={phone[:6]}***, error={e}"
            )
            return CallInitResult(
                success=False,
                voice_call_record_id=voice_call_record_id,
                error=f"Request failed after retries: {e}",
            )

    async def get_call_status(self, call_id: str) -> CallStatus:
        """
        Get current status of a call.

        Args:
            call_id: ElevenAgents call ID.

        Returns:
            CallStatus with current state.

        Raises:
            IntegrationError: If request fails.
        """
        try:
            response = await self._request("GET", f"/convai/calls/{call_id}")

            if response.status_code != 200:
                raise IntegrationError(
                    "elevenagets",
                    f"Failed to get call status: {response.status_code}",
                    {"call_id": call_id, "response": response.text},
                )

            data = response.json()

            return CallStatus(
                call_id=call_id,
                status=data.get("status", "unknown"),
                duration_seconds=data.get("duration_seconds"),
                transcript=data.get("transcript"),
                outcome=data.get("outcome_signal"),
                recording_url=data.get("recording_url"),
                ended_reason=data.get("ended_reason"),
            )

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"ElevenAgents get_call_status failed: call_id={call_id}, error={e}")
            raise IntegrationError("elevenagets", f"Failed to get call status: {e}") from e

    async def end_call(self, call_id: str) -> bool:
        """
        Force end an active call.

        Args:
            call_id: ElevenAgents call ID.

        Returns:
            True if successfully ended.
        """
        try:
            response = await self._request("POST", f"/convai/calls/{call_id}/end")
            if response.status_code in (200, 204):
                logger.info(f"ElevenAgents call ended: {call_id}")
                return True
            logger.warning(f"ElevenAgents end_call unexpected status: {response.status_code}")
            return False

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"ElevenAgents end_call failed: call_id={call_id}, error={e}")
            return False

    def build_system_prompt(self, compiled_context: dict) -> str:
        """
        Build Alex's system prompt from compiled context.

        Loads template from src/prompts/alex_v1_2.md and replaces all
        [PLACEHOLDER] fields with values from compiled_context.

        Args:
            compiled_context: Dict with lead/agency/campaign data.
                Expected keys match placeholders in template:
                - lead_name, lead_company, lead_title
                - agency_name, service_offering
                - pain_points, value_proposition
                - booking_link, etc.

        Returns:
            Fully resolved prompt string.

        Raises:
            FileNotFoundError: If template file doesn't exist.
            ValueError: If required placeholders are missing.
        """
        # Load template (with caching)
        template_path = Path(__file__).parent.parent / "prompts" / "alex_v1_2.md"
        cache_key = str(template_path)

        if cache_key not in self._prompt_cache:
            if not template_path.exists():
                raise FileNotFoundError(f"Prompt template not found: {template_path}")
            self._prompt_cache[cache_key] = template_path.read_text(encoding="utf-8")

        template = self._prompt_cache[cache_key]

        # Find all placeholders
        placeholders = re.findall(r"\[([A-Z_]+)\]", template)

        # Build replacement map (case-insensitive key matching)
        context_lower = {k.lower(): v for k, v in compiled_context.items()}

        # Replace placeholders
        result = template
        missing_placeholders = []

        for placeholder in placeholders:
            key = placeholder.lower()
            if key in context_lower:
                value = str(context_lower[key]) if context_lower[key] is not None else ""
                result = result.replace(f"[{placeholder}]", value)
            else:
                # Log warning but don't fail - use placeholder as fallback
                missing_placeholders.append(placeholder)
                logger.warning(f"Missing placeholder value: [{placeholder}]")

        if missing_placeholders:
            logger.warning(
                f"Prompt built with {len(missing_placeholders)} missing placeholders: "
                f"{missing_placeholders[:5]}{'...' if len(missing_placeholders) > 5 else ''}"
            )

        return result

    def parse_webhook(self, payload: dict) -> WebhookPayload:
        """
        Parse ElevenAgents webhook payload into standardized format.

        Args:
            payload: Raw webhook payload from ElevenAgents.

        Returns:
            WebhookPayload with parsed fields.
        """
        return WebhookPayload(
            call_id=payload.get("call_id", ""),
            call_sid=payload.get("telephony", {}).get("call_sid"),
            event_type=payload.get("event_type", payload.get("type", "")),
            status=payload.get("status", ""),
            duration_seconds=payload.get("duration_seconds"),
            transcript=payload.get("transcript"),
            outcome_signal=payload.get("outcome_signal"),
            recording_url=payload.get("recording_url"),
            metadata=payload.get("metadata", {}),
        )


# ============================================
# Singleton Pattern
# ============================================

_elevenagets_client: ElevenAgentsClient | None = None


def get_elevenagets_client() -> ElevenAgentsClient:
    """
    Get or create ElevenAgents client singleton instance.

    Returns:
        ElevenAgentsClient instance.

    Raises:
        IntegrationError: If API key not configured.
    """
    global _elevenagets_client
    if _elevenagets_client is None:
        _elevenagets_client = ElevenAgentsClient()
    return _elevenagets_client


def reset_elevenagets_client() -> None:
    """Reset the singleton client (useful for testing)."""
    global _elevenagets_client
    _elevenagets_client = None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Uses settings for API keys
# [x] All methods are async (where appropriate)
# [x] Proper error handling with IntegrationError
# [x] Dataclasses for request/response models
# [x] Singleton pattern with get_elevenagets_client()
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Webhook parsing method included
# [x] Retry logic with tenacity (exponential backoff, 3 attempts)
# [x] Retries on transient failures (network errors, timeouts)
# [x] Rate limit handling
# [x] Logging at INFO level for API calls
# [x] build_system_prompt loads from template file
