# SKILL.md — Campaign Generation

**Skill:** Campaign Generation Skills for Agency OS  
**Author:** CTO (Claude)  
**Version:** 1.0  
**Created:** December 25, 2025  
**Spec Document:** `docs/CAMPAIGN_SKILLS_SPEC.md`

---

## Purpose

Transform ICP data into campaign messaging and sequences. The ICP Discovery system (Phase 11) extracts WHO to target. This skill defines HOW to reach them with automated multi-channel campaigns.

---

## Prerequisites

- Phase 11 (ICP Discovery) ✅ Complete
- ICPProfile model exists with pain_points, titles, industries
- Base skill infrastructure in place

---

## Architecture Overview

```
ICPProfile (from Phase 11)
        │
        ▼
Campaign Generation Agent
├── CampaignSplitterSkill (if multi-industry)
├── SequenceBuilderSkill
└── MessagingGeneratorSkill (per touch)
        │
        ▼
Campaign(s) ready to launch
```

---

## Required Files (Phase 12A)

| Task ID | File | Purpose |
|---------|------|---------|
| CAM-001 | `src/agents/skills/sequence_builder.py` | Build 6-touch sequence |
| CAM-002 | `src/agents/skills/messaging_generator.py` | Generate email/SMS/LinkedIn copy |
| CAM-003 | `src/agents/skills/campaign_splitter.py` | Split multi-industry campaigns |
| CAM-004 | `src/agents/campaign_generation_agent.py` | Orchestrate skills |
| CAM-005 | `supabase/migrations/013_campaign_templates.sql` | Database table |
| CAM-006 | `src/api/routes/campaign_generation.py` | API endpoints |

---

## Implementation Order

```
1. CAM-001: SequenceBuilderSkill (no dependencies)
2. CAM-002: MessagingGeneratorSkill (no dependencies)
3. CAM-003: CampaignSplitterSkill (no dependencies)
4. CAM-004: CampaignGenerationAgent (needs 1-3)
5. CAM-005: Database migration (no dependencies)
6. CAM-006: API routes (needs 4)
```

---

## Skill 1: Sequence Builder

**File:** `src/agents/skills/sequence_builder.py`
**Task:** CAM-001

### Input Model

```python
class SequenceBuilderInput(BaseModel):
    """Input for sequence building."""
    icp_profile: dict               # Full ICPProfile as dict
    available_channels: list[str]   # ["email", "linkedin", "sms", "voice", "mail"]
    sequence_days: int = 14         # Total sequence duration
    aggressive: bool = False        # Faster timing for hot leads
```

### Output Model

```python
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
    channel_summary: dict           # {"email": 3, "linkedin": 1}
```

### The Universal "Growth Engine" Sequence

```yaml
touches:
  - day: 1
    channel: email
    purpose: intro
    condition: null
    skip_if: null
    messaging_key: "touch_1_email"
    
  - day: 3
    channel: linkedin
    purpose: connect
    condition: null
    skip_if: linkedin_url_missing
    messaging_key: "touch_2_linkedin"
    
  - day: 5
    channel: email
    purpose: value_add
    condition: no_reply
    skip_if: null
    messaging_key: "touch_3_email"
    
  - day: 8
    channel: sms
    purpose: pattern_interrupt
    condition: no_reply
    skip_if: phone_missing
    messaging_key: "touch_4_sms"
    
  - day: 12
    channel: email
    purpose: breakup
    condition: no_reply
    skip_if: null
    messaging_key: "touch_5_email"
    
  - day: 14
    channel: voice
    purpose: discovery
    condition: als_score >= 80 AND no_reply
    skip_if: phone_missing
    messaging_key: "touch_6_voice"

adaptive_rules:
  - "Stop sequence immediately if reply detected"
  - "Classify reply intent (interested, not_interested, meeting_request)"
  - "Accelerate next touch by 1 day if email opened 3+ times"
  - "Skip channel if required data missing (don't fail)"
```

### System Prompt

