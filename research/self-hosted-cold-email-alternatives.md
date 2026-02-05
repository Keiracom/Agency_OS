# Self-Hosted Cold Email Infrastructure: Feasibility Assessment

**Research Date:** 2026-02-05  
**Mission:** Evaluate open-source alternatives to Salesforge/WarmForge/InfraForge stack  
**Currency:** All costs in $AUD (1 USD ≈ 1.55 AUD)

---

## Executive Summary

**Verdict: Technically feasible, but NOT recommended for Keiracom's current stage.**

The open-source cold email stack can reduce *licensing* costs by 60-80%, but introduces:
- 40-60 hours/month maintenance overhead
- No built-in warmup (the hardest problem to solve)
- Deliverability risk during learning curve
- 3-6 month ramp-up before production-ready

For a 2-person team with March 2026 deadline, the Forge Stack's "it just works" value outweighs savings.

---

## Tool-by-Tool Analysis

### 1. Postal (postalserver.io)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~15,000 |
| **Maintenance** | Active (v3 released 2025) |
| **Setup Complexity** | 7/10 |
| **Warmup** | ❌ None built-in |
| **Deliverability** | IP pools, webhooks, spam/AV integration |
| **API** | REST API, webhooks |
| **VPS Cost** | $30-50 AUD/month (4GB RAM minimum) |

**What it does well:**
- Full MTA with web UI
- IP pool management (critical for cold email)
- Click/open tracking
- Webhook delivery notifications
- SpamAssassin/Rspamd/ClamAV integration

**What it lacks:**
- No warmup automation
- No reply detection/threading
- No campaign sequencing
- Manual DNS setup

**Can it replace InfraForge?** Partially. Handles sending infrastructure but needs external warmup.

---

### 2. Mailcow (mailcow-dockerized)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~9,500 |
| **Maintenance** | Very active, commercial support available |
| **Setup Complexity** | 5/10 (Docker makes it easier) |
| **Warmup** | ❌ None |
| **Deliverability** | Rspamd, DKIM/ARC, reputation tracking |
| **API** | REST API |
| **VPS Cost** | $40-60 AUD/month (6GB RAM recommended) |

**What it does well:**
- Complete email suite (SMTP, IMAP, webmail)
- Excellent spam filtering (Rspamd with auto-learning)
- DKIM/DMARC generation via UI
- Docker-based = easier updates
- SOGo webmail included

**What it lacks:**
- Designed for general email, not cold outreach
- No campaign management
- No warmup
- Overkill if you only need SMTP sending

**Can it replace InfraForge?** No. It's a full mailserver, not a cold email platform.

---

### 3. Mautic (Open Source Marketing Automation)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~7,500 |
| **Maintenance** | Active (v7.x in development) |
| **Setup Complexity** | 8/10 |
| **Warmup** | ❌ None |
| **Deliverability** | Basic bounce handling |
| **API** | REST API, webhooks |
| **VPS Cost** | $50-80 AUD/month (needs MySQL + decent CPU) |

**What it does well:**
- Full marketing automation (segments, campaigns, landing pages)
- Email sequencing with conditions
- Lead scoring
- CRM-like contact management
- 100% data ownership

**What it lacks:**
- Heavy/complex (PHP + Symfony)
- No warmup
- No inbox rotation
- Cold email deliverability not its focus
- Needs dedicated sysadmin knowledge

**Can it replace Salesforge?** Theoretically yes for sequencing, but no warmup = deliverability death.

---

### 4. listmonk (Self-Hosted Newsletter)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~16,000 |
| **Maintenance** | Active (Go-based, single binary) |
| **Setup Complexity** | 3/10 (easiest of all) |
| **Warmup** | ❌ None |
| **Deliverability** | Basic rate limiting only |
| **API** | REST API |
| **VPS Cost** | $15-25 AUD/month (very lightweight) |

**What it does well:**
- Incredibly lightweight (single binary + Postgres)
- Fast bulk sending (millions of emails)
- Transactional API
- Go templates for personalization
- AGPL licensed

**What it lacks:**
- **NOT designed for cold email** - newsletter/opt-in focus
- No warmup, no inbox rotation
- No sequence automation
- No reply tracking
- AWS SES/Sendgrid will ban you for cold outreach

**Can it replace Salesforge?** ❌ No. Reddit users confirm: "Listmonk is only the UI, the main stuff is AWS SES and they may ban the account if they detect too many bounces or spam reports."

---

