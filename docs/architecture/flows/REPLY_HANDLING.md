# Reply Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Priority:** HIGH
**Owner:** CTO
**Last Updated:** January 22, 2026

---

## Executive Summary

Unified reply handling across all channels. When a lead responds via email, SMS, or LinkedIn, the system classifies intent, generates an appropriate response, and takes sequence actions automatically.

**Principle:** Fully automated. No human review except for angry/complaint intents.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Closer engine | ✅ | `src/engines/closer.py` (10 intents including referral, wrong_person, angry_or_complaint) |
| Reply analyzer service | ✅ | `src/services/reply_analyzer.py` |
| Reply agent (Pydantic AI) | ✅ | `src/agents/reply_agent.py` |
| Thread service | ✅ | `src/services/thread_service.py` |
| Conversation threads table | ✅ | Migration 027 |
| Reply tasks | ✅ | `src/orchestration/tasks/reply_tasks.py` |
| Reply recovery flow | ✅ | `src/orchestration/flows/reply_recovery_flow.py` |
| Email events service | ✅ | `src/services/email_events_service.py` |
| Response timing service | ✅ | `src/services/response_timing_service.py` (3-5 min / 10-15 min delays) |
| Lead replies table | ✅ | Migration 046 (created 2026-01-22) |
| SMS webhook service | 🟡 | Needs full implementation |
| LinkedIn webhook service | 🟡 | Needs full implementation |

---

## CTO Decisions (2026-01-20)

| Decision | Choice |
|----------|--------|
| Automation level | **Fully automated** (except angry/complaint) |
| Cost cap | **$0.50/lead lifetime** for SDK reply usage |
| Response timing | **3-5 min** (business hours), **10-15 min** (outside) |
| Response channel | **Same channel** lead used |
| Priority | **Phase 26** (after resource pool) |

---

## Reply Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     INBOUND REPLY                                │
├─────────────────────────────────────────────────────────────────┤
│  Email Webhook    SMS Webhook    LinkedIn Webhook               │
│       │               │               │                         │
│       └───────────────┴───────────────┘                         │
│                       │                                          │
│                ┌──────▼──────┐                                   │
│                │ Reply Router │                                  │
│                └──────┬──────┘                                   │
│                       │                                          │
│                ┌──────▼──────┐                                   │
│                │   Intent     │                                  │
│                │ Classifier   │  (Smart Prompt)                  │
│                └──────┬──────┘                                   │
│                       │                                          │
│       ┌───────────────┼───────────────┐                         │
│       │               │               │                          │
│  ┌────▼────┐    ┌────▼────┐    ┌────▼────┐                     │
│  │ Meeting │    │ Question │    │Negative │                     │
│  │ Interest│    │  Asked   │    │ Intent  │                     │
│  └────┬────┘    └────┬────┘    └────┬────┘                     │
│       │               │               │                          │
│  ┌────▼────┐    ┌────▼────┐    ┌────▼────┐                     │
│  │ Send    │    │ Generate │    │ Stop    │                     │
│  │Calendar │    │ Response │    │Sequence │                     │
│  │ Link    │    │ (SDK?)   │    │Suppress │                     │
│  └────┬────┘    └────┬────┘    └────┬────┘                     │
│       │               │               │                          │
│       └───────────────┼───────────────┘                         │
│                       │                                          │
│                ┌──────▼──────┐                                   │
│                │  Response   │                                   │
│                │  Sender     │  (Same channel, delayed)          │
│                └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Note:** Voice replies handled real-time by Vapi (separate flow).

---

## Intent Classification

### Intent Definitions

