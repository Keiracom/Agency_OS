# Infrastructure Leverage Audit

**Date:** 2026-01-30  
**Purpose:** Master what we OWN before looking outward  
**Core Question:** "Before suggesting a new tool, can THIS do the job?"

---

## Executive Summary

This audit identifies **significant untapped leverage** across our existing infrastructure. The key finding: we have ~$5,000+/month in tool spend but utilize perhaps 30-40% of actual capabilities. Elliot (as AI COO) could dramatically expand self-directed operations using existing APIs.

**Highest Leverage Opportunities:**
1. **Prefect** — Can orchestrate ANY recurring task, not just Agency OS flows
2. **Supabase** — Untapped: Realtime, Edge Functions, Vector/AI capabilities
3. **Redis** — Beyond caching: pub/sub, streams for event architecture
4. **Apify** — 100+ pre-built actors for nearly any web data need
5. **DataForSEO** — Full competitive intelligence suite barely touched

---

## 1. SUPABASE (PostgreSQL + BaaS)

### What It Does
- PostgreSQL database with built-in auth, realtime subscriptions, storage, edge functions
- Row Level Security (RLS) for multi-tenant isolation
- Realtime pub/sub for live updates
- Vector/AI capabilities (pgvector) for embeddings

### Current Use (Agency OS)
- Primary database via SQLAlchemy async engine
- Auth via anon/service keys (RLS enforced)
- Health checks and connection pooling (5/10 config)
- Simple CRUD operations for leads, clients, activities

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Realtime Subscriptions** | Monitor database changes in real-time. Elliot could subscribe to `leads` table and get instant alerts when hot leads appear, without polling. |
| **Edge Functions** | Deploy lightweight serverless functions. Elliot could create webhooks, scheduled tasks, or API endpoints without touching Railway. |
| **Storage Buckets** | Store artifacts, reports, backups. Currently not used for anything. |
| **pgvector** | Embed memory, conversations, or lead profiles for semantic search. "Find me leads similar to X" becomes possible. |
| **Database Webhooks** | Trigger actions on INSERT/UPDATE/DELETE. Could auto-notify Elliot on critical events. |
| **Scheduled Functions** | Built-in cron capability. Alternative to Prefect for simple scheduled tasks. |
| **Full-Text Search** | PostgreSQL FTS is powerful. Could enable natural language search across all lead/company data. |

### Creative Applications
- **Personal Knowledge Base:** Store Dave's notes, preferences, decisions in structured tables with vector search
- **Conversation Memory:** Persist Elliot's session context long-term, searchable by semantic similarity
- **Audit Trail:** Every action Elliot takes → logged in Supabase with realtime dashboard
- **Cross-Session State:** Maintain state across different Elliot instances/sessions

### Self-Improvement Leverage
Elliot could use Supabase to:
1. Build a "learning database" — store what worked, what didn't, with patterns
2. Track own performance metrics over time
3. Store successful prompts/approaches for retrieval
4. Create a "second brain" that persists beyond session memory

**Verdict: HIGHLY UNDERUTILIZED.** We're using it as a dumb database when it's a full BaaS platform.

---

## 2. RAILWAY (PaaS + Hosting)

### What It Does
- Container hosting (Docker-based)
- GraphQL API for programmatic control
- Environments, deployments, logs, metrics
- Cron jobs, volumes, networking

### Current Use
- Hosts Agency OS backend (FastAPI)
- Hosts self-hosted Prefect server
- Deploy via GitHub Actions

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **GraphQL API** | Full programmatic control. Elliot could deploy services, check logs, restart containers, scale resources. |
| **Cron Jobs** | Native cron without Prefect. Simpler tasks could run directly here. |
| **Service Logs** | Query logs programmatically for debugging, monitoring, anomaly detection. |
| **Metrics API** | CPU, memory, network usage. Could alert Dave before outages. |
| **Deploy Previews** | Spin up temporary environments for testing changes. |
| **Private Networking** | Connect services securely. Could run internal tools. |

### Creative Applications
- **Self-Healing:** Elliot monitors service health, restarts crashed services automatically
- **Cost Optimization:** Track usage patterns, suggest right-sizing
- **Deploy Assistant:** Elliot manages the full deploy cycle via API
- **Log Analysis:** Proactive error detection and alerting
- **Spin Up Utilities:** Temporary workers for batch jobs