```
You are a sales sequence strategist. Given an ICP profile and available channels,
build an optimal touch sequence following the "Growth Engine" pattern.

The Growth Engine sequence is:
1. Email intro (Day 1) - Personalized, hint at pain point
2. LinkedIn connect (Day 3) - Brief, professional
3. Email value add (Day 5) - Share insight, not just follow-up
4. SMS pattern interrupt (Day 8) - Short, direct
5. Email breakup (Day 12) - Last chance, soft close
6. Voice discovery (Day 14) - For hot leads only (ALS >= 80)

Adjust timing based on:
- Industry norms (B2B SaaS = faster, Healthcare = slower)
- aggressive flag (if True, compress to 10 days)
- Available channels (skip unavailable)

Always include skip_if conditions for channels requiring specific data.
```

---

## Skill 2: Messaging Generator

**File:** `src/agents/skills/messaging_generator.py`
**Task:** CAM-002

### Input Model

```python
class MessagingGeneratorInput(BaseModel):
    """Input for messaging generation."""
    # From ICPProfile
    icp_pain_points: list[str]
    icp_titles: list[str]
    agency_value_prop: str
    agency_name: str
    agency_services: list[str]
    industry: str
    
    # Generation params
    channel: Literal["email", "sms", "linkedin", "voice"]
    touch_number: int               # 1-6
    touch_purpose: str              # "intro", "value_add", "follow_up", "breakup"
    tone: str = "professional"      # From industry
```

### Output Model

```python
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
    inmail_body: str | None
    
    # Voice (if channel == "voice")
    voice_script_points: list[str] | None
    voice_objection_handlers: dict | None
    
    # Metadata
    placeholders_used: list[str]         # ["first_name", "company"]
    pain_point_addressed: str            # Which pain point
```

### Touch Purpose Guidelines

| Touch | Purpose | Messaging Focus |
|-------|---------|-----------------|
| 1 | intro | Personalized opener, hint at pain point, no pitch |
| 2 | connect | LinkedIn - brief, professional, mutual benefit |
| 3 | value_add | Share insight/tip, demonstrate expertise, not selling |
| 4 | pattern_interrupt | SMS - short, direct, conversational |
| 5 | breakup | Last chance, acknowledge busy, leave door open |
| 6 | discovery | Voice - talking points for AI caller |

### Placeholder Reference

Always use these exact placeholder names:

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{first_name}` | Lead.first_name | "Sarah" |
| `{company}` | Lead.company_name | "TechCorp" |
| `{title}` | Lead.title | "Marketing Director" |
| `{industry}` | Lead.industry | "healthcare" |
| `{pain_point}` | Selected from ICP | "inconsistent lead flow" |
| `{agency_name}` | Client.name | "GrowthAgency" |
| `{sender_name}` | User.name | "Mike" |

### System Prompt

```
You are an expert cold outreach copywriter. Generate messaging for a specific 
touch in a multi-channel sequence.

RULES:
1. Never use {company} in subject lines (spam trigger)
2. Subject lines under 50 characters
3. Email body under 150 words
4. SMS under 160 characters
5. LinkedIn connection note under 300 characters
6. Voice scripts as bullet points, not full scripts
7. Always sound human, never robotic or salesy
8. Focus on THEIR problem, not your solution
9. One clear CTA per message
10. Use placeholders for personalization

TONE BY INDUSTRY:
- Healthcare: Professional, trustworthy, patient-focused
- SaaS/Tech: Casual, direct, metrics-focused
- Professional Services: Formal, consultative
- Trades/Home Services: Straightforward, practical
- Ecommerce: Energetic, results-focused

TOUCH PURPOSE:
- intro: Pattern interrupt, hint at pain, no pitch
- value_add: Give something useful, build credibility
- follow_up: Quick check-in, reference previous touch
- breakup: Last attempt, acknowledge their time
```

---

## Skill 3: Campaign Splitter

**File:** `src/agents/skills/campaign_splitter.py`
**Task:** CAM-003

### Input Model

```python
class CampaignSplitterInput(BaseModel):
    """Input for campaign splitting."""
    icp_profile: dict               # Full ICPProfile
    total_lead_budget: int          # Total leads to allocate
    lead_distribution: dict | None  # {"healthcare": 0.5, "legal": 0.3}
```

### Output Model

```python
class CampaignPlan(BaseModel):
    """Plan for a single industry campaign."""
    name: str                       # "Healthcare Outreach - February"
    industry: str                   # "healthcare"
    lead_allocation: int            # 500
    icp_subset: dict                # Filtered ICP for this industry
    priority: int                   # 1 = launch first

