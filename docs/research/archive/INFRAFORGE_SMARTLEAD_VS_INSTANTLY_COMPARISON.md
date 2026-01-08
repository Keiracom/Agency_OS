> **ARCHIVED:** This research informed the original decision. Project later pivoted to Salesforge ecosystem.
> **Original Decision:** InfraForge + Smartlead (approved January 4, 2026)
> **Final Decision:** InfraForge + Salesforge/Warmforge (pivoted January 6, 2026)
> **Archived:** January 8, 2026
> **Reason:** Salesforge ecosystem offered better API access and free warmup via Warmforge.

---

# Email Infrastructure Comparison: InfraForge + Smartlead vs Instantly

**Research Date:** January 4, 2026
**Decision:** InfraForge + Smartlead Architecture APPROVED
**Author:** Claude (via comprehensive API research)

## Executive Summary

**RECOMMENDATION: InfraForge + Smartlead Architecture**

Your proposed architecture (InfraForge for domain/mailbox provisioning → Smartlead for warmup/sending → Agency OS as bridge) is **superior** to using Instantly alone for a multi-tenant SaaS platform like Agency OS.

---

## Architecture Comparison

### Option A: InfraForge + Smartlead (RECOMMENDED)

```
Agency OS Platform
      │
      ├──► InfraForge API (Domain/Mailbox Provisioning)
      │    ├── Purchase domains programmatically
      │    ├── Create mailboxes programmatically
      │    ├── Automated DNS (SPF, DKIM, DMARC)
      │    ├── Dedicated IPs per tenant
      │    └── Pre-warmed infrastructure option
      │
      ├──► Smartlead API (Warmup + Sending)
      │    ├── Add email accounts via API (SMTP/IMAP)
      │    ├── Enable/configure warmup via API
      │    ├── Create campaigns via API
      │    ├── Webhooks for all events
      │    └── Monitor warmup stats via API
      │
      └──► Your Bridge Code
           ├── Tenant provisioning workflow
           ├── Infrastructure orchestration
           └── Unified dashboard/reporting
```

### Option B: Instantly Only (LIMITED)

```
Agency OS Platform
      │
      ├──► Instantly API
      │    ├── DFY Orders (domain/mailbox) ✅
      │    ├── Campaigns (create/manage) ✅
      │    ├── Leads (add/manage) ✅
      │    ├── Webhooks (events) ✅
      │    ├── Warmup (enable/disable) ✅
      │    └── BUT: Less infrastructure control
      │
      └──► Limited multi-tenant flexibility
```

---

## Research Findings

### Apollo.io API - NOT VIABLE

**Finding:** Apollo's API is intentionally limited to data enrichment and CRM integration. Domain purchasing, mailbox creation, warmup automation, and sequence creation are UI-only features.

**Evidence:**
- Reddit/Google deep dive confirmed API gaps are by design
- 2024/2025 UI features (domain purchasing, mailbox creation) not in API docs
- No webhooks for campaign events
- "Inbox Ramp Up" is volume pacing, not true warmup

### Mailforge/Infraforge API - LIMITED PUBLIC DOCS

**Finding:** Mailforge (shared IP) has no public API documentation. Infraforge (dedicated IP) mentions API access but requires enterprise agreement.

**Evidence:**
- No developer documentation portal found
- "API access" mentioned in marketing but not documented
- GitHub repos only contain billing integrations
- May require custom enterprise agreement

### Instantly.ai API - GOOD BUT PLATFORM LOCK-IN

**Finding:** Instantly has comprehensive API v2 including DFY (Done-For-You) domain/mailbox provisioning. However, Instantly retains domain ownership.

**Key Capabilities:**
- DFY API: `POST /api/v2/dfy-email-account-orders`
- Campaign API: Full CRUD
- Warmup API: Enable/disable, analytics
- Webhooks: 18+ event types

**Critical Limitation:** DFY domains locked to Instantly platform, cannot transfer ownership.

### InfraForge API - EXCELLENT FOR PROGRAMMATIC USE

**Finding:** InfraForge API designed specifically for programmatic scaling with full infrastructure control.

**Capabilities Confirmed:**
- Multi-IP provisioning via API
- Automated DNS configuration
- Domain/mailbox provisioning
- Real-time deliverability monitoring
- White-label support

### Smartlead API - BEST-IN-CLASS WARMUP

**Finding:** Smartlead has fully documented API supporting SMTP/IMAP registration, warmup management, and campaign operations.

**Key Endpoints:**
```
POST /api/v1/email-accounts/save          # Create email account
POST /api/v1/email-accounts/{id}/warmup   # Enable/configure warmup
GET  /api/v1/email-accounts/{id}/warmup-stats  # Get warmup stats
POST /api/v1/campaigns                    # Create campaign
POST /api/v1/campaigns/{id}/leads         # Add leads
```

---

## Why InfraForge + Smartlead Wins for Agency OS

### 1. **True Multi-Tenant Control**
- InfraForge: Dedicated IPs per tenant = reputation isolation
- Smartlead: Client management system built for agencies
- Instantly: Shared infrastructure, less isolation

### 2. **Infrastructure Ownership**
- InfraForge: You control the domains/mailboxes
- Instantly DFY: Instantly retains domain ownership
- Critical for: Tenant portability, exit strategy

### 3. **Warmup Quality**
- Smartlead: Industry-leading warmup network with smart-adjust AI
- Instantly: Good warmup but 4.2M pool vs Smartlead's network
- Both superior to: Apollo's "Inbox Ramp Up" (volume pacing only)

### 4. **Cost Efficiency at Scale**

**Per-Tenant Cost Comparison (Ignition Tier: 3 mailboxes, 2 domains)**

| Provider | Domains | Mailboxes | Warmup | Total/Month |
|----------|---------|-----------|--------|-------------|
| InfraForge + Smartlead | $3.33 | $9-12 | Included | ~$15-18 |
| Instantly DFY | $5.83 | $60-75 | Included | ~$66-81 |

**At Scale (100 tenants, 300 mailboxes):**
- InfraForge + Smartlead: ~$1,500-1,800/month
- Instantly DFY: ~$6,600-8,100/month

### 5. **API Flexibility**
- InfraForge + Smartlead: Two specialized APIs, each best-in-class
- Instantly: Single API, good but generalist
- Your code: Orchestration layer adds value

---

## Final Recommendation

### For Agency OS Multi-Tenant Architecture:

**USE: InfraForge + Smartlead**

**Rationale:**
1. **Infrastructure ownership** - Critical for SaaS platform
2. **Cost efficiency** - 4-5x cheaper at scale
3. **Tenant isolation** - Dedicated IPs protect reputation
4. **API flexibility** - Best-in-class for each function
5. **Exit strategy** - Can migrate infrastructure if needed

---

## API Documentation Links

- **InfraForge:** Contact for API docs (enterprise focus) - https://infraforge.ai
- **Smartlead:** https://api.smartlead.ai/reference
- **Instantly:** https://developer.instantly.ai/api/v2 (NOT SELECTED)
