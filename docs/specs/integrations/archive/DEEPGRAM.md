> **ARCHIVED:** This integration was replaced/superseded. Kept for historical reference.
> **Replaced by:** Vapi internal STT (Deepgram is used internally by Vapi, no direct integration needed)
> **Archived:** January 8, 2026
> **Reason:** Voice AI uses Vapi which handles STT internally. No separate Deepgram wrapper needed.

---

# Deepgram Integration (ARCHIVED)

**File:** `src/integrations/deepgram.py` (never implemented)
**Purpose:** Speech-to-text (STT) for Voice AI
**API Docs:** https://developers.deepgram.com/

---

## Capabilities

- Real-time speech-to-text
- Pre-recorded audio transcription
- Speaker diarization
- Punctuation and formatting

---

## Usage Pattern

```python
from deepgram import Deepgram

class DeepgramClient:
    def __init__(self, api_key: str):
        self.client = Deepgram(api_key)

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[TranscriptChunk]:
        """Real-time transcription for voice calls."""
        socket = await self.client.transcription.live({
            "punctuate": True,
            "interim_results": True,
            "language": "en-AU"
        })

        async for audio_chunk in audio_stream:
            socket.send(audio_chunk)
            result = await socket.receive()
            if result.get("is_final"):
                yield TranscriptChunk(
                    text=result["channel"]["alternatives"][0]["transcript"],
                    confidence=result["channel"]["alternatives"][0]["confidence"],
                    is_final=True
                )

    async def transcribe_audio(
        self,
        audio_url: str
    ) -> Transcript:
        """Transcribe pre-recorded audio file."""
        response = await self.client.transcription.prerecorded(
            {"url": audio_url},
            {
                "punctuate": True,
                "diarize": True,
                "language": "en-AU"
            }
        )
        return Transcript(**response)
```

---

## Integration with Vapi

Deepgram is configured as the STT provider in Vapi:

```python
transcriber_config = {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-AU"
}
```

---

## Models

| Model | Use Case | Accuracy |
|-------|----------|----------|
| Nova-2 | Real-time conversation | Best |
| Enhanced | General transcription | Good |
| Base | High volume, lower cost | Fair |

---

## Cost

- **Nova-2:** $0.0043/minute
- **Included via Vapi:** Part of $0.35/minute rate

---

## Australian English

- **Language code:** `en-AU`
- **Supports:** Australian accent recognition
- **Custom vocabulary:** Can add industry terms
