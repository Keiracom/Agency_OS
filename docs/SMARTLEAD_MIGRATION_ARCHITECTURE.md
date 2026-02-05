# SMARTLEAD MIGRATION ARCHITECTURE
## Agency OS Email Infrastructure Migration Plan

**Phase:** FIXED_COST_OPTIMIZATION_PHASE_2
**Status:** ARCHITECTURE DESIGN
**Savings:** ~$36 AUD/month ($111 → $75)
**Migration Type:** Parallel-run with cutover

---

## 1. EXECUTIVE SUMMARY

### Cost Comparison

| Component | Forge Stack (Current) | Smartlead (Proposed) | Savings |
|-----------|----------------------|----------------------|---------|
| InfraForge (Domains) | $18.10 AUD/mo | Included | $18.10 |
| WarmForge (Warmup) | $46.50 AUD/mo | Included (Unlimited) | $46.50 |
| Salesforge (Sending) | $46.50 AUD/mo | $75 AUD/mo | -$28.50 |
| **Total** | **$111.10 AUD/mo** | **$75 AUD/mo** | **$36.10/mo** |

**Annual Savings:** $433.20 AUD

### Strategic Benefits
1. **Single Platform:** Eliminates 3-way integration complexity
2. **Unlimited Warmup:** No per-mailbox warmup fees
3. **Built-in Analytics:** Reply detection, open tracking
4. **Simpler Error Surface:** One API vs three

### Risks
1. **Vendor Lock-in:** More dependent on single vendor
2. **Feature Gaps:** Domain purchasing is external
3. **Migration Effort:** ~15 hours one-time

---

## 2. MIGRATION ARCHITECTURE

### Current Flow (Forge Stack)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FORGE STACK FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Namecheap/   │───▶│  InfraForge  │───▶│  WarmForge   │          │
│  │ Cloudflare   │    │ (DNS + DKIM) │    │  (Warmup)    │          │
│  │ (Domains)    │    │              │    │              │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                   │
│         │                   ▼                   │                   │
│         │            ┌──────────────┐           │                   │
│         │            │ Salesforge   │◀──────────┘                   │
│         └───────────▶│ (Sending)    │                               │
│                      │              │                               │
│                      └──────────────┘                               │
│                             │                                       │
│                             ▼                                       │
│                      ┌──────────────┐                               │
│                      │  Supabase    │                               │
│                      │ (Tracking)   │                               │
│                      └──────────────┘                               │
│                                                                     │
│  Cost: $111.10 AUD/mo | APIs: 3 | Complexity: HIGH                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Proposed Flow (Smartlead)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SMARTLEAD FLOW                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐         ┌──────────────────────────────────┐     │
│  │ Namecheap/   │────────▶│           SMARTLEAD              │     │
│  │ Cloudflare   │         │  ┌────────────────────────────┐  │     │
│  │ (Domains)    │         │  │ Mailbox Management         │  │     │
│  └──────────────┘         │  │ • DKIM/SPF/DMARC Setup     │  │     │
│         │                 │  │ • Auto Warmup (Unlimited)  │  │     │
│         │                 │  │ • Reputation Monitoring    │  │     │
│         │                 │  └────────────────────────────┘  │     │
│  ┌──────────────┐         │  ┌────────────────────────────┐  │     │
│  │ Prefect      │────────▶│  │ Campaign Engine            │  │     │
│  │ (DNS Flow)   │         │  │ • Sequence Management      │  │     │
│  └──────────────┘         │  │ • Send Scheduling          │  │     │
│                           │  │ • Reply Detection          │  │     │
│                           │  └────────────────────────────┘  │     │
│                           │  ┌────────────────────────────┐  │     │
│                           │  │ Lead Management            │  │     │
│                           │  │ • Deduplication            │  │     │
│                           │  │ • Sequence Exit Logic      │  │     │
│                           │  └────────────────────────────┘  │     │
│                           └──────────────────────────────────┘     │
│                                          │                          │
│                                          │ Webhooks                 │
│                                          ▼                          │
│                           ┌──────────────────────────────────┐     │
│                           │          Supabase                │     │
│                           │  • Email Events                  │     │
│                           │  • Lead Status Sync              │     │
│                           │  • Analytics                     │     │
│                           └──────────────────────────────────┘     │
│                                                                     │
│  Cost: $75 AUD/mo | APIs: 1 | Complexity: LOW                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Domain Provisioning Strategy

**Option A: Namecheap + Cloudflare (Recommended)**
- Purchase domains via Namecheap ($10-14 USD/year)
- DNS management via Cloudflare (Free)
- Prefect flow handles DKIM/SPF/DMARC record creation
- Records provided by Smartlead API