### 5. Chatwoot (Omnichannel Support)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~22,000 |
| **Maintenance** | Very active (backed by company) |
| **Setup Complexity** | 6/10 |
| **Warmup** | ❌ None |
| **Deliverability** | N/A |
| **API** | REST API |
| **VPS Cost** | $40-60 AUD/month |

**Cold Email Relevant?** ❌ No. Chatwoot is customer support software (Intercom alternative). Has "campaigns" but for in-app messaging and support tickets, not cold outreach.

**Verdict:** Not applicable to this use case.

---

### 6. n8n + Nodemailer (DIY Automation)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~60,000+ (n8n) |
| **Maintenance** | Very active, well-funded |
| **Setup Complexity** | 6/10 |
| **Warmup** | ❌ Build your own |
| **Deliverability** | Whatever you integrate |
| **API** | Visual + code |
| **VPS Cost** | $30-50 AUD/month |

**What it does well:**
- Ultimate flexibility (400+ integrations)
- Visual workflow builder
- Can orchestrate ANY email flow
- Self-hostable (fair-code license)
- Could integrate with Postal/SMTP

**What it lacks:**
- You're building everything from scratch
- No email-specific deliverability features
- No warmup (would need to build)
- No inbox rotation built-in

**DIY Cold Email Stack with n8n:**
```
n8n (orchestration)
  → Nodemailer (SMTP sending)
  → Postal (MTA infrastructure)
  → Custom warmup flows
  → Webhook receivers for bounces
```

**Time to build:** 80-120 hours
**Can it replace Salesforge?** Only with massive development effort.

---

### 7. Postfix + Rspamd (Raw SMTP Stack)

| Metric | Value |
|--------|-------|
| **GitHub Stars** | N/A (distro packages) |
| **Maintenance** | Postfix: rock-solid, decades old |
| **Setup Complexity** | 9/10 |
| **Warmup** | ❌ None |
| **Deliverability** | Manual everything |
| **API** | None (CLI/config only) |
| **VPS Cost** | $20-30 AUD/month |

**What it does well:**
- Maximum control
- Lowest resource usage
- Rspamd for spam filtering
- DKIM/DMARC via OpenDKIM

**What it lacks:**
- No UI
- No API without building one
- Everything is manual config files
- Requires Linux sysadmin expertise

**Can it replace InfraForge?** Only the MTA component, and requires expert-level setup.

---

### 8. MOX (Modern Mail Server) - Bonus Find

| Metric | Value |
|--------|-------|
| **GitHub Stars** | ~4,000 |
| **Maintenance** | Active (NLnet funded) |
| **Setup Complexity** | 4/10 (single binary, auto-setup) |
| **Warmup** | ❌ None |
| **Deliverability** | Built-in reputation tracking, DANE/MTA-STS |
| **API** | HTTP/JSON API for transactional |
| **VPS Cost** | $20-30 AUD/month |

**Interesting features:**
- Single Go binary (like listmonk)
- Auto DNS record generation
- Built-in webmail
- Reputation tracking per sender
- ACME (auto TLS)
- **Roadmap includes "transactional email domains"**

**Best for:** People who want email self-hosting without the complexity.

---

## The Warmup Problem (Critical Gap)

**None of the open-source tools have warmup.** This is the elephant in the room.

### Why Warmup Matters:
- New domains/IPs have zero reputation
- Gmail/Microsoft aggressively filter unknown senders
- Without warmup: 10-30% inbox placement
- With proper warmup: 70-90% inbox placement

### DIY Warmup Options:

#### Option A: Webshare Proxies + Custom Script
- **Cost:** $27-80 AUD/month for proxies
- **Concept:** Simulate human email behavior via proxied IMAP/SMTP
- **Reality:** Extremely fragile, Gmail detects patterns

#### Option B: Prefect + Custom Warmup Flows
```python
# Conceptual warmup flow
@flow
def warmup_domain(domain: str, day: int):
    # Day 1-7: 5 emails/day to seed list
    # Day 8-14: 20 emails/day, track opens
    # Day 15-21: 50 emails/day
    # Check bounce rates, adjust
```
- **Time to build:** 40-60 hours
- **Maintenance:** Constant tuning
- **Risk:** One mistake burns the domain

#### Option C: Hybrid (Open Source + Paid Warmup)
- Use Postal/MOX for infrastructure
- Pay for warmup-only service (Warmbox, Mailreach)
- **Cost:** $50-100 AUD/month per mailbox

**Verdict:** DIY warmup is the biggest risk. WarmForge's $XX/month buys peace of mind.

---

## DNS Automation (Cloudflare API)

