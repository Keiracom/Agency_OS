# Agency OS Admin Dashboard Manual

## Overview

The Admin Dashboard is your "Bloomberg Terminal for Client Acquisition" - a comprehensive control center for monitoring and managing all aspects of the Agency OS platform. It's designed for platform administrators to have complete visibility into revenue, operations, costs, and system health.

**Access:** https://agency-os-liart.vercel.app/admin  
**Requirement:** User must have `is_platform_admin = true` in the database

---

## Navigation Structure

| Section | Path | Purpose |
|---------|------|---------|
| **Command Center** | `/admin` | Main dashboard overview |
| **Revenue** | `/admin/revenue` | Financial metrics & transactions |
| **Costs** | `/admin/costs` | Operational cost tracking |
| **Clients** | `/admin/clients` | Client management |
| **Campaigns** | `/admin/campaigns` | All campaigns across clients |
| **Leads** | `/admin/leads` | Lead management & enrichment |
| **Activity** | `/admin/activity` | Real-time activity feed |
| **Replies** | `/admin/replies` | Response management |
| **Compliance** | `/admin/compliance` | Bounces & suppression |
| **System** | `/admin/system` | Health, errors, queues |
| **Settings** | `/admin/settings` | Platform configuration |

---

## 1. Command Center (`/admin`)

The main dashboard provides at-a-glance KPIs and system status.

### Key Metrics Displayed
- **MRR (Monthly Recurring Revenue)** - Total revenue from all active subscriptions
- **Active Clients** - Number of paying clients
- **Leads Today** - Total leads processed today
- **AI Spend** - Current AI API usage vs budget

### Alerts Banner
Shows critical and warning alerts requiring attention:
- 🔴 **Critical** - Immediate action required (failures, outages)
- 🟡 **Warning** - Attention needed soon (rate limits, approaching thresholds)
- 🔵 **Info** - Informational notices

### System Status
Real-time status of all integrated services:
- Supabase (Database)
- Redis (Cache)
- Apollo (Enrichment)
- Resend (Email)
- Twilio (SMS)
- HeyReach (LinkedIn)
- Vapi (Voice)

### Live Activity Feed
Real-time stream of platform events across all clients.

---

## 2. Revenue Dashboard (`/admin/revenue`)

Track all financial metrics and subscription health.

### Metrics
| Metric | Description |
|--------|-------------|
| **MRR** | Monthly Recurring Revenue |
| **ARR** | Annual Recurring Revenue (MRR × 12) |
| **New MRR** | Revenue from new subscriptions this month |
| **Churned MRR** | Revenue lost to cancellations |
| **Net Growth** | New MRR - Churned MRR |
| **Churn Rate** | Percentage of revenue churned |
| **ARPU** | Average Revenue Per User |

### Tier Breakdown
Shows client distribution across pricing tiers:
- **Ignition** ($2,500/month) - Starter tier
- **Velocity** ($4,995/month) - Growth tier  
- **Dominance** ($7,500/month) - Enterprise tier

### Recent Transactions
Log of all subscription events (new, renewal, upgrade, downgrade, churn).

---

## 3. Costs Dashboard (`/admin/costs`)

Monitor operational expenses and maintain 75% gross margins.

### Sub-sections

#### `/admin/costs/ai`
AI API spending across providers:
- Anthropic (Claude) - Content generation
- Cost per lead enrichment
- Cost per message generated
- Budget utilization

#### `/admin/costs/channels`
Per-channel delivery costs:
- Email (Resend) - Cost per send
- SMS (Twilio) - Cost per message
- LinkedIn (HeyReach) - Cost per action
- Voice (Vapi) - Cost per minute
- Direct Mail (ClickSend) - Cost per piece

### Margin Calculator
Real-time gross margin calculation:
```
Gross Margin = (Revenue - Total Costs) / Revenue × 100
Target: 75%+
```

---

## 4. Clients Dashboard (`/admin/clients`)

Manage all client accounts on the platform.

### Client List View
- Client name & tier
- Subscription status (active, trialing, past_due, canceled)
- Credits remaining
- Member count
- Monthly spend

### Individual Client View (`/admin/clients/[id]`)
- Full client profile
- Team members & roles
- Active campaigns
- Usage metrics
- Billing history
- Credit adjustments

---

