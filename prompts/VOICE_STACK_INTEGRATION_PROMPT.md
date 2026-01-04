# Claude Code Prompt: Voice AI Stack Integration

**Task:** Create the Vapi + Twilio + ElevenLabs + Deepgram voice integration stack

**Priority:** P1  
**Estimated Hours:** 6-8  
**Dependencies:** Existing `src/integrations/twilio.py` (for SMS) can be referenced for patterns

---

## Context

We're replacing the Synthflow all-in-one voice AI with a modular stack for maximum control and voice quality:

| Component | Provider | Purpose |
|-----------|----------|---------|
| Orchestration | Vapi | Coordinates the voice AI pipeline |
| Telephony | Twilio | Phone calls (already have for SMS) |
| TTS | ElevenLabs | High-quality voice synthesis |
| STT | Deepgram | Speech-to-text transcription |
| LLM | Anthropic | Conversation intelligence (existing) |

---

## Files to Create

### 1. `src/integrations/vapi.py`

```python
"""
Vapi Voice AI Integration for Agency OS

Orchestrates voice calls using:
- Twilio for telephony
- ElevenLabs for TTS
- Deepgram for STT  
- Anthropic Claude for LLM
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
        self.api_key = api_key or settings.VAPI_API_KEY
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
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": config.language
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
            "phoneNumberId": settings.VAPI_PHONE_NUMBER_ID,
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


# Singleton instance
vapi_client = VapiClient() if settings.VAPI_API_KEY else None


def get_vapi_client() -> VapiClient:
    """Get or create Vapi client instance."""
    global vapi_client
    if vapi_client is None:
        vapi_client = VapiClient()
    return vapi_client
```

### 2. `src/integrations/elevenlabs.py`

```python
"""
ElevenLabs Voice Integration for Agency OS

High-quality text-to-speech for voice AI.
Used by Vapi for voice synthesis.

API Docs: https://elevenlabs.io/docs/api-reference
"""

import httpx
from typing import Optional
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
    preview_url: Optional[str] = None


class ElevenLabsClient:
    """
    ElevenLabs API client for voice synthesis.
    
    Primary use: Provide voice IDs and settings for Vapi integration.
    Direct TTS calls are optional (Vapi handles this).
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Recommended voices for Australian business context
    RECOMMENDED_VOICES = {
        "adam": "pNInz6obpgDQGcFmaJgB",      # Professional male
        "rachel": "21m00Tcm4TlvDq8ikWAM",    # Professional female
        "josh": "TxGEqnHWrfWFTfGW9XjX",      # Casual male
        "bella": "EXAVITQu4vr4xnSDxMaL",     # Friendly female
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        if not self.api_key:
            raise IntegrationError("ELEVENLABS_API_KEY not configured")
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def list_voices(self) -> list[ElevenLabsVoice]:
        """List all available voices."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/voices",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs list_voices failed: {response.text}")
            
            data = response.json()
            return [
                ElevenLabsVoice(
                    voice_id=v["voice_id"],
                    name=v["name"],
                    category=v.get("category", "premade"),
                    labels=v.get("labels", {}),
                    preview_url=v.get("preview_url")
                )
                for v in data.get("voices", [])
            ]
    
    async def get_voice(self, voice_id: str) -> ElevenLabsVoice:
        """Get details for a specific voice."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/voices/{voice_id}",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs get_voice failed: {response.text}")
            
            v = response.json()
            return ElevenLabsVoice(
                voice_id=v["voice_id"],
                name=v["name"],
                category=v.get("category", "premade"),
                labels=v.get("labels", {}),
                preview_url=v.get("preview_url")
            )
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str = None,
        settings: VoiceSettings = None
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Returns MP3 audio bytes.
        Note: For voice calls, Vapi handles TTS directly.
        This is for preview/testing purposes.
        """
        voice_id = voice_id or self.RECOMMENDED_VOICES["adam"]
        settings = settings or VoiceSettings()
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": settings.stability,
                "similarity_boost": settings.similarity_boost,
                "style": settings.style,
                "use_speaker_boost": settings.use_speaker_boost
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/text-to-speech/{voice_id}",
                json=payload,
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs TTS failed: {response.text}")
            
            return response.content
    
    async def get_subscription_info(self) -> dict:
        """Get current subscription and usage info."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/user/subscription",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"ElevenLabs subscription check failed: {response.text}")
            return response.json()


# Singleton instance
elevenlabs_client = ElevenLabsClient() if settings.ELEVENLABS_API_KEY else None


def get_elevenlabs_client() -> ElevenLabsClient:
    """Get or create ElevenLabs client instance."""
    global elevenlabs_client
    if elevenlabs_client is None:
        elevenlabs_client = ElevenLabsClient()
    return elevenlabs_client
```

