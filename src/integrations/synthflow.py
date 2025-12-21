"""
FILE: src/integrations/synthflow.py
PURPOSE: Synthflow integration for Voice AI calls
PHASE: 3 (Integrations)
TASK: INT-010
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
"""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class SynthflowClient:
    """
    Synthflow client for AI voice calls.

    Handles outbound voice campaigns with AI agents.
    """

    BASE_URL = "https://api.synthflow.ai/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.synthflow_api_key
        if not self.api_key:
            raise IntegrationError(
                service="synthflow",
                message="Synthflow API key is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                service="synthflow",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="synthflow",
                message=f"Synthflow request failed: {str(e)}",
            )

    async def initiate_call(
        self,
        phone_number: str,
        agent_id: str,
        lead_data: dict[str, Any],
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Initiate an AI voice call.

        Args:
            phone_number: Target phone number (E.164 format)
            agent_id: Synthflow agent ID to use
            lead_data: Lead context for personalization
            callback_url: Webhook URL for call events

        Returns:
            Call initiation result
        """
        data = {
            "phone_number": phone_number,
            "agent_id": agent_id,
            "context": {
                "first_name": lead_data.get("first_name"),
                "last_name": lead_data.get("last_name"),
                "company": lead_data.get("company"),
                "title": lead_data.get("title"),
            },
        }

        if callback_url:
            data["callback_url"] = callback_url

        result = await self._request("POST", "/calls/initiate", data)

        return {
            "success": True,
            "call_id": result.get("call_id"),
            "status": result.get("status"),
            "provider": "synthflow",
        }

    async def get_call_status(self, call_id: str) -> dict[str, Any]:
        """
        Get call status and details.

        Args:
            call_id: Synthflow call ID

        Returns:
            Call status and details
        """
        result = await self._request("GET", f"/calls/{call_id}")

        return {
            "call_id": call_id,
            "status": result.get("status"),
            "duration": result.get("duration"),
            "outcome": result.get("outcome"),
            "transcript": result.get("transcript"),
            "sentiment": result.get("sentiment"),
            "started_at": result.get("started_at"),
            "ended_at": result.get("ended_at"),
        }

    async def get_transcript(self, call_id: str) -> dict[str, Any]:
        """
        Get call transcript.

        Args:
            call_id: Synthflow call ID

        Returns:
            Call transcript
        """
        result = await self._request("GET", f"/calls/{call_id}/transcript")

        return {
            "call_id": call_id,
            "transcript": result.get("transcript"),
            "summary": result.get("summary"),
            "intent": result.get("detected_intent"),
            "action_items": result.get("action_items", []),
        }

    async def get_agents(self) -> list[dict[str, Any]]:
        """
        Get available voice agents.

        Returns:
            List of agents
        """
        result = await self._request("GET", "/agents")

        return [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "description": a.get("description"),
                "voice": a.get("voice"),
                "language": a.get("language"),
            }
            for a in result.get("agents", [])
        ]

    def parse_call_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Synthflow call event webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed call event
        """
        return {
            "call_id": payload.get("call_id"),
            "event": payload.get("event"),  # started, answered, ended, failed
            "status": payload.get("status"),
            "duration": payload.get("duration"),
            "outcome": payload.get("outcome"),  # voicemail, answered, no_answer, busy
            "transcript": payload.get("transcript"),
            "sentiment": payload.get("sentiment"),
            "intent": payload.get("detected_intent"),
            "meeting_booked": payload.get("meeting_booked", False),
            "meeting_time": payload.get("meeting_time"),
        }


# Singleton instance
_synthflow_client: SynthflowClient | None = None


def get_synthflow_client() -> SynthflowClient:
    """Get or create Synthflow client instance."""
    global _synthflow_client
    if _synthflow_client is None:
        _synthflow_client = SynthflowClient()
    return _synthflow_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Call initiation with AI agent
# [x] Call status retrieval
# [x] Transcript retrieval
# [x] Agent listing
# [x] Webhook parsing
# [x] Lead context passing
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