## 5. Campaigns Dashboard (`/admin/campaigns`)

Cross-client campaign visibility.

### Features
- All campaigns across all clients
- Filter by status (draft, active, paused, completed)
- Filter by channel (email, SMS, LinkedIn, voice, mail)
- Performance metrics (sent, delivered, replies, conversions)

---

## 6. Leads Dashboard (`/admin/leads`)

Platform-wide lead management.

### Views
- All leads across clients
- Enrichment status (pending, enriched, failed)
- ALS distribution
- Lead quality tiers (Hot, Warm, Cool, Cold, Dead)

### Actions
- Manual enrichment trigger
- Suppression management
- Quality scoring review

---

## 7. Activity Feed (`/admin/activity`)

Real-time platform activity stream.

### Event Types
- Lead created/updated
- Email sent/delivered/opened/replied
- SMS sent/delivered/replied
- LinkedIn connection/message
- Voice call initiated/completed
- Enrichment completed
- Campaign status changes

### Filters
- By client
- By event type
- By channel
- By time range

---

## 8. Replies Dashboard (`/admin/replies`)

Centralized response management.

### Features
- All inbound replies across channels
- Intent classification (interested, not_interested, meeting_request, etc.)
- Sentiment analysis
- Response suggestions
- Approval queue (for co-pilot mode)

---

## 9. Compliance Dashboard (`/admin/compliance`)

Maintain deliverability and legal compliance.

### Sub-sections

#### `/admin/compliance/bounces`
- Hard bounces (invalid emails)
- Soft bounces (temporary failures)
- Bounce rate by client
- Auto-suppression status

#### `/admin/compliance/suppression`
- Global suppression list
- Client-specific suppression
- Do-not-contact management
- Unsubscribe handling

---

## 10. System Dashboard (`/admin/system`)

Technical health and operations.

### Sub-sections

#### `/admin/system` (Overview)
- Service status grid
- Uptime metrics
- Response times
- Error rates

#### `/admin/system/errors`
- Error log viewer
- Error categorization
- Stack traces
- Affected clients/campaigns

#### `/admin/system/queues`
- Job queue status
- Pending jobs count
- Processing rates
- Failed job retry

#### `/admin/system/rate-limits`
- API rate limit status per service
- Usage percentages
- Rate limit warnings
- Historical usage

---

## 11. Settings (`/admin/settings`)

Platform configuration.

### Sub-sections

#### `/admin/settings` (General)
- Platform name/branding
- Default settings
- Feature flags
- Notification preferences

#### `/admin/settings/users`
- Platform admin management
- Add/remove admins
- Role assignments

---

## Key Concepts

### ALS (Lead Score)
The platform's proprietary lead qualification algorithm (0-100):
- **90-100**: Ideal fit, high intent
- **70-89**: Strong match
- **50-69**: Moderate match
- **30-49**: Weak match
- **0-29**: Poor fit

### Permission Modes
- **Autopilot**: Fully automated, no human approval
- **Co-pilot**: Human reviews & approves before sending
- **Manual**: Human controls everything

### Credit System
- Credits are consumed by enrichment, AI generation, and channel sends
- Each tier includes monthly credit allocation
- Credits reset monthly on subscription date
- Overage tracked for billing

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `G + H` | Go to Command Center |
| `G + R` | Go to Revenue |
| `G + C` | Go to Clients |
| `G + S` | Go to System |
| `/` | Focus search |
| `?` | Show shortcuts help |

---

## Current Status

**Note:** The admin dashboard currently displays **mock data** for demonstration purposes. The next development phase will connect all sections to the live Railway backend API.

### What's Working
- ✅ Navigation structure
- ✅ UI components
- ✅ Role-based access (platform admin check)
- ✅ Layout and styling

### What Needs Connection
- ⏳ Revenue metrics → Stripe API
- ⏳ Client data → Supabase
- ⏳ Campaign data → Backend API
- ⏳ Lead data → Backend API
- ⏳ Activity feed → Real-time subscriptions
- ⏳ System status → Health checks
- ⏳ Cost tracking → Usage metering

---

## Support

For issues or questions about the Admin Dashboard:
1. Check System → Errors for any logged issues
2. Review this manual
3. Contact platform support

---

*Last Updated: December 2025*
*Version: 3.0.0*