class CampaignSplitterOutput(BaseModel):
    """Split campaign plans."""
    should_split: bool              # False if single industry
    campaigns: list[CampaignPlan]
    total_leads: int
    recommendation: str             # "Start with healthcare first"
    launch_strategy: str            # "parallel" or "sequential"
```

### Splitting Logic

```python
def should_split(icp_industries: list[str]) -> bool:
    """Determine if campaign should be split."""
    if len(icp_industries) <= 1:
        return False
    if len(icp_industries) > 3:
        # Force user to pick top 3
        raise ValueError("Too many industries. Select top 3.")
    return True

def allocate_leads(
    industries: list[str],
    total_budget: int,
    distribution: dict | None
) -> dict[str, int]:
    """Allocate leads across industries."""
    if distribution:
        return {ind: int(total_budget * pct) 
                for ind, pct in distribution.items()}
    
    # Equal split
    per_industry = total_budget // len(industries)
    return {ind: per_industry for ind in industries}
```

### System Prompt

```
You are a campaign strategist. Given a multi-industry ICP, determine how to
split into separate campaigns for maximum effectiveness.

RULES:
1. Single industry → No split, return single campaign
2. 2-3 industries → Split with proportional lead allocation
3. 4+ industries → Recommend user picks top 3

ALLOCATION STRATEGY:
- Portfolio weight: More past clients = more leads
- Market size: Larger TAM = more leads
- User override: Always respect explicit distribution

LAUNCH STRATEGY:
- sequential: One campaign at a time, learn then scale
- parallel: All campaigns at once (only if sufficient budget)

Recommend sequential for:
- First-time users
- Budget < 500 leads per industry
- Testing new industries

Recommend parallel for:
- Experienced users
- Budget >= 500 per industry
- Proven industries
```

---

## Campaign Generation Agent

**File:** `src/agents/campaign_generation_agent.py`
**Task:** CAM-004

### Agent Structure

```python
class CampaignGenerationAgent(BaseAgent):
    """
    Generate campaign(s) from ICP profile.
    
    Flow:
    1. Check multi-industry → split if needed
    2. For each campaign:
       a. Build sequence (SequenceBuilder)
       b. Generate messaging for each touch (MessagingGenerator)
    3. Return ready-to-launch campaign(s)
    """
    
    name = "campaign_generation"
    
    def __init__(self):
        self._skills = {
            "build_sequence": SequenceBuilderSkill(),
            "generate_messaging": MessagingGeneratorSkill(),
            "split_campaigns": CampaignSplitterSkill(),
        }
    
    async def generate_campaign(
        self,
        icp_profile: ICPProfile,
        available_channels: list[str],
        lead_budget: int,
    ) -> CampaignGenerationResult:
        """Main entry point for campaign generation."""
        
        # Step 1: Check if multi-industry split needed
        split_result = await self.use_skill(
            "split_campaigns",
            icp_profile=icp_profile.model_dump(),
            total_lead_budget=lead_budget,
        )
        
        campaigns = []
        
        for plan in split_result.data.campaigns:
            # Step 2: Build sequence for this campaign
            sequence = await self.use_skill(
                "build_sequence",
                icp_profile=plan.icp_subset,
                available_channels=available_channels,
            )
            
            # Step 3: Generate messaging for each touch
            messaging = {}
            for touch in sequence.data.touches:
                msg = await self.use_skill(
                    "generate_messaging",
                    icp_pain_points=plan.icp_subset["icp_pain_points"],
                    icp_titles=plan.icp_subset["icp_titles"],
                    agency_value_prop=icp_profile.value_proposition,
                    agency_name=icp_profile.company_name,
                    agency_services=icp_profile.services_offered,
                    industry=plan.industry,
                    channel=touch.channel,
                    touch_number=touch.day,
                    touch_purpose=touch.purpose,
                )
                messaging[touch.messaging_key] = msg.data
            
            campaigns.append(GeneratedCampaign(
                plan=plan,
                sequence=sequence.data,
                messaging=messaging,
            ))
        
        return CampaignGenerationResult(
            campaigns=campaigns,
            total_tokens=...,
            total_cost_aud=...,
        )