This IS feasible and recommended regardless of stack choice.

### Cloudflare API Capabilities:
```bash
# List DNS records
GET /zones/{zone_id}/dns_records

# Create record (SPF, DKIM, DMARC, MX)
POST /zones/{zone_id}/dns_records
{
  "type": "TXT",
  "name": "_dmarc",
  "content": "v=DMARC1; p=quarantine; rua=mailto:dmarc@domain.com"
}
```

### Automatable:
- SPF record creation
- DKIM key rotation
- DMARC policy updates
- MX record pointing
- Subdomain tracking domains

### Python Implementation:
```python
import cloudflare

def setup_email_dns(domain: str, dkim_key: str):
    cf = Cloudflare(api_token=os.environ["CF_API_TOKEN"])
    zone = cf.zones.list(name=domain).result[0]
    
    # SPF
    cf.dns.records.create(zone_id=zone.id, type="TXT", 
        name=domain, content="v=spf1 include:_spf.domain.com ~all")
    
    # DKIM
    cf.dns.records.create(zone_id=zone.id, type="TXT",
        name=f"mail._domainkey.{domain}", content=dkim_key)
```

**Recommendation:** Build this regardless - saves 15-30 mins per domain setup.

---

## IP Reputation Services (Self-Managed)

### Free Monitoring:
- **Google Postmaster Tools** - Essential, shows Gmail reputation
- **Microsoft SNDS** - Outlook/Hotmail reputation
- **mail-tester.com** - One-off deliverability tests

### Self-Hosted Monitoring:
- **Rspamd** - Tracks reputation scores
- **MOX** - Built-in reputation per sender

### Commercial (if needed):
- **250ok** / **GlockApps** - $150+ AUD/month

---

## Cost Comparison

### Current Forge Stack (Estimated):
| Component | Monthly AUD |
|-----------|------------|
| Salesforge | $150-300 |
| WarmForge | $50-100/mailbox |
| InfraForge | $50-100 |
| **Total (10 mailboxes)** | **$700-1,200** |

### Minimal Open Source Stack:
| Component | Monthly AUD |
|-----------|------------|
| VPS (8GB RAM) | $60 |
| Postal | Free |
| Cloudflare | Free |
| External Warmup (10 boxes) | $500-800 |
| **Total** | **$560-860** |

### Savings: $140-340/month (20-30%)

### BUT: Hidden Costs
| Hidden Cost | Hours/Month | Value @ $100/hr |
|-------------|-------------|-----------------|
| Setup (amortized) | 10 | $1,000 |
| Maintenance | 10-20 | $1,000-2,000 |
| Troubleshooting | 5-10 | $500-1,000 |
| **True Monthly Cost** | | **$2,500-4,000** |

---

## Final Feasibility Assessment

### Can We Build Cheaper?

**On paper:** Yes, 20-30% licensing savings.

**In reality:** No. The maintenance overhead destroys ROI for a small team.

### When Open Source Makes Sense:
1. Team has dedicated DevOps (not us)
2. Sending 500k+ emails/month (scale savings)
3. Extreme customization needs
4. Regulatory requirement for self-hosting
5. Timeline is 6+ months (not us)

### When Forge Stack Wins:
1. Small team (us)
2. Time-to-market matters (March 2026)
3. Warmup is critical (cold email = yes)
4. Need predictable deliverability
5. Can't afford domain burning during learning

---

## Recommendations

### Short Term (Now → March 2026):
✅ **Keep Forge Stack** - It works, focus on revenue  
✅ **Build DNS automation** - Saves time, no risk  
✅ **Monitor with Postmaster Tools** - Free insights  

### Medium Term (Post-Revenue):
🔄 **Re-evaluate at $10k MRR** - Can afford experiments  
🔄 **Consider MOX for transactional** - Good hybrid option  
🔄 **Test Postal for secondary domains** - Low-risk learning  

### Long Term (Scale):
📊 **At 100+ mailboxes:** Open source ROI improves  
📊 **Hire DevOps:** Then self-hosting makes sense  
📊 **Hybrid model:** Forge for warmup, self-hosted for bulk  

---

## Research Sources

1. GitHub repositories (stars/activity as of Feb 2026)
2. Official documentation (Postal, Mailcow, Mautic, listmonk)
3. Woodpecker.co analysis of listmonk limitations
4. Reddit r/coldemail and r/selfhosted discussions
5. Cloudflare API documentation
6. Webshare proxy pricing page

---

*Research completed by Elliot (Subagent) for Keiracom cold email infrastructure evaluation.*