**Option B: Smartlead Domain Purchasing**
- Not available in Basic plan
- Only for Enterprise (>$299/mo USD)
- Not recommended for cost target

### DNS Automation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DNS AUTOMATION FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Domain Purchase (Manual or Namecheap API)                       │
│         │                                                           │
│         ▼                                                           │
│  2. Cloudflare Zone Creation                                        │
│         │  POST /zones {name: "domain.com"}                         │
│         ▼                                                           │
│  3. Smartlead Mailbox Creation                                      │
│         │  POST /email-accounts                                     │
│         │  Response includes DKIM selector + public key             │
│         ▼                                                           │
│  4. DNS Record Automation (Prefect Task)                            │
│         │                                                           │
│         ├──▶ SPF: "v=spf1 include:_spf.smartlead.ai ~all"          │
│         │                                                           │
│         ├──▶ DKIM: {selector}._domainkey TXT "v=DKIM1; k=rsa; p=.."│
│         │                                                           │
│         └──▶ DMARC: _dmarc TXT "v=DMARC1; p=quarantine; ..."       │
│                                                                     │
│  5. Nameserver Update (if not already Cloudflare)                   │
│         │                                                           │
│         ▼                                                           │
│  6. Verification Check (Prefect scheduled task)                     │
│         │  Wait for DNS propagation (up to 48h)                     │
│         ▼                                                           │
│  7. Enable Warmup                                                   │
│         POST /email-accounts/{id}/warmup                            │
│         {warmup_enabled: true, total_warmup_per_day: 20}            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. SMARTLEAD API REFERENCE

### Base URL
```
https://server.smartlead.ai/api/v1
```

### Authentication
```
?api_key={SMARTLEAD_API_KEY}
```

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/email-accounts` | GET | List all mailboxes |
| `/email-accounts` | POST | Add new mailbox |
| `/email-accounts/{id}` | GET | Get mailbox details |
| `/email-accounts/{id}/warmup` | POST | Configure warmup |
| `/campaigns` | GET/POST | Manage campaigns |
| `/campaigns/{id}/leads` | POST | Add leads |
| `/campaigns/{id}/leads` | GET | List campaign leads |
| `/leads/{email}` | GET | Get lead by email |
| `/campaigns/{id}/schedule` | POST | Set send schedule |

### Webhook Events
```json
{
  "events": [
    "EMAIL_SENT",
    "EMAIL_OPENED", 
    "EMAIL_CLICKED",
    "EMAIL_REPLIED",
    "EMAIL_BOUNCED",
    "EMAIL_UNSUBSCRIBED",
    "LEAD_CATEGORY_UPDATE"
  ]
}
```

---

## 4. PREFECT INTEGRATION DESIGN

### Flow 1: smartlead_domain_setup_flow.py

```python
"""
FILE: src/orchestration/flows/smartlead_domain_setup_flow.py
PURPOSE: Automated DNS configuration for Smartlead mailboxes
PHASE: SMARTLEAD_MIGRATION
DEPENDENCIES:
  - src/integrations/smartlead.py
  - src/integrations/cloudflare.py
TRIGGER: On-demand (new domain provisioning)
"""

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

# Tasks:
# 1. create_cloudflare_zone_task(domain) → zone_id
# 2. create_smartlead_mailbox_task(email, imap_config) → {dkim_selector, dkim_key}
# 3. create_dns_records_task(zone_id, spf, dkim, dmarc)
# 4. verify_dns_propagation_task(domain) → bool
# 5. enable_warmup_task(mailbox_id, warmup_config)
# 6. log_provisioning_task(domain, mailboxes, status)

@flow(
    name="smartlead_domain_setup",
    description="Configure DNS and create mailboxes for new domain",
    task_runner=ConcurrentTaskRunner(),
    tags=["tier:bulk", "smartlead", "infra:spot"],
)
async def smartlead_domain_setup_flow(
    domain: str,
    mailbox_count: int = 2,
    client_id: str = None,
    cloudflare_zone_id: str = None,  # Optional if zone exists
) -> dict:
    """
    Steps:
    1. Create/verify Cloudflare zone
    2. Create mailboxes in Smartlead
    3. Extract DKIM records from Smartlead response
    4. Create SPF/DKIM/DMARC records in Cloudflare
    5. Wait for propagation (async check)
    6. Enable warmup
    
    Returns:
        {
            "success": True,
            "domain": "example.com",
            "mailboxes_created": 2,
            "dns_configured": True,
            "warmup_enabled": True,
            "estimated_ready_date": "2026-02-19"  # 14 days
        }
    """
    pass
