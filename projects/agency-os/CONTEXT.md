# Agency OS — Current Context

*What Elliot needs to know to work on Agency OS effectively.*

---

## What It Is

**Multi-channel client acquisition SaaS for Australian marketing agencies**

"Bloomberg Terminal for Client Acquisition" — orchestrates automated outreach across email, SMS, LinkedIn, voice AI, and direct mail with proprietary lead scoring.

---

## Tech Stack

| Layer | Technology | Host |
|-------|------------|------|
| Backend | FastAPI + Pydantic AI | Railway |
| Frontend | Next.js | Vercel |
| Database | PostgreSQL | Supabase (AP-Southeast-1) |
| Orchestration | Prefect (self-hosted) | Railway |
| CI/CD | GitHub Actions | GitHub |
| Repo | github.com/Keiracom/Agency_OS | GitHub |

### Key Integrations (15+)
- **Email:** Salesforge ecosystem (InfraForge → Warmforge → Salesforge), Resend (transactional)
- **LinkedIn:** Unipile (primary), HeyReach (deprecated)
- **Voice:** Vapi (AI calls), Cartesia (TTS), ElevenLabs (fallback)
- **SMS:** Twilio, ClickSend
- **Data:** Apollo, Prospeo, DataForSEO, Apify

---

## Architecture Essentials

### Import Hierarchy (4 layers)
```
models → integrations → engines → orchestration
```
Never import upward.

### ALS (Agency Lead Score)
- Proprietary lead scoring algorithm
- **Hot threshold: ALS 85+** (not 80)
- SDK is tiered with 75% cost savings for sub-85 leads

### Key Detectors (src/detectors/)
- WHO Detector — decision maker identification
- WHAT Detector — company fit signals
- WHEN Detector — timing signals
- HOW Detector — channel preferences

### ML Infrastructure (Already Exists)
- ConversionPattern model with confidence scores
- Weight Optimizer using scipy
- Platform Priors as seed data
- Full funnel: Meetings & Deals tables
- Activity tracking: timing, opens, clicks, replies
- ICP Refinement Log for transparency

---

## Current State (as of 2026-01-28)

### ✅ Complete
- Platform build: 174/174 tasks
- CI pipeline: Fixed and green
- P0 bugs: All 3 fixed (LinkedIn weekends, funnel detector, voice retry)
- GitHub push access: Working
- Dashboard prototype: Ready

### 🔴 Blocking Launch
- **Phase 21 (E2E Testing):** All journeys J0-J6 at 🔴
- Dashboard: Prototype needs to replace production page

### Infrastructure Status
- All production services alive
- Database latency: 2.2 seconds (Railway possibly in wrong region)
- No dependency pinning (all >=, no ==)
- Test coverage thin (47 test files vs 185 source files)

---

## Business Model

### Pricing (AUD/month)
| Tier | Price | Target |
|------|-------|--------|
| Ignition | $2,500 | Entry level |
| Velocity | $5,000 | Growth |
| Dominance | $7,500 | Premium |

### Target Market
- Australian marketing agencies
- $30K–$300K monthly revenue
- Need client acquisition at scale

### Differentiators vs AI SDR Competitors
1. Australian market specialist
2. Outcome-focused (show rate, not activity)
3. Agency B2B model (not direct sales)
4. Meetings-as-a-service positioning

---

## Design Language (STRICT)

### Banned Terms
- "Leads" → Use "Prospects" or "Opportunities"
- "Credits" → Subscription model, no credits
- Any commodity language

### ALS Tier Labels
- 85+ = Hot
- 70-84 = Warm
- Below 70 = Nurture

### Dashboard Principles
- Show customer metrics, not operator metrics
- Every element answers: "Is this working?", "How well?", "What should I do next?"
- Emotions: Confidence, excitement, validation — NOT anxiety, confusion, overwhelm

---

## Key Files

| File | Purpose |
|------|---------|
| src/detectors/ | WHO/WHAT/WHEN/HOW ML models |
| src/engines/ | Core processing logic |
| src/orchestration/ | Prefect flows |
| ARCHITECTURE_BRIEF.md | 18KB system synthesis |
| DASHBOARD_UX_REVIEW.md | Dashboard audit |
| CODEBASE_DEEP_DIVE.md | Full code analysis |

---

*Update this file when significant state changes occur.*
