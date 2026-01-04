# Campaign Generation Skills Specification

**Document Type:** Technical Specification  
**Status:** PENDING BUILD  
**Created:** December 25, 2024  
**Priority:** High - Required for campaign automation  

---

## Executive Summary

The ICP Discovery system is **complete** (8 skills + agent + engine). It extracts WHO to target.

What's missing is the **Campaign Generation layer** that transforms ICP data into actual campaign messaging and sequences.

This document specifies 4 new skills to bridge that gap.

---

## Build Strategy: Phased Approach

### Phase 12A: Core Campaign Generation (PRIORITY)
Build without web search dependency. Launch faster.

| Skill | Purpose | Effort |
|-------|---------|--------|
| SequenceBuilderSkill | Build touch sequence | 4 hrs |
| MessagingGeneratorSkill | Generate copy from ICP | 6 hrs |
| CampaignSplitterSkill | Multi-industry handling | 3 hrs |
| CampaignGenerationAgent | Orchestrate skills | 4 hrs |
| **Total** | | **17 hrs** |

### Phase 12B: Web Search Enhancement (LATER)
Add when needed for weak ICP data.

| Skill | Purpose | Effort |
|-------|---------|--------|
| IndustryResearcherSkill | Web search enhancement | 5 hrs |
| Serper API integration | Web search provider | 2 hrs |
| **Total** | | **7 hrs** |

### When to Use Each Phase

**Phase 12A works well when:**
- Agency has 5+ portfolio clients
- Clear industry focus
- Pain points derived from actual client patterns
- ICP confidence >= 0.6

**Phase 12B needed when:**
- New agency, no portfolio
- Weak website content  
- Generalist agency entering new niche
- ICP confidence < 0.6
- User explicitly requests deeper research

### Recommended Web Search API: Serper

**Why Serper:**
- Cost: $0.01/search (vs Tavily $0.08)
- Google's index (most comprehensive)
- Simple JSON API
- Fast (sub-second)
- We scrape full content with Apify anyway

**Cost projection:** ~$6/month at 200 new clients

---

## Current State: What We Have

### ICP Discovery System (✅ Complete)

```
src/agents/
├── icp_discovery_agent.py          # ✅ Orchestrates ICP extraction
├── skills/
│   ├── base_skill.py               # ✅ Base class + registry
│   ├── website_parser.py           # ✅ Parse HTML → structured pages
│   ├── service_extractor.py        # ✅ Extract services offered
│   ├── value_prop_extractor.py     # ✅ Extract value proposition
│   ├── portfolio_extractor.py      # ✅ Find client logos/cases
│   ├── industry_classifier.py      # ✅ Classify target industries
│   ├── company_size_estimator.py   # ✅ Estimate team size
│   ├── icp_deriver.py              # ✅ Derive ICP from portfolio
│   └── als_weight_suggester.py     # ✅ Suggest ALS weights

src/engines/
└── icp_scraper.py                  # ✅ Apify + Apollo data fetching
```

### ICPProfile Output (Already Generated)

```python
class ICPProfile:
    # Agency info
    company_name: str
    website_url: str
    services_offered: list[str]
    value_proposition: str
    differentiators: list[str]
    
    # Portfolio
    portfolio_companies: list[str]
    notable_brands: list[str]
    
    # Target ICP (ALREADY DERIVED)
    icp_industries: list[str]        # ["healthcare", "saas"]
    icp_company_sizes: list[str]     # ["11-50", "51-200"]
    icp_revenue_ranges: list[str]    # ["$1M-$10M"]
    icp_locations: list[str]         # ["Australia"]
    icp_titles: list[str]            # ["CEO", "CMO", "Marketing Director"]
    icp_pain_points: list[str]       # ALREADY EXISTS
    icp_signals: list[str]           # ["Recently funded", "Hiring"]
    
    # Scoring
    als_weights: dict[str, int]
    
    # Metadata
    pattern_description: str         # "Growth-stage B2B SaaS..."
    confidence: float                # 0.85
```