### Self-Improvement Leverage
With Railway API access, Elliot could:
1. Deploy experimental services/tools
2. Monitor and optimize infrastructure costs
3. Run background workers for long tasks
4. Create isolated environments for testing

**Verdict: PARTIAL USE.** We deploy but don't leverage the programmatic control layer.

---

## 3. PREFECT (Orchestration)

### What It Does
- Workflow orchestration with DAGs
- Scheduled/triggered flows
- Retry logic, concurrency, observability
- Self-hosted (Railway) = unlimited runs

### Current Use
- 20+ Agency OS flows (pacing, enrichment, outreach, etc.)
- Scheduled daily/weekly flows
- Task-level retries and error handling

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Generic Orchestration** | Not limited to Agency OS! Any Python code can be a Prefect flow. |
| **Event-Driven Flows** | Trigger on webhooks, API calls, database events. |
| **Work Pools** | Distribute work across multiple workers. |
| **Artifacts** | Store flow outputs (reports, data) with version history. |
| **Blocks** | Reusable config/credentials. Could store Elliot's operational settings. |
| **Automations** | Trigger actions based on flow state (failure alerts, etc.) |
| **Sub-flows** | Compose complex workflows from smaller pieces. |

### Creative Applications

**For Elliot Self-Directed Ops:**
- Daily briefing flow (compile metrics, news, priorities → send to Dave)
- Memory maintenance flow (rollup logs, extract patterns)
- Infrastructure health check flow (ping all services, alert on issues)
- Content generation flow (social posts, reports, summaries)
- Learning flow (analyze past sessions, extract improvements)