```

### Flow 2: smartlead_mailbox_provisioning_flow.py

```python
"""
FILE: src/orchestration/flows/smartlead_mailbox_provisioning_flow.py
PURPOSE: Bulk mailbox provisioning with warmup management
PHASE: SMARTLEAD_MIGRATION
TRIGGER: Scheduled daily or on-demand
"""

from prefect import flow, task

# Tasks:
# 1. get_current_mailboxes_task() → list[mailbox]
# 2. check_warmup_status_task(mailbox_id) → {heat_score, status}
# 3. graduate_warmed_mailboxes_task(mailboxes) → graduated_count
# 4. create_new_mailboxes_task(domains, count_per_domain)
# 5. rotate_degraded_mailboxes_task(threshold=60)
# 6. sync_status_to_supabase_task(mailboxes)

@flow(
    name="smartlead_mailbox_provisioning",
    description="Manage mailbox lifecycle: create, warmup, graduate, retire",
    tags=["tier:realtime", "smartlead"],
)
async def smartlead_mailbox_provisioning_flow(
    action: str = "sync",  # sync | create | graduate | retire
    target_mailbox_count: int = 20,
    domains: list[str] = None,
) -> dict:
    """
    Actions:
    - sync: Check all mailboxes, update Supabase status
    - create: Create new mailboxes on specified domains
    - graduate: Move warmed mailboxes (heat>=85) to production
    - retire: Disable mailboxes with poor reputation (<60)
    
    Returns:
        {
            "action": "sync",
            "mailboxes_total": 20,
            "warming": 5,
            "production": 12,
            "retired": 3,
            "graduated_this_run": 2
        }
    """
    pass
```

### Flow 3: smartlead_campaign_flow.py

```python
"""
FILE: src/orchestration/flows/smartlead_campaign_flow.py
PURPOSE: Campaign creation and sequence management
PHASE: SMARTLEAD_MIGRATION
TRIGGER: On-demand (new campaign) or scheduled (send batches)
"""

from prefect import flow, task

# Tasks:
# 1. create_campaign_task(name, settings) → campaign_id
# 2. configure_sequence_task(campaign_id, steps) → sequence_id
# 3. assign_mailboxes_task(campaign_id, mailbox_ids)
# 4. set_schedule_task(campaign_id, schedule)
# 5. add_leads_batch_task(campaign_id, leads) → added_count
# 6. start_campaign_task(campaign_id)
# 7. pause_campaign_task(campaign_id, reason)
# 8. get_campaign_stats_task(campaign_id) → stats

@flow(
    name="smartlead_campaign",
    description="Create and manage email campaigns",
    tags=["tier:realtime", "smartlead"],
)
async def smartlead_campaign_flow(
    action: str = "create",  # create | start | pause | stats | add_leads
    campaign_id: str = None,
    campaign_config: dict = None,
    leads: list[dict] = None,
) -> dict:
    """
    Campaign Configuration Schema:
    {
        "name": "Q1 Outreach - Trades",
        "client_id": "uuid",
        "from_mailboxes": ["outreach1@domain.com", "outreach2@domain.com"],
        "sequence": [
            {"step": 1, "subject": "...", "body": "...", "delay_days": 0},
            {"step": 2, "subject": "Re: ...", "body": "...", "delay_days": 3},
            {"step": 3, "subject": "Re: ...", "body": "...", "delay_days": 5}
        ],
        "schedule": {
            "timezone": "Australia/Sydney",
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "start_hour": 9,
            "end_hour": 17
        },
        "limits": {
            "daily_per_mailbox": 40,
            "warmup_reserve": 20  # Keep 20 for warmup even in production
        }
    }
    """
    pass
```

### Flow 4: smartlead_lead_sync_flow.py

```python
"""
FILE: src/orchestration/flows/smartlead_lead_sync_flow.py
PURPOSE: Bidirectional lead sync between Supabase and Smartlead
PHASE: SMARTLEAD_MIGRATION
TRIGGER: Webhook-triggered or scheduled (every 15 min)
"""

from prefect import flow, task

# Tasks:
# 1. fetch_new_leads_from_supabase_task(since) → leads
# 2. deduplicate_leads_task(leads) → unique_leads
# 3. push_leads_to_smartlead_task(campaign_id, leads)
# 4. fetch_lead_updates_from_smartlead_task(since) → updates
# 5. update_lead_status_in_supabase_task(updates)
# 6. handle_replies_task(replies) → leads_to_exit
# 7. handle_bounces_task(bounces) → leads_to_suppress
# 8. sync_unsubscribes_task(unsubscribes)

