# Outreach Flow — Agency OS

**Purpose:** Orchestrate multi-channel outreach (email, SMS, LinkedIn, voice, mail) with JIT validation, rate limiting, and SDK-enhanced personalization for hot leads.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

The Outreach Flow is the core distribution mechanism of Agency OS, responsible for sending personalized messages to leads across five channels. It runs hourly via Prefect and processes leads that are in the `in_sequence` status, ensuring all business rules, compliance requirements, and rate limits are respected before any outreach is sent.

The flow implements Just-In-Time (JIT) validation to ensure that client subscriptions are active, campaigns are running, and leads have not unsubscribed or bounced at the exact moment of sending. This prevents edge cases where state changes between batch processing and actual send would result in unwanted outreach.

Hot leads (ALS score 85+) receive SDK-enhanced content generation, which uses Claude Agent SDK with web research tools to create hyper-personalized emails and voice knowledge bases. This two-tier content strategy maximizes personalization ROI by investing more compute on high-value prospects.

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| **Main Flow** | `src/orchestration/flows/outreach_flow.py` | Hourly Prefect flow with JIT validation |
| **Channel Tasks** | `src/orchestration/tasks/outreach_tasks.py` | Individual channel send tasks |
| **JIT Validator** | `src/services/jit_validator.py` | Pre-send validation service |
| **Send Limiter** | `src/services/send_limiter.py` | TEST_MODE protection service |
| **Allocator Engine** | `src/engines/allocator.py` | Resource allocation, round-robin, rate limits |
| **Email Engine** | `src/engines/email.py` | Salesforge integration, threading |
| **SMS Engine** | `src/engines/sms.py` | ClickSend integration, DNCR compliance |
| **Voice Engine** | `src/engines/voice.py` | Vapi + ElevenLabs integration |
| **LinkedIn Engine** | `src/engines/linkedin.py` | Unipile integration |
| **Mail Engine** | `src/engines/mail.py` | Lob integration |
| **Content Engine** | `src/engines/content.py` | AI content generation |
| **SDK Agents** | `src/agents/sdk_agents/` | Hot lead personalization |

---

## Data Flow

```
                                    HOURLY TRIGGER
                                          |
                                          v
                            +---------------------------+
                            | hourly_outreach_flow()    |
                            | batch_size=50             |
                            +---------------------------+
                                          |
                                          v
                    +----------------------------------------+
                    | get_leads_ready_for_outreach_task()    |
                    |   - status = IN_SEQUENCE               |
                    |   - client.subscription = ACTIVE       |
                    |   - client.credits > 0                 |
                    |   - campaign.status = ACTIVE           |
                    +----------------------------------------+
                                          |
                                          v
                               +--------------------+
                               | Group by Channel   |
                               | (email, linkedin,  |
                               |  sms, voice, mail) |
                               +--------------------+
                                          |
              +------------------+--------+--------+------------------+
              |                  |                 |                  |
              v                  v                 v                  v
      +-------------+    +-------------+    +-------------+    +-------------+
      | Email Leads |    | LinkedIn    |    | SMS Leads   |    | Voice Leads |
      +-------------+    | Leads       |    +-------------+    +-------------+
              |          +-------------+          |                  |
              |                  |                 |                  |
              v                  v                 v                  v
      +------------------------------------------------------------------+
      |                    JIT VALIDATION (per lead)                      |
      |   1. Lead status != UNSUBSCRIBED/BOUNCED/CONVERTED               |
      |   2. Client subscription = ACTIVE or TRIALING                     |
      |   3. Client credits > 0                                           |
      |   4. Campaign status = ACTIVE                                     |
      |   5. Permission mode != MANUAL                                    |
      +------------------------------------------------------------------+
                                          |
                                          v
      +------------------------------------------------------------------+
      |                    ALLOCATOR CHECK (per channel)                  |
      |   - Check rate limit via Redis                                   |
      |   - Consume quota if available                                   |
      |   - Return error if exhausted                                    |
      +------------------------------------------------------------------+
                                          |
                    +---------------------+---------------------+
                    |                                           |
                    v                                           v
          +------------------+                       +--------------------+
          | ALS < 85         |                       | ALS >= 85 (Hot)    |
          | Standard Content |                       | SDK-Enhanced       |
          +------------------+                       +--------------------+
                    |                                           |
                    v                                           v
          +------------------+                       +--------------------+
          | generate_email() |                       | generate_email_    |
          | generate_sms()   |                       | with_sdk()         |
          | generate_linkedin|                       | generate_voice_kb()|
          +------------------+                       +--------------------+
                                          |
                                          v
      +------------------------------------------------------------------+
      |                    CHANNEL ENGINE SEND                            |
      |   - Email: Salesforge (Warmforge-warmed mailboxes)               |
      |   - SMS: ClickSend (DNCR compliance)                             |
      |   - LinkedIn: Unipile (connection/message)                       |
      |   - Voice: Vapi + Twilio + ElevenLabs                            |
      |   - Mail: Lob                                                    |
      +------------------------------------------------------------------+
                                          |
                                          v
      +------------------------------------------------------------------+
      |                    LOG ACTIVITY                                   |
      |   - Record to activities table                                   |
      |   - Store content_snapshot for Conversion Intelligence           |
      |   - Track template_id, ab_test_id, personalization fields        |
      +------------------------------------------------------------------+
                                          |
                                          v
                            +---------------------------+
                            | Return Summary            |
                            | - emails_sent             |
                            | - linkedin_sent           |
                            | - sms_sent                |
                            | - errors                  |
                            +---------------------------+
```

