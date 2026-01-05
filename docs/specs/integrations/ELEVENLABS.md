# ElevenLabs Integration

**File:** `src/integrations/elevenlabs.py`  
**Purpose:** Text-to-speech for Voice AI  
**API Docs:** https://docs.elevenlabs.io/

---

## Capabilities

- Natural voice synthesis
- Multiple voice options
- Real-time streaming
- Voice cloning (custom voices)

---

## Usage Pattern

```python
class ElevenLabsClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.elevenlabs.io/v1",
            headers={"xi-api-key": api_key}
        )
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_monolingual_v1"
    ) -> bytes:
        """Convert text to speech audio."""
        response = await self.client.post(
            f"/text-to-speech/{voice_id}",
            json={
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.7,
                    "similarity_boost": 0.8
                }
            }
        )
        return response.content
    
    async def get_voices(self) -> list[Voice]:
        """List available voices."""
        response = await self.client.get("/voices")
        return [Voice(**v) for v in response.json()["voices"]]
```

---

## Recommended Voices

| Voice | ID | Use Case |
|-------|-----|----------|
| Professional Male (AU) | `pNInz6obpgDQGcFmaJgB` | Default male |
| Professional Female (AU) | `21m00Tcm4TlvDq8ikWAM` | Default female |

---

## Voice Settings

| Setting | Range | Recommended |
|---------|-------|-------------|
| Stability | 0-1 | 0.7 |
| Similarity Boost | 0-1 | 0.8 |
| Style | 0-1 | 0.5 |

---

## Integration with Vapi

ElevenLabs is configured in Vapi assistant:

```python
voice_config = {
    "provider": "elevenlabs",
    "voiceId": "pNInz6obpgDQGcFmaJgB",
    "stability": 0.7,
    "similarityBoost": 0.8
}
```

---

## Cost

- **Characters:** ~$0.30 per 1000 characters
- **Included via Vapi:** Part of $0.35/minute rate
