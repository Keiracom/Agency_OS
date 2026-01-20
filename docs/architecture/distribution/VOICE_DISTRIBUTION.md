# Voice Distribution Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Provider:** Vapi (AI voice) + Twilio (telephony) + ElevenLabs (voice synthesis)
**Rate Limit:** 50 calls/day/number

---

## Executive Summary

Voice is Step 2 in the default sequence (Day 3 - follow-up call). AI voice agent makes the call using a knowledge base generated per-lead. Voice KB generation uses SDK for Hot leads, Smart Prompt for others.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Twilio integration | ✅ | `src/integrations/twilio.py` |
| Vapi integration | 🟡 | Basic setup, needs KB integration |
| Voice engine | ✅ | `src/engines/voice.py` |
| Voice KB generation | ✅ | Smart Prompt + SDK for Hot |
| Outreach flow integration | 🟡 | Flow exists but voice untested |
| Phone pool | ❌ | Not implemented (see RESOURCE_POOL.md) |
| Call recording | 🟡 | Twilio handles, need retrieval |

---

## Architecture Flow

```
Day 3: Voice Step Due
    └── Outreach flow queries leads due for Step 2
        └── Allocator selects phone number (round-robin)
            └── Voice engine generates KB (Smart Prompt or SDK)
                └── Vapi initiates call with KB
                    └── Twilio handles telephony
                        └── Call outcome logged
                            └── Recording stored
```

---

## Voice Knowledge Base

### Per-Lead KB Generation

Before each call, generate a knowledge base:

```python
# src/engines/voice.py

async def generate_voice_kb(
    db: AsyncSession,
    lead_id: UUID,
    campaign_id: UUID,
) -> EngineResult:
    """
    Generate voice agent knowledge base for a lead.

    Uses Smart Prompt with full lead context.
    SDK used for Hot leads (ALS >= 85).
    """
    lead = await get_lead(db, lead_id)
    context = await build_full_lead_context(db, lead_id)

    if lead.als_score >= 85:
        # SDK for deeper research on Hot leads
        kb = await sdk_voice_kb_agent.generate(context)
    else:
        # Smart Prompt for Warm/Cool
        kb = await generate_kb_from_prompt(VOICE_KB_PROMPT, context)

    return EngineResult.ok(data={
        'lead_id': str(lead_id),
        'kb_content': kb,
        'generation_method': 'sdk' if lead.als_score >= 85 else 'smart_prompt',
    })
```

### KB Content Structure

```json
{
    "lead_summary": "John Smith, VP Sales at TechCorp...",
    "company_context": "B2B SaaS, 150 employees, Series B...",
    "pain_points": ["manual lead qualification", "CRM data quality"],
    "talking_points": [
        "Reference their recent funding",
        "Mention case study with similar company"
    ],
    "objection_handlers": {
        "not interested": "I understand. Quick question though...",
        "send info": "Happy to. What specific aspect...",
        "in a meeting": "No problem. When's a better time..."
    },
    "goal": "Book 15-minute discovery call",
    "calendar_link": "https://calendly.com/..."
}
```

---

## Vapi Integration

### Call Initiation

```python
# src/integrations/vapi.py

class VapiClient:
    async def initiate_call(
        self,
        to_phone: str,
        from_phone: str,
        knowledge_base: dict,
        voice_id: str,
        max_duration_seconds: int = 120,
    ) -> dict:
        """
        Initiate AI voice call.

        Args:
            to_phone: Recipient phone number
            from_phone: Caller ID (from phone pool)
            knowledge_base: Lead-specific KB
            voice_id: ElevenLabs voice ID
            max_duration_seconds: Auto-hangup limit

        Returns:
            {
                'call_id': 'call_xxx',
                'status': 'initiated',
            }
        """
```

### Call Outcomes

| Outcome | Action |
|---------|--------|
| `answered` | Log activity, continue to outcome |
| `voicemail` | Leave VM or skip per settings |
| `busy` | Retry later (cooling period) |
| `no_answer` | Mark as no_answer |
| `failed` | Log error, don't retry |