---

## Rate Limits

Resource-level rate limits are enforced via Redis counters with 24-hour TTL. The Allocator engine checks and consumes quota before each send.

| Channel | Daily Limit | Per | Enforced By |
|---------|-------------|-----|-------------|
| **Email** | 50 | Domain | `allocator.py`, `email.py` |
| **SMS** | 100 | Phone Number | `allocator.py`, `sms.py` |
| **Voice** | 50 | Phone Number | `allocator.py`, `voice.py` |
| **LinkedIn** | 17 (default) | Account/Seat | `allocator.py`, `linkedin.py` |
| **Mail** | 1000 | N/A | `allocator.py` |

**Note:** LinkedIn limits are configurable via `settings.linkedin_max_daily`. Unipile supports 80-100/day but we default to conservative 17/day.

---

## ALS Requirements

Different channels have minimum ALS score requirements enforced at various layers.

| Channel | Min ALS | Where Enforced | Notes |
|---------|---------|----------------|-------|
| **Email** | None | `outreach_flow.py` | SDK routing for 85+ |
| **SMS** | None | Allocator | Restricts to Hot only in tier mapping |
| **LinkedIn** | None | No requirement | All tiers eligible |
| **Voice** | 70 | `voice.py send()` | Hard check, returns error if < 70 |
| **Mail** | 85 | `outreach_tasks.py` | Hard check, returns error if < 85 |

---

## JIT Validation Checks

JIT validation runs immediately before each send to catch state changes since batch selection.

| Check | Description | Block Code |
|-------|-------------|------------|
| **Lead Status** | Must be `IN_SEQUENCE` (not unsubscribed/bounced/converted) | `lead_status_*` |
| **Client Subscription** | Must be `ACTIVE` or `TRIALING` | `subscription_inactive` |
| **Client Credits** | Must have credits > 0 | `no_credits` |
| **Campaign Status** | Must be `ACTIVE` | `campaign_inactive` |
| **Permission Mode** | Must not be `MANUAL` | `manual_mode` |
| **Rate Limit** | Daily limit not exceeded | `rate_limit_*` |
| **Cooldown Period** | 2 days between touches to same lead | `too_recent` |
| **Channel Cooldown** | 5 days before reusing same channel | `channel_cooldown` |
| **Email Warmup** | Client active 14+ days for email | `warmup_not_ready` |
| **Global Bounce** | Lead not globally bounced | `bounced_globally` |
| **Unsubscribe** | Lead not globally unsubscribed | `unsubscribed_globally` |
| **Suppression** | Lead not on client suppression list | `suppressed_*` |

---

## SDK Integration

Hot leads (ALS 85+) trigger SDK-enhanced content generation for higher personalization.

### SDK Eligibility Functions

```python
from src.agents.sdk_agents import (
    should_use_sdk_enrichment,  # Hot + priority signals
    should_use_sdk_email,       # ALS >= 85
    should_use_sdk_voice_kb,    # ALS >= 85
)
```

### SDK Routing in Outreach Flow

| Channel | Standard Method | SDK Method | Trigger |
|---------|-----------------|------------|---------|
| Email | `content.generate_email()` | `content.generate_email_with_sdk()` | ALS >= 85 |
| Voice | N/A | `voice.generate_voice_kb()` | ALS >= 85 |

### SDK Cost Limits

| Agent | Max Cost (AUD) | Max Turns |
|-------|----------------|-----------|
| Enrichment | $1.50 | 8 |
| Email | $0.50 | 3 |
| Voice KB | $2.00 | 3 |

---

## Resource Round-Robin

The Allocator engine selects resources using round-robin ordering to distribute load evenly.

```sql
-- Resources selected by last_used_at (nulls first = unused resources prioritized)
ORDER BY last_used_at ASC NULLS FIRST
```

After each use, `last_used_at` is updated to `NOW()` and `usage_count` is incremented.

---

## Providers

| Channel | Provider | Integration File | Notes |
|---------|----------|------------------|-------|
| **Email** | Salesforge | `src/integrations/salesforge.py` | Warmforge-warmed mailboxes |
| **SMS** | ClickSend | `src/integrations/clicksend.py` | Australian provider, DNCR built-in |
| **Voice** | Vapi + Twilio + ElevenLabs | `src/integrations/vapi.py` | STT (Vapi) + LLM (Claude) + TTS (ElevenLabs) |
| **LinkedIn** | Unipile | `src/integrations/unipile.py` | Migrated from HeyReach (70-85% cost reduction) |
| **Mail** | Lob | `src/integrations/lob.py` | Direct mail printing |