---

## The Gap: ICP → Campaign

| Have (ICP) | Missing (Campaign) |
|------------|-------------------|
| `icp_industries: ["healthcare"]` | Industry-specific **messaging** |
| `icp_pain_points: ["inconsistent leads"]` | **Email copy** using those pain points |
| `icp_titles: ["Practice Owner"]` | **Sequence** of touches |
| `icp_signals: ["hiring"]` | **Channel-specific** content |

---

## New Skills Required

### Architecture

```
ICPProfile (from ICP Discovery)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CAMPAIGN GENERATION AGENT                       │
│                  (NEW - To Be Built)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Skill 1: IndustryResearcherSkill (OPTIONAL - enhancement)       │
│           └── Only if ICP pain_points weak/generic               │
│           └── Web search for industry-specific intelligence      │
│                                                                  │
│  Skill 2: MessagingGeneratorSkill                                │
│           └── ICP → email/SMS/LinkedIn/voice copy                │
│           └── Per touch in sequence                              │
│                                                                  │
│  Skill 3: SequenceBuilderSkill                                   │
│           └── Build "Growth Engine" 6-touch sequence             │
│           └── Assign channels, timing, conditions                │
│                                                                  │
│  Skill 4: CampaignSplitterSkill                                  │
│           └── Multi-industry → separate campaigns                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Campaign(s) ready to launch
```

---

## Skill 1: Industry Researcher (Enhancement)

**Purpose:** Enhance ICP with web-researched industry intelligence when existing data is weak.

**When it runs:**
- `icp_pain_points` has < 3 items
- `confidence` < 0.6
- User explicitly requests deeper research

**File:** `src/agents/skills/industry_researcher.py`

```python
class IndustryResearcherInput(BaseModel):
    """Input for industry research."""
    industry: str                    # From ICPProfile.icp_industries[0]
    sub_niche: str | None           # "pediatric dentistry"
    location: str | None            # From ICPProfile.icp_locations[0]
    existing_pain_points: list[str] # From ICPProfile
    agency_services: list[str]      # From ICPProfile

class IndustryResearcherOutput(BaseModel):
    """Enhanced industry intelligence."""
    enhanced_pain_points: list[str]  # Merged + deduplicated
    objections: list[dict]           # {"objection": "...", "response": "..."}
    messaging_angles: list[str]      # How to position value
    tone_recommendation: str         # "professional", "casual"
    industry_benchmarks: dict        # {"avg_response_rate": "2-3%"}
    sources: list[str]               # URLs used for research
    research_date: datetime
```

**Implementation approach:**
1. Web search for `"{industry} biggest challenges 2024"`
2. Web search for `"how to sell to {industry}"`
3. Web search for `"{industry} marketing agency case studies"`
4. Scrape top results via Apify
5. AI synthesizes findings into structured output
6. Cache results for 30 days (same industry = reuse)

---

## Skill 2: Messaging Generator

**Purpose:** Transform ICP data into channel-specific copy.

**File:** `src/agents/skills/messaging_generator.py`

```python
class MessagingGeneratorInput(BaseModel):
    """Input for messaging generation."""
    # From ICPProfile
    icp_pain_points: list[str]
    icp_titles: list[str]
    agency_value_prop: str
    agency_name: str
    agency_services: list[str]
    
    # Generation params
    channel: Literal["email", "sms", "linkedin", "voice"]
    touch_number: int               # 1-6
    touch_purpose: str              # "intro", "value_add", "follow_up", "breakup"
    tone: str = "professional"      # From industry research

class MessagingGeneratorOutput(BaseModel):
    """Generated messaging for one touch."""
    channel: str
    touch_number: int
    
    # Email (if channel == "email")
    subject_options: list[str] | None    # 3 subject line variants
    email_body: str | None               # With {placeholders}
    
    # SMS (if channel == "sms")
    sms_message: str | None              # Under 160 chars
    
    # LinkedIn (if channel == "linkedin")
    connection_note: str | None          # 300 char limit
    inmail_body: str | None              # For InMails
    
    # Voice (if channel == "voice")
    voice_script_points: list[str] | None  # Talking points for AI
    voice_objection_handlers: dict | None  # Common objections
    
    # Metadata
    placeholders_used: list[str]         # ["first_name", "company", "pain_point"]
    pain_point_addressed: str            # Which pain point this touch uses
```