```python
# src/services/intent_classifier.py

REPLY_INTENTS = {
    'meeting_interest': {
        'signals': ['yes', 'sure', 'let\'s chat', 'available', 'calendar',
                    'schedule', 'book', 'meet', 'call me', 'free'],
        'action': 'send_calendar_link',
        'sequence_action': 'pause',
        'auto_respond': True,
    },
    'question': {
        'signals': ['?', 'how', 'what', 'why', 'can you', 'tell me',
                    'explain', 'more info', 'details'],
        'action': 'generate_response',
        'sequence_action': 'pause',
        'auto_respond': True,
    },
    'positive_engagement': {
        'signals': ['interesting', 'tell me more', 'sounds good',
                    'send info', 'intrigued', 'go on'],
        'action': 'generate_response',
        'sequence_action': 'continue',
        'auto_respond': True,
    },
    'not_interested': {
        'signals': ['no thanks', 'not interested', 'remove', 'stop',
                    'unsubscribe', 'don\'t contact', 'not for us'],
        'action': 'acknowledge_politely',
        'sequence_action': 'stop',
        'suppress': True,
        'auto_respond': True,
    },
    'out_of_office': {
        'signals': ['out of office', 'on leave', 'vacation', 'returning',
                    'away from', 'back on', 'auto-reply'],
        'action': 'none',
        'sequence_action': 'pause_until_return',
        'auto_respond': False,
    },
    'wrong_person': {
        'signals': ['wrong person', 'no longer', 'left company',
                    'doesn\'t work', 'retired', 'moved on'],
        'action': 'none',
        'sequence_action': 'stop',
        'mark_invalid': True,
        'auto_respond': False,
    },
    'referral': {
        'signals': ['speak to', 'contact', 'better person', 'try reaching',
                    'talk to', 'handles this', 'responsible for'],
        'action': 'extract_referral',
        'sequence_action': 'stop',
        'create_new_lead': True,
        'auto_respond': True,
    },
    'angry_or_complaint': {
        'signals': ['frustrated', 'annoyed', 'terrible', 'lawsuit',
                    'report', 'spam', 'harassing', 'illegal', 'reported'],
        'action': 'hold_for_review',
        'sequence_action': 'stop',
        'alert_admin': True,
        'auto_respond': False,  # HUMAN REVIEW REQUIRED
    },
}
```

### Classification Logic

```python
# src/services/intent_classifier.py

async def classify_intent(
    content: str,
    lead_context: dict,
) -> dict:
    """
    Classify reply intent using Smart Prompt.

    Returns:
        {
            'intent': 'meeting_interest',
            'confidence': 0.92,
            'extracted_data': {'preferred_time': 'next Tuesday'},
        }
    """
    prompt = f"""
    Classify this reply into one of these intents:
    - meeting_interest (wants to meet/call)
    - question (asking something)
    - positive_engagement (interested, wants more info)
    - not_interested (declining)
    - out_of_office (auto-reply, away)
    - wrong_person (no longer at company)
    - referral (suggesting someone else)
    - angry_or_complaint (upset, threatening)

    Reply: "{content}"

    Previous context: {lead_context.get('last_outreach_summary', 'Initial outreach')}

    Return JSON: {{"intent": "...", "confidence": 0.0-1.0, "extracted_data": {{}}}}
    """

    result = await smart_prompt(prompt)
    return result
```

---

## Response Generation

### Strategy by Intent

| Intent | Method | Cost | Template/Logic |
|--------|--------|------|----------------|
| `meeting_interest` | Template | $0.00 | Calendar link |
| `question` (simple) | Smart Prompt | ~$0.01 | Context-aware answer |
| `question` (complex) | SDK | ~$0.20 | Research-backed (if budget) |
| `positive_engagement` | Smart Prompt | ~$0.01 | Value-add follow-up |
| `not_interested` | Template | $0.00 | Polite close |
| `referral` | Template | $0.00 | Thank you + acknowledge |
| `angry_or_complaint` | HOLD | $0.00 | Human review |
| `out_of_office` | None | $0.00 | Wait for return |
| `wrong_person` | None | $0.00 | Mark invalid |

### Cost Cap Enforcement

```python
# src/services/response_generator.py

MAX_REPLY_SDK_COST_PER_LEAD = 0.50  # USD lifetime cap

async def generate_response(
    lead_id: UUID,
    intent: str,
    content: str,
    channel: str,
) -> dict:
    """
    Generate response based on intent.
    """
    # Check SDK budget
    sdk_spent = await get_lead_reply_sdk_cost(lead_id)
    can_use_sdk = sdk_spent < MAX_REPLY_SDK_COST_PER_LEAD

    if intent == 'meeting_interest':
        persona = await get_lead_persona(lead_id)
        return {
            'response': f"Great! Here's my calendar: {persona.calendly_url}",
            'method': 'template',
            'cost': 0.00,
        }

    if intent == 'question':
        if is_complex_question(content) and can_use_sdk:
            # SDK for complex questions (within budget)
            response = await sdk_generate_reply(lead_id, content)
            return {
                'response': response.content,
                'method': 'sdk',
                'cost': response.cost,
            }
        else:
            # Smart Prompt for simple questions or over budget
            response = await smart_prompt_reply(lead_id, content)
            return {
                'response': response,
                'method': 'smart_prompt',
                'cost': 0.01,
            }

    if intent == 'not_interested':
        return {
            'response': "No problem at all, thanks for letting me know. All the best!",
            'method': 'template',
            'cost': 0.00,
        }

    if intent == 'referral':
        return {
            'response': "Thanks for the referral! I'll reach out to them.",
            'method': 'template',
            'cost': 0.00,
        }

    # Default: positive engagement
    response = await smart_prompt_reply(lead_id, content)
    return {
        'response': response,
        'method': 'smart_prompt',
        'cost': 0.01,
    }
```

