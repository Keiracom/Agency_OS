# Claude Agent SDK Integration Plan — Agency OS

**Document Version:** 1.0
**Created:** January 2026
**Author:** CTO Office
**Status:** PLANNING
**Currency:** AUD (Australian Dollars)

---

## Table of Contents

1. [What is the Claude Agent SDK?](#1-what-is-the-claude-agent-sdk)
2. [Why SDK Matters to Agency OS](#2-why-sdk-matters-to-agency-os)
3. [The Philosophy: Deterministic + Intelligent](#3-the-philosophy-deterministic--intelligent)
4. [Current vs SDK Architecture](#4-current-vs-sdk-architecture)
5. [Five Use Cases for SDK Brain](#5-five-use-cases-for-sdk-brain)
6. [Cost Optimization Strategies](#6-cost-optimization-strategies)
7. [Implementation Architecture](#7-implementation-architecture)
8. [Step-by-Step Integration Guide](#8-step-by-step-integration-guide)
9. [File Changes Required](#9-file-changes-required)
10. [Testing & Validation](#10-testing--validation)
11. [Rollout Plan](#11-rollout-plan)
12. [Appendix: Code Examples](#12-appendix-code-examples)

---

## 1. What is the Claude Agent SDK?

### 1.1 Simple Explanation

Imagine you have two types of workers:

**Worker A (Current System):**
- You give them a task: "Write an email for this lead"
- They write ONE email and hand it back
- If the email is wrong, you have to manually tell them to fix it
- They can't look anything up—they only use what you give them

**Worker B (SDK Agent):**
- You give them a goal: "Research this lead and write a personalized email"
- They automatically:
  1. Search the web for recent news about the company
  2. Check LinkedIn for the person's recent posts
  3. Look for pain points in job postings
  4. Draft an email
  5. Review their own work
  6. Revise if needed
  7. Return the final result
- They use tools (web search, web fetch, etc.) autonomously
- They can self-correct without you intervening

### 1.2 Technical Definition

The **Claude Agent SDK** is a Python library that lets Claude:

1. **Use Tools**: Call functions (web search, database queries, API calls) during a conversation
2. **Loop Autonomously**: Keep working until a goal is achieved, not just one response
3. **Self-Correct**: Evaluate its own work and improve it
4. **Maintain Context**: Remember what it's done across multiple turns
5. **Return Structured Data**: Output JSON that matches your exact schema

### 1.3 Current Agency OS AI vs SDK

| Feature | Current (Anthropic Client) | SDK Agent |
|---------|---------------------------|-----------|
| Single request-response | ✅ Yes | ✅ Yes |
| Multi-turn conversation | ❌ No (manual) | ✅ Yes (automatic) |
| Tool use (web search) | ❌ No | ✅ Yes |
| Self-correction loops | ❌ No | ✅ Yes (up to N turns) |
| Structured output | ⚠️ Manual parsing | ✅ Schema-enforced |
| Cost control | ✅ Daily limit | ✅ Per-call limit |

### 1.4 What SDK Is NOT

- **NOT a replacement for Prefect**: Prefect handles workflow orchestration (scheduling, retries, monitoring). SDK handles intelligent decision-making within tasks.
- **NOT a database**: SDK doesn't store data. It processes data and returns results.
- **NOT always-on**: SDK agents run for specific tasks, not continuously.
- **NOT magic**: It's still Claude—just with the ability to use tools and loop.

---

## 2. Why SDK Matters to Agency OS

### 2.1 The Current Limitation

Right now, Agency OS uses Claude for:

```
Lead data → Claude → Single response → Save to database
```

This works for simple tasks (classify intent, write email draft). But it fails for complex tasks that require:

1. **Research**: Finding information not in the lead record
2. **Judgment**: Deciding what information is relevant
3. **Iteration**: Refining output until it's good enough

### 2.2 The SDK Opportunity

With SDK, Agency OS can:

```
Lead data → SDK Agent → [Research → Evaluate → Refine → Validate] → High-quality output
```

**Real-world example:**

**Current flow for Hot Lead email:**
1. Get lead data from database (name, company, title)
2. Call Claude: "Write email for {name} at {company}"
3. Get generic email back
4. Send it

**SDK flow for Hot Lead email:**
1. Get lead data from database
2. Start SDK Agent with goal: "Research and write personalized email"
3. Agent autonomously:
   - Searches web for "{company} recent news"
   - Fetches company website for pain points
   - Checks LinkedIn for person's recent posts
   - Identifies a relevant hook
   - Writes email with specific, researched personalization
   - Evaluates: "Is this hook specific enough?"
   - Revises if needed
4. Returns high-quality, researched email
5. Send it

**The difference**: The SDK email references something real and specific. The current email is generic and templated.

### 2.3 Business Impact

| Metric | Current Model | With SDK Brain | Source |
|--------|---------------|----------------|--------|
| Email reply rate | 5% | 7.5% (+50%) | Industry research |
| Meeting booking rate | Baseline | +25-40% | Cognism/Genesy |
| Voice call conversion | Baseline | +60-70% engagement | Voice AI research |
| Cost per meeting | $34.14 | $27.67 (-19%) | Internal analysis |

---

## 3. The Philosophy: Deterministic + Intelligent

### 3.1 The Core Principle

> **Use AI at decision points, not everywhere.**

Most of Agency OS should remain deterministic (predictable, fast, cheap):

- Fetching data from Apollo ← Deterministic API call
- Sending an email via Salesforge ← Deterministic API call
- Scheduling a Prefect flow ← Deterministic orchestration
- Calculating ALS score ← Deterministic algorithm

AI (SDK Brain) should only be used where humans would need to think:

- "What should I research about this lead?" ← Intelligent
- "How should I personalize this email?" ← Intelligent
- "Is this reply positive or negative?" ← Intelligent
- "How should I handle this objection?" ← Intelligent

### 3.2 The Hybrid Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     PREFECT ORCHESTRATION                        │
│                   (Deterministic Shell)                          │
│                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │ Fetch Lead  │───▶│ Check ALS   │───▶│ Select      │         │
│   │ (DB Query)  │    │ (Algorithm) │    │ Channel     │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
│                                               │                  │
│                            ┌──────────────────┴────────────────┐ │
│                            │                                   │ │
│                            ▼                                   ▼ │
│                    ┌──────────────┐                   ┌──────────┐
│                    │ Hot Lead?    │                   │ Cold?    │
│                    │ (ALS 85+)    │                   │ Template │
│                    └──────────────┘                   │ Email    │
│                            │                          └──────────┘
│                            ▼                                     │
│                  ╔══════════════════╗                            │
│                  ║   SDK BRAIN      ║  ← AI decision point       │
│                  ║                  ║                            │
│                  ║ 1. Research lead ║                            │
│                  ║ 2. Find pain pts ║                            │
│                  ║ 3. Write email   ║                            │
│                  ║ 4. Self-review   ║                            │
│                  ╚══════════════════╝                            │
│                            │                                     │
│                            ▼                                     │
│                    ┌──────────────┐                              │
│                    │ Send Email   │ ← Back to deterministic      │
│                    │ (Salesforge) │                              │
│                    └──────────────┘                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 When to Use SDK Brain vs Simple Claude Call

| Task | Use SDK Brain? | Reasoning |
|------|----------------|-----------|
| Intent classification | ❌ No (use Haiku) | Single classification, no tools needed |
| Email template personalization | ⚠️ Maybe | Cold leads: No. Hot leads: Yes |
| Deep lead research | ✅ Yes | Needs web search, multi-step |
| Voice call KB generation | ✅ Yes | Needs research, complex output |
| Objection handling | ⚠️ Maybe | Simple objections: No. Complex: Yes |
| ALS score calculation | ❌ No | Deterministic algorithm |
| Campaign scheduling | ❌ No | Deterministic rules |

### 3.4 The Golden Rule

> **If a human SDR would need to "think about it" or "look something up", use SDK Brain.**
> **If a human SDR would just "follow the process", use deterministic code.**

---

## 4. Current vs SDK Architecture

### 4.1 Current Agency OS AI Architecture

```
src/
├── integrations/
│   └── anthropic.py          ← Simple Claude client (request-response)
│
├── agents/
│   ├── base_agent.py         ← Pydantic AI wrapper
│   ├── icp_discovery_agent   ← Single-turn agent
│   ├── content_agent.py      ← Single-turn agent
│   ├── reply_agent.py        ← Single-turn agent
│   └── skills/               ← Skill modules
│       ├── base_skill.py
│       ├── research_skills.py    ← Deep research (basic)
│       ├── messaging_generator.py
│       └── ...
│
├── engines/
│   ├── scout.py              ← Uses Apollo/Apify, calls skills
│   ├── closer.py             ← Uses anthropic.classify_intent()
│   ├── content.py            ← Uses content_agent
│   └── voice.py              ← Uses templates (no AI yet)
│
└── orchestration/
    └── flows/
        ├── enrichment_flow.py
        ├── outreach_flow.py
        └── reply_recovery_flow.py
```

**Current limitations:**
1. `anthropic.py` does single request-response (no tools, no loops)
2. Agents are single-turn (one input → one output)
3. Research skills call Apify but can't autonomously decide what to search
4. Voice engine uses static templates, no personalized KB

### 4.2 SDK-Enhanced Architecture

```
src/
├── integrations/
│   ├── anthropic.py          ← Keep for simple tasks (Haiku)
│   └── sdk_brain.py          ← NEW: SDK Agent wrapper
│
├── agents/
│   ├── base_agent.py         ← Keep for simple agents
│   ├── sdk_agents/           ← NEW: SDK-powered agents
│   │   ├── base_sdk_agent.py     ← SDK wrapper with cost control
│   │   ├── enrichment_agent.py   ← Deep research agent
│   │   ├── email_agent.py        ← Personalized email agent
│   │   ├── voice_kb_agent.py     ← Voice call prep agent
│   │   └── objection_agent.py    ← Objection handling agent
│   └── skills/               ← Keep existing skills
│
├── engines/
│   ├── scout.py              ← Updated: calls SDK for Hot leads
│   ├── closer.py             ← Updated: SDK for complex objections
│   ├── content.py            ← Updated: SDK for Hot lead emails
│   └── voice.py              ← Updated: SDK for call KB
│
└── orchestration/
    └── flows/                ← No changes (Prefect stays same)
```

### 4.3 Data Flow Comparison

**Current: Cold Lead Email**
```
Prefect Flow → ContentEngine.generate_email() → anthropic.complete() → Email
```

**SDK: Hot Lead Email**
```
Prefect Flow → ContentEngine.generate_email()
                    → (ALS < 85) → anthropic.complete() → Email
                    → (ALS ≥ 85) → SDKBrain.research_and_write()
                                       → [WebSearch → WebFetch → Draft → Review]
                                       → Personalized Email
```

---

## 5. Five Use Cases for SDK Brain

### 5.1 Use Case 1: Deep Lead Enrichment (Hot Leads Only)

**Trigger:** Lead ALS score ≥ 85 (Hot tier)

**Goal:** Gather rich context beyond what Apollo/Clay provide

**SDK Agent Workflow:**
```
Input: Lead basic data (name, company, title, LinkedIn URL)
│
├─→ Tool: WebSearch("{company} recent news funding")
│   └─→ Finds: "Company raised Series B last month"
│
├─→ Tool: WebFetch(company_website + "/careers")
│   └─→ Finds: "Hiring 3 SDRs → likely scaling outbound"
│
├─→ Tool: WebFetch(linkedin_posts_url)
│   └─→ Finds: CEO posted about "leads going cold"
│
├─→ Evaluate: "Do I have enough to personalize?"
│   └─→ Confidence: 87% → Yes, sufficient
│
└─→ Output: EnrichmentResult
        - pain_points: ["lead response time", "scaling outbound"]
        - recent_news: "Series B funding, Feb 2026"
        - hiring_signals: ["SDR", "AE", "CSM"]
        - personalization_hooks: ["CEO quote about cold leads"]
```

**Cost:** ~$0.78 AUD per lead (worst case)
**Optimized Cost:** ~$0.40 AUD per lead (with caching)

**Files Changed:**
- `src/agents/sdk_agents/enrichment_agent.py` (new)
- `src/engines/scout.py` (update to call SDK for Hot leads)

---

### 5.2 Use Case 2: Personalized Email Writing (Hot Leads Only)

**Trigger:** Outreach to Hot lead (ALS ≥ 85) with enriched data

**Goal:** Write email that references specific, researched information

**SDK Agent Workflow:**
```
Input: Lead data + enrichment data + campaign messaging
│
├─→ Analyze: Pain points, recent news, hooks
│
├─→ Draft: Initial email using best hook
│
├─→ Self-Review: "Is this specific enough?"
│   └─→ "Hook references funding but not pain point"
│
├─→ Revise: Add pain point reference
│
├─→ Final Check: Length, tone, CTA
│
└─→ Output: PersonalizedEmail
        - subject: "Congrats on Series B, {first_name}"
        - body: "Saw your CEO's post about lead response time..."
        - hook_used: "CEO pain point quote"
        - confidence: 0.91
```

**Cost:** ~$0.16 AUD per email (worst case)
**Optimized Cost:** ~$0.05 AUD per email (with templates + personalization)

**Files Changed:**
- `src/agents/sdk_agents/email_agent.py` (new)
- `src/engines/content.py` (update to call SDK for Hot leads)

---

### 5.3 Use Case 3: Response Classification (All Replies)

**Trigger:** Incoming reply from any channel

**Goal:** Classify intent with high accuracy

**Note:** This does NOT need full SDK—use simple Haiku call. But we upgrade the classification prompt and add context awareness.

**Current vs Upgraded:**

| Aspect | Current | Upgraded |
|--------|---------|----------|
| Model | Haiku | Haiku (same) |
| Context | Reply text only | Reply + previous thread + lead data |
| Output | 7 intents | 7 intents + sub-categories |
| Batch | One at a time | Batch processing (50% discount) |

**Cost:** ~$0.01 AUD per classification (Haiku + batch)

**Files Changed:**
- `src/engines/closer.py` (update classification prompt)
- No new SDK agent needed

---

### 5.4 Use Case 4: Objection Handling (Complex Objections)

**Trigger:** Reply classified as "not_interested" with specific objection

**Goal:** Generate contextual response to overcome objection

**SDK Agent Workflow:**
```
Input: Objection text + lead data + previous thread + campaign context
│
├─→ Classify Objection Type:
│   - Budget → "We don't have budget"
│   - Timing → "Not the right time"
│   - Authority → "I'm not the decision maker"
│   - Need → "We don't need this"
│   - Competition → "We use [competitor]"
│
├─→ Load Objection Framework (from campaign):
│   - Budget: "Our clients typically see ROI in 3 months..."
│   - Timing: "When would be a better time to reconnect?"
│
├─→ Personalize Response:
│   - Reference their specific situation
│   - Include relevant case study/stat
│
├─→ Self-Review: "Is this pushy? Is it respectful?"
│
└─→ Output: ObjectionResponse
        - response_text: "..."
        - suggested_follow_up_days: 14
        - confidence: 0.85
```

**Cost:** ~$0.16 AUD per objection (worst case)
**Optimized Cost:** ~$0.08 AUD per objection (template-augmented)

**Files Changed:**
- `src/agents/sdk_agents/objection_agent.py` (new)
- `src/engines/closer.py` (update to call SDK for complex objections)

---

### 5.5 Use Case 5: Voice Call Knowledge Base (Hot Leads Only)

**Trigger:** Voice call scheduled for Hot lead (ALS ≥ 85)

**Goal:** Generate personalized knowledge base for Vapi voice agent

**This is the most valuable SDK use case.** Traditional voice AI uses static scripts. SDK generates dynamic, personalized call prep.

**SDK Agent Workflow:**
```
Input: Lead enriched data + campaign context + ICP
│
├─→ Generate Pronunciation Guide:
│   - Name: "MAR-kus CHEN"
│   - Company: "GROW-stack"
│
├─→ Generate Opening Lines:
│   - Primary: "Congrats on the Series B, Marcus"
│   - Fallback: "I saw GrowthStack is hiring SDRs"
│
├─→ Generate Pain Point Discussion:
│   - "You mentioned on LinkedIn that leads are going cold..."
│   - Probe: "How quickly are your SDRs following up?"
│
├─→ Generate Objection Responses:
│   - Budget: "With your new funding, this is the perfect time..."
│   - Timing: "When are you planning to scale the team?"
│
├─→ Generate Don't Mention List:
│   - "Competitor X" (they're a partner)
│   - "2023 layoffs" (sensitive topic)
│
└─→ Output: VoiceKnowledgeBase (JSON for Vapi)
        - pronunciation: {...}
        - openers: [...]
        - pain_points: [...]
        - objection_handlers: {...}
        - dont_mention: [...]
```

**Cost:** ~$1.16 AUD per call (worst case)
**Optimized Cost:** ~$0.50 AUD per call (cached context, lighter prompts)

**Files Changed:**
- `src/agents/sdk_agents/voice_kb_agent.py` (new)
- `src/engines/voice.py` (update to call SDK before calls)

---

### 5.6 Use Case 6: ICP Extraction (Client Onboarding)

**Trigger:** New client onboarding — website URL submitted

**Goal:** Extract high-quality Ideal Customer Profile through intelligent research

**Why SDK for ICP?** The current ICP extraction has TWO waterfalls:

1. **Website Scraping Waterfall** (Apify):
   - Tier 0: URL Validation
   - Tier 1: Cheerio (static HTML)
   - Tier 2: Playwright (JS rendering)
   - Tier 3: Camoufox (future)
   - Tier 4: Manual fallback

2. **Portfolio Company Enrichment Waterfall** (Multi-source):
   - Tier 0: Claude inference (baseline)
   - Tier 1: Apollo domain/name search
   - Tier 1.5: LinkedIn scrape (fill gaps)
   - Tier 1.6: Clay enrichment (fill gaps)
   - Tier 2: LinkedIn via Google search
   - Tier 3: Google Business
   - Tier 4: General Google search

**Current limitation:** Claude analysis is single-turn. It can't search for additional context or self-correct its ICP analysis.

**SDK Agent Workflow:**
```
Input: Scraped website data + enriched portfolio companies
│
├─→ Tool: WebSearch("{company_name} target customers case studies")
│   └─→ Finds: Additional context about who the agency serves
│
├─→ Tool: WebFetch(industry_report_url)
│   └─→ Finds: Industry benchmarks for ICP sizing
│
├─→ Analyze: Portfolio companies, industries, company sizes
│
├─→ Self-Review: "Is this ICP specific enough? Do I have enough data?"
│   └─→ If confidence < 70%: Search for more context
│
├─→ Refine: Adjust industry weights, size ranges, pain points
│
└─→ Output: ICPProfile
        - target_industries: [{name, weight, reasoning}]
        - company_size_range: {min, max, sweet_spot}
        - target_titles: [priority-ranked]
        - pain_points: [specific, researched]
        - buying_signals: [actionable triggers]
        - confidence_score: 0.85
```

**Cost Comparison:**

| Component | Current | With SDK |
|-----------|---------|----------|
| Website scrape (Apify) | $0.05-0.20 | $0.05-0.20 |
| Portfolio enrichment (Apollo/Clay) | $0.03-0.10 | $0.03-0.10 |
| Claude analysis | $0.03 (1-turn) | $0.15-0.30 (multi-turn) |
| **Total** | **$0.10-0.30** | **$0.25-0.60** |

**Why the increase is worth it:**
- ICP is extracted ONCE per client (not per lead)
- Better ICP = better lead scoring = higher conversion
- Self-correction catches errors that would compound downstream
- Additional research fills gaps in portfolio data

**Cost:** ~$0.60 AUD per client onboarding (worst case)
**Optimized Cost:** ~$0.35 AUD per client (with caching + efficient prompts)

**Files Changed:**
- `src/agents/sdk_agents/icp_agent.py` (new)
- `src/engines/icp_scraper.py` (update to call SDK for analysis)
- `src/orchestration/flows/icp_extraction_flow.py` (integrate SDK agent)

---

## 6. Cost Optimization Strategies

### 6.1 Overview: From Worst Case to Optimized

| Use Case | Worst Case | Optimized | Savings |
|----------|------------|-----------|---------|
| Deep Enrichment | $0.78/lead | $0.40/lead | 49% |
| Email Writing | $0.16/email | $0.05/email | 69% |
| Classification | $0.08/reply | $0.01/reply | 88% |
| Objection Handling | $0.16/objection | $0.08/objection | 50% |
| Voice KB | $1.16/call | $0.50/call | 57% |
| **ICP Extraction** | $0.60/client | $0.35/client | 42% |

**Total SDK cost reduction: ~55% with optimizations**

**Note on ICP Extraction:** Unlike other use cases, ICP runs ONCE per client onboarding (not per lead). The $0.35-0.60 cost is amortized across all leads for that client.

### 6.2 Strategy 1: Prompt Caching (50-90% savings)

**What it is:** Store frequently-used context in Anthropic's cache for reuse across requests.

**How to apply:**

```python
# Without caching: Full context sent every time
messages = [
    {"role": "system", "content": FULL_ICP_CONTEXT},  # 5000 tokens
    {"role": "user", "content": lead_data}             # 500 tokens
]
# Cost: 5500 input tokens × $3/MTok = $0.0165 per lead

# With caching: Context cached, only lead data sent
# First request caches the ICP context
# Subsequent requests reuse cache
# Cost: 500 input tokens × $3/MTok + cache read fee = ~$0.002 per lead
```

**Where to apply:**
- ICP context (same for all leads in campaign)
- Industry research (reuse across leads in same industry)
- Company context (reuse across multiple contacts at same company)

**Implementation:**
```python
# src/agents/sdk_agents/base_sdk_agent.py

async def create_cached_context(self, campaign_id: UUID) -> str:
    """Create or retrieve cached context for campaign."""
    cache_key = f"sdk_context:{campaign_id}"

    # Check Redis for cached context ID
    cached = await self.redis.get(cache_key)
    if cached:
        return cached

    # Generate context and cache
    context = await self._build_campaign_context(campaign_id)
    # Use Anthropic's beta caching API
    # Context automatically cached for 5 min
    return context
```

### 6.3 Strategy 2: Model Routing (70-90% savings on simple tasks)

**What it is:** Use cheaper models (Haiku) for simple tasks, expensive models (Sonnet) for complex tasks.

**Model pricing comparison:**

| Model | Input $/MTok | Output $/MTok | Best For |
|-------|--------------|---------------|----------|
| Haiku 3.5 | $0.80 | $4.00 | Classification, simple Q&A |
| Sonnet 3.5 | $3.00 | $15.00 | Complex reasoning, writing |
| Opus 4.5 | $5.00 | $25.00 | Most complex tasks (rarely needed) |

**Routing rules:**

```python
# src/agents/sdk_agents/base_sdk_agent.py

def select_model(self, task_type: str) -> str:
    """Select model based on task complexity."""
    HAIKU_TASKS = [
        "intent_classification",
        "sentiment_analysis",
        "simple_qa",
        "template_selection",
    ]
    SONNET_TASKS = [
        "email_writing",
        "objection_handling",
        "research_synthesis",
        "voice_kb_generation",
    ]

    if task_type in HAIKU_TASKS:
        return "claude-3-5-haiku-20241022"
    elif task_type in SONNET_TASKS:
        return "claude-sonnet-4-20250514"
    else:
        return "claude-sonnet-4-20250514"  # Default to Sonnet
```

### 6.4 Strategy 3: Batch Processing (50% savings)

**What it is:** Send multiple requests together instead of one-by-one.

**When to use:**
- Processing multiple leads at once (enrichment batch)
- Classifying multiple replies at once
- NOT for real-time responses (too slow)

**Implementation:**
```python
# src/orchestration/tasks/enrichment_tasks.py

@task(name="batch_classify_replies")
async def batch_classify_replies(reply_ids: list[UUID]) -> list[dict]:
    """Classify multiple replies in one batch request."""
    # Anthropic Batch API: 50% discount, 24-hour turnaround
    batch_request = {
        "custom_id": f"batch_{datetime.now().isoformat()}",
        "requests": [
            {"reply_id": rid, "text": get_reply_text(rid)}
            for rid in reply_ids
        ]
    }
    # Submit batch and poll for results
    # Costs 50% less than real-time
```

### 6.5 Strategy 4: Template Augmentation (40-60% savings)

**What it is:** Use pre-written templates as a starting point, let AI personalize specific sections.

**Without augmentation:**
```
Prompt: "Write a cold email to Marcus Chen at GrowthStack about our lead management solution."
Output: Full 150-word email generated from scratch
Cost: ~$0.015 per email
```

**With augmentation:**
```
Prompt: "Fill in the [BRACKETS] in this template:

Hi [FIRST_NAME],

[PERSONALIZED_OPENER - 1 sentence referencing their recent news/posts]

I help [INDUSTRY] companies like [COMPANY] solve [PAIN_POINT].

[SPECIFIC_VALUE_PROP - 1 sentence with relevant stat]

Worth a quick chat?

[SIGN_OFF]"

Output: Only the bracketed sections generated
Cost: ~$0.005 per email
```

**Implementation:**
```python
# src/agents/sdk_agents/email_agent.py

AUGMENTATION_TEMPLATE = """
Hi {first_name},

[HOOK: Write 1 sentence referencing: {research_context}]

I help {industry} companies like {company} {value_prop}.

[PROOF: Add 1 relevant stat or case study for {industry}]

Worth a quick chat this week?

Best,
{sender_name}
"""

async def generate_personalized_email(self, lead: Lead, research: dict):
    """Generate email using template augmentation."""
    template = AUGMENTATION_TEMPLATE.format(
        first_name=lead.first_name,
        company=lead.company,
        industry=lead.organization_industry,
        value_prop=self.campaign.value_prop,
        sender_name=self.sender.name,
        research_context=research.get("personalization_hooks", [])
    )

    # Only generate the [BRACKETED] sections
    return await self.sdk_brain.complete(
        prompt=f"Fill in only the [BRACKETED] sections:\n\n{template}",
        max_tokens=200,  # Much smaller than full email
    )
```

### 6.6 Strategy 5: Selective Usage (30-50% savings)

**What it is:** Only use SDK Brain for leads most likely to convert.

**Current plan:** SDK Brain for all Hot leads (ALS ≥ 85)

**Optimized plan:** SDK Brain for top 50% of Hot leads (highest-intent signals)

**Selection criteria:**
```python
def should_use_sdk_brain(lead: Lead) -> bool:
    """Determine if lead qualifies for SDK Brain treatment."""
    # Must be Hot (ALS 85+)
    if lead.als_score < 85:
        return False

    # Priority signals (use SDK for any of these):
    priority_signals = [
        lead.recent_funding,           # Recent funding round
        lead.hiring_count > 3,         # Actively hiring
        lead.tech_stack_match > 0.8,   # Strong tech fit
        lead.engagement_score > 70,    # LinkedIn engagement
        lead.referral_source,          # Came from referral
    ]

    return any(priority_signals)
```

**Impact:**
- Cuts SDK usage by ~50% while keeping highest-value leads
- Focuses budget on leads with strongest buying signals

### 6.7 Cost Control: Daily and Per-Call Limits

**Existing system:** `src/integrations/anthropic.py` has daily spend limit via Redis.

**SDK enhancement:** Add per-call limits.

```python
# src/agents/sdk_agents/base_sdk_agent.py

class SDKBrainConfig:
    """Configuration for SDK Brain cost control."""

    # Per-call limits (AUD)
    MAX_COST_ENRICHMENT = 1.50      # Single enrichment
    MAX_COST_EMAIL = 0.50           # Single email
    MAX_COST_VOICE_KB = 2.00        # Single voice KB
    MAX_COST_OBJECTION = 0.50       # Single objection

    # Daily limits (AUD) - per client
    DAILY_LIMIT_IGNITION = 50.00
    DAILY_LIMIT_VELOCITY = 100.00
    DAILY_LIMIT_DOMINANCE = 200.00

    # Turn limits (prevent runaway loops)
    MAX_TURNS_ENRICHMENT = 10
    MAX_TURNS_EMAIL = 5
    MAX_TURNS_VOICE_KB = 15
    MAX_TURNS_OBJECTION = 5
```

---

## 7. Implementation Architecture

### 7.1 New Files to Create

```
src/
├── agents/
│   └── sdk_agents/                    ← NEW DIRECTORY
│       ├── __init__.py
│       ├── base_sdk_agent.py          ← SDK wrapper with cost control
│       ├── sdk_config.py              ← Configuration and limits
│       ├── sdk_tools.py               ← Tool definitions for SDK
│       ├── enrichment_agent.py        ← Hot lead deep research
│       ├── email_agent.py             ← Personalized email writing
│       ├── voice_kb_agent.py          ← Voice call knowledge base
│       └── objection_agent.py         ← Objection handling
│
├── integrations/
│   └── sdk_brain.py                   ← NEW: Core SDK client wrapper
│
└── models/
    └── sdk_models.py                  ← NEW: Pydantic models for SDK I/O
```

### 7.2 Files to Modify

```
src/
├── engines/
│   ├── scout.py                       ← Add SDK enrichment for Hot leads
│   ├── content.py                     ← Add SDK email for Hot leads
│   ├── closer.py                      ← Add SDK for complex objections
│   └── voice.py                       ← Add SDK for voice KB
│
├── orchestration/
│   └── flows/
│       ├── enrichment_flow.py         ← Route Hot leads to SDK
│       └── outreach_flow.py           ← Route Hot leads to SDK
│
└── config/
    └── settings.py                    ← Add SDK configuration
```

### 7.3 Database Changes

**New table:** `sdk_usage_log`

```sql
CREATE TABLE sdk_usage_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID REFERENCES clients(id),
    lead_id UUID REFERENCES leads(id),
    agent_type VARCHAR(50) NOT NULL,  -- enrichment, email, voice_kb, objection
    model_used VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    turns INTEGER NOT NULL,
    cost_aud DECIMAL(10, 4) NOT NULL,
    cached_tokens INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sdk_usage_client ON sdk_usage_log(client_id, created_at);
CREATE INDEX idx_sdk_usage_lead ON sdk_usage_log(lead_id);
```

### 7.4 Configuration Settings

**Add to `src/config/settings.py`:**

```python
# SDK Brain Configuration
sdk_brain_enabled: bool = Field(default=False, description="Enable SDK Brain for Hot leads")
sdk_brain_model: str = Field(default="claude-sonnet-4-20250514", description="Default SDK model")
sdk_brain_max_turns: int = Field(default=10, description="Max turns per SDK call")

# SDK Cost Limits (AUD)
sdk_daily_limit_ignition: float = Field(default=50.0)
sdk_daily_limit_velocity: float = Field(default=100.0)
sdk_daily_limit_dominance: float = Field(default=200.0)

# SDK Feature Flags
sdk_enrichment_enabled: bool = Field(default=True)
sdk_email_enabled: bool = Field(default=True)
sdk_voice_kb_enabled: bool = Field(default=True)
sdk_objection_enabled: bool = Field(default=True)

# Minimum ALS for SDK (default: Hot leads only)
sdk_min_als_score: int = Field(default=85)
```

---

## 8. Step-by-Step Integration Guide

### Phase 1: Foundation (Week 1)

**Goal:** Create SDK wrapper and base infrastructure

**Tasks:**

1. **Install Claude SDK**
   ```bash
   pip install anthropic[sdk]
   ```
   Add to `requirements.txt`

2. **Create `src/integrations/sdk_brain.py`**
   - Wrapper around Claude SDK
   - Cost tracking integration with existing Redis tracker
   - Per-call and daily limits

3. **Create `src/agents/sdk_agents/base_sdk_agent.py`**
   - Base class for all SDK agents
   - Tool registration
   - Output schema enforcement
   - Error handling

4. **Create `src/agents/sdk_agents/sdk_tools.py`**
   - Define tools: WebSearch, WebFetch, DatabaseQuery
   - Tool execution wrappers

5. **Add database migration for `sdk_usage_log`**

6. **Update `src/config/settings.py`** with SDK configuration

**Deliverables:**
- [ ] SDK wrapper working in isolation
- [ ] Cost tracking integrated
- [ ] Base agent class created
- [ ] Tools defined and testable

---

### Phase 2: Enrichment Agent (Week 2)

**Goal:** Deep research for Hot leads

**Tasks:**

1. **Create `src/agents/sdk_agents/enrichment_agent.py`**
   - Input: Lead basic data
   - Tools: WebSearch, WebFetch
   - Output: EnrichmentResult schema

2. **Update `src/engines/scout.py`**
   - Add ALS check before enrichment
   - Route Hot leads (ALS ≥ 85) to SDK agent
   - Keep existing flow for Cold/Cool/Warm leads

3. **Update `src/orchestration/flows/enrichment_flow.py`**
   - Add SDK enrichment task
   - Track SDK usage in flow metadata

4. **Create tests**
   - Unit test for enrichment agent
   - Integration test with mock tools
   - E2E test with real API (TEST_MODE)

**Deliverables:**
- [ ] Enrichment agent working
- [ ] Scout engine routes correctly
- [ ] Tests passing
- [ ] Cost tracking verified

---

### Phase 3: Email Agent (Week 3)

**Goal:** Personalized emails for Hot leads

**Tasks:**

1. **Create `src/agents/sdk_agents/email_agent.py`**
   - Input: Lead data + enrichment result + campaign
   - Output: PersonalizedEmail schema

2. **Update `src/engines/content.py`**
   - Add ALS check before email generation
   - Route Hot leads to SDK agent
   - Use template augmentation for cost efficiency

3. **Update `src/orchestration/flows/outreach_flow.py`**
   - Add SDK email task for Hot leads

4. **Create tests**

**Deliverables:**
- [ ] Email agent working
- [ ] Template augmentation implemented
- [ ] Tests passing

---

### Phase 4: Voice KB Agent (Week 4)

**Goal:** Personalized call preparation for Hot leads

**Tasks:**

1. **Create `src/agents/sdk_agents/voice_kb_agent.py`**
   - Input: Lead enriched data + campaign
   - Output: VoiceKnowledgeBase (JSON for Vapi)

2. **Update `src/engines/voice.py`**
   - Generate KB before scheduling call
   - Pass KB to Vapi assistant config

3. **Update Vapi integration**
   - Accept dynamic knowledge base
   - Include pronunciation guide in assistant

4. **Create tests**

**Deliverables:**
- [ ] Voice KB agent working
- [ ] Vapi integration updated
- [ ] Tests passing

---

### Phase 5: Objection Agent (Week 5)

**Goal:** Smart objection handling

**Tasks:**

1. **Create `src/agents/sdk_agents/objection_agent.py`**
   - Input: Objection text + lead + thread context
   - Output: ObjectionResponse schema

2. **Update `src/engines/closer.py`**
   - Detect objection type from classification
   - Route complex objections to SDK agent
   - Keep simple template responses for common objections

3. **Create tests**

**Deliverables:**
- [ ] Objection agent working
- [ ] Closer engine routes correctly
- [ ] Tests passing

---

### Phase 6: Optimization (Week 6)

**Goal:** Implement all cost optimizations

**Tasks:**

1. **Implement prompt caching**
   - Cache ICP context per campaign
   - Cache industry context
   - Cache company context for multi-contact accounts

2. **Implement model routing**
   - Add task-type detection
   - Route simple tasks to Haiku
   - Route complex tasks to Sonnet

3. **Implement batch processing**
   - Batch classification requests
   - Add background batch job

4. **Implement selective usage**
   - Add intent signal scoring
   - Only use SDK for top 50% of Hot leads

5. **Verify cost reduction**
   - Compare actual vs projected costs
   - Adjust limits if needed

**Deliverables:**
- [ ] All optimizations implemented
- [ ] Cost tracking verified
- [ ] Target margins achieved

---

## 9. File Changes Required

### 9.1 New Files (14 files)

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `src/integrations/sdk_brain.py` | Core SDK wrapper | 300 |
| `src/agents/sdk_agents/__init__.py` | Package init | 20 |
| `src/agents/sdk_agents/base_sdk_agent.py` | Base class | 400 |
| `src/agents/sdk_agents/sdk_config.py` | Configuration | 100 |
| `src/agents/sdk_agents/sdk_tools.py` | Tool definitions | 250 |
| `src/agents/sdk_agents/enrichment_agent.py` | Deep research | 350 |
| `src/agents/sdk_agents/email_agent.py` | Email writing | 300 |
| `src/agents/sdk_agents/voice_kb_agent.py` | Voice KB | 400 |
| `src/agents/sdk_agents/objection_agent.py` | Objection handling | 300 |
| `src/models/sdk_models.py` | I/O schemas | 200 |
| `migrations/xxx_add_sdk_usage_log.sql` | Database table | 30 |
| `tests/agents/sdk_agents/test_enrichment.py` | Tests | 200 |
| `tests/agents/sdk_agents/test_email.py` | Tests | 150 |
| `tests/agents/sdk_agents/test_voice_kb.py` | Tests | 150 |

**Total new code:** ~3,150 lines

### 9.2 Modified Files (8 files)

| File | Changes | Lines Changed (est.) |
|------|---------|---------------------|
| `src/config/settings.py` | Add SDK config | +30 |
| `src/engines/scout.py` | Add SDK routing | +50 |
| `src/engines/content.py` | Add SDK routing | +40 |
| `src/engines/closer.py` | Add SDK routing | +40 |
| `src/engines/voice.py` | Add SDK KB integration | +60 |
| `src/orchestration/flows/enrichment_flow.py` | Add SDK task | +30 |
| `src/orchestration/flows/outreach_flow.py` | Add SDK task | +30 |
| `requirements.txt` | Add SDK dependency | +1 |

**Total modifications:** ~280 lines

---

## 10. Testing & Validation

### 10.1 Unit Tests

Each SDK agent requires:

```python
# tests/agents/sdk_agents/test_enrichment.py

class TestEnrichmentAgent:
    """Unit tests for SDK Enrichment Agent."""

    async def test_enrichment_basic(self, mock_sdk_brain):
        """Test basic enrichment with mocked tools."""
        agent = EnrichmentAgent()
        result = await agent.enrich(
            lead_data=SAMPLE_LEAD,
            tools=mock_sdk_brain.tools,
        )
        assert result.success
        assert result.pain_points
        assert result.cost_aud < 2.0

    async def test_enrichment_cost_limit(self, mock_sdk_brain):
        """Test that cost limit is enforced."""
        agent = EnrichmentAgent(max_cost=0.01)
        result = await agent.enrich(lead_data=SAMPLE_LEAD)
        assert not result.success
        assert "cost limit" in result.error.lower()

    async def test_enrichment_turn_limit(self, mock_sdk_brain):
        """Test that turn limit is enforced."""
        agent = EnrichmentAgent(max_turns=1)
        result = await agent.enrich(lead_data=SAMPLE_LEAD)
        # Should complete but with limited research
        assert result.turns_used == 1
```

### 10.2 Integration Tests

```python
# tests/integration/test_sdk_flow.py

class TestSDKEnrichmentFlow:
    """Integration tests for SDK in Prefect flows."""

    async def test_hot_lead_gets_sdk_enrichment(self, test_client, test_db):
        """Test that Hot leads are routed to SDK."""
        # Create Hot lead (ALS 90)
        lead = await create_test_lead(als_score=90)

        # Run enrichment flow
        await enrichment_flow(lead_ids=[lead.id])

        # Verify SDK was used
        usage = await get_sdk_usage(lead_id=lead.id)
        assert usage is not None
        assert usage.agent_type == "enrichment"

    async def test_cold_lead_skips_sdk(self, test_client, test_db):
        """Test that Cold leads don't use SDK."""
        # Create Cold lead (ALS 30)
        lead = await create_test_lead(als_score=30)

        # Run enrichment flow
        await enrichment_flow(lead_ids=[lead.id])

        # Verify SDK was NOT used
        usage = await get_sdk_usage(lead_id=lead.id)
        assert usage is None
```

### 10.3 E2E Tests

```python
# tests/e2e/test_sdk_e2e.py

class TestSDKE2E:
    """E2E tests with real API calls (TEST_MODE)."""

    @pytest.mark.skipif(not TEST_MODE, reason="Requires TEST_MODE")
    async def test_full_sdk_enrichment_real_api(self):
        """Test SDK enrichment with real Claude API."""
        agent = EnrichmentAgent()
        result = await agent.enrich(
            lead_data={
                "first_name": "David",
                "last_name": "Stephens",
                "company": "Agency OS",
                "linkedin_url": "https://linkedin.com/in/davidstephens",
            }
        )

        # Verify real results
        assert result.success
        assert len(result.pain_points) > 0
        assert result.cost_aud < 2.0

        # Log actual cost for tracking
        print(f"Actual cost: ${result.cost_aud:.4f} AUD")
```

### 10.4 Cost Validation

```python
# tests/cost/test_sdk_costs.py

class TestSDKCosts:
    """Validate SDK costs match projections."""

    async def test_enrichment_cost_within_budget(self):
        """Test enrichment cost stays within projected range."""
        costs = []
        for _ in range(10):
            result = await run_test_enrichment()
            costs.append(result.cost_aud)

        avg_cost = sum(costs) / len(costs)
        max_projected = 0.78  # Worst case
        optimized_projected = 0.40  # Optimized

        assert avg_cost < max_projected, f"Avg cost ${avg_cost} exceeds max ${max_projected}"
        print(f"Average enrichment cost: ${avg_cost:.4f} AUD")
        print(f"vs Optimized target: ${optimized_projected:.4f} AUD")
```

---

## 11. Rollout Plan

### 11.1 Phase 1: Internal Testing (Week 1-2)

**Environment:** Development / Staging

**Scope:**
- SDK enabled for test accounts only
- All 4 agents functional
- Cost tracking verified

**Success Criteria:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Costs within 20% of projections
- [ ] No errors in Sentry

### 11.2 Phase 2: Limited Pilot (Week 3-4)

**Environment:** Production

**Scope:**
- SDK enabled for 3-5 pilot clients (Velocity tier)
- Monitor costs daily
- Gather feedback on output quality

**Success Criteria:**
- [ ] No budget overruns
- [ ] Email reply rate improves (vs control)
- [ ] No customer complaints about AI quality
- [ ] Margin stays above 50%

### 11.3 Phase 3: Velocity Tier Rollout (Week 5-6)

**Environment:** Production

**Scope:**
- SDK enabled for all Velocity tier clients
- Full cost optimization implemented

**Success Criteria:**
- [ ] Margin stays above 55%
- [ ] Meeting guarantee confidence improved
- [ ] Cost per meeting reduced or stable

### 11.4 Phase 4: Full Rollout (Week 7-8)

**Environment:** Production

**Scope:**
- SDK enabled for all tiers
- Ignition: Lower daily limits
- Dominance: Higher daily limits

**Success Criteria:**
- [ ] All tiers profitable
- [ ] Dominance margin above 40%
- [ ] Customer satisfaction maintained

### 11.5 Kill Switch

If costs exceed projections by >30% or margins drop below 35%:

```python
# Immediate disable via settings
SDK_BRAIN_ENABLED=false

# Or per-client disable
UPDATE clients SET sdk_brain_enabled = false WHERE id = 'xxx';
```

---

## 12. Appendix: Code Examples

### 12.1 SDK Brain Wrapper

```python
# src/integrations/sdk_brain.py

"""
Contract: src/integrations/sdk_brain.py
Purpose: Claude Agent SDK wrapper with cost control
Layer: 2 - integrations
Imports: models ONLY
Consumers: sdk_agents
"""

from typing import Any, Callable
from uuid import UUID

import anthropic
from anthropic import Anthropic
from pydantic import BaseModel

from src.config.settings import settings
from src.exceptions import AISpendLimitError
from src.integrations.redis import ai_spend_tracker


class SDKBrainConfig(BaseModel):
    """Configuration for SDK Brain."""
    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 10
    max_cost_aud: float = 2.0
    enable_caching: bool = True


class SDKBrain:
    """
    Claude Agent SDK wrapper with cost control.

    Provides:
    - Tool execution with cost tracking
    - Per-call and daily spend limits
    - Automatic prompt caching
    - Structured output enforcement
    """

    # Pricing (AUD, as of Jan 2026)
    PRICING = {
        "claude-sonnet-4-20250514": {"input": 4.65, "output": 23.25},  # $3/$15 USD × 1.55
        "claude-3-5-haiku-20241022": {"input": 1.24, "output": 6.20},  # $0.80/$4 USD × 1.55
    }

    def __init__(self, config: SDKBrainConfig | None = None):
        self.config = config or SDKBrainConfig()
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self._total_cost = 0.0
        self._turns = 0

    async def run(
        self,
        prompt: str,
        tools: list[dict],
        output_schema: type[BaseModel],
        system: str | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """
        Run SDK agent with tools until completion or limit.

        Args:
            prompt: User prompt / goal
            tools: List of tool definitions
            output_schema: Pydantic model for structured output
            system: System prompt
            context: Additional context for caching

        Returns:
            Dict with result, cost, turns used

        Raises:
            AISpendLimitError: If cost limit exceeded
        """
        # Check daily budget
        remaining = await ai_spend_tracker.get_remaining()
        if remaining < 0.10:
            raise AISpendLimitError(
                spent=settings.anthropic_daily_spend_limit - remaining,
                limit=settings.anthropic_daily_spend_limit,
                message="Daily AI budget exhausted"
            )

        messages = [{"role": "user", "content": prompt}]

        while self._turns < self.config.max_turns:
            self._turns += 1

            # Make API call
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,
                system=system or "",
                messages=messages,
                tools=tools,
            )

            # Track cost
            cost = self._calculate_cost(response.usage)
            self._total_cost += cost
            await ai_spend_tracker.add_spend(cost)

            # Check per-call limit
            if self._total_cost > self.config.max_cost_aud:
                return {
                    "success": False,
                    "error": f"Cost limit exceeded: ${self._total_cost:.2f}",
                    "cost_aud": self._total_cost,
                    "turns": self._turns,
                }

            # Check for tool use
            if response.stop_reason == "tool_use":
                # Execute tools and continue
                tool_results = await self._execute_tools(response.content)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            # Check for completion
            if response.stop_reason == "end_turn":
                # Parse output
                try:
                    result = self._parse_output(response.content, output_schema)
                    return {
                        "success": True,
                        "data": result,
                        "cost_aud": self._total_cost,
                        "turns": self._turns,
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Output parsing failed: {e}",
                        "cost_aud": self._total_cost,
                        "turns": self._turns,
                    }

        # Turn limit reached
        return {
            "success": False,
            "error": f"Turn limit reached: {self.config.max_turns}",
            "cost_aud": self._total_cost,
            "turns": self._turns,
        }

    def _calculate_cost(self, usage) -> float:
        """Calculate cost from API usage."""
        pricing = self.PRICING.get(self.config.model, self.PRICING["claude-sonnet-4-20250514"])
        input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    async def _execute_tools(self, content: list) -> list:
        """Execute tool calls and return results."""
        results = []
        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                # Execute tool (implementations in sdk_tools.py)
                result = await self._run_tool(tool_name, tool_input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        return results

    async def _run_tool(self, name: str, input: dict) -> str:
        """Run a specific tool."""
        from src.agents.sdk_agents.sdk_tools import TOOL_REGISTRY

        if name not in TOOL_REGISTRY:
            return f"Error: Unknown tool {name}"

        tool_fn = TOOL_REGISTRY[name]
        return await tool_fn(**input)

    def _parse_output(self, content: list, schema: type[BaseModel]) -> BaseModel:
        """Parse response into structured output."""
        for block in content:
            if hasattr(block, "text"):
                # Try to parse as JSON matching schema
                import json
                data = json.loads(block.text)
                return schema(**data)
        raise ValueError("No parseable output found")
```

### 12.2 Enrichment Agent

```python
# src/agents/sdk_agents/enrichment_agent.py

"""
Contract: src/agents/sdk_agents/enrichment_agent.py
Purpose: Deep research agent for Hot Lead enrichment
Layer: Agents (uses integrations)
Consumers: scout.py engine
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.agents.sdk_agents.base_sdk_agent import BaseSDKAgent
from src.agents.sdk_agents.sdk_tools import WEB_SEARCH_TOOL, WEB_FETCH_TOOL
from src.integrations.sdk_brain import SDKBrain, SDKBrainConfig


class EnrichmentInput(BaseModel):
    """Input for enrichment agent."""
    first_name: str
    last_name: str
    company: str
    title: str | None = None
    linkedin_url: str | None = None
    company_website: str | None = None
    industry: str | None = None


class EnrichmentOutput(BaseModel):
    """Output from enrichment agent."""
    pain_points: list[str] = Field(default_factory=list)
    recent_news: list[str] = Field(default_factory=list)
    hiring_signals: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    personalization_hooks: list[str] = Field(default_factory=list)
    company_summary: str = ""
    confidence: float = 0.0


class EnrichmentAgent(BaseSDKAgent):
    """
    SDK Agent for deep lead enrichment.

    Used for Hot leads (ALS >= 85) to gather rich context
    beyond what Apollo/Clay provide.

    Tools available:
    - web_search: Search for company news, funding, etc.
    - web_fetch: Fetch specific pages (careers, about, LinkedIn)

    Cost target: $0.40-0.78 AUD per lead
    """

    SYSTEM_PROMPT = """You are a sales research assistant. Your goal is to gather actionable intelligence about a prospect that can be used for personalized outreach.

Focus on finding:
1. **Pain points**: What challenges is the company facing? Look for hiring posts (scaling pain), news (pivots, challenges), CEO quotes.
2. **Recent news**: Funding rounds, product launches, awards, executive changes.
3. **Hiring signals**: What roles are they hiring for? This indicates priorities and budget.
4. **Personalization hooks**: Specific, recent things you can reference in outreach.

DO NOT:
- Make up information
- Include generic industry facts
- Return anything you can't verify from a source

When you have enough information (3+ pain points OR 2+ strong hooks), stop and return results."""

    def __init__(self, max_cost: float = 1.50, max_turns: int = 10):
        self.config = SDKBrainConfig(
            model="claude-sonnet-4-20250514",
            max_turns=max_turns,
            max_cost_aud=max_cost,
        )
        self.sdk = SDKBrain(config=self.config)
        self.tools = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL]

    async def enrich(self, input: EnrichmentInput) -> dict[str, Any]:
        """
        Perform deep research on a lead.

        Args:
            input: Lead basic data

        Returns:
            EnrichmentOutput with research findings
        """
        prompt = f"""Research this prospect and find personalization opportunities:

**Prospect:**
- Name: {input.first_name} {input.last_name}
- Company: {input.company}
- Title: {input.title or 'Unknown'}
- Industry: {input.industry or 'Unknown'}
- LinkedIn: {input.linkedin_url or 'Not provided'}
- Website: {input.company_website or f'https://{input.company.lower().replace(" ", "")}.com'}

**Your task:**
1. Search for recent news about {input.company}
2. Check their careers page for hiring signals
3. Find any interviews, podcasts, or posts from leadership
4. Identify 3+ pain points or personalization hooks

Return your findings as JSON matching this schema:
{EnrichmentOutput.model_json_schema()}"""

        result = await self.sdk.run(
            prompt=prompt,
            tools=self.tools,
            output_schema=EnrichmentOutput,
            system=self.SYSTEM_PROMPT,
        )

        return result
```

### 12.3 Tool Definitions

```python
# src/agents/sdk_agents/sdk_tools.py

"""
Contract: src/agents/sdk_agents/sdk_tools.py
Purpose: Tool definitions for SDK agents
Layer: Agents
"""

from typing import Any

import httpx

from src.integrations.serper import get_serper_client


# Tool definitions for Claude SDK
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for information. Use for finding news, company info, etc.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results (1-10)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}

WEB_FETCH_TOOL = {
    "name": "web_fetch",
    "description": "Fetch the content of a specific webpage. Use for reading careers pages, about pages, etc.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            }
        },
        "required": ["url"]
    }
}


# Tool implementations
async def web_search(query: str, num_results: int = 5) -> str:
    """Execute web search using Serper API."""
    try:
        client = get_serper_client()
        results = await client.search(query, num_results=num_results)

        # Format results for Claude
        formatted = []
        for r in results.get("organic", [])[:num_results]:
            formatted.append(f"**{r.get('title', 'No title')}**\n{r.get('snippet', '')}\nURL: {r.get('link', '')}\n")

        return "\n---\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Search error: {str(e)}"


async def web_fetch(url: str) -> str:
    """Fetch webpage content."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            # Simple HTML to text (could use better parser)
            from html import unescape
            import re

            text = response.text
            # Remove scripts and styles
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            # Remove tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text)
            text = unescape(text)

            # Truncate to avoid token limits
            return text[:8000]
    except Exception as e:
        return f"Fetch error: {str(e)}"


# Registry for tool execution
TOOL_REGISTRY = {
    "web_search": web_search,
    "web_fetch": web_fetch,
}
```

---

## Summary

This document provides everything needed to integrate Claude Agent SDK into Agency OS:

1. **Understanding**: What SDK is and why it matters
2. **Philosophy**: Deterministic + Intelligent hybrid approach
3. **Use Cases**: 5 specific applications with cost estimates
4. **Optimization**: 5 strategies to reduce costs by ~55%
5. **Architecture**: New files and modifications needed
6. **Implementation**: Week-by-week guide
7. **Testing**: Unit, integration, E2E, and cost validation
8. **Rollout**: Phased approach with kill switch
9. **Code**: Working examples for all major components

**Expected outcome:**
- 7-15% margin reduction (from current 64% to 50-57%)
- 50% improvement in meeting booking confidence
- 19% reduction in cost per meeting (with 50% meeting uplift)
- Defensible competitive moat through personalization quality

**Next step:** CEO approval to proceed with Phase 1 (Foundation).