**Touch purposes and messaging strategy:**

| Touch | Purpose | Messaging Focus |
|-------|---------|-----------------|
| 1 | intro | Personalized opener, hint at pain point |
| 2 | connect | LinkedIn - brief, professional |
| 3 | value_add | Share insight/value, not just follow-up |
| 4 | pattern_interrupt | SMS - short, direct |
| 5 | breakup | Last chance, soft close |
| 6 | discovery | Voice - for hot leads only |

---

## Skill 3: Sequence Builder

**Purpose:** Build the complete campaign touch sequence.

**File:** `src/agents/skills/sequence_builder.py`

```python
class SequenceBuilderInput(BaseModel):
    """Input for sequence building."""
    icp_profile: dict               # Full ICPProfile as dict
    available_channels: list[str]   # ["email", "linkedin", "sms", "voice", "mail"]
    sequence_days: int = 14         # Total sequence duration
    aggressive: bool = False        # Faster timing for hot leads

class SequenceTouch(BaseModel):
    """A single touch in the sequence."""
    day: int                        # Day 1, Day 3, etc.
    channel: str                    # "email", "sms", etc.
    purpose: str                    # "intro", "value_add", etc.
    condition: str | None           # "no_reply", "als_score >= 80"
    skip_if: str | None             # "phone_missing", "linkedin_missing"
    messaging_key: str              # Reference for content lookup

class SequenceBuilderOutput(BaseModel):
    """Complete campaign sequence."""
    sequence_name: str              # "Growth Engine - Healthcare"
    total_days: int
    total_touches: int
    touches: list[SequenceTouch]
    adaptive_rules: list[str]       # Runtime behavior rules
    channel_summary: dict           # {"email": 3, "linkedin": 1, "sms": 1}
```

**The Universal "Growth Engine" Sequence:**

```yaml
touches:
  - day: 1
    channel: email
    purpose: intro
    condition: null
    skip_if: null
    
  - day: 3
    channel: linkedin
    purpose: connect
    condition: null
    skip_if: linkedin_url_missing
    
  - day: 5
    channel: email
    purpose: value_add
    condition: no_reply
    skip_if: null
    
  - day: 8
    channel: sms
    purpose: pattern_interrupt
    condition: no_reply
    skip_if: phone_missing
    
  - day: 12
    channel: email
    purpose: breakup
    condition: no_reply
    skip_if: null
    
  - day: 14
    channel: voice
    purpose: discovery
    condition: als_score >= 80 AND no_reply
    skip_if: phone_missing

adaptive_rules:
  - "Stop sequence immediately if reply detected"
  - "Classify reply intent (interested, not_interested, meeting_request)"
  - "Accelerate next touch by 1 day if email opened 3+ times"
  - "Add direct mail at day 10 if als_score >= 85"
  - "Skip channel if required data missing (don't fail)"
```

---

## Skill 4: Campaign Splitter

**Purpose:** Handle multi-industry agencies by splitting into separate campaigns.

**File:** `src/agents/skills/campaign_splitter.py`

```python
class CampaignSplitterInput(BaseModel):
    """Input for campaign splitting."""
    icp_profile: dict               # Full ICPProfile (has multiple industries)
    total_lead_budget: int          # Total leads to allocate
    lead_distribution: dict | None  # Optional: {"healthcare": 0.5, "legal": 0.3}

class CampaignPlan(BaseModel):
    """Plan for a single industry campaign."""
    name: str                       # "Healthcare Outreach - February"
    industry: str                   # "healthcare"
    lead_allocation: int            # 500
    icp_subset: dict                # Filtered ICP for this industry
    priority: int                   # 1 = launch first

class CampaignSplitterOutput(BaseModel):
    """Split campaign plans."""
    campaigns: list[CampaignPlan]
    total_leads: int
    recommendation: str             # "Start with healthcare first"
    launch_strategy: str            # "parallel" or "sequential"
```

