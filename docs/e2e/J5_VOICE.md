# J5: Voice Outreach Journey

**Status:** 🟡 Sub-tasks Defined (Pending CEO Approval)
**Priority:** P1 — High-touch channel for warm/hot leads
**Depends On:** J2 Complete + TEST_MODE Verified
**Last Updated:** January 11, 2026
**Sub-Tasks:** 13 groups, 52 individual checks

---

## Overview

Tests the complete AI voice call flow via Vapi + Twilio + ElevenLabs.

**Key Finding from Code Review:**
- Voice requires **ALS >= 70** (not 85 like SMS/Email hot threshold)
- Uses Vapi for orchestration with Anthropic Claude as LLM
- Default voice is ElevenLabs "Adam" (professional male)
- Max call duration: 5 minutes

**User Journey:**
```
ALS >= 70 → Lead Ready → Create/Get Assistant → JIT Validation → TEST_MODE Redirect → Initiate Call via Vapi → AI Conversation → Webhook → Activity Logged
```

---

## Test Recipients (TEST_MODE)

| Field | Value |
|-------|-------|
| Test Phone | +61457543392 |
| TEST_MODE Setting | `settings.TEST_MODE` |
| Redirect Variable | `settings.TEST_VOICE_RECIPIENT` |
| Note | **Real call will be made — have phone ready!** |

---

## Sub-Tasks

### J5.1 — TEST_MODE Verification
**Purpose:** Ensure TEST_MODE redirects all voice calls to test recipient.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.1.1 | Read `src/config/settings.py` — verify `TEST_VOICE_RECIPIENT` | Check Railway env var |
| J5.1.2 | Read `src/engines/voice.py` lines 173-177 — verify redirect logic | N/A |
| J5.1.3 | Verify redirect happens BEFORE call initiation | Trigger call, check logs |
| J5.1.4 | Verify original phone preserved in logs/activity | Check activity record |

**Code Verified:**
```python
# src/engines/voice.py lines 173-177
if settings.TEST_MODE:
    lead.phone = settings.TEST_VOICE_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting voice call {original_phone} → {lead.phone}")
```

**Pass Criteria:**
- [ ] TEST_MODE setting exists
- [ ] TEST_VOICE_RECIPIENT configured
- [ ] Redirect happens before call
- [ ] Original phone logged for reference

<!-- E2E_SESSION_BREAK: J5.1 complete. Next: J5.2 Vapi Integration -->

---

### J5.2 — Vapi Integration
**Purpose:** Verify Vapi client is properly configured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.2.1 | Read `src/integrations/vapi.py` — verify complete implementation | N/A |
| J5.2.2 | Verify `VAPI_API_KEY` env var in Railway | Check Railway vars |
| J5.2.3 | Verify `VAPI_PHONE_NUMBER_ID` env var in Railway | Check Railway vars |
| J5.2.4 | Verify `create_assistant` method | Test assistant creation |
| J5.2.5 | Verify `start_outbound_call` method | Test call initiation |
| J5.2.6 | Verify `get_call` method | Test call status retrieval |
| J5.2.7 | Verify `parse_webhook` method | Test webhook parsing |

**Vapi Client Methods (VERIFIED):**
- `create_assistant()` — Create AI assistant with config
- `get_assistant()` — Get assistant details
- `update_assistant()` — Update assistant config
- `delete_assistant()` — Delete assistant
- `start_outbound_call()` — Initiate call via Twilio
- `get_call()` — Get call status and transcript
- `list_calls()` — List recent calls
- `end_call()` — Force end active call
- `parse_webhook()` — Parse Vapi webhooks

**Pass Criteria:**
- [ ] Vapi integration is complete (290 lines verified)
- [ ] API key and phone number configured
- [ ] Assistant operations work
- [ ] Call operations work
- [ ] Webhook parsing works

<!-- E2E_SESSION_BREAK: J5.2 complete. Next: J5.3 ElevenLabs Voice Configuration -->

---

