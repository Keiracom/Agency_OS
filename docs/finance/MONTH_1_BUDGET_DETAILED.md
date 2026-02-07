# Month 1 Budget: Detailed Line Items

**Period:** February 2026
**Currency:** AUD
**Prepared:** 2026-02-06

---

## AI & COMPUTE

### Option A: All API (Current)
| Service | Plan | Unit Cost | Est. Usage | Monthly Cost |
|---------|------|-----------|------------|--------------|
| Anthropic Claude API | Pay-per-use | $3/1M input, $15/1M output | 30M in, 10M out | $240 |
| Anthropic Claude API (Opus) | Pay-per-use | $15/1M input, $75/1M output | 2M in, 0.5M out | $67.50 |
| OpenAI GPT-4o | Pay-per-use | $2.50/1M input, $10/1M output | 5M in, 1M out | $22.50 |
| OpenAI Embeddings | Pay-per-use | $0.13/1M tokens | 10M tokens | $1.30 |
| Groq (Llama/Mixtral) | Pay-per-use | $0.27/1M tokens | 5M tokens | $1.35 |
| **Subtotal Option A** | | | | **$332.65** |

### Option B: Subscription + API (Recommended)
| Service | Plan | Monthly Cost | Notes |
|---------|------|--------------|-------|
| Claude Max (Sub-agents) | Subscription | $100 | Unlimited for BUILDER, WRITER, RESEARCHER, etc. |
| Anthropic API (Elliot only) | Pay-per-use | $50 | Orchestration, critical decisions |
| OpenAI Embeddings | Pay-per-use | $5 | Memory/search only |
| Groq | Pay-per-use | $5 | Voice AI LLM |
| **Subtotal Option B** | | **$160** | **SAVES $172/mo** |

---

## VOICE AI

| Service | Plan | Unit Cost | Est. Usage | Monthly Cost |
|---------|------|-----------|------------|--------------|
| Cartesia TTS | Pay-per-use | $0.10/1000 chars | 500K chars | $50 |
| Vapi | Starter | $0.05/min | 200 mins | $10 + usage |
| Vapi usage | Per-minute | $0.05/min | 200 mins | $10 |
| Telnyx - AU Number | Monthly | $3/number | 2 numbers | $6 |
| Telnyx - Inbound | Per-minute | $0.015/min | 100 mins | $1.50 |
| Telnyx - Outbound AU | Per-minute | $0.025/min | 200 mins | $5 |
| ClickSend SMS | Per-SMS | $0.08/SMS | 300 SMS | $24 |
| **Subtotal Voice** | | | | **$106.50** |

---

## EMAIL INFRASTRUCTURE

| Service | Plan | Monthly Cost | Notes |
|---------|------|--------------|-------|
| Salesforge | Growth | $99 | 5,000 emails/mo, unlimited mailboxes |
| WarmForge | 3 mailboxes | $29 | Auto warmup |
| InfraForge | 2 domains | $22 | DNS setup, DKIM, SPF |
| Backup domain (.com.au) | Annual prorated | $5 | ~$60/year |
| **Subtotal Email** | | **$155** | |

---

## ENRICHMENT

| Service | Plan | Unit Cost | Est. Usage | Monthly Cost |
|---------|------|-----------|------------|--------------|
| ABN Bulk Data | Free | $0 | Unlimited | $0 |
| Hunter.io | Starter | $49/mo | 500 searches | $49 |
| Proxycurl | Pay-per-use | $0.01/profile | 500 profiles | $5 |
| Proxycurl | Credit pack | $50/5000 credits | Bulk buy | $50 |
| Kaspr | Starter | €49/mo (~$85 AUD) | 50 mobile reveals | $85 |
| ZeroBounce | Pay-per-use | $0.008/email | 1000 verifications | $8 |
| **Subtotal Enrichment** | | | | **$197** |

---

## INFRASTRUCTURE

| Service | Plan | Monthly Cost | Notes |
|---------|------|--------------|-------|
| Railway | Pro | $20 base + usage | Backend + Prefect |
| Railway usage | Compute | ~$30 | Estimated |
| Vercel | Pro | $20 | Frontend + landing page |
| Supabase | Pro | $25 | Database + auth |
| Upstash Redis | Pay-per-use | $10 | Cache |
| Webshare Proxies | Residential | $30 | 1000 IPs |
| Sentry | Team | $26 | Error tracking |
| **Subtotal Infra** | | **$161** | |

---

## MARKETING & ADS

| Service | Plan | Monthly Cost | Notes |
|---------|------|--------------|-------|
| LinkedIn Ads | Campaign | $300 | Test budget - retargeting |
| Google Ads | Campaign | $150 | High-intent keywords |
| Canva | Pro | $18 | Design |
| Unsplash+ | Pro | $12 | Stock images |
| **Subtotal Marketing** | | **$480** | |

---