---

## TEST_MODE Behavior

When `settings.TEST_MODE = True`:

| Channel | Behavior |
|---------|----------|
| Email | Redirects to `settings.TEST_EMAIL_RECIPIENT` |
| SMS | Redirects to `settings.TEST_SMS_RECIPIENT` |
| Voice | Redirects to `settings.TEST_VOICE_RECIPIENT` |
| LinkedIn | Redirects to `settings.TEST_LINKEDIN_RECIPIENT` |

Additional protection via `send_limiter.py` enforces `TEST_DAILY_EMAIL_LIMIT` (default 15).

---

## Key Rules

1. **JIT Validation Required:** Every outreach must pass JIT validation immediately before send (Rule 13).

2. **Resource-Level Rate Limits:** Limits are per-resource, not per-client. 50/day/domain, not 50/day/client (Rule 17).

3. **SDK for Hot Leads:** Leads with ALS >= 85 must use SDK-enhanced content generation methods.

4. **Voice Requires ALS 70+:** Voice calls are blocked for leads below ALS 70.

5. **Mail Requires ALS 85+:** Direct mail is reserved for Hot leads only.

6. **DNCR Compliance:** SMS sends must pass DNCR (Do Not Call Register) check for Australian numbers.

7. **Email Threading:** Follow-ups use In-Reply-To and References headers for threading (Rule 18).

8. **Round-Robin Resources:** Resources are selected by `last_used_at` to distribute load.

9. **Soft Deletes Only:** Never hard delete records; use `deleted_at` timestamp (Rule 14).

10. **Activity Logging:** All sends are logged to `activities` table with content snapshots for Conversion Intelligence.

---

## Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| `settings.TEST_MODE` | `false` | Redirects all outreach to test recipients |
| `settings.TEST_EMAIL_RECIPIENT` | - | Email address for TEST_MODE |
| `settings.TEST_DAILY_EMAIL_LIMIT` | 15 | Max emails/day in TEST_MODE |
| `settings.linkedin_max_daily` | 17 | LinkedIn actions per account per day |
| `EMAIL_DAILY_LIMIT_PER_DOMAIN` | 50 | Emails per domain per day |
| `SMS_DAILY_LIMIT_PER_NUMBER` | 100 | SMS per number per day |
| `VOICE_DAILY_LIMIT_PER_NUMBER` | 50 | Voice calls per number per day |
| `JITValidator.MIN_TOUCH_GAP_DAYS` | 2 | Days between any touches |
| `JITValidator.CHANNEL_COOLDOWN_DAYS` | 5 | Days before reusing same channel |

---

## Prefect Configuration

```python
@flow(
    name="hourly_outreach",
    description="Hourly outreach flow with JIT validation and multi-channel execution",
    log_prints=True,
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
async def hourly_outreach_flow(batch_size: int = 50):
    ...
```

Tasks use exponential backoff retries:
- Email/SMS/LinkedIn: 3 retries at [60s, 300s, 900s]
- Voice/Mail: 2 retries at [120s, 600s]

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| JIT Validation Failure | Logged, lead skipped, continues to next |
| Rate Limit Exceeded | Logged, returns error in result, continues to next |
| Provider Error | Retry with backoff, then logged as failed |
| DNCR Rejection | Logged as `rejected_dncr`, lead marked |
| ALS Too Low | Returns error, lead skipped |

---

## Activity Logging

All outreach creates Activity records with:

| Field | Description |
|-------|-------------|
| `channel` | Email, SMS, LinkedIn, Voice, Mail |
| `action` | sent, rejected_dncr, completed, etc. |
| `provider_message_id` | External ID from provider |
| `content_preview` | First 200 chars of message |
| `content_snapshot` | Full snapshot for Conversion Intelligence |
| `sequence_step` | Step number in sequence |
| `template_id` | Template UUID (Phase 24B) |
| `ab_test_id` | A/B test UUID (Phase 24B) |
| `ai_model_used` | AI model for generation |

---

## Cross-References

- [`../distribution/EMAIL.md`](../distribution/EMAIL.md) — Email channel spec, Salesforge, domain warmup
- [`../distribution/SMS.md`](../distribution/SMS.md) — SMS channel spec, ClickSend, DNCR
- [`../distribution/VOICE.md`](../distribution/VOICE.md) — Voice channel spec, Vapi, ElevenLabs
- [`../distribution/LINKEDIN.md`](../distribution/LINKEDIN.md) — LinkedIn channel spec, Unipile
- [`../business/SCORING.md`](../business/SCORING.md) — ALS scoring and tier definitions
- [`./ENRICHMENT.md`](./ENRICHMENT.md) — Lead enrichment before outreach
- [`../content/SDK_AND_PROMPTS.md`](../content/SDK_AND_PROMPTS.md) — SDK agent details

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