**Splitting logic:**

1. If single industry → No split, return single campaign
2. If 2-3 industries → Split with proportional lead allocation
3. If 4+ industries → Force user to pick top 3, warn about dilution
4. Lead allocation based on:
   - Portfolio weight (more past clients = more leads)
   - User override (if provided)
   - Default: equal split

---

## Campaign Generation Agent

**Purpose:** Orchestrate all campaign skills.

**File:** `src/agents/campaign_generation_agent.py`

```python
class CampaignGenerationAgent(BaseAgent):
    """
    Generate campaign(s) from ICP profile.
    
    Flow:
    1. Check ICP quality → enhance with IndustryResearcher if needed
    2. Check multi-industry → split if needed
    3. For each campaign:
       a. Build sequence (SequenceBuilder)
       b. Generate messaging for each touch (MessagingGenerator)
    4. Return ready-to-launch campaign(s)
    """
    
    def __init__(self):
        self._skills = {
            "research_industry": IndustryResearcherSkill(),
            "generate_messaging": MessagingGeneratorSkill(),
            "build_sequence": SequenceBuilderSkill(),
            "split_campaigns": CampaignSplitterSkill(),
        }
    
    async def generate_campaign(
        self,
        icp_profile: ICPProfile,
        available_channels: list[str],
        lead_budget: int,
    ) -> CampaignGenerationResult:
        """Main entry point for campaign generation."""
        pass
```

---

## Database Changes

### New table: campaign_templates

```sql
-- Store generated campaign templates for reuse
CREATE TABLE campaign_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Template info
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    
    -- Sequence
    sequence JSONB NOT NULL,  -- SequenceBuilderOutput
    
    -- Messaging (per touch)
    messaging JSONB NOT NULL,  -- {touch_1: MessagingOutput, ...}
    
    -- Source ICP
    source_icp_id UUID,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_client_template UNIQUE (client_id, name)
);

-- Index for quick lookup
CREATE INDEX idx_campaign_templates_client ON campaign_templates(client_id);
```

---

## Implementation Order

### Phase 12A: Core (Build First)

| Step | Skill | Effort | Dependencies |
|------|-------|--------|--------------|
| 1 | SequenceBuilderSkill | 4 hrs | None |
| 2 | MessagingGeneratorSkill | 6 hrs | None |
| 3 | CampaignSplitterSkill | 3 hrs | None |
| 4 | CampaignGenerationAgent | 4 hrs | Skills 1-3 |
| 5 | Database migration | 1 hr | None |
| 6 | API routes | 2 hrs | Agent |

**Phase 12A Total:** ~20 hours

### Phase 12B: Enhancement (Build Later)

| Step | Skill | Effort | Dependencies |
|------|-------|--------|--------------|
| 1 | Serper API integration | 2 hrs | API key |
| 2 | IndustryResearcherSkill | 5 hrs | Serper |

**Phase 12B Total:** ~7 hours

---

## Open Questions

1. **Voice AI scripts** - How detailed should voice talking points be? Full script or bullet points?

2. **A/B testing** - Should we generate multiple message variants and let the system test them? Or single best version?

3. **Caching strategy** - Cache industry research for all clients or per-client?

---

## Related Documents

- `PROJECT_BLUEPRINT.md` - Overall system architecture
- `PROGRESS.md` - Build status tracking
- `src/agents/icp_discovery_agent.py` - ICP extraction (complete)
- `src/agents/skills/` - Existing skill implementations

---

## Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| CEO | | | [ ] |
| CTO | Claude | Dec 25, 2024 | [x] Spec complete |

---

**END OF SPECIFICATION**
