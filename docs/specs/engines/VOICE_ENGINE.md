# Voice Engine — Voice AI Calls

**File:** `src/engines/voice.py`  
**Purpose:** AI-powered voice calls via Vapi + Twilio + ElevenLabs  
**Layer:** 3 - engines

---

## Voice Stack

| Component | Provider | Purpose |
|-----------|----------|---------|
| Orchestration | Vapi | Call flow, AI conversation |
| Telephony | Twilio | Phone numbers, call routing |
| TTS | ElevenLabs | Natural voice synthesis |
| STT | Deepgram | Speech-to-text |

---

## Call Flow

```
Lead selected for Voice (Warm+ tier)
        │
        ▼
┌─────────────────┐
│ Check phone     │
│ number valid    │
└─────────────────┘
        │
        ├── Invalid ──► Skip
        │
        └── Valid
                │
                ▼
┌─────────────────┐
│ Check business  │
│ hours (AU)      │
└─────────────────┘
        │
        ├── Outside hours ──► Schedule for later
        │
        └── Within hours
                │
                ▼
┌─────────────────┐
│ Initiate call   │
│ via Vapi        │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ AI conversation │
│ (Vapi + Claude) │
└─────────────────┘
        │
        ├── Meeting booked ──► Create meeting record
        ├── Callback requested ──► Schedule follow-up
        ├── Not interested ──► Update lead status
        └── Voicemail ──► Leave message, retry later
```

---

## Business Hours (Australia)

| Timezone | Hours |
|----------|-------|
| AEST/AEDT | 9am - 6pm weekdays |
| AWST | 9am - 6pm weekdays |

Auto-detect timezone from phone number area code.

---

## Voice Persona

```python
voice_config = {
    "provider": "elevenlabs",
    "voice_id": "professional_australian_male",  # or female variant
    "stability": 0.7,
    "similarity_boost": 0.8,
    "style": "conversational"
}
```

---

## Conversation Script (Vapi)

```
Opening:
"Hi, is this {first_name}? This is {agent_name} from Agency OS. 
I'm reaching out because I noticed {company} does great work in 
{industry}, and I wanted to share something that might help you 
acquire more clients predictably. Do you have a quick minute?"

If yes → Discovery questions
If no → "No problem, when would be a better time to chat?"
If voicemail → Leave brief message with callback number
```

---

## Rate Limiting

| Resource | Limit | Period |
|----------|-------|--------|
| Phone number | 50 calls | per day |
| Concurrent calls | 5 | per client |

---

## API

```python
class VoiceEngine:
    async def initiate_call(
        self,
        db: AsyncSession,
        lead_id: UUID,
        phone_number_id: str
    ) -> CallResult:
        """
        Initiate AI voice call to lead.
        
        Args:
            db: Database session
            lead_id: Target lead (must be Warm+ tier)
            phone_number_id: Twilio number to use
            
        Returns:
            CallResult with call_id, status
        """
        ...
    
    async def handle_call_complete(
        self,
        call_id: str,
        outcome: CallOutcome
    ) -> None:
        """Process call completion webhook from Vapi."""
        ...
```

---

## Cost

- **Vapi:** $0.35/minute (all-in: orchestration + AI + telephony)
- **Average call:** 2-3 minutes = $0.70-1.05