---

## Response Timing

**Never respond instantly.** Looks robotic.

```python
# src/services/reply_router.py

import random
from datetime import datetime, timedelta

def calculate_response_delay(timezone: str) -> int:
    """
    Calculate delay before sending response.

    Returns:
        Delay in seconds
    """
    if is_business_hours(timezone):
        # 3-5 minutes during business hours
        return random.randint(180, 300)
    else:
        # 10-15 minutes outside business hours
        return random.randint(600, 900)


async def schedule_response(
    lead_id: UUID,
    channel: str,
    response: str,
    delay_seconds: int,
):
    """
    Schedule response to be sent after delay.
    """
    send_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

    await create_scheduled_task(
        task_type='send_reply',
        lead_id=lead_id,
        channel=channel,
        content=response,
        scheduled_for=send_at,
    )
```

---

## Sequence Actions

| Intent | Sequence Action | Details |
|--------|----------------|---------|
| `meeting_interest` | **Pause** | Stop outreach, wait for meeting outcome |
| `question` | **Pause** | Wait for acknowledgment of answer |
| `positive_engagement` | **Continue** | Keep sequence running |
| `not_interested` | **Stop + Suppress** | End sequence, add to suppression |
| `out_of_office` | **Pause until date** | Extract return date, resume then |
| `wrong_person` | **Stop + Invalid** | Mark lead as invalid |
| `referral` | **Stop + Create** | End sequence, create new lead |
| `angry_or_complaint` | **Stop + Alert** | End immediately, alert admin |

```python
# src/services/sequence_manager.py

async def apply_sequence_action(
    lead_id: UUID,
    intent: str,
    extracted_data: dict,
):
    """
    Apply sequence action based on intent.
    """
    intent_config = REPLY_INTENTS[intent]
    action = intent_config['sequence_action']

    if action == 'stop':
        await stop_sequence(lead_id)

        if intent_config.get('suppress'):
            await add_to_suppression(lead_id, reason=intent)

        if intent_config.get('mark_invalid'):
            await mark_lead_invalid(lead_id, reason=intent)

        if intent_config.get('alert_admin'):
            await send_admin_alert(
                subject=f"Angry reply from lead",
                lead_id=lead_id,
            )

    elif action == 'pause':
        await pause_sequence(lead_id)

    elif action == 'pause_until_return':
        return_date = extracted_data.get('return_date')
        await pause_sequence_until(lead_id, return_date)

    elif action == 'continue':
        pass  # Sequence continues normally

    # Handle referral creation
    if intent_config.get('create_new_lead'):
        referral_info = extracted_data.get('referral')
        if referral_info:
            await create_referral_lead(
                source_lead_id=lead_id,
                referral_name=referral_info.get('name'),
                referral_email=referral_info.get('email'),
            )
```

---

## Conversation Threading

Track conversation state to avoid repetition.

```python
# src/services/conversation_tracker.py

MAX_CONTEXT_MESSAGES = 5

async def get_conversation_context(lead_id: UUID) -> list[dict]:
    """
    Get last N messages for context.
    """
    replies = await get_lead_replies(
        lead_id=lead_id,
        limit=MAX_CONTEXT_MESSAGES,
        order='desc',
    )

    return [
        {
            'direction': 'inbound' if r.is_inbound else 'outbound',
            'channel': r.channel,
            'content': r.content,
            'timestamp': r.created_at,
        }
        for r in reversed(replies)
    ]
```

---

## Database Schema

```sql
-- supabase/migrations/043_lead_replies.sql

CREATE TABLE lead_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id),

    -- Source
    channel TEXT NOT NULL,                    -- 'email', 'sms', 'linkedin'
    direction TEXT NOT NULL DEFAULT 'inbound', -- 'inbound', 'outbound'
    content TEXT NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),

    -- Classification (for inbound)
    intent TEXT,
    intent_confidence FLOAT,
    extracted_data JSONB DEFAULT '{}',
    classified_at TIMESTAMPTZ,

    -- Response (for outbound)
    response_method TEXT,                     -- 'template', 'smart_prompt', 'sdk'
    response_cost DECIMAL(10,4) DEFAULT 0,
    scheduled_for TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,

    -- Outcome
    sequence_action TEXT,
    meeting_created BOOLEAN DEFAULT false,
    referral_lead_id UUID REFERENCES lead_pool(id),
    admin_review_required BOOLEAN DEFAULT false,
    admin_reviewed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_replies_lead ON lead_replies(lead_id);
CREATE INDEX idx_replies_client ON lead_replies(client_id);
CREATE INDEX idx_replies_intent ON lead_replies(intent);
CREATE INDEX idx_replies_pending ON lead_replies(scheduled_for)
    WHERE sent_at IS NULL AND scheduled_for IS NOT NULL;
CREATE INDEX idx_replies_review ON lead_replies(admin_review_required)
    WHERE admin_review_required = true AND admin_reviewed_at IS NULL;

-- Track SDK costs per lead
CREATE OR REPLACE VIEW lead_reply_sdk_costs AS
SELECT
    lead_id,
    SUM(response_cost) as total_sdk_cost
FROM lead_replies
WHERE response_method = 'sdk'
GROUP BY lead_id;
```