### Post-Call Analysis

```python
async def analyze_call_outcome(call_id: str) -> dict:
    """
    Analyze completed call.

    Returns:
        {
            'call_id': 'call_xxx',
            'duration_seconds': 45,
            'outcome': 'meeting_booked',
            'sentiment': 'positive',
            'transcript_summary': '...',
            'next_action': 'send_calendar_invite',
        }
    """
```

---

## Phone Number Pool

### Allocation per Tier

| Tier | Voice Numbers |
|------|---------------|
| Ignition | 1 |
| Velocity | 2 |
| Dominance | 3 |

### Capacity

At 50 calls/day/number:
- Velocity: 2 numbers × 50 = 100 calls/day
- Monthly: 100 × 22 days = 2,200 call capacity

For 2,250 leads with 1 voice step:
- Needed: ~2,000 calls/month (with attrition)
- Capacity: 2,200 ✅ Sufficient

---

## Call Timing

### Business Hours Only

```python
def can_call_now(lead: Lead, timezone: str) -> tuple[bool, str]:
    """
    Check if we can call now based on recipient timezone.
    """
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)

    # Business hours: 9 AM - 5 PM
    if now.hour < 9 or now.hour >= 17:
        return False, "Outside business hours"

    # Weekdays only
    if now.weekday() >= 5:
        return False, "Weekend"

    # Lunch break: 12-1 PM (low answer rate)
    if now.hour == 12:
        return False, "Lunch hour"

    return True, None
```

### Optimal Call Windows

| Time (Local) | Answer Rate |
|--------------|-------------|
| 9-10 AM | High |
| 10-12 PM | Medium |
| 12-1 PM | Low (lunch) |
| 1-3 PM | Medium |
| 3-5 PM | High |

---

## Call Recording

### Storage

Twilio recordings stored for:
- Quality assurance
- Compliance
- Training data for voice agent

```python
async def retrieve_recording(call_sid: str) -> dict:
    """
    Retrieve call recording from Twilio.
    """
    recording = await twilio_client.recordings.list(call_sid=call_sid)
    return {
        'url': recording.media_url,
        'duration': recording.duration,
        'call_sid': call_sid,
    }
```

### Retention

- Keep recordings for 90 days
- Delete after unless flagged for training
- Anonymize transcripts for analytics

---

## Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `src/integrations/twilio.py` | Telephony | ✅ |
| `src/integrations/vapi.py` | AI voice | 🟡 Basic |
| `src/engines/voice.py` | Voice logic | ✅ |
| `src/agents/sdk_agents/voice_kb_agent.py` | SDK KB gen | ✅ |

---

## Verification Checklist

- [x] Twilio integration works
- [x] Voice engine generates KB
- [x] SDK integration for Hot leads
- [ ] Phone pool allocation (RESOURCE_POOL.md)
- [ ] Vapi call initiation
- [ ] Call outcome handling
- [ ] Recording retrieval
- [ ] Timezone-aware scheduling
- [ ] Voicemail detection

---

## Configuration

### Environment Variables

```bash
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
VAPI_API_KEY=xxx
ELEVENLABS_API_KEY=xxx
ELEVENLABS_VOICE_ID=xxx
```

### Settings

```python
# src/config/settings.py

voice_max_per_number_day: int = 50
voice_max_duration_seconds: int = 120
voice_leave_voicemail: bool = True
voice_business_hours_start: int = 9
voice_business_hours_end: int = 17
```

---

## Costs

| Item | Cost |
|------|------|
| Twilio call (AU) | $0.02/min |
| Vapi | $0.05/min |
| ElevenLabs | $0.15/1000 chars |

Avg call: 1 minute
- Per call: $0.02 + $0.05 + ~$0.02 = $0.09 AUD
- Monthly (2,000 calls): ~$180 AUD