### J5.3 — ElevenLabs Voice Configuration
**Purpose:** Verify ElevenLabs voice synthesis is configured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.3.1 | Verify default voice ID in voice.py | `DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"` |
| J5.3.2 | Verify ElevenLabs provider in vapi.py | Check `voice.provider = "11labs"` |
| J5.3.3 | Verify voice stability/similarity settings | Check config |
| J5.3.4 | Verify language set to Australian English | `language: "en-AU"` |

**ElevenLabs Config (VERIFIED from vapi.py):**
```python
"voice": {
    "provider": "11labs",
    "voiceId": config.voice_id,
    "stability": 0.5,
    "similarityBoost": 0.75
}
```

**Pass Criteria:**
- [ ] ElevenLabs voice ID configured
- [ ] Voice stability settings appropriate
- [ ] Australian English language set

<!-- E2E_SESSION_BREAK: J5.3 complete. Next: J5.4 Voice Engine Implementation -->

---

### J5.4 — Voice Engine Implementation
**Purpose:** Verify voice engine is fully implemented.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.4.1 | Read `src/engines/voice.py` — verify `send` method | N/A |
| J5.4.2 | Verify no TODO/FIXME/pass in voice.py | `grep -n "TODO\|FIXME\|pass" src/engines/voice.py` |
| J5.4.3 | Verify `create_campaign_assistant` method | N/A |
| J5.4.4 | Verify `get_call_status` method | N/A |
| J5.4.5 | Verify `get_call_transcript` method | N/A |
| J5.4.6 | Verify `process_call_webhook` method | N/A |
| J5.4.7 | Verify OutreachEngine base class extended | Check class definition |

**Voice Engine Features (VERIFIED from voice.py 530 lines):**
- Campaign assistant creation
- Call initiation
- Call status retrieval
- Transcript retrieval
- Webhook processing
- Activity logging with content_snapshot (Phase 16)
- Led_to_booking tracking
- TEST_MODE redirect

**Pass Criteria:**
- [ ] No incomplete implementations
- [ ] All methods have implementations
- [ ] Extends OutreachEngine correctly

<!-- E2E_SESSION_BREAK: J5.4 complete. Next: J5.5 ALS Score Validation -->

---

### J5.5 — ALS Score Validation
**Purpose:** Verify ALS >= 70 required for voice calls.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.5.1 | Read voice.py lines 163-171 — verify ALS check | N/A |
| J5.5.2 | Verify threshold is 70 (not 85) | Check constant |
| J5.5.3 | Verify error returned for low ALS | Test with ALS=60 |

**ALS Validation (VERIFIED):**
```python
# src/engines/voice.py lines 163-171
if lead.als_score is None or lead.als_score < 70:
    return EngineResult.fail(
        error=f"ALS score too low for voice: {lead.als_score} (minimum 70)",
        metadata={"lead_id": str(lead_id), "als_score": lead.als_score},
    )
```

**Pass Criteria:**
- [ ] Voice requires ALS >= 70
- [ ] Low ALS leads rejected
- [ ] Clear error message returned

<!-- E2E_SESSION_BREAK: J5.5 complete. Next: J5.6 Assistant Configuration -->

---

### J5.6 — Assistant Configuration
**Purpose:** Verify AI assistant is properly configured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.6.1 | Read `_build_system_prompt` method | N/A |
| J5.6.2 | Verify system prompt includes conversation rules | Check prompt content |
| J5.6.3 | Verify max_duration_seconds = 300 (5 min) | Check config |
| J5.6.4 | Verify model = claude-sonnet-4-20250514 | Check config |
| J5.6.5 | Verify recording enabled | Check config |

**Assistant Config (VERIFIED from vapi.py):**
```python
class VapiAssistantConfig(BaseModel):
    name: str
    first_message: str
    system_prompt: str
    voice_id: str = "pNInz6obpgDQGcFmaJgB"  # ElevenLabs "Adam"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_duration_seconds: int = 300  # 5 min max
    language: str = "en-AU"
```