@flow(
    name="smartlead_lead_sync",
    description="Sync leads and events between Supabase and Smartlead",
    tags=["tier:realtime", "smartlead"],
)
async def smartlead_lead_sync_flow(
    direction: str = "bidirectional",  # push | pull | bidirectional
    campaign_id: str = None,
    since_minutes: int = 15,
) -> dict:
    """
    Sync Logic:
    
    PUSH (Supabase → Smartlead):
    1. Get leads with status='ready_to_send' from leads table
    2. Deduplicate against existing Smartlead leads
    3. Push to appropriate campaign
    4. Update leads.smartlead_id in Supabase
    
    PULL (Smartlead → Supabase):
    1. Fetch events from Smartlead (opens, clicks, replies, bounces)
    2. Update leads.email_status in Supabase
    3. Handle special cases:
       - Reply: Mark as 'replied', exit sequence
       - Bounce: Mark as 'bounced', add to suppression list
       - Unsubscribe: Mark as 'unsubscribed', never email again
    
    Returns:
        {
            "pushed": 45,
            "pulled_events": 123,
            "replies_processed": 3,
            "bounces_processed": 2,
            "sequence_exits": 3
        }
    """
    pass
```

---

## 5. BUFFER & SAFEGUARD SYSTEM

### Daily Send Limits

```python
# Send limit configuration
SEND_LIMITS = {
    "warmup": {
        "day_1_7": {"min": 5, "max": 20, "rampup_per_day": 3},
        "day_8_14": {"min": 20, "max": 40, "rampup_per_day": 5},
        "day_15_30": {"min": 40, "max": 60, "rampup_per_day": 3},
        "day_30+": {"min": 60, "max": 80, "rampup_per_day": 2},
    },
    "production": {
        "soft_limit": 50,  # Recommended daily per mailbox
        "hard_limit": 80,  # Absolute maximum
        "warmup_reserve": 20,  # Always reserve for warmup even in production
    },
    "emergency": {
        "pause_threshold": 100,  # Pause if anyone tries to exceed
    }
}
```

### Warmup Graduation Logic

```
┌─────────────────────────────────────────────────────────────────────┐
│                   WARMUP GRADUATION STATE MACHINE                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    ┌──────────┐     14 days     ┌──────────┐     Heat ≥ 85         │
│    │   NEW    │───────────────▶│ WARMING  │──────────────────┐     │
│    └──────────┘                 └──────────┘                  │     │
│         │                            │                        │     │
│         │ API Error                  │ Heat < 60              │     │
│         ▼                            ▼                        ▼     │
│    ┌──────────┐                ┌──────────┐            ┌──────────┐│
│    │  ERROR   │                │ DEGRADED │            │PRODUCTION││
│    └──────────┘                └──────────┘            └──────────┘│
│         │                            │                        │     │
│         │ Retry OK                   │ 7 days recovery        │     │
│         ▼                            ▼                        │     │
│    ┌──────────┐                ┌──────────┐    Heat < 60      │     │
│    │   NEW    │◀───────────────│ WARMING  │◀──────────────────┘     │
│    └──────────┘   Recovery     └──────────┘   Reputation Drop       │
│                                      │                              │
│                                      │ 30 days, no recovery         │
│                                      ▼                              │
│                                ┌──────────┐                         │
│                                │ RETIRED  │                         │
│                                └──────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Graduation Criteria

```python
GRADUATION_CRITERIA = {
    "minimum_warmup_days": 14,
    "minimum_heat_score": 85,
    "minimum_emails_sent": 200,
    "maximum_bounce_rate": 0.02,  # 2%
    "maximum_spam_rate": 0.001,   # 0.1%
    "minimum_open_rate": 0.15,    # 15% (ensures reputation)
}
```

### Bounce Rate Monitoring

```python
# Bounce monitoring thresholds
BOUNCE_THRESHOLDS = {
    "normal": 0.02,      # < 2% - All good
    "warning": 0.05,     # 2-5% - Alert, reduce volume
    "critical": 0.08,    # 5-8% - Pause new sends
    "emergency": 0.10,   # > 10% - Pause all, investigate
}

# Actions per threshold
BOUNCE_ACTIONS = {
    "warning": [
        "send_slack_alert",
        "reduce_daily_limit_by_25_percent",
        "increase_monitoring_frequency",
    ],
    "critical": [
        "send_urgent_alert",
        "pause_new_lead_additions",
        "reduce_daily_limit_by_50_percent",
    ],
    "emergency": [
        "pause_all_campaigns",
        "send_sms_alert_to_dave",
        "trigger_investigation_flow",
    ],
}
```

### Auto-Pause Logic