### 3. `src/integrations/deepgram.py`

```python
"""
Deepgram Speech-to-Text Integration for Agency OS

Real-time and batch transcription for voice AI.
Used by Vapi for speech recognition.

API Docs: https://developers.deepgram.com/docs
"""

import httpx
from typing import Optional
from pydantic import BaseModel
from src.config.settings import settings
from src.exceptions import IntegrationError


class TranscriptionResult(BaseModel):
    """Result from Deepgram transcription."""
    transcript: str
    confidence: float
    words: list[dict] = []
    duration: float = 0
    language: str = "en"


class DeepgramClient:
    """
    Deepgram API client for speech-to-text.
    
    Primary use: Vapi handles STT during calls.
    This client is for:
    - Post-call transcript enhancement
    - Audio file transcription
    - Testing and validation
    """
    
    BASE_URL = "https://api.deepgram.com/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.DEEPGRAM_API_KEY
        if not self.api_key:
            raise IntegrationError("DEEPGRAM_API_KEY not configured")
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def transcribe_url(
        self,
        audio_url: str,
        language: str = "en-AU",
        model: str = "nova-2",
        punctuate: bool = True,
        diarize: bool = False,
        smart_format: bool = True
    ) -> TranscriptionResult:
        """
        Transcribe audio from URL.
        
        Args:
            audio_url: URL to audio file (MP3, WAV, etc.)
            language: Language code (en-AU for Australian English)
            model: Deepgram model (nova-2 recommended)
            punctuate: Add punctuation
            diarize: Speaker diarization (identify different speakers)
            smart_format: Smart formatting (numbers, dates, etc.)
        """
        params = {
            "language": language,
            "model": model,
            "punctuate": str(punctuate).lower(),
            "diarize": str(diarize).lower(),
            "smart_format": str(smart_format).lower()
        }
        
        payload = {"url": audio_url}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/listen",
                params=params,
                json=payload,
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Deepgram transcribe failed: {response.text}")
            
            data = response.json()
            result = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0]
            
            return TranscriptionResult(
                transcript=result.get("transcript", ""),
                confidence=result.get("confidence", 0),
                words=result.get("words", []),
                duration=data.get("metadata", {}).get("duration", 0),
                language=language
            )
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        mimetype: str = "audio/mp3",
        language: str = "en-AU",
        model: str = "nova-2"
    ) -> TranscriptionResult:
        """
        Transcribe audio from bytes.
        
        Args:
            audio_data: Raw audio bytes
            mimetype: Audio MIME type
            language: Language code
            model: Deepgram model
        """
        params = {
            "language": language,
            "model": model,
            "punctuate": "true",
            "smart_format": "true"
        }
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": mimetype
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/listen",
                params=params,
                content=audio_data,
                headers=headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Deepgram transcribe failed: {response.text}")
            
            data = response.json()
            result = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0]
            
            return TranscriptionResult(
                transcript=result.get("transcript", ""),
                confidence=result.get("confidence", 0),
                words=result.get("words", []),
                duration=data.get("metadata", {}).get("duration", 0),
                language=language
            )
    
    async def get_usage(self) -> dict:
        """Get current usage and limits."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/projects",
                headers=self.headers
            )
            if response.status_code != 200:
                raise IntegrationError(f"Deepgram usage check failed: {response.text}")
            return response.json()


# Singleton instance
deepgram_client = DeepgramClient() if settings.DEEPGRAM_API_KEY else None


def get_deepgram_client() -> DeepgramClient:
    """Get or create Deepgram client instance."""
    global deepgram_client
    if deepgram_client is None:
        deepgram_client = DeepgramClient()
    return deepgram_client
```