**For Dave's Personal Automation:**
- Expense tracking (scrape bank, categorize, report)
- News aggregation (Dave's interests, summarized daily)
- Social media scheduling
- Personal CRM (track relationships, remind follow-ups)
- Project time tracking

### Self-Improvement Leverage
Prefect is Elliot's **automation backbone**. Key flows to build:
1. **Daily Reflection** — Analyze yesterday's logs, extract lessons
2. **Pattern Recognition** — Find recurring issues/requests
3. **Knowledge Consolidation** — Update MEMORY.md automatically
4. **Health Monitoring** — Check all infrastructure, report status
5. **Proactive Alerts** — Anticipate issues before they happen

**Verdict: HIGHLY UNDERUTILIZED for Elliot-specific needs.** We use it for Agency OS but not for meta-operations.

---

## 4. REDIS (Upstash)

### What It Does
- Key-value store, caching
- Pub/Sub messaging
- Streams (append-only logs)
- Sorted sets, lists, hashes
- Lua scripting

### Current Use
- Enrichment cache (90-day TTL)
- Rate limiting (resource-level, daily resets)
- AI spend tracking (daily budget circuit breaker)

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Pub/Sub** | Real-time event bus. Services can publish events, Elliot can subscribe. |
| **Streams** | Event sourcing. Every action logged as immutable stream entry. |
| **Sorted Sets** | Priority queues, leaderboards. Could rank leads by urgency. |
| **TTL on Any Key** | Ephemeral state. Session data, temp flags, cooldowns. |
| **Atomic Operations** | INCR, DECR, etc. Counters, rate limiters, distributed locks. |
| **Geospatial** | Location-based queries. Could geo-filter leads. |

### Creative Applications
- **Event Bus:** All Elliot actions publish events → other services can react
- **Rate Limiting Anything:** Not just API calls — limit any behavior
- **Session State:** Fast, shared state between Elliot instances
- **Distributed Locks:** Coordinate between concurrent operations
- **Real-time Metrics:** Update dashboards instantly

### Self-Improvement Leverage
Redis enables:
1. **Cross-session memory** — Fast-access recent context
2. **Operation counters** — Track what Elliot does most
3. **Cooldown timers** — Prevent repetitive actions
4. **Priority queues** — Task management with urgency ranking

**Verdict: PARTIALLY UTILIZED.** Caching/rate limiting is good, but pub/sub and streams unused.

---

## 5. SALESFORGE ECOSYSTEM (Cold Email)

### What It Does
- **InfraForge:** Domain purchasing, mailbox provisioning
- **WarmForge:** Email warmup (reputation building)
- **Salesforge:** Campaign sending, sequences, tracking

### Current Use
- 3 domains, 6 mailboxes configured
- 1 mailbox fully warmed (david@agencyxos-reach.com)
- 5 mailboxes at 47% warmup (paused!)
- Salesforge workspace exists but 0 mailboxes connected

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Domain Health Monitoring** | Track deliverability scores, alert on issues |
| **Warmup Automation** | Ensure all mailboxes stay warmed |
| **Sequence Management** | A/B test email copy, optimize automatically |
| **Analytics API** | Track opens, replies, bounces programmatically |
| **Mailbox Rotation** | Smart selection of which mailbox to use |
| **Blacklist Monitoring** | Alert if domains get blacklisted |

### Creative Applications
- **Reputation Dashboard:** Real-time view of all domain/mailbox health
- **Auto-Healing:** Pause sends from degraded mailboxes, increase from healthy
- **Copy Evolution:** Use reply data to evolve email templates
- **Dave's Personal Email:** Could warm up personal domains for better deliverability

### Immediate Actions Needed
1. **Connect mailboxes to Salesforge** (unlocks unlimited warmup)
2. **Resume warmup on 5 paused mailboxes**
3. **Monitor deliverability programmatically**

**Verdict: CRITICALLY UNDERUTILIZED.** 5/6 mailboxes not warming = wasted infrastructure.

---

## 6. RESEND (Transactional Email)

### What It Does
- Transactional email (notifications, alerts, receipts)
- Threading support (In-Reply-To headers)
- Batch sending
- Analytics/tracking

### Current Use
- Available for transactional emails
- Threading support implemented

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Alert System** | Send Elliot's alerts/reports to Dave via email |
| **Scheduled Digests** | Daily/weekly summaries to stakeholders |
| **Webhook Notifications** | Email on important events |
| **HTML Templates** | Rich formatted reports |

### Creative Applications
- **Daily Briefing Email:** Elliot sends morning summary to Dave
- **Exception Alerts:** Immediate notification on critical issues
- **Weekly Metrics Report:** Automated Agency OS performance summary
- **Personal Notifications:** Dave's personal automation alerts

**Verdict: UNDERUTILIZED.** Mostly just available but not systematically used for Elliot operations.

---

## 7. UNIPILE (LinkedIn Automation)

### What It Does
- LinkedIn automation via hosted auth
- Connection requests, messages, profile scraping
- Webhook status updates
- SOC 2 compliant

### Current Use
- Primary LinkedIn outreach for Agency OS
- Connection/message sending
- Rate limits enforced (80-100 connections/day)

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Profile Monitoring** | Track when leads update their profiles (job changes, etc.) |
| **Company Page Scraping** | Pull company updates, news, job postings |
| **Network Analysis** | Map connections, find warm intros |
| **Content Monitoring** | Track what leads post/engage with |
| **Dave's LinkedIn** | Could manage Dave's personal LinkedIn presence |

### Creative Applications
- **Trigger Alerts:** Lead posts about pain point → alert sales
- **Timing Optimization:** Find when leads are most active
- **Warm Intro Finding:** "Who in our network knows this lead?"
- **Dave's Network Building:** Automated connection strategy for Dave personally

**Verdict: PARTIALLY UTILIZED.** Basic outreach works, but intelligence gathering capabilities unused.

---

## 8. TWILIO (Voice/SMS)

### What It Does
- Phone number provisioning
- SMS sending/receiving
- Voice calls (via Vapi)
- Phone number lookup
- Webhook handling

### Current Use
- SMS sending with DNCR compliance
- Phone number: +61240126220
- Webhook parsing for inbound/status

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Inbound SMS Handling** | Receive and process responses |
| **Phone Lookup** | Enrich phone data (carrier, type, location) |
| **Call Recordings** | Store/transcribe for analysis |
| **Multi-Channel** | Coordinate SMS + Voice timing |
| **Number Management** | Programmatic number provisioning |

### Creative Applications
- **Personal Alerts:** SMS Dave on urgent matters
- **2FA Verification:** Build verification flows
- **Appointment Reminders:** Automated meeting confirmations
- **Response Bot:** Auto-reply to common SMS queries

**Verdict: BASIC USE ONLY.** Outbound works but inbound handling and intelligence features unused.

---

## 9. CLICKSEND (SMS + Direct Mail)

### What It Does
- SMS (Australian-native, primary for AU)
- Direct mail (letters, postcards)
- MMS
- Fax (legacy)
- Voice (TTS calls)

### Current Use
- SMS for Australian leads
- DNCR compliance
- Basic send tracking

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Direct Mail API** | Physical mail automation (letters, postcards) |
| **Address Verification** | Validate postal addresses |
| **Postcard Campaigns** | Tangible outreach for high-value leads |
| **Letter Generation** | Automated document creation |
| **Bulk Operations** | Batch sending with templates |

### Creative Applications
- **Premium Outreach:** Hot leads (ALS 85+) get physical postcards
- **Event Invitations:** Physical invites for exclusivity
- **Thank You Notes:** Automated appreciation letters
- **Dave's Personal Mail:** Birthday cards, thank yous automated

### Unique Value
ClickSend's **direct mail** is completely untapped. In a digital world, physical mail has 10x open rates.

**Verdict: SEVERELY UNDERUTILIZED.** Direct mail capabilities completely dormant.

---

## 10. VAPI (Voice AI)

### What It Does
- AI-powered voice calls
- Integrates Twilio + ElevenLabs + Claude
- Call recording, transcription
- Webhook events
- Assistant management

### Current Use
- Voice calls for Agency OS outreach
- Recording cleanup flow (90-day retention)
- Retry logic implemented

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Inbound Calls** | AI receptionist capability |
| **Call Analytics** | Analyze transcripts for patterns |
| **Custom Assistants** | Different voices/personas for different contexts |
| **Real-time Coaching** | Could assist Dave during calls |
| **Sentiment Analysis** | Track call outcomes and sentiment |

### Creative Applications
- **AI Receptionist:** Handle inbound calls to Dave's business
- **Meeting Prep Calls:** Vapi calls leads before meetings to confirm/qualify
- **Follow-up Calls:** Automated check-ins after meetings
- **Dave's Personal Assistant:** Vapi handles Dave's scheduling calls

**Verdict: SINGLE-PURPOSE USE.** Only outbound sales calls. Inbound and personal use unexplored.

---

## 11. ELEVENLABS (Voice Synthesis)

### What It Does
- Text-to-speech (multilingual)
- Voice cloning
- Custom voice creation
- High-quality synthesis

### Current Use
- Voice provider for Vapi calls
- Default voice (Adam) used

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Voice Cloning** | Create brand voice for Agency OS |
| **Content Narration** | Turn written content into audio |
| **Podcast Generation** | Automated audio summaries |
| **Multilingual** | Support for non-English markets |
| **Custom Voices** | Different personas for different contexts |

### Creative Applications
- **Audio Briefings:** Elliot narrates daily summary for Dave to listen
- **Content Repurposing:** Blog posts → podcasts automatically
- **Personalized Voicemails:** Custom audio messages
- **Dave's Voice:** Clone Dave's voice for scalable personal touch

**Verdict: PASS-THROUGH ONLY.** Used via Vapi but direct capabilities unused.

---

## 12. APOLLO (Lead Enrichment)

### What It Does
- Person/company enrichment
- Email finding
- LinkedIn data
- 50+ data points per lead
- Email verification

### Current Use
- Primary enrichment (Tier 1)
- Full field capture implemented
- Email status tracking

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Saved Searches** | Automated lead discovery |
| **Sequences** | Apollo has its own outreach engine |
| **Lists** | Bulk enrichment batches |
| **Webhooks** | Get notified when data changes |
| **Intent Data** | Track which companies are researching topics |

### Creative Applications
- **ICP Evolution:** Continuously refine ideal customer profile from data
- **Market Mapping:** Build comprehensive views of target markets
- **Competitor Tracking:** Monitor competitor hiring/growth
- **Network Enrichment:** Enrich Dave's personal contacts

### Self-Improvement Leverage
Apollo data could feed ML models for:
1. Better ALS scoring
2. Pattern recognition in successful deals
3. Timing prediction (when to reach out)

**Verdict: GOOD ENRICHMENT USE, but discovery and intelligence features untapped.**

---

## 13. PROSPEO (Email Finding)

### What It Does
- Email finding/verification
- Domain search
- LinkedIn-to-email
- Bulk operations

### Current Use
- API key configured but no integration found in codebase
- Likely intended as Apollo backup

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Email Verification** | Secondary verification layer |
| **Domain Search** | Find all emails at a company |
| **LinkedIn Scraping** | Alternative enrichment path |
| **Bulk Operations** | High-volume email finding |

### Immediate Action
**Build the Prospeo integration!** It's paid for but not used.

**Verdict: COMPLETELY UNUSED despite having API key.**

---

## 14. DATAFORSEO (SEO Intelligence)

### What It Does
- Domain authority/rank
- Backlink analysis
- Organic traffic estimates
- Keyword tracking
- SERP monitoring
- Competitor analysis

### Current Use
- Domain overview (organic metrics)
- Backlinks summary
- ALS enhancement (~$0.03/lead)

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Competitor Monitoring** | Track competitor rankings, content |
| **Content Gap Analysis** | Find keywords competitors rank for but we don't |
| **Link Opportunity Finding** | Identify link building targets |
| **SERP Tracking** | Monitor ranking changes |
| **Rank Tracking API** | Automated ranking reports |
| **On-Page Analysis** | Audit client websites |

### Creative Applications
- **SEO Health Dashboard:** Monitor Agency OS client sites
- **Content Strategy:** Data-driven content recommendations
- **Lead Qualification:** Better SEO metrics = better ALS accuracy
- **Dave's Projects:** Track SEO for any of Dave's sites

### Coverage
DataForSEO has **71 different API endpoints**. We use maybe 3.

**Verdict: BARELY SCRATCHED THE SURFACE.** Massive intelligence capability unused.

---

## 15. APIFY (Web Scraping)

### What It Does
- 2000+ pre-built scrapers (actors)
- Custom actor deployment
- Proxy management
- Scheduling
- Storage

### Current Use
- LinkedIn profile/company scraping
- Website content crawling
- Review platform scraping (Trustpilot, G2, etc.)
- Waterfall architecture (Cheerio → Playwright → Camoufox)

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Google News** | Track news about leads/competitors |
| **Job Board Scraping** | Hiring signals (growth indicator) |
| **Social Media Monitoring** | Track mentions, sentiment |
| **Price Monitoring** | Competitor pricing intelligence |
| **YouTube/Podcast** | Find where leads appear as guests |
| **Event Scraping** | Find conferences leads attend |

### Pre-Built Actors Available
- Twitter/X scraper
- Instagram scraper
- Google Maps scraper
- YouTube channel scraper
- Crunchbase scraper
- Product Hunt scraper
- Reddit scraper
- GitHub scraper
- And 2000+ more...

### Creative Applications
- **News Intelligence:** Morning briefing with relevant news for hot leads
- **Competitive Intelligence:** Track competitor moves, pricing, hiring
- **Trend Monitoring:** Track industry trends, topics
- **Dave's Personal:** Track anything for Dave's personal interests

**Verdict: DEEP CAPABILITIES, SHALLOW USE.** We use 5 actors out of 2000+.

---

## 16. ANTHROPIC (Claude AI)

### What It Does
- LLM completions (Claude 3.5)
- Intent classification
- Content generation
- Analysis/reasoning

### Current Use
- Intent classification for replies
- Email personalization
- Daily spend limiting (circuit breaker)
- Model: claude-3-5-haiku-20241022 default

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Tool Use** | Claude can call tools (code, search, etc.) |
| **Vision** | Analyze images, screenshots, documents |
| **Long Context** | 200K token window for large document analysis |
| **Batch API** | 50% cost discount for async processing |
| **Computer Use** | GUI automation (experimental) |

### Creative Applications
- **Self-Reflection:** Analyze own conversation logs
- **Report Generation:** Automatic analysis documents
- **Code Generation:** Write scripts, automations
- **Research Synthesis:** Combine multiple sources into insights
- **Vision Analysis:** Analyze competitor websites, ads, etc.

### Self-Improvement Leverage
Claude is Elliot's "brain" — but we use it narrowly. Expand to:
1. Self-analysis (what could I do better?)
2. Pattern recognition across sessions
3. Hypothesis generation
4. Learning from feedback

**Verdict: USED BUT NOT LEVERAGED.** Narrow application of broad capability.

---

## 17. OPENROUTER (AI Fallback)

### What It Does
- Multi-model routing
- Access to 100+ models
- Fallback capability
- Cost optimization

### Current Use
- Fallback when Anthropic unavailable

### Untapped Potential for Elliot

| Capability | Self-Directed Application |
|------------|---------------------------|
| **Model Selection** | Pick best model for each task |
| **Cost Optimization** | Use cheaper models for simple tasks |
| **Specialized Models** | Code models, math models, etc. |
| **Comparison Testing** | A/B test model performance |

### Creative Applications
- **Task Routing:** Simple tasks → cheap model, complex → Claude
- **Capability Expansion:** Access models Anthropic doesn't have
- **Cost Reduction:** Significant savings on high-volume simple tasks

**Verdict: PURE FALLBACK.** Not strategically used for optimization.

---

## Synthesis: The Leverage Matrix

### Tier 1: Highest Untapped Leverage

| Service | Unlock Potential | Effort |
|---------|------------------|--------|
| **Prefect** | Orchestrate ALL automation, not just Agency OS | Low |
| **Supabase** | Realtime, Edge Functions, Vector search | Medium |
| **Apify** | 2000+ scrapers for any data need | Low |
| **DataForSEO** | Full competitive intelligence suite | Medium |
| **Salesforge** | Fix warmup (5 mailboxes paused!) | Immediate |

### Tier 2: Medium Leverage, Worth Pursuing

| Service | Unlock Potential | Effort |
|---------|------------------|--------|
| **Redis** | Event bus, pub/sub architecture | Medium |
| **Railway** | Programmatic infrastructure control | Medium |
| **ClickSend** | Direct mail (physical outreach) | Low |
| **Vapi** | Inbound calls, AI receptionist | Medium |

### Tier 3: Incremental Improvements

| Service | Unlock Potential | Effort |
|---------|------------------|--------|
| **Apollo** | Discovery/intelligence features | Low |
| **Unipile** | LinkedIn intelligence gathering | Medium |
| **Anthropic** | Vision, tools, batch processing | Low |
| **OpenRouter** | Cost optimization via model routing | Low |

### Tier 4: Build the Integration

| Service | Status | Action |
|---------|--------|--------|
| **Prospeo** | API key exists, no integration | Build it |

---

## Recommended Actions

### Immediate (This Week)
1. ☐ **Fix Salesforge/WarmForge** — 5 mailboxes not warming is money wasted
2. ☐ **Build Prospeo integration** — Paid for but unused
3. ☐ **Create Elliot-specific Prefect flows** — Daily briefing, memory maintenance

### Short-Term (This Month)
4. ☐ **Supabase Realtime** — Subscribe to hot lead insertions
5. ☐ **ClickSend Direct Mail** — Implement postcard capability for ALS 90+ leads
6. ☐ **Apify expansion** — Add news, jobs, social monitoring actors
7. ☐ **DataForSEO expansion** — Competitor monitoring, content gap analysis

### Medium-Term (This Quarter)
8. ☐ **Redis event bus** — Implement pub/sub for cross-service coordination
9. ☐ **Railway API integration** — Elliot can manage infrastructure
10. ☐ **Supabase pgvector** — Semantic search across all data
11. ☐ **Vapi inbound** — AI receptionist capability

---

## Key Insight

**We don't need more tools. We need to actually use the tools we have.**

Every service above has capabilities we're paying for but ignoring. Elliot's self-directed operations could expand 10x just by leveraging existing infrastructure better.

The pattern is clear:
- We build the basic integration
- We use it for the immediate need
- We never revisit to discover advanced features

This audit should become a **living document** — revisit quarterly to assess capability utilization.

---

*Generated by Elliot (AI COO) — 2026-01-30*