**System Prompt Rules (VERIFIED):**
- Be conversational and natural
- Listen actively
- Offer to call back if busy
- Thank politely if not interested
- Book meeting or transfer if interested
- Keep responses concise (1-2 sentences)
- Use Australian English

**Pass Criteria:**
- [ ] System prompt well-defined
- [ ] Max duration appropriate
- [ ] Recording enabled for review

<!-- E2E_SESSION_BREAK: J5.6 complete. Next: J5.7 Rate Limiting -->

---

### J5.7 — Rate Limiting
**Purpose:** Verify call rate limits are enforced.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.7.1 | Check rate limit constant in voice.py | Should be 50/day/number |
| J5.7.2 | Verify rate_limiter.check_and_increment called | Check code |
| J5.7.3 | Verify Redis used for rate limiting | Check redis.py |
| J5.7.4 | Test hitting limit | Make 51 calls, verify 51st blocked |

**Note:** Voice rate limit is 50/day/number (Rule 17).

**Pass Criteria:**
- [ ] Rate limit enforced
- [ ] Redis tracks counts
- [ ] Excess calls blocked

<!-- E2E_SESSION_BREAK: J5.7 complete. Next: J5.8 Activity Logging -->

---

### J5.8 — Activity Logging
**Purpose:** Verify all calls create activity records.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.8.1 | Read `_log_call_activity` method in voice.py | N/A |
| J5.8.2 | Verify activity created on call initiation | Check activity |
| J5.8.3 | Verify content_snapshot stored (Phase 16) | Check snapshot |
| J5.8.4 | Verify call metadata stored (to_number, from_number, lead_name) | Check metadata |
| J5.8.5 | Verify call completion activity created | Check webhook handler |

**Activity Fields (VERIFIED from voice.py):**
- provider_message_id (call_id)
- provider = "vapi"
- provider_status
- metadata: to_number, from_number, lead_name, company
- content_snapshot (Phase 16)
- led_to_booking (Phase 16)

**Pass Criteria:**
- [ ] Activity created on call start
- [ ] Activity created on call end
- [ ] All metadata captured

<!-- E2E_SESSION_BREAK: J5.8 complete. Next: J5.9 Webhook Processing -->

---

### J5.9 — Webhook Processing
**Purpose:** Verify call webhooks are processed correctly.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.9.1 | Read `process_call_webhook` method | N/A |
| J5.9.2 | Verify webhook endpoint exists in webhooks.py | Check `/webhooks/vapi/call` |
| J5.9.3 | Verify call-ended event handling | Check event processing |
| J5.9.4 | Verify transcript stored | Check activity metadata |
| J5.9.5 | Verify recording_url stored | Check activity metadata |
| J5.9.6 | Verify meeting_booked detection | Check lead status update |

**Webhook Event Types:**
- call-ended
- end-of-call-report

**Pass Criteria:**
- [ ] Webhooks processed correctly
- [ ] Transcript captured
- [ ] Recording URL captured
- [ ] Meeting booking detected

<!-- E2E_SESSION_BREAK: J5.9 complete. Next: J5.10 Call Recording -->

---

### J5.10 — Call Recording
**Purpose:** Verify call recordings are captured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.10.1 | Verify `recordingEnabled: true` in config | Check vapi.py |
| J5.10.2 | Verify recording_url stored in activity | Check webhook handler |
| J5.10.3 | N/A | Access recording URL, verify audio plays |

**Pass Criteria:**
- [ ] Recording enabled
- [ ] Recording URL stored
- [ ] Recording accessible

<!-- E2E_SESSION_BREAK: J5.10 complete. Next: J5.11 Call Outcome Handling -->

---

### J5.11 — Call Outcome Handling
**Purpose:** Verify call outcomes are classified and handled.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.11.1 | Verify ended_reason captured from webhook | Check parsing |
| J5.11.2 | Verify outcome stored in activity | Check metadata |
| J5.11.3 | Verify lead status updated on meeting booked | Check lead update |
| J5.11.4 | Verify reply_count incremented | Check lead update |