---

## Settings Updates

Add to `src/config/settings.py`:

```python
# Voice AI Stack (Vapi + Twilio + ElevenLabs + Deepgram)
VAPI_API_KEY: str = ""
VAPI_PHONE_NUMBER_ID: str = ""  # Twilio number linked in Vapi
ELEVENLABS_API_KEY: str = ""
DEEPGRAM_API_KEY: str = ""
```

---

## Files to Update

### Update `src/engines/voice.py`

Replace Synthflow references with Vapi:

```python
"""
Voice Engine - Vapi + Twilio + ElevenLabs + Deepgram

Handles outbound voice AI calls for hot leads.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from src.engines.base import BaseEngine
from src.integrations.vapi import (
    get_vapi_client, 
    VapiAssistantConfig, 
    VapiCallRequest,
    VapiCallResult
)
from src.models.lead import Lead
from src.models.activity import Activity


class VoiceEngine(BaseEngine):
    """
    Voice AI engine using Vapi orchestration.
    
    Flow:
    1. Create/get assistant for campaign
    2. Initiate outbound call via Twilio (through Vapi)
    3. Vapi orchestrates: STT (Deepgram) → LLM (Claude) → TTS (ElevenLabs)
    4. Webhook receives call result
    5. Log activity + transcript
    """
    
    # Default voice - ElevenLabs "Adam" (professional male)
    DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
    
    async def create_campaign_assistant(
        self,
        db: AsyncSession,
        campaign_id: str,
        script: str,
        first_message: str,
        voice_id: str = None
    ) -> str:
        """
        Create a Vapi assistant for a campaign.
        
        Returns:
            assistant_id to store in campaign record
        """
        vapi = get_vapi_client()
        
        config = VapiAssistantConfig(
            name=f"AgencyOS-{campaign_id[:8]}",
            first_message=first_message,
            system_prompt=self._build_system_prompt(script),
            voice_id=voice_id or self.DEFAULT_VOICE_ID
        )
        
        result = await vapi.create_assistant(config)
        return result["id"]
    
    async def call_lead(
        self,
        db: AsyncSession,
        lead: Lead,
        assistant_id: str,
        campaign_id: str
    ) -> dict:
        """
        Initiate an outbound call to a lead.
        
        JIT Validation (Rule 13):
        - Lead has phone number
        - Lead not in suppression
        - Campaign is active
        """
        # Validate
        if not lead.phone:
            return {"status": "skipped", "reason": "no_phone"}
        
        if lead.status in ["unsubscribed", "bounced"]:
            return {"status": "skipped", "reason": f"lead_{lead.status}"}
        
        vapi = get_vapi_client()
        
        # Initiate call
        request = VapiCallRequest(
            assistant_id=assistant_id,
            phone_number=lead.phone,
            customer_name=f"{lead.first_name} {lead.last_name}",
            metadata={
                "lead_id": str(lead.id),
                "campaign_id": str(campaign_id),
                "client_id": str(lead.client_id)
            }
        )
        
        result = await vapi.start_outbound_call(request)
        
        # Log activity
        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel="voice",
            action="call_initiated",
            provider_message_id=result["id"],
            metadata={
                "vapi_call_id": result["id"],
                "status": result.get("status")
            }
        )
        db.add(activity)
        await db.commit()
        
        return {"status": "initiated", "call_id": result["id"]}
    
    async def get_call_result(self, call_id: str) -> VapiCallResult:
        """Get call result including transcript."""
        vapi = get_vapi_client()
        return await vapi.get_call(call_id)
    
    def _build_system_prompt(self, script: str) -> str:
        """Build the system prompt for the voice assistant."""
        return f"""You are a friendly, professional sales development representative for a marketing agency.

SCRIPT GUIDANCE:
{script}

RULES:
- Be conversational and natural, not robotic
- Listen actively and respond to what the person actually says
- If they seem busy, offer to call back at a better time
- If they're not interested, thank them politely and end the call
- If they're interested, book a meeting or transfer to a human
- Keep responses concise (1-2 sentences max)
- Use Australian English spellings and expressions

GOAL:
Qualify the lead and either:
1. Book a meeting if interested
2. Gather objection data if not interested
3. Schedule a callback if timing is bad

Always be respectful of their time."""
```