---

## Channel Integration

### Email

```python
# src/services/email_events_service.py

async def handle_email_reply(event: dict):
    """
    Handle inbound email reply from Salesforge webhook.
    """
    await reply_router.process(
        channel='email',
        lead_email=event['from'],
        content=event['body'],
        subject=event['subject'],
        message_id=event['message_id'],
        thread_id=event['thread_id'],
    )
```

### SMS

```python
# src/services/sms_webhook_service.py

async def handle_sms_reply(event: dict):
    """
    Handle inbound SMS reply from ClickSend webhook.
    """
    await reply_router.process(
        channel='sms',
        lead_phone=event['from'],
        content=event['body'],
    )
```

### LinkedIn

```python
# src/services/linkedin_webhook_service.py

async def handle_linkedin_message(event: dict):
    """
    Handle inbound LinkedIn message from Unipile webhook.
    """
    await reply_router.process(
        channel='linkedin',
        linkedin_id=event['sender_id'],
        content=event['message'],
    )
```

---

## Files Involved

| File | Status | Purpose |
|------|--------|---------|
| `src/engines/closer.py` | ✅ | Reply handling engine with AI intent |
| `src/services/reply_analyzer.py` | ✅ | Sentiment, objections, questions |
| `src/agents/reply_agent.py` | ✅ | Pydantic AI agent for classification |
| `src/services/thread_service.py` | ✅ | Conversation threading |
| `src/services/email_events_service.py` | ✅ | Email reply handling |
| `src/orchestration/tasks/reply_tasks.py` | ✅ | Reply processing tasks |
| `src/orchestration/flows/reply_recovery_flow.py` | ✅ | Reply recovery flow |
| `supabase/migrations/027_conversation_threads.sql` | ✅ | Thread schema |
| `src/services/sms_webhook_service.py` | 🟡 | SMS reply handling |
| `src/services/linkedin_webhook_service.py` | 🟡 | LinkedIn reply handling |
| `supabase/migrations/046_lead_replies.sql` | ✅ | Replies schema (created 2026-01-22) |
| `src/services/response_timing_service.py` | ✅ | Response timing delays (created 2026-01-22) |

---

## Verification Checklist

- [x] Closer engine implemented with AI intent classification
- [x] Reply analyzer with sentiment/objection detection
- [x] Reply agent (Pydantic AI) for classification
- [x] Thread service for conversation context
- [x] Conversation threads table (migration 027)
- [x] Email events service handles email replies
- [x] Reply tasks in orchestration layer
- [x] Reply recovery flow exists
- [x] `lead_replies` table created (migration 046, 2026-01-22)
- [ ] SMS webhook service fully wired
- [ ] LinkedIn webhook service fully wired
- [x] Response timing delays implemented (`response_timing_service.py`, 2026-01-22)
- [x] Admin alerts for angry/complaint (logger.warning in closer.py, 2026-01-22)
- [x] Referral intent type added (IntentType.REFERRAL + handling, 2026-01-22)

---

## Metrics

```python
REPLY_METRICS = [
    'replies_received_total',
    'replies_by_channel',
    'replies_by_intent',
    'response_time_avg_seconds',
    'sdk_cost_per_reply_avg',
    'sdk_cost_per_lead_avg',
    'meeting_conversion_rate',        # replies → meetings
    'reply_to_meeting_time_avg',
    'suppression_rate',               # not_interested / total
    'referral_rate',
    'angry_complaint_rate',
]
```

---

## Cost Summary

| Component | Cost |
|-----------|------|
| Intent classification | ~$0.005/reply |
| Template response | $0.00 |
| Smart Prompt response | ~$0.01 |
| SDK response | ~$0.15-0.30 |
| **Lifetime cap per lead** | **$0.50** |

**Expected monthly cost (Velocity tier):**
- ~800 replies × $0.02 avg = ~$16/month for reply handling