```python
async def check_auto_pause_conditions(mailbox_id: str) -> dict:
    """
    Check if mailbox should be auto-paused.
    
    Pause Triggers:
    1. Bounce rate > 8% (last 24h)
    2. Spam complaints > 0.3% (last 7 days)
    3. Heat score dropped below 60
    4. API returns "mailbox_disabled" error
    5. Sender reputation score < 50 (if available)
    """
    conditions = {
        "bounce_rate_exceeded": bounce_rate > 0.08,
        "spam_rate_exceeded": spam_rate > 0.003,
        "heat_score_low": heat_score < 60,
        "api_disabled": api_status == "disabled",
        "reputation_critical": reputation < 50,
    }
    
    should_pause = any(conditions.values())
    
    return {
        "should_pause": should_pause,
        "reasons": [k for k, v in conditions.items() if v],
        "recommended_action": determine_recovery_action(conditions),
    }
```

### Lead Deduplication

```python
# Deduplication strategy
DEDUP_CONFIG = {
    "scope": "global",  # Check across ALL campaigns, not just current
    "key_fields": ["email"],  # Primary dedup key
    "secondary_check": ["company", "domain"],  # Prevent multi-touch to same org
    "time_window_days": 90,  # Don't re-email within 90 days
    "status_blocklist": [
        "replied",
        "bounced", 
        "unsubscribed",
        "spam_complaint",
    ],
}

async def deduplicate_leads(leads: list[dict]) -> tuple[list, list]:
    """
    Returns:
        (unique_leads, duplicate_leads)
    
    Dedup checks:
    1. Email exists in Smartlead (any campaign)
    2. Email exists in Supabase suppression_list
    3. Domain has been contacted in last 90 days
    4. Email status is in blocklist
    """
    pass
```

### Reply Detection & Sequence Exit

```python
# Reply handling configuration
REPLY_CONFIG = {
    "detection_method": "webhook",  # webhook | polling
    "polling_interval_minutes": 5,  # If using polling
    
    # Auto-categorization
    "auto_categories": {
        "positive": ["interested", "schedule", "call", "meeting", "yes"],
        "negative": ["not interested", "remove", "unsubscribe", "stop"],
        "out_of_office": ["ooo", "out of office", "vacation", "away"],
    },
    
    # Actions per category
    "actions": {
        "positive": {
            "exit_sequence": True,
            "update_status": "lead_hot",
            "create_task": "follow_up_call",
            "notify_channel": "#sales-hot-leads",
        },
        "negative": {
            "exit_sequence": True,
            "update_status": "rejected",
            "add_to_suppression": True,
        },
        "out_of_office": {
            "exit_sequence": False,  # Keep in sequence
            "pause_days": 7,         # Resume after OOO period
            "update_status": "paused_ooo",
        },
        "unknown": {
            "exit_sequence": True,  # Conservative - assume reply = interested
            "update_status": "needs_review",
            "create_task": "review_reply",
        },
    },
}
```

---

## 6. ERROR HANDLING MATRIX

| Error Type | Detection Method | Immediate Response | Recovery Strategy | Escalation |
|------------|------------------|-------------------|-------------------|------------|
| **API Timeout** | `httpx.TimeoutException` | Retry with exponential backoff (3 attempts) | Increase timeout, check API status | If >5 failures/hour → Slack alert |
| **Rate Limit (429)** | HTTP 429 + `Retry-After` header | Wait `Retry-After` seconds, then retry | Reduce batch sizes, add jitter | If hitting limits consistently → review quota |
| **Bounce (Hard)** | Webhook: `EMAIL_BOUNCED` | Remove from sequence, add to suppression | Never email again | If bounce rate >5% → pause campaign |
| **Bounce (Soft)** | Webhook: `EMAIL_BOUNCED` (temp) | Retry after 24h (max 3 retries) | After 3 soft bounces → treat as hard | Log pattern for domain analysis |
| **Spam Complaint** | Webhook: `SPAM_COMPLAINT` | Remove from all sequences, permanent suppress | Never email, review content | If >0.1% complaints → pause all campaigns |
| **Mailbox Disabled** | API error / Webhook | Pause all campaigns using mailbox | Investigate cause, try re-enable | If disabled >24h → retire mailbox |
| **Campaign Paused (External)** | API response / Webhook | Log reason, don't auto-resume | Human review required | Notify via Slack |
| **Invalid Lead Data** | Pre-send validation | Skip lead, log error | Enrich/fix lead data | Batch of >10 failures → alert |
| **Webhook Delivery Failure** | Smartlead dashboard / missing events | Poll API as fallback | Fix webhook endpoint | If >1h of missed events → critical alert |
| **DNS Misconfiguration** | Warmup failures, high bounce | Pause new sends on domain | Audit DNS records, fix | Domain remains paused until verified |

