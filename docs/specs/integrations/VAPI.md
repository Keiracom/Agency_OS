# Vapi Integration

**File:** `src/integrations/vapi.py`  
**Purpose:** Voice AI conversation orchestration  
**API Docs:** https://docs.vapi.ai/

---

## Capabilities

- AI-powered voice conversations
- Real-time speech-to-text
- Natural language understanding
- Call flow management
- Meeting booking during calls

---

## Architecture

```
Vapi (Orchestration)
├── Twilio (Telephony)
├── ElevenLabs (TTS)
├── Deepgram (STT)
└── Claude (Conversation AI)
```

---

## Usage Pattern

```python
class VapiClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.vapi.ai",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def create_call(
        self,
        phone_number: str,
        assistant_id: str,
        customer_number: str,
        metadata: dict
    ) -> CallResult:
        """Initiate AI voice call."""
        response = await self.client.post(
            "/call/phone",
            json={
                "phoneNumberId": phone_number,
                "assistantId": assistant_id,
                "customer": {
                    "number": customer_number
                },
                "metadata": metadata
            }
        )
        return CallResult(**response.json())
    
    async def create_assistant(
        self,
        name: str,
        system_prompt: str,
        voice_id: str
    ) -> Assistant:
        """Create AI assistant for calls."""
        response = await self.client.post(
            "/assistant",
            json={
                "name": name,
                "model": {
                    "provider": "anthropic",
                    "model": "claude-3-sonnet"
                },
                "voice": {
                    "provider": "elevenlabs",
                    "voiceId": voice_id
                },
                "firstMessage": "Hi, this is...",
                "systemPrompt": system_prompt
            }
        )
        return Assistant(**response.json())
```

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `call.started` | Call initiated |
| `call.answered` | Customer answered |
| `call.ended` | Call completed |
| `transcript.partial` | Real-time transcript |
| `transcript.final` | Complete transcript |
| `tool.called` | AI triggered a tool (e.g., book meeting) |

---

## Call Outcomes

| Outcome | Description | Action |
|---------|-------------|--------|
| `meeting_booked` | Customer agreed to meeting | Create meeting record |
| `callback_requested` | Asked for callback | Schedule follow-up |
| `not_interested` | Declined | Update lead status |
| `voicemail` | Reached voicemail | Leave message, retry |
| `no_answer` | No answer | Retry later |

---

## Cost

- **All-in rate:** $0.35 AUD/minute
- **Includes:** Vapi + Twilio + ElevenLabs + Deepgram
- **Average call:** 2-3 minutes = $0.70-1.05

---

## Voice Configuration

```python
voice_config = {
    "provider": "elevenlabs",
    "voiceId": "pNInz6obpgDQGcFmaJgB",  # Professional male
    "stability": 0.7,
    "similarityBoost": 0.8
}
```
