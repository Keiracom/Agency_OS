# AGENCY OS — FIXED COSTS BREAKDOWN
## Monthly Recurring Infrastructure Costs

**Last Updated:** 2026-02-05
**Currency:** All costs in $AUD (USD × 1.55)
**Scope:** Pre-revenue operational costs

---

## EXECUTIVE SUMMARY

| Category | Current (AUD/mo) | After FCO-001 (AUD/mo) |
|----------|------------------|------------------------|
| Infrastructure | $193 | $168 |
| SaaS & APIs | $524 | $444 |
| Communication | $270 | $270 |
| AI/LLM | $155 | $155 |
| **TOTAL** | **$1,142** | **$1,037** |
| **Savings** | — | **$105/mo** |

---

## 1. INFRASTRUCTURE

### Compute & Hosting

| Service | Plan | USD/mo | AUD/mo | Purpose |
|---------|------|--------|--------|---------|
| **Railway** | Pro | ~$50 | **$78** | Backend API + Prefect |
| **Vercel** | Pro | $20 | **$31** | Frontend hosting |
| **Supabase** | Pro | $25 | **$39** | Postgres DB + Auth |
| **Upstash Redis** | Pay-as-you-go | ~$10 | **$16** | Caching + queues |
| **AWS Spot** (new) | Spot instances | ~$3 | **$5** | Bulk processing |
| **Subtotal** | | | **$169** | |

### After FCO-001 Optimization
- Railway: $78 → $50 (bulk flows moved to Spot)
- AWS Spot: +$5 (new)
- **Net savings: $23/mo**

---

## 2. SAAS & APIS

### Data & Enrichment

| Service | Plan | USD/mo | AUD/mo | Purpose |
|---------|------|--------|--------|---------|
| **Hunter.io** | Starter | $49 | **$76** | Email verification |
| **Proxycurl** | Growth | $99 | **$153** | LinkedIn data |
| **DataForSEO** | Pay-as-you-go | ~$50 | **$78** | SEO metrics |
| **Apollo.io** | Basic | $49 | **$76** | Lead enrichment (legacy) |
| **Webshare** | Proxy pool | ~$30 | **$47** | 215K residential proxies |
| **Subtotal** | | | **$430** | |

### After FCO-001 Optimization
- Proxy costs: $47 → $19 (Proxy Waterfall ~60% reduction)
- **Net savings: $28/mo**

### Future Considerations
- Apollo.io: May deprecate as Siege Waterfall matures (-$76/mo)
- Kaspr: May add for Identity Gold (+$76/mo Starter)

---

## 3. COMMUNICATION & OUTREACH

### Email Infrastructure

| Service | Plan/Seats | USD/mo | AUD/mo | Purpose |
|---------|------------|--------|--------|---------|
| **Google Workspace** | 22 seats @ $6 | $132 | **$205** | Email (admin + burners) |
| **Salesforge** | Pro | $48 | **$74** | Cold email sequencing |
| **WarmForge** | Included | $0 | **$0** | Email warmup |
| **Resend** | Free tier | $0 | **$0** | Transactional email |
| **Subtotal** | | | **$279** | |

### FCO-001 Email Decision (2026-02-05)
**Titan Migration REJECTED.** Forge Stack validated as optimal.
- Current: InfraForge/Mailforge 20 mailboxes @ $4.65 = $93/mo + domains $18/mo = **$111/mo**
- Forge Stack provides: Automated DNS, integrated WarmForge warmup, native Salesforge integration
- Research: 8 agents, 15 competitors analyzed — Forge is CHEAPEST at agency scale
- Smartlead/Instantly are MORE expensive ($149-612 AUD) with required add-ons

### SMS & Voice

| Service | Plan | USD/mo | AUD/mo | Purpose |
|---------|------|--------|--------|---------|
| **ClickSend** | Pay-as-you-go | ~$20 | **$31** | SMS outbound |
| **Vapi** | Pay-as-you-go | ~$30 | **$47** | Voice AI orchestration |
| **Telnyx** | Pay-as-you-go | ~$15 | **$23** | AU mobile telephony |
| **Subtotal** | | | **$101** | |

*Note: SMS/Voice costs scale with usage. Estimates based on Ignition tier (1,250 leads/mo).*

### LinkedIn

| Service | Plan | USD/mo | AUD/mo | Purpose |
|---------|------|--------|--------|---------|
| **Unipile** | Starter | ~$50 | **$78** | LinkedIn automation |
| **Subtotal** | | | **$78** | |

---

## 4. AI & LLM

