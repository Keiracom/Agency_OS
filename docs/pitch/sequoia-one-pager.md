# Agency OS — Sequoia Intro One-Pager
*For: Bryce Keane, Sequoia Capital*
*Prepared: March 2026*

---

## The Headline

**Agency OS is the AI-powered acquisition engine for B2B service businesses.**

We automate the entire outbound pipeline — finding prospects, enriching them with verified contact data, scoring their intent, and reaching them across email, SMS, voice AI, and LinkedIn — so agencies can focus on closing, not sourcing.

---

## The Problem

Australian marketing agencies spend 40–60% of their time on manual business development — cold prospecting, contact research, chasing unverified leads. Existing tools (Apollo, HubSpot) are built for US enterprise. There's no purpose-built acquisition infrastructure for the ANZ market.

---

## What We Built

A full-stack acquisition OS with three layers:

**1. Intelligence Engine (Siege Waterfall)**
5-tier enrichment pipeline seeded from 3.5M+ Australian business records (ABN bulk extract — free government data). Enriches with Google Maps signals, professional email, LinkedIn identity, and verified mobile — spending < $0.50 AUD per lead. Cost-gated: expensive tiers only trigger for high-intent leads (ALS ≥ 85).

**2. Intent Scoring (ALS — Automated Lead Score)**
Proprietary 0–100 score combining ad spend signals, hiring signals, funding events, and multi-source verification. Tells you *which* leads to pursue before you spend on outreach.

**3. Multi-Channel Distribution**
Automated outreach across:
- Cold email (Salesforge infrastructure)
- Voice AI (Vapi + Telnyx + Cartesia — sub-$0.10/call)
- SMS
- LinkedIn
- Direct mail

Smart Prompts engine generates personalised copy at scale — no templates, no spray-and-pray.

---

## The Business Model

High-ticket SaaS targeting marketing agencies (5–50 employees):

| Tier | AUD/month | Lead Credits |
|------|-----------|--------------|
| Ignition | $2,500 | 1,250 |
| Growth | $5,000 | 3,500 |

**TAM:** ~12,000 Australian marketing agencies
**Blended ARPU target:** ~$4,000 AUD/month
**COGS per lead:** ~$0.10 AUD weighted (most leads never hit the expensive tiers)

---

## The Long Game: business_universe

Agency OS is the Trojan Horse. The real product is **business_universe** — a platform that turns every Australian SMB into an enriched, scoreable, contactable entity, with cross-agency intelligence, bidirectional CRM sync, and AI-driven reactivation.

Think: the B2B data infrastructure layer for the ANZ market. Modelled on what ZoomInfo/Apollo built in the US, but purpose-built for the regulatory and data landscape here (ABN/ACN/ASIC as native primitives).

---

## Why Now

- Voice AI calling costs have collapsed (< $0.10/min with Groq + Cartesia)
- Australian SMBs are dramatically underserved by US-built GTM tooling
- Government data (ABN bulk extract) provides a free, defensible seed layer no competitor can replicate
- AI content generation makes personalisation at scale real for the first time

---

## Stack

FastAPI · Next.js · Supabase · Railway · Prefect · Pydantic AI · Salesforge · Telnyx · Vapi · Cartesia

---

## The Ask

Not fundraising yet — pre-launch, building toward first paying customers. Looking for:
- Feedback on product thesis and go-to-market
- Sequoia's perspective on the AI GTM / sales automation space
- Understanding what milestones would make this a fundable story

---

*Dave — Founder*