## TOOLS & SUBSCRIPTIONS

| Service | Plan | Monthly Cost | Notes |
|---------|------|--------------|-------|
| Unipile | Growth | $79 | LinkedIn automation |
| Cal.com | Free | $0 | Demo booking |
| HeyGen | Creator | $48 | Maya video avatar |
| Notion | Free | $0 | Docs (if needed) |
| Loom | Free | $0 | Video recording |
| **Subtotal Tools** | | **$127** | |

---

## CONTINGENCY

| Item | Monthly Cost | Notes |
|------|--------------|-------|
| Unexpected API overages | $50 | Buffer |
| Emergency tool purchase | $50 | Buffer |
| Currency fluctuation | $20 | USD→AUD buffer |
| **Subtotal Contingency** | **$120** | |

---

## GRAND TOTAL (Option B - Recommended)

| Category | Monthly Cost |
|----------|--------------|
| AI & Compute (Subscription model) | $160 |
| Voice AI | $107 |
| Email Infrastructure | $155 |
| Enrichment | $197 |
| Infrastructure | $161 |
| Marketing & Ads | $480 |
| Tools & Subscriptions | $127 |
| Contingency | $120 |
| **TOTAL** | **$1,507** |

**Under budget by $493** — Can reallocate to ads if needed.

---

## WHAT YOU NEED TO SET UP

### Subscriptions (Dave creates accounts)
| Service | Action | Cost |
|---------|--------|------|
| Claude Max | Subscribe with your card | $100/mo |
| Salesforge | Already have? Verify plan | $99/mo |
| Hunter.io | Create account | $49/mo |
| Kaspr | Create account | €49/mo |
| HeyGen | Create account | $48/mo |

### API Keys (I configure after you create)
| Service | Get From |
|---------|----------|
| Anthropic | console.anthropic.com |
| Groq | console.groq.com |
| Cartesia | cartesia.ai |
| Telnyx | portal.telnyx.com |
| Proxycurl | proxycurl.com |
| ZeroBounce | zerobounce.net |

### Already Configured
- Railway ✅
- Vercel ✅
- Supabase ✅
- Upstash ✅
- Webshare ✅
- Unipile ✅ (but 401 error)

---

## SUB-AGENT ARCHITECTURE (Subscription Model)

```
┌─────────────────────────────────────────────────────────┐
│                  ANTHROPIC API ($50/mo)                 │
│                                                         │
│   ELLIOT (Main orchestrator)                            │
│   - Critical decisions                                  │
│   - Dave communications                                 │
│   - Error handling                                      │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               CLAUDE MAX SUBSCRIPTION ($100/mo)         │
│                                                         │
│   All Sub-Agents:                                       │
│   - BUILDER (code)                                      │
│   - WRITER (content)                                    │
│   - RESEARCHER (learning)                               │
│   - AUDITOR (review)                                    │
│   - OUTREACH (campaigns)                                │
│   - SUPPORT (tickets)                                   │
│   - etc.                                                │
│                                                         │
│   Unlimited usage for fixed $100                        │
└─────────────────────────────────────────────────────────┘
```

**How this works:**
1. Elliot (me) runs on API for reliability
2. When I spawn a sub-agent, it uses the Claude Max subscription
3. Clawdbot would need config to route sub-agents to Max vs API

**Question for you:** 
Does Clawdbot support routing different sessions to subscription vs API? 
If not, we may need to use the Claude Code CLI or similar for sub-agents.

---

## APPROVAL CHECKLIST

| Line Item | Amount | Approved? |
|-----------|--------|-----------|
| Claude Max subscription | $100 | [ ] |
| Anthropic API (Elliot) | $50 | [ ] |
| Cartesia TTS | $50 | [ ] |
| Groq API | $5 | [ ] |
| Vapi | $20 | [ ] |
| Telnyx | $12.50 | [ ] |
| ClickSend | $24 | [ ] |
| Salesforge | $99 | [ ] |
| WarmForge | $29 | [ ] |
| InfraForge | $22 | [ ] |
| Domain | $5 | [ ] |
| Hunter.io | $49 | [ ] |
| Proxycurl | $55 | [ ] |
| Kaspr | $85 | [ ] |
| ZeroBounce | $8 | [ ] |
| Railway | $50 | [ ] |
| Vercel | $20 | [ ] |
| Supabase | $25 | [ ] |
| Upstash | $10 | [ ] |
| Webshare | $30 | [ ] |
| Sentry | $26 | [ ] |
| LinkedIn Ads | $300 | [ ] |
| Google Ads | $150 | [ ] |
| Canva | $18 | [ ] |
| Unsplash+ | $12 | [ ] |
| Unipile | $79 | [ ] |
| HeyGen | $48 | [ ] |
| Contingency | $120 | [ ] |
| **TOTAL** | **$1,507** | [ ] |

---

*Every dollar accounted for. Ready for your approval.*
