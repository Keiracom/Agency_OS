"""
FILE: src/integrations/elevenlabs.py
PURPOSE: ElevenLabs Voice Integration for Agency OS
PHASE: 17 (Launch Prerequisites)
TASK: CRED-007a
DEPENDENCIES:
  - httpx
  - pydantic
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: No hardcoded credentials

High-quality text-to-speech for voice AI.
Used by Vapi for voice synthesis.

API Docs: https://elevenlabs.io/docs/api-reference
"""

import httpx
from pydantic import BaseModel

from src.config.settings import settings
from src.exceptions import IntegrationError


class VoiceSettings(BaseModel):
    """Voice configuration settings."""

    stability: float = 0.5  # 0-1, higher = more consistent
    similarity_boost: float = 0.75  # 0-1, higher = closer to original
    style: float = 0.0  # 0-1, style exaggeration (v2 voices only)
    use_speaker_boost: bool = True


class ElevenLabsVoice(BaseModel):
    """Voice model from ElevenLabs."""

    voice_id: str
    name: str
    category: str  # premade, cloned, generated
    labels: dict = {}
    preview_url: str | None = None


class ElevenLabsClient:
    """
    ElevenLabs API client for voice synthesis.

    Primary use: Provide voice IDs and settings for Vapi integration.
    Direct TTS calls are optional (Vapi handles this during calls).
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Recommended voices for Australian business context
    RECOMMENDED_VOICES = {
        "adam": "pNInz6obpgDQGcFmaJgB",  # Professional male
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # Professional female
        "josh": "TxGEqnHWrfWFTfGW9XjX",  # Casual male
        "bella": "EXAVITQu4vr4xnSDxMaL",  # Friendly female
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.elevenlabs_api_key
        if not self.api_key:
            raise IntegrationError("ELEVENLABS_API_KEY not configured")
        self.headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}

    async def list_voices(self) -> list[ElevenLabsVoice]:
        """List all available voices."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/voices", headers=self.headers)
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs list_voices failed: {response.text}")

            data = response.json()
            return [
                ElevenLabsVoice(
                    voice_id=v["voice_id"],
                    name=v["name"],
                    category=v.get("category", "premade"),
                    labels=v.get("labels", {}),
                    preview_url=v.get("preview_url"),
                )
                for v in data.get("voices", [])
            ]

    async def get_voice(self, voice_id: str) -> ElevenLabsVoice:
        """Get details for a specific voice."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/voices/{voice_id}", headers=self.headers)
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs get_voice failed: {response.text}")

            v = response.json()
            return ElevenLabsVoice(
                voice_id=v["voice_id"],
                name=v["name"],
                category=v.get("category", "premade"),
                labels=v.get("labels", {}),
                preview_url=v.get("preview_url"),
            )

    async def text_to_speech(
        self, text: str, voice_id: str | None = None, voice_settings: VoiceSettings | None = None
    ) -> bytes:
        """
        Convert text to speech audio.

        Returns MP3 audio bytes.
        Note: For voice calls, Vapi handles TTS directly.
        This is for preview/testing purposes.
        """
        voice_id = voice_id or self.RECOMMENDED_VOICES["adam"]
        voice_settings = voice_settings or VoiceSettings()

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": voice_settings.stability,
                "similarity_boost": voice_settings.similarity_boost,
                "style": voice_settings.style,
                "use_speaker_boost": voice_settings.use_speaker_boost,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/text-to-speech/{voice_id}", json=payload, headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs TTS failed: {response.text}")

            return response.content

    async def get_subscription_info(self) -> dict:
        """Get current subscription and usage info."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/user/subscription", headers=self.headers)
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs subscription check failed: {response.text}")
            return response.json()

    async def get_user_info(self) -> dict:
        """Get user account info including character usage."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/user", headers=self.headers)
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs user info failed: {response.text}")
            return response.json()


# Singleton instance
_elevenlabs_client: ElevenLabsClient | None = None


def get_elevenlabs_client() -> ElevenLabsClient:
    """Get or create ElevenLabs client instance."""
    global _elevenlabs_client
    if _elevenlabs_client is None:
        _elevenlabs_client = ElevenLabsClient()
    return _elevenlabs_client


# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Uses settings for API keys
# [x] All methods are async
# [x] Proper error handling with IntegrationError
# [x] Pydantic models for request/response validation
# [x] Singleton pattern for client instance
# [x] Recommended voices for Australian context
# [x] TTS method for preview/testing
# [x] Subscription info for usage tracking
# [x] All functions have type hints
# [x] All functions have docstrings
