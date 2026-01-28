---
name: Fix 12 - Resend Email Reply Handler
description: Adds replied event handler for Resend webhooks
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 12: Resend Email Reply Handling Missing

## Gap Reference
- **TODO.md Item:** #12
- **Priority:** P2 High
- **Location:** `src/api/routes/webhooks.py`
- **Issue:** No "replied" event handler for Resend

## Pre-Flight Checks

1. Find Resend webhook handler:
   ```bash
   grep -rn "resend\|Resend" src/api/routes/webhooks.py
   ```

2. Check existing event handlers:
   ```bash
   grep -n "delivered\|opened\|clicked\|bounced" src/api/routes/webhooks.py
   ```

3. Check Resend documentation for reply event:
   - Resend may use "email.replied" or similar event type

## Implementation Steps

1. **Identify reply event type** from Resend:
   - Check if Resend sends reply events directly
   - Or if replies come via inbound email webhook

2. **Add reply handler to webhooks.py:**
   ```python
   @router.post("/webhooks/resend")
   async def handle_resend_webhook(
       request: Request,
       db: Session = Depends(get_db)
   ):
       payload = await request.json()
       event_type = payload.get("type")

       if event_type == "email.delivered":
           await handle_email_delivered(db, payload)
       elif event_type == "email.opened":
           await handle_email_opened(db, payload)
       elif event_type == "email.clicked":
           await handle_email_clicked(db, payload)
       elif event_type == "email.bounced":
           await handle_email_bounced(db, payload)
       # ADD THIS:
       elif event_type == "email.replied":
           await handle_email_replied(db, payload)

       return {"status": "ok"}

   async def handle_email_replied(db: Session, payload: dict):
       """Handle email reply event from Resend."""
       email_id = payload.get("data", {}).get("email_id")
       reply_content = payload.get("data", {}).get("content")

       # Find original outreach record
       outreach = await get_outreach_by_email_id(db, email_id)
       if not outreach:
           logger.warning(f"Reply for unknown email: {email_id}")
           return

       # Update lead status
       lead = outreach.lead
       lead.status = "responded"
       lead.last_response_at = datetime.utcnow()

       # Store reply content
       await create_lead_activity(
           db,
           lead_id=lead.id,
           activity_type="email_reply",
           content=reply_content,
           metadata={"email_id": email_id}
       )

       # Trigger reply processing (sentiment, objection handling, etc.)
       await process_email_reply(db, lead.id, reply_content)

       db.commit()
       logger.info(f"Processed reply for lead {lead.id}")
   ```

3. **Add helper functions** if needed:
   - `get_outreach_by_email_id()`
   - `create_lead_activity()`
   - `process_email_reply()`

4. **Handle inbound email** if Resend uses that instead:
   ```python
   @router.post("/webhooks/resend/inbound")
   async def handle_resend_inbound(request: Request, db: Session = Depends(get_db)):
       """Handle inbound email (reply) from Resend."""
       # Match reply to original by In-Reply-To header or subject
   ```

## Acceptance Criteria

- [ ] Reply event handler added to webhooks.py
- [ ] Extracts email_id and reply content from payload
- [ ] Updates lead status to "responded"
- [ ] Records lead activity for the reply
- [ ] Triggers downstream reply processing
- [ ] Logs reply handling

## Validation

```bash
# Check handler exists
grep -n "replied\|reply" src/api/routes/webhooks.py

# Verify no syntax errors
python -m py_compile src/api/routes/webhooks.py

# Type check
mypy src/api/routes/webhooks.py --ignore-missing-imports

# Check function signature
grep -A 5 "handle_email_replied" src/api/routes/webhooks.py
```

## Post-Fix

1. Update TODO.md — delete gap row #12
2. Report: "Fixed #12. Resend reply handler added to webhooks.py."