| Service | Plan | USD/mo | AUD/mo | Purpose |
|---------|------|--------|--------|---------|
| **Anthropic** | Pay-as-you-go | ~$50 | **$78** | Claude (primary LLM) |
| **Groq** | Pay-as-you-go | ~$20 | **$31** | Voice AI (fast inference) |
| **OpenAI** | Pay-as-you-go | ~$15 | **$23** | Embeddings |
| **Cartesia** | Pay-as-you-go | ~$15 | **$23** | TTS for Voice AI |
| **Subtotal** | | | **$155** | |

*Note: AI costs are highly variable based on usage.*

---

## 5. DEVELOPMENT & TOOLS

| Service | Plan | USD/mo | AUD/mo | Purpose |
|---------|------|--------|--------|---------|
| **GitHub** | Free | $0 | **$0** | Code hosting |
| **Clawdbot** | Self-hosted | $0 | **$0** | AI assistant |
| **Cursor/IDE** | Free tier | $0 | **$0** | Development |
| **Subtotal** | | | **$0** | |

---

## 6. VARIABLE/USAGE COSTS

These scale with lead volume:

| Cost Type | Rate (AUD) | At Ignition (1,250 leads) |
|-----------|------------|---------------------------|
| Siege Waterfall (weighted) | $0.105/lead | **$131** |
| SMS sends | $0.08/SMS | ~$50 (est.) |
| Voice AI calls | $0.50/call | ~$100 (est.) |
| Email sends | Included | $0 |
| **Variable Total** | | **~$281/mo** |

---

## FULL COST BREAKDOWN (CURRENT)

| Category | Fixed (AUD/mo) | Variable (AUD/mo) | Total |
|----------|----------------|-------------------|-------|
| Infrastructure | $169 | — | $169 |
| SaaS & APIs | $430 | $131 | $561 |
| Email | $279 | — | $279 |
| SMS/Voice | $101 | $150 | $251 |
| LinkedIn | $78 | — | $78 |
| AI/LLM | $155 | — | $155 |
| **TOTAL** | **$1,212** | **$281** | **$1,493** |

---

## POST-OPTIMIZATION PROJECTION (FCO-001)

| Optimization | Savings (AUD/mo) | Status |
|--------------|------------------|--------|
| Railway → Spot migration | $23 | 📋 Planned |
| Proxy Waterfall | $11 | ✅ Implemented |
| ~~Titan Email migration~~ | ~~$80~~ | ❌ REJECTED (Forge validated) |
| **Total Savings** | **$34** | |

### New Monthly Total: ~$1,362 AUD/mo

---

## BREAK-EVEN ANALYSIS

| Pricing Tier | MRR (AUD) | Fixed Costs | Variable Costs | Profit |
|--------------|-----------|-------------|----------------|--------|
| **Ignition** (1 client) | $2,500 | $1,081 | $281 | **$1,138** |
| **Growth** (1 client) | $5,000 | $1,081 | $560 | **$3,359** |
| **Domination** (1 client) | $7,500 | $1,081 | $750 | **$5,669** |

### First Client = Profitable
With 1 Ignition client ($2,500/mo), we cover all fixed costs with ~$1,100 margin.

---

## COST REDUCTION ROADMAP

### Immediate (FCO-001) — $34/mo savings
- [x] Proxy Waterfall implemented ($11/mo)
- [ ] Prefect Spot migration ($23/mo)
- [x] ~~Titan Email migration~~ — REJECTED, Forge Stack validated as optimal

### Q2 2026 — Potential $150/mo additional
- [ ] Deprecate Apollo.io (Siege Waterfall replaces)
- [ ] Negotiate annual plans (10-20% discounts)
- [ ] Review Vercel usage (may downgrade)

### At Scale (10+ clients)
- Volume discounts on Hunter.io, Proxycurl
- Dedicated infrastructure vs pay-as-you-go
- Custom enterprise deals

---

## SERVICES TO MONITOR

| Service | Risk | Action |
|---------|------|--------|
| Apollo.io | Redundant with Siege Waterfall | Evaluate deprecation Q2 |
| Webshare | Proxy Waterfall reduces usage | Monitor actual savings |
| Vapi | Middleman markup on Telnyx | Evaluate direct integration |

---

## NOTES

1. **All costs estimated** — Actual Railway/Supabase bills may vary
2. **USD → AUD at 1.55** — Update if exchange rate shifts
3. **Variable costs scale linearly** with lead volume
4. **First client covers fixed costs** — Unit economics are strong

---

*Compiled: 2026-02-05 | Elliot (CTO)*
