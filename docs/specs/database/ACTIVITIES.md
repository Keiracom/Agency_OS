# Database: Activities

**Migration:** `005_activities.sql`

---

## Activities Table

```sql
CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    channel channel_type NOT NULL,
    action TEXT NOT NULL,
    provider_message_id TEXT,       -- For email threading
    led_to_booking BOOLEAN DEFAULT FALSE,  -- Conversion tracking (Phase 16)
    content_snapshot JSONB DEFAULT '{}',   -- Message content for analysis (Phase 16)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRITICAL: Composite indexes for performance
CREATE INDEX idx_activities_client_created ON activities(client_id, created_at DESC);
CREATE INDEX idx_activities_lead_created ON activities(lead_id, created_at DESC);
CREATE INDEX idx_activities_campaign_channel ON activities(campaign_id, channel, action);
CREATE INDEX idx_activities_thread ON activities(lead_id, channel, provider_message_id)
    WHERE provider_message_id IS NOT NULL;
CREATE INDEX idx_activities_booking ON activities(led_to_booking)
    WHERE led_to_booking = TRUE;
```

---

## Activity Actions

| Channel | Possible Actions |
|---------|-----------------|
| `email` | `sent`, `opened`, `clicked`, `replied`, `bounced`, `unsubscribed` |
| `sms` | `sent`, `delivered`, `replied`, `failed` |
| `linkedin` | `connection_sent`, `connection_accepted`, `message_sent`, `message_replied` |
| `voice` | `call_initiated`, `call_answered`, `call_completed`, `voicemail_left`, `meeting_booked` |
| `mail` | `sent`, `delivered`, `returned` |

---

## Content Snapshot Structure (Phase 16)

```json
{
  "subject": "Re: Quick question about...",
  "body_preview": "Hi Sarah, I noticed...",
  "pain_points": ["scaling", "lead quality"],
  "cta_type": "meeting_request",
  "personalization_used": ["company_name", "recent_news"],
  "word_count": 87,
  "has_question": true
}
```

---

## Email Threading

For email follow-ups, store `provider_message_id` to enable:
- Threading via `In-Reply-To` header
- Conversation grouping
- Reply attribution

```sql
-- Find thread for a lead
SELECT * FROM activities
WHERE lead_id = $1
  AND channel = 'email'
  AND provider_message_id IS NOT NULL
ORDER BY created_at DESC;
```

---

## Conversion Trigger (Phase 16)

```sql
-- Trigger: Mark touch that led to booking
CREATE OR REPLACE FUNCTION mark_converting_touch()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'converted' AND OLD.status != 'converted' THEN
        UPDATE activities
        SET led_to_booking = TRUE
        WHERE lead_id = NEW.id
          AND created_at = (
              SELECT MAX(created_at) FROM activities
              WHERE lead_id = NEW.id AND action IN ('sent', 'message_sent', 'call_completed')
          );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_lead_converted
    AFTER UPDATE OF status ON leads
    FOR EACH ROW
    WHEN (NEW.status = 'converted')
    EXECUTE FUNCTION mark_converting_touch();
```