**Outcome Types (from Vapi):**
- completed
- busy
- no-answer
- voicemail
- failed

**Pass Criteria:**
- [ ] Outcomes captured correctly
- [ ] Lead status updated appropriately
- [ ] Meeting bookings detected

<!-- E2E_SESSION_BREAK: J5.11 complete. Next: J5.12 Error Handling -->

---

### J5.12 — Error Handling
**Purpose:** Verify graceful error handling.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.12.1 | Verify Vapi errors caught | Check exception handling |
| J5.12.2 | Verify EngineResult.fail returned on error | Check return structure |
| J5.12.3 | Verify missing assistant_id handled | Test without assistant_id |
| J5.12.4 | Verify missing phone handled | Test without phone |

**Pass Criteria:**
- [ ] Errors don't crash the flow
- [ ] Clear error messages returned
- [ ] Required fields validated

<!-- E2E_SESSION_BREAK: J5.12 complete. Next: J5.13 Live Voice Call Test -->

---

### J5.13 — Live Voice Call Test
**Purpose:** Verify real AI voice call works end-to-end.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J5.13.1 | Verify test phone ready | Have phone available |
| J5.13.2 | N/A | Initiate call via TEST_MODE |
| J5.13.3 | N/A | **Answer phone, talk to AI agent** |
| J5.13.4 | N/A | Verify conversation quality |
| J5.13.5 | N/A | Verify personalization spoken correctly |
| J5.13.6 | N/A | Check activity record after call |
| J5.13.7 | N/A | Check transcript captured |
| J5.13.8 | N/A | Check recording accessible |

**Pass Criteria:**
- [ ] Call connects successfully
- [ ] AI agent speaks clearly
- [ ] AI agent responds appropriately
- [ ] Personalization works
- [ ] Transcript captured
- [ ] Recording accessible

<!-- E2E_SESSION_BREAK: J5 JOURNEY COMPLETE. Next: J6 LinkedIn Outreach -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Voice Engine | `src/engines/voice.py` | 530 | ✅ VERIFIED |
| Vapi Integration | `src/integrations/vapi.py` | 290 | ✅ VERIFIED |
| Webhooks | `src/api/routes/webhooks.py` | - | Vapi endpoint exists |
| Settings | `src/config/settings.py` | - | TEST_MODE config |

---

## Completion Criteria

All checks must pass:

- [ ] **J5.1** TEST_MODE redirects all calls
- [ ] **J5.2** Vapi integration complete
- [ ] **J5.3** ElevenLabs voice configured
- [ ] **J5.4** Voice engine fully implemented
- [ ] **J5.5** ALS >= 70 validation works
- [ ] **J5.6** Assistant configured correctly
- [ ] **J5.7** Rate limits enforced
- [ ] **J5.8** Activities logged
- [ ] **J5.9** Webhooks processed
- [ ] **J5.10** Recordings captured
- [ ] **J5.11** Outcomes classified
- [ ] **J5.12** Errors handled gracefully
- [ ] **J5.13** **Live voice call works end-to-end**

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Voice engine is comprehensive (530 lines)
2. ✅ Vapi integration complete (290 lines)
3. ✅ ALS threshold is 70 (not 85 like email/SMS hot)
4. ✅ TEST_MODE redirect implemented
5. ✅ Activity logging with Phase 16 content_snapshot
6. ✅ Webhook processing for call completion
7. ✅ Led_to_booking tracking for conversion

**No Issues Found** - Voice engine is well-implemented.

---

## Notes

**IMPORTANT:** J5.13 requires a REAL phone call:
- Have test phone (+61457543392) ready
- Be prepared to answer and talk to AI
- Verify conversation flows naturally
- This is the only way to validate voice works correctly

**Cost Consideration:**
Voice calls cost ~$0.15-0.25/min via Vapi. Test calls will incur real costs.