### Error Response Code Reference

```python
ERROR_RESPONSES = {
    # HTTP Status Codes
    400: {"action": "log_and_skip", "retry": False, "message": "Bad request - fix payload"},
    401: {"action": "alert_critical", "retry": False, "message": "Auth failed - check API key"},
    403: {"action": "alert_critical", "retry": False, "message": "Forbidden - check permissions"},
    404: {"action": "log_and_skip", "retry": False, "message": "Resource not found"},
    429: {"action": "wait_and_retry", "retry": True, "message": "Rate limited"},
    500: {"action": "retry_with_backoff", "retry": True, "message": "Server error"},
    502: {"action": "retry_with_backoff", "retry": True, "message": "Bad gateway"},
    503: {"action": "retry_with_backoff", "retry": True, "message": "Service unavailable"},
    
    # Smartlead-Specific Error Codes (from API response body)
    "MAILBOX_DISABLED": {"action": "pause_and_alert", "retry": False},
    "CAMPAIGN_LIMIT_REACHED": {"action": "queue_for_tomorrow", "retry": False},
    "LEAD_ALREADY_EXISTS": {"action": "skip_silently", "retry": False},
    "INVALID_EMAIL": {"action": "log_and_suppress", "retry": False},
    "WARMUP_FAILED": {"action": "check_dns_and_retry", "retry": True},
}
```

---

## 7. ROLLBACK PLAN

