---
name: email
description: Use when sending, reading, or managing emails. Covers cold outreach (Salesforge), transactional (Resend), and inbox management. Triggers on "send email", "check mail", "email automation", "inbox", bulk email operations.
metadata: {"clawdbot":{"emoji":"📧","always":true,"requires":{"bins":["curl","jq"]}}}
---

# Email 📧

## Purpose (CEO Summary)

This skill handles all email operations for Agency OS:

1. **Cold Outreach** (Salesforge) — Automated sequences to prospects
2. **Transactional** (Resend) — System notifications, confirmations
3. **Inbox Management** — Reading replies, organizing responses

**When to use:** Any email send, read, or automation task.

**Key distinction:** Cold outreach goes through Salesforge (with warmup/deliverability). Transactional goes through Resend (instant, no warmup needed).

---

## Cost Structure ($AUD)

### Salesforge Ecosystem (Cold Outreach)

| Component | Monthly Cost (USD) | Monthly Cost (AUD) | Included |
|-----------|-------------------|-------------------|----------|
| **Salesforge Pro** | $99/mo | ~$154/mo | 5 mailboxes, 5k emails/day |
| **InfraForge** | $3/domain/mo | ~$4.65/domain/mo | Custom sending domains |
| **WarmForge** | Included | Included | Deliverability warmup |

**Per-Email Cost:** At 5k emails/day capacity:
- ~$0.001 AUD/email (at full volume)
- ~$0.01 AUD/email (at 10% utilization)

**Monthly Budget:** Running 3 campaigns at 1000 emails each = ~$154 AUD base + domains

### Resend (Transactional)

| Tier | Monthly Cost (USD) | Monthly Cost (AUD) | Included |
|------|-------------------|-------------------|----------|
| **Free** | $0 | $0 | 100 emails/day, 1 domain |
| **Pro** | $20/mo | ~$31/mo | 50,000 emails/mo |
| **Enterprise** | Custom | Custom | Unlimited |

**Per-Email Cost:**
- Free tier: $0 (within limits)
- Pro tier: ~$0.0006 AUD/email

**Current Usage:** Agency OS uses Free tier for system emails (~50/day)

### Exchange Rate

**1 USD = 1.55 AUD** (verify for budget planning)

---

## Features

- Send individual or bulk emails
- Read inbox and manage replies
- Search messages by date/sender/subject
- Organize with labels/folders
- Email sequence automation
- Template management

---

## Usage Examples

**Conceptual Summary:** Commands interact with email APIs. Cold sends queue through Salesforge; transactional fires immediately via Resend.

```bash
# Check cold outreach stats
# (No direct cost - reading dashboard)
curl "$SALESFORGE_API_URL/campaigns/stats"

# Send transactional email via Resend
# (Cost: ~$0.0006 AUD per email on Pro, free on Free tier)
curl -X POST "https://api.resend.com/emails" \
  -H "Authorization: Bearer $RESEND_API_KEY" \
  -d '{"to":"user@example.com","subject":"Welcome"}'
```

---

## Supported Providers

| Provider | Use Case | Cost Model |
|----------|----------|------------|
| **Salesforge** | Cold outreach | Monthly subscription |
| **Resend** | Transactional | Per-email (free tier available) |
| **Gmail/IMAP** | Inbox reading | Free |

---

## Governance Compliance

- **LAW I:** Read this file before first email operation each session
- **LAW II:** All costs shown in $AUD with conversion notes
- **LAW III:** State cost impact before bulk sends
- **LAW IV:** Conceptual summaries provided

---

## Replaces

- Direct SMTP scripts
- Manual email sending