### Update `src/api/routes/webhooks.py`

Add Vapi webhook handler:

```python
@router.post("/vapi")
async def vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Vapi call webhooks.
    
    Events:
    - call.started
    - call.ended
    - transcript.update
    """
    payload = await request.json()
    event_type = payload.get("type")
    
    if event_type == "call.ended":
        call_data = payload.get("call", {})
        metadata = call_data.get("metadata", {})
        
        lead_id = metadata.get("lead_id")
        if lead_id:
            activity = Activity(
                client_id=metadata.get("client_id"),
                campaign_id=metadata.get("campaign_id"),
                lead_id=lead_id,
                channel="voice",
                action="call_completed",
                provider_message_id=call_data.get("id"),
                metadata={
                    "duration": call_data.get("duration"),
                    "transcript": call_data.get("transcript"),
                    "recording_url": call_data.get("recordingUrl"),
                    "end_reason": call_data.get("endedReason"),
                    "cost": call_data.get("cost")
                }
            )
            db.add(activity)
            await db.commit()
    
    return {"received": True}
```

---

## Files to Delete

- `src/integrations/synthflow.py` (if exists)

---

## Tests to Create

### `tests/test_integrations/test_vapi.py`

```python
"""Tests for Vapi integration."""
import pytest
from unittest.mock import AsyncMock, patch
from src.integrations.vapi import VapiClient, VapiAssistantConfig, VapiCallRequest


@pytest.fixture
def vapi_client():
    with patch.object(VapiClient, '__init__', lambda self, api_key=None: None):
        client = VapiClient()
        client.api_key = "test_key"
        client.headers = {"Authorization": "Bearer test_key"}
        return client


@pytest.mark.asyncio
async def test_create_assistant(vapi_client):
    config = VapiAssistantConfig(
        name="Test Assistant",
        first_message="Hello!",
        system_prompt="You are helpful."
    )
    
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=201,
            json=lambda: {"id": "asst_123"}
        )
        
        result = await vapi_client.create_assistant(config)
        assert result["id"] == "asst_123"


@pytest.mark.asyncio
async def test_start_outbound_call(vapi_client):
    request = VapiCallRequest(
        assistant_id="asst_123",
        phone_number="+61412345678",
        customer_name="Test User"
    )
    
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=201,
            json=lambda: {"id": "call_456", "status": "queued"}
        )
        
        result = await vapi_client.start_outbound_call(request)
        assert result["id"] == "call_456"
```

---

## Validation Checklist

After implementation, verify:

1. [ ] `src/integrations/vapi.py` created with all methods
2. [ ] `src/integrations/elevenlabs.py` created with TTS support
3. [ ] `src/integrations/deepgram.py` created with STT support
4. [ ] `src/config/settings.py` updated with new env vars
5. [ ] `src/engines/voice.py` updated to use Vapi
6. [ ] `src/api/routes/webhooks.py` has Vapi webhook handler
7. [ ] Tests pass for all new integrations
8. [ ] `src/integrations/synthflow.py` deleted (if exists)

---

## Environment Variables Required

```bash
# Voice AI Stack
VAPI_API_KEY=your_vapi_key
VAPI_PHONE_NUMBER_ID=your_linked_twilio_number_id
ELEVENLABS_API_KEY=your_elevenlabs_key
DEEPGRAM_API_KEY=your_deepgram_key

# Twilio (already configured for SMS)
TWILIO_ACCOUNT_SID=existing
TWILIO_AUTH_TOKEN=existing
TWILIO_PHONE_NUMBER=existing
```

---

## Sign Up Links

1. **Vapi**: https://vapi.ai (free $10 credit)
2. **ElevenLabs**: https://elevenlabs.io (free tier available)
3. **Deepgram**: https://deepgram.com (free 12K minutes)

---

## Notes

- Vapi orchestrates the full voice pipeline - we don't call ElevenLabs/Deepgram directly during calls
- ElevenLabs and Deepgram integrations are for testing, voice selection, and post-call processing
- Twilio number must be linked in Vapi dashboard before calls work
- Cost estimate: $0.13-0.18/minute (vs $0.08 Synthflow) but much higher quality
