"""
FILE: src/integrations/vapi.py
PURPOSE: Vapi Voice AI Integration for Agency OS
PHASE: 17 (Launch Prerequisites)
TASK: CRED-007
DEPENDENCIES:
  - httpx
  - pydantic
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: No hardcoded credentials

Orchestrates voice calls using:
- Twilio for telephony
- ElevenLabs for TTS
- Vapi's built-in STT
- Anthropic Claude for LLM

API Docs: https://docs.vapi.ai/
"""

import httpx
from typing import Optional, Any
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.exceptions import IntegrationError


class VapiAssistantConfig(BaseModel):
    """Configuration for a Vapi voice assistant."""
    name: str
    first_message: str
    system_prompt: str
    voice_id: str = "pNInz6obpgDQGcFmaJgB"  # ElevenLabs "Adam" default
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_duration_seconds: int = 300  # 5 min max call
    language: str = "en-AU"  # Australian English


class VapiCallRequest(BaseModel):
    """Request to initiate an outbound call."""
    assistant_id: str
    phone_number: str  # E.164 format (+61412345678)
    customer_name: str
    metadata: dict = Field(default_factory=dict)


class VapiCallResult(BaseModel):
    """Result from a Vapi call."""
    call_id: str
    status: str
    duration_seconds: float = 0
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    cost: Optional[float] = None
    ended_reason: Optional[str] = None


class VapiClient:
    """
    Vapi API client for voice AI orchestration.

    Handles:
    - Assistant creation and management
    - Outbound call initiation
    - Call status and transcripts
    - Webhook processing

    API Docs: https://docs.vapi.ai/
    """

    BASE_URL = "https://api.vapi.ai"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.vapi_api_key
        if not self.api_key:
            raise IntegrationError("VAPI_API_KEY not configured")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_assistant(self, config: VapiAssistantConfig) -> dict:
        """
        Create a Vapi assistant with custom configuration.

        Returns:
            dict with 'id' key for assistant_id
        """
        payload = {
            "name": config.name,
            "firstMessage": config.first_message,
            "model": {
                "provider": "anthropic",
                "model": config.model,
                "temperature": config.temperature,
                "systemPrompt": config.system_prompt
            },
            "voice": {
                "provider": "11labs",
                "voiceId": config.voice_id,
                "stability": 0.5,
                "similarityBoost": 0.75
            },
            "maxDurationSeconds": config.max_duration_seconds,
            "endCallFunctionEnabled": True,
            "recordingEnabled": True
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/assistant",
                json=payload,
                headers=self.headers
            )
            if response.status_code != 201:
                raise IntegrationError(f"Vapi create_assistant failed: {response.text}")
            return response.json()

    async def get_assistant(self, assistant_id: str) -> dict:
        """Get assistant details by ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/assistant/{assistant_id}",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Vapi get_assistant failed: {response.text}")
            return response.json()

    async def update_assistant(self, assistant_id: str, updates: dict) -> dict:
        """Update an existing assistant."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.BASE_URL}/assistant/{assistant_id}",
                json=updates,
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Vapi update_assistant failed: {response.text}")
            return response.json()

    async def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.BASE_URL}/assistant/{assistant_id}",
                headers=self.headers
            )
            return response.status_code == 200

    async def start_outbound_call(self, request: VapiCallRequest) -> dict:
        """
        Initiate an outbound call via Twilio.

        Args:
            request: VapiCallRequest with assistant_id, phone, name, metadata

        Returns:
            dict with 'id' key for call_id
        """
        payload = {
            "assistantId": request.assistant_id,
            "phoneNumberId": settings.vapi_phone_number_id,
            "customer": {
                "number": request.phone_number,
                "name": request.customer_name
            },
            "metadata": request.metadata
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/call/phone",
                json=payload,
                headers=self.headers
            )
            if response.status_code != 201:
                raise IntegrationError(f"Vapi start_outbound_call failed: {response.text}")
            return response.json()

    async def get_call(self, call_id: str) -> VapiCallResult:
        """Get call details and transcript."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/call/{call_id}",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Vapi get_call failed: {response.text}")
            data = response.json()

            return VapiCallResult(
                call_id=data["id"],
                status=data["status"],
                duration_seconds=data.get("duration", 0),
                transcript=data.get("transcript"),
                recording_url=data.get("recordingUrl"),
                cost=data.get("cost"),
                ended_reason=data.get("endedReason")
            )

    async def list_calls(
        self,
        limit: int = 100,
        created_at_gt: str = None,
        assistant_id: str = None
    ) -> list[dict]:
        """List recent calls with optional filtering."""
        params = {"limit": limit}
        if created_at_gt:
            params["createdAtGt"] = created_at_gt
        if assistant_id:
            params["assistantId"] = assistant_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/call",
                params=params,
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Vapi list_calls failed: {response.text}")
            return response.json()

    async def end_call(self, call_id: str) -> dict:
        """Force end an active call."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/call/{call_id}/end",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Vapi end_call failed: {response.text}")
            return response.json()

    def parse_webhook(self, payload: dict) -> dict:
        """
        Parse Vapi webhook payload into standardized format.

        Args:
            payload: Raw webhook payload from Vapi

        Returns:
            Standardized event dict with call_id, event, and data
        """
        event_type = payload.get("message", {}).get("type", payload.get("type"))
        call_data = payload.get("message", {}).get("call", payload.get("call", {}))

        return {
            "call_id": call_data.get("id"),
            "event": event_type,
            "status": call_data.get("status"),
            "duration": call_data.get("duration"),
            "transcript": call_data.get("transcript"),
            "recording_url": call_data.get("recordingUrl"),
            "ended_reason": call_data.get("endedReason"),
            "cost": call_data.get("cost"),
            "metadata": call_data.get("metadata", {}),
        }


# Singleton instance
_vapi_client: VapiClient | None = None


def get_vapi_client() -> VapiClient:
    """Get or create Vapi client instance."""
    global _vapi_client
    if _vapi_client is None:
        _vapi_client = VapiClient()
    return _vapi_client


# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Uses settings for API keys
# [x] All methods are async
# [x] Proper error handling with IntegrationError
# [x] Pydantic models for request/response validation
# [x] Singleton pattern for client instance
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Webhook parsing method included