```

---

## Database Migration

**File:** `supabase/migrations/013_campaign_templates.sql`
**Task:** CAM-005

```sql
-- Campaign templates for reuse
CREATE TABLE campaign_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Template info
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    
    -- Sequence (SequenceBuilderOutput as JSONB)
    sequence JSONB NOT NULL,
    
    -- Messaging per touch (dict of MessagingGeneratorOutput)
    messaging JSONB NOT NULL,
    
    -- Source ICP
    source_icp_id UUID REFERENCES client_icp_profiles(id),
    
    -- Status
    status TEXT DEFAULT 'draft',  -- draft, active, paused, archived
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete
    
    CONSTRAINT unique_client_template UNIQUE (client_id, name, deleted_at)
);

-- Index for quick lookup
CREATE INDEX idx_campaign_templates_client ON campaign_templates(client_id) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_campaign_templates_status ON campaign_templates(status) 
    WHERE deleted_at IS NULL;

-- RLS policies
ALTER TABLE campaign_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Clients can view own templates"
    ON campaign_templates FOR SELECT
    USING (client_id IN (
        SELECT id FROM clients WHERE id = current_setting('app.client_id')::uuid
    ));

CREATE POLICY "Clients can insert own templates"
    ON campaign_templates FOR INSERT
    WITH CHECK (client_id IN (
        SELECT id FROM clients WHERE id = current_setting('app.client_id')::uuid
    ));

CREATE POLICY "Clients can update own templates"
    ON campaign_templates FOR UPDATE
    USING (client_id IN (
        SELECT id FROM clients WHERE id = current_setting('app.client_id')::uuid
    ));
```

---

## API Routes

**File:** `src/api/routes/campaign_generation.py`
**Task:** CAM-006

```python
"""
Campaign generation API routes.

Endpoints:
- POST /api/v1/campaigns/generate - Generate campaign from ICP
- GET /api/v1/campaigns/templates - List campaign templates
- GET /api/v1/campaigns/templates/{id} - Get template details
- POST /api/v1/campaigns/templates/{id}/launch - Launch from template
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.campaign_generation_agent import (
    CampaignGenerationAgent,
    get_campaign_generation_agent,
)
from src.api.deps import get_db, get_current_client
from src.models.client import Client

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/generate")
async def generate_campaign(
    request: GenerateCampaignRequest,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client),
):
    """Generate campaign from client's ICP profile."""
    agent = get_campaign_generation_agent()
    
    # Get client's ICP profile
    icp = await get_client_icp(db, client.id)
    if not icp:
        raise HTTPException(404, "ICP profile not found. Complete onboarding first.")
    
    # Generate campaign
    result = await agent.generate_campaign(
        icp_profile=icp,
        available_channels=request.channels,
        lead_budget=request.lead_budget,
    )
    
    return result
```

---

## Success Criteria

### Phase 12A Complete When:

- [ ] All 6 tasks marked 🟢 in PROGRESS.md
- [ ] SequenceBuilderSkill generates valid sequences
- [ ] MessagingGeneratorSkill generates all channel content
- [ ] CampaignSplitterSkill handles 1-3 industries
- [ ] CampaignGenerationAgent orchestrates all skills
- [ ] Database migration applied
- [ ] API routes functional
- [ ] Unit tests passing

### Test Scenarios

1. **Single industry ICP** → One campaign, 6 touches, all messaging
2. **Multi-industry ICP (3)** → Three campaigns, each with sequence + messaging
3. **Missing channels** → Sequence skips unavailable channels gracefully
4. **Hot lead sequence** → Aggressive timing (10 days vs 14)

---

## QA Checks (Specific to Phase 12A)

| Check | Severity | Pattern |
|-------|----------|---------|
| Skill extends BaseSkill | CRITICAL | `class.*Skill\(BaseSkill\[` |
| Input/Output models defined | CRITICAL | `class Input\(BaseModel\)` |
| System prompt present | HIGH | `system_prompt = """` |
| Registered with SkillRegistry | HIGH | `SkillRegistry.register` |
| No hardcoded messaging | HIGH | No literal email copy |
| Placeholders documented | MEDIUM | `{first_name}` format |

---

## Fix Patterns (Specific to Phase 12A)

| Issue | Fix |
|-------|-----|
| Missing BaseSkill inheritance | Add `(BaseSkill[Input, Output])` |
| Missing Input/Output models | Create nested classes |
| No system prompt | Add `system_prompt = """..."""` |
| Not registered | Add `SkillRegistry.register(SkillClass())` |

---

**END OF CAMPAIGN SKILL**