### Migration Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MIGRATION TIMELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Week 1-2: Parallel Setup                                           │
│  ├─ Set up Smartlead account                                        │
│  ├─ Create 2 test mailboxes (new domains)                          │
│  ├─ Configure DNS via Cloudflare                                    │
│  ├─ Start warmup                                                    │
│  └─ Forge Stack: RUNNING (no changes)                               │
│                                                                     │
│  Week 3-4: Pilot Campaign                                           │
│  ├─ Run small test campaign (100 leads) via Smartlead               │
│  ├─ Compare deliverability metrics vs Forge                         │
│  ├─ Test all Prefect flows                                          │
│  ├─ Verify webhook reliability                                      │
│  └─ Forge Stack: RUNNING (primary)                                  │
│                                                                     │
│  Week 5-6: Gradual Migration                                        │
│  ├─ Migrate 25% of campaigns to Smartlead                          │
│  ├─ Monitor metrics daily                                           │
│  ├─ If issues: Route back to Forge                                 │
│  └─ Forge Stack: RUNNING (75% traffic)                              │
│                                                                     │
│  Week 7-8: Majority Migration                                       │
│  ├─ Migrate 75% of campaigns to Smartlead                          │
│  ├─ Keep Forge warm (don't disable warmup)                         │
│  ├─ Ready for instant rollback                                      │
│  └─ Forge Stack: STANDBY (25% traffic)                              │
│                                                                     │
│  Week 9+: Full Cutover (if successful)                              │
│  ├─ 100% campaigns on Smartlead                                     │
│  ├─ Disable Forge warmup (save cost)                                │
│  ├─ Keep Forge credentials for 30 days                              │
│  └─ Forge Stack: DORMANT                                            │
│                                                                     │
│  Week 13: Full Decommission                                         │
│  ├─ Cancel Forge subscriptions                                      │
│  ├─ Archive Forge credentials                                       │
│  └─ Document lessons learned                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Export Requirements

Before disabling Forge Stack, export and preserve:

```python
EXPORT_REQUIREMENTS = {
    "salesforge": {
        "campaigns": "All campaign configurations",
        "sequences": "Email templates and sequences",
        "analytics": "Historical open/click/reply rates",
        "leads": "Lead status and engagement history",
    },
    "warmforge": {
        "mailbox_status": "Current heat scores for all mailboxes",
        "reputation_history": "Historical reputation data",
    },
    "infraforge": {
        "domains": "List of all domains with DNS records",
        "mailboxes": "All mailbox credentials (encrypted)",
    },
    "export_format": "JSON + CSV backup",
    "storage_location": "Supabase + encrypted S3 backup",
    "retention_period": "90 days post-migration",
}
```

### Rollback Triggers

```python
ROLLBACK_TRIGGERS = {
    "automatic": [
        "Deliverability drops > 15% vs Forge baseline",
        "Bounce rate exceeds 8% for > 48 hours",
        "API availability < 99% for > 4 hours",
        "Critical bug affecting > 50% of sends",
    ],
    "manual_review": [
        "Deliverability drops 5-15%",
        "Reply rate drops > 20%",
        "Unexpected feature limitations discovered",
        "Support response time > 24 hours for critical issue",
    ],
}
```

### Rollback Procedure

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROLLBACK PROCEDURE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. PAUSE (Immediate - < 5 minutes)                                 │
│     ├─ Pause all Smartlead campaigns                                │
│     ├─ Disable lead sync flow (Prefect)                             │
│     └─ Alert: "Smartlead paused, evaluating rollback"               │
│                                                                     │
│  2. ASSESS (15-30 minutes)                                          │
│     ├─ Review metrics: bounce rate, deliverability, errors          │
│     ├─ Check Smartlead status page                                  │
│     ├─ Query Supabase for affected leads                            │
│     └─ Decision: Resume Smartlead OR proceed with rollback          │
│                                                                     │
│  3. ROLLBACK (If proceeding - 1-2 hours)                            │
│     ├─ Export pending leads from Smartlead                          │
│     ├─ Re-enable Forge warmup (if disabled)                         │
│     ├─ Reconfigure Prefect to use Forge flows                       │
│     ├─ Import pending leads to Salesforge                           │
│     ├─ Resume campaigns via Salesforge                              │
│     └─ Monitor for 24 hours                                         │
│                                                                     │
│  4. POST-MORTEM (Within 48 hours)                                   │
│     ├─ Document root cause                                          │
│     ├─ Assess if issue is fixable                                   │
│     ├─ Update migration plan                                        │
│     └─ Schedule retry (if appropriate)                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Parallel Running Configuration

```python
PARALLEL_CONFIG = {
    "traffic_split": {
        "week_3_4": {"smartlead": 0.10, "forge": 0.90},
        "week_5_6": {"smartlead": 0.25, "forge": 0.75},
        "week_7_8": {"smartlead": 0.75, "forge": 0.25},
        "week_9+": {"smartlead": 1.00, "forge": 0.00},
    },
    "routing_logic": {
        "method": "campaign_based",  # Route entire campaigns, not individual leads
        "selection": "random_weighted",  # Weighted random per traffic split
    },
    "shared_components": {
        "lead_source": "Supabase (single source of truth)",
        "suppression_list": "Supabase (global)",
        "analytics": "Supabase (merged from both platforms)",
    },
    "isolation": {
        "no_cross_platform_leads": True,  # Lead goes to ONE platform only
        "separate_domains": False,  # Can share domains between platforms
    },
}
```

---

## 8. SMARTLEAD INTEGRATION CLIENT

```python
"""
FILE: src/integrations/smartlead.py
PURPOSE: Smartlead API client for email campaigns
PHASE: SMARTLEAD_MIGRATION
"""

import httpx
from typing import Any
from src.config.settings import settings
from src.exceptions import APIError

class SmartleadClient:
    """
    Smartlead API client.
    
    Replaces: SalesforgeClient + WarmForgeClient
    Cost: $75 AUD/mo (vs $111 for Forge Stack)
    """
    
    BASE_URL = "https://server.smartlead.ai/api/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.smartlead_api_key
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated API request."""
        url = f"{self.BASE_URL}{endpoint}"
        params = kwargs.pop("params", {})
        params["api_key"] = self.api_key
        
        response = await self._client.request(method, url, params=params, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # ===== EMAIL ACCOUNTS =====
    
    async def list_email_accounts(self) -> list[dict]:
        """Get all mailboxes."""
        return await self._request("GET", "/email-accounts")
    
    async def create_email_account(
        self,
        email: str,
        password: str,
        imap_host: str,
        smtp_host: str,
        **kwargs
    ) -> dict:
        """Create new mailbox."""
        return await self._request("POST", "/email-accounts", json={
            "from_email": email,
            "email_password": password,
            "smtp_host": smtp_host,
            "smtp_port": kwargs.get("smtp_port", 587),
            "imap_host": imap_host,
            "imap_port": kwargs.get("imap_port", 993),
            **kwargs
        })
    
    async def configure_warmup(
        self,
        email_account_id: int,
        enabled: bool = True,
        total_per_day: int = 35,
        rampup: int = 2,
    ) -> dict:
        """Configure mailbox warmup."""
        return await self._request(
            "POST",
            f"/email-accounts/{email_account_id}/warmup",
            json={
                "warmup_enabled": enabled,
                "total_warmup_per_day": total_per_day,
                "daily_rampup": rampup,
            }
        )
    
    async def get_warmup_status(self, email_account_id: int) -> dict:
        """Get warmup status and heat score."""
        return await self._request("GET", f"/email-accounts/{email_account_id}")
    
    # ===== CAMPAIGNS =====
    
    async def create_campaign(self, name: str, settings: dict = None) -> dict:
        """Create new campaign."""
        return await self._request("POST", "/campaigns", json={
            "name": name,
            **(settings or {})
        })
    
    async def get_campaign(self, campaign_id: int) -> dict:
        """Get campaign details."""
        return await self._request("GET", f"/campaigns/{campaign_id}")
    
    async def list_campaigns(self) -> list[dict]:
        """List all campaigns."""
        return await self._request("GET", "/campaigns")
    
    async def add_leads_to_campaign(
        self,
        campaign_id: int,
        leads: list[dict]
    ) -> dict:
        """Add leads to campaign."""
        return await self._request(
            "POST",
            f"/campaigns/{campaign_id}/leads",
            json={"lead_list": leads}
        )
    
    async def get_campaign_leads(
        self,
        campaign_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> dict:
        """Get leads in a campaign."""
        return await self._request(
            "GET",
            f"/campaigns/{campaign_id}/leads",
            params={"offset": offset, "limit": limit}
        )
    
    async def start_campaign(self, campaign_id: int) -> dict:
        """Start/resume campaign."""
        return await self._request("POST", f"/campaigns/{campaign_id}/start")
    
    async def pause_campaign(self, campaign_id: int) -> dict:
        """Pause campaign."""
        return await self._request("POST", f"/campaigns/{campaign_id}/pause")
    
    # ===== LEADS =====
    
    async def get_lead_by_email(self, email: str) -> dict:
        """Get lead by email address."""
        return await self._request("GET", f"/leads/{email}")
    
    async def update_lead_status(
        self,
        campaign_id: int,
        lead_email: str,
        status: str
    ) -> dict:
        """Update lead status in campaign."""
        return await self._request(
            "POST",
            f"/campaigns/{campaign_id}/leads/{lead_email}/status",
            json={"status": status}
        )
    
    # ===== WEBHOOKS =====
    
    async def configure_webhook(self, url: str, events: list[str]) -> dict:
        """Configure webhook endpoint."""
        return await self._request("POST", "/webhooks", json={
            "url": url,
            "events": events
        })
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()


# Singleton
_client: SmartleadClient = None

def get_smartlead_client() -> SmartleadClient:
    global _client
    if _client is None:
        _client = SmartleadClient()
    return _client
```

---

## 9. IMPLEMENTATION CHECKLIST

### Phase 1: Setup (Week 1)
- [ ] Sign up for Smartlead Pro ($49 USD/mo)
- [ ] Create API key
- [ ] Add `SMARTLEAD_API_KEY` to env
- [ ] Create `src/integrations/smartlead.py`
- [ ] Write integration tests

### Phase 2: DNS Automation (Week 1-2)
- [ ] Create `src/integrations/cloudflare.py` (if not exists)
- [ ] Implement `smartlead_domain_setup_flow.py`
- [ ] Test with 2 new domains
- [ ] Verify DNS propagation check

### Phase 3: Mailbox Management (Week 2)
- [ ] Implement `smartlead_mailbox_provisioning_flow.py`
- [ ] Create mailbox status table in Supabase
- [ ] Configure warmup settings
- [ ] Test graduation logic

### Phase 4: Campaign Engine (Week 3)
- [ ] Implement `smartlead_campaign_flow.py`
- [ ] Create campaign templates
- [ ] Test sequence management
- [ ] Verify send limits

### Phase 5: Lead Sync (Week 3-4)
- [ ] Implement `smartlead_lead_sync_flow.py`
- [ ] Configure webhooks
- [ ] Test deduplication
- [ ] Verify reply detection

### Phase 6: Parallel Run (Week 4-8)
- [ ] Configure traffic split
- [ ] Monitor metrics daily
- [ ] Document issues
- [ ] Gradual migration

### Phase 7: Cutover (Week 9+)
- [ ] Full migration to Smartlead
- [ ] Disable Forge warmup
- [ ] Cancel Forge subscriptions (Week 13)
- [ ] Archive documentation

---

## 10. SUCCESS METRICS

| Metric | Forge Baseline | Smartlead Target | Rollback Trigger |
|--------|----------------|------------------|------------------|
| Inbox Placement | 92% | > 88% | < 80% |
| Bounce Rate | 2% | < 3% | > 8% |
| Reply Rate | 4% | > 3.5% | < 2% |
| API Uptime | 99.9% | > 99.5% | < 99% |
| Warmup Time | 14 days | < 21 days | > 30 days |
| Cost (AUD/mo) | $111 | $75 | N/A |

---

*Architecture designed: 2026-02-05*
*Pending approval: Dave (CEO)*
*Estimated implementation: 15 hours*
*Annual savings: $433.20 AUD*
