This is where SDK really shines over raw API.
Self-Correcting Enrichment Loop
Claude doesn't just run once - it keeps going until the data meets your threshold.
@task
async def enrichment_with_waterfall(lead):
    async for msg in query(
        prompt=f"""
        Goal: Enrich this lead until ALS confidence >= 80%.

        Lead: {lead.name} at {lead.company}
        Current data: {lead.raw_data}

        ALS requires these fields with confidence scores:
        - company_size (need >= 70% confidence)
        - decision_maker (need >= 80% confidence)  
        - budget_signals (need >= 60% confidence)
        - timing_signals (need >= 50% confidence)
        - pain_points (need >= 70% confidence)

        WATERFALL STRATEGY:
        1. Start with Apollo API
        2. If gaps: search company website
        3. If gaps: search LinkedIn
        4. If gaps: search news/press releases
        5. If gaps: search podcasts/interviews
        6. If gaps: search job postings (hiring = budget)
        7. If gaps: search tech stack (BuiltWith patterns)

        After EACH source, evaluate:
        - What fields are now sufficient?
        - What's still missing?
        - What's the next best source?

        STOP when:
        - Overall confidence >= 80%, OR
        - All waterfall sources exhausted

        Output JSON with all findings and final confidence score.
        """,
        options=ClaudeAgentOptions(
            allowed_tools=["WebSearch", "WebFetch", "Bash"],
            permission_mode="bypassPermissions"
        )
    ):
        if hasattr(msg, "result"):
            return msg.result
The Brain's Internal Loop
Claude thinks:
1. Apollo returned company_size=50, decision_maker=unknown
   → Confidence: 45%. Not sufficient.
   → Next: Search LinkedIn for CEO/CMO

Found CMO on LinkedIn, 8 years experience, ex-HubSpot
→ decision_maker confidence now 90%
→ Confidence: 62%. Still need budget signals.
→ Next: Check job postings

Found 3 marketing job postings this month
→ budget_signals: "actively hiring marketing = has budget"
→ Confidence: 78%. Close. Need pain points.
→ Next: Search for interviews/podcasts

Found CEO on podcast complaining about "leads going cold"
→ pain_points: "lead response time" - perfect fit for Agency OS
→ Confidence: 89%. SUFFICIENT.
→ Output final JSON.
What This Looks Like in Prefect
@flow
def waterfall_enrichment_flow(leads):
 for lead in leads:
     # Quick check - is basic API enough?
     basic = enrich_via_apis(lead)

     if calculate_confidence(basic) >= 80:
         save_to_db(basic)
         continue

     # Not enough - deploy the brain with waterfall
     enriched = await enrichment_with_waterfall(lead)

     # Validate output meets schema
     if validate_enrichment(enriched):
         save_to_db(enriched)
     else:
         flag_for_manual_review(lead)
The Magic
Traditional Waterfall
SDK Waterfall
You code every fallback path
Claude figures out next best source
Fixed order
Adaptive based on what's missing
Fails on edge cases
Problem-solves edge cases
"No data found"
"Found signal in unexpected place"
Guardrails
You'd want to add:
options=ClaudeAgentOptions(
 allowed_tools=["WebSearch", "WebFetch"],
 permission_mode="bypassPermissions",
 max_turns=20,  # Don't let it run forever
 # Could also add cost limits via hooks
)
This is genuinely novel
I haven't seen anyone combine Prefect + SDK like this for a SaaS product. Deterministic orchestration with intelligent agents at the decision points.
Want me to sketch out the full architecture for how this would fit into Agency OS?

Agency OS + Claude Agent SDK Architecture
High-Level Overview
┌─────────────────────────────────────────────────────────────────┐
│                        AGENCY OS                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Next.js   │    │   FastAPI   │    │  Supabase   │         │
│  │  Frontend   │───▶│   Backend   │───▶│  Database   │         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    PREFECT ORCHESTRATOR                   │  │
│  │                                                           │  │
│  │   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐  │  │
│  │   │  Lead   │   │  Email  │   │LinkedIn │   │  Voice  │  │  │
│  │   │ Engine  │   │ Engine  │   │ Engine  │   │ Engine  │  │  │
│  │   └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘  │  │
│  │        │             │             │             │        │  │
│  └────────┼─────────────┼─────────────┼─────────────┼────────┘  │
│           │             │             │             │           │
│           ▼             ▼             ▼             ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 CLAUDE AGENT SDK LAYER                    │  │
│  │                      "The Brain"                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
Directory Structure
agency-os/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   └── services/
│   │
│   ├── orchestration/           # Prefect flows
│   │   ├── flows/
│   │   │   ├── lead_enrichment.py
│   │   │   ├── email_sequences.py
│   │   │   ├── linkedin_outreach.py
│   │   │   └── voice_campaigns.py
│   │   │
│   │   └── tasks/
│   │       ├── deterministic/   # API calls, scoring, sending
│   │       │   ├── apollo.py
│   │       │   ├── clearbit.py
│   │       │   ├── salesforge.py
│   │       │   └── als_scoring.py
│   │       │
│   │       └── intelligent/     # SDK-powered tasks
│   │           ├── enrichment_brain.py
│   │           ├── email_brain.py
│   │           ├── response_brain.py
│   │           └── objection_brain.py
│   │
│   └── brain/                   # Claude Agent SDK wrapper
│       ├── __init__.py
│       ├── client.py            # SDK configuration
│       ├── prompts/             # Prompt templates
│       │   ├── enrichment.md
│       │   ├── email_writer.md
│       │   └── response_classifier.md
│       └── tools/               # Custom MCP tools if needed
│
└── ...
Core Brain Client
# backend/brain/client.py

from claude_agent_sdk import query, ClaudeAgentOptions, ClaudeSDKClient
from typing import AsyncIterator, Optional
import json

class AgencyOSBrain:
    """Wrapper around Claude Agent SDK for Agency OS"""

    def __init__(
        self,
        max_turns: int = 30,
        timeout_seconds: int = 300,
        cost_limit_usd: float = 1.00
    ):
        self.max_turns = max_turns
        self.timeout = timeout_seconds
        self.cost_limit = cost_limit_usd
        self.total_cost = 0.0

    async def think(
        self,
        prompt: str,
        tools: list[str] = None,
        output_schema: dict = None
    ) -> dict:
        """
        Run a brain task and return structured output.
        """
        tools = tools or ["WebSearch", "WebFetch"]

        full_prompt = prompt
        if output_schema:
            full_prompt += f"\n\nReturn JSON matching this schema:\n{json.dumps(output_schema, indent=2)}"

        result = None

        async for msg in query(
            prompt=full_prompt,
            options=ClaudeAgentOptions(
                allowed_tools=tools,
                permission_mode="bypassPermissions",
                can_use_tool=self._auto_approve
            )
        ):
            # Track costs
            if hasattr(msg, "total_cost_usd"):
                self.total_cost = msg.total_cost_usd
                if self.total_cost > self.cost_limit:
                    raise CostLimitExceeded(f"Brain exceeded ${self.cost_limit}")

            # Capture final result
            if hasattr(msg, "result"):
                result = msg.result

        return self._parse_result(result, output_schema)

    async def _auto_approve(self, tool_name, input_data, context):
        """Auto-approve tools and auto-answer questions"""

        if tool_name == "AskUserQuestion":
            # Auto-select first/recommended option
            answers = {}
            for q in input_data.get("questions", []):
                options = q.get("options", [])
                recommended = next(
                    (o for o in options if "recommend" in o.get("description", "").lower()),
                    options[0] if options else {"label": "continue"}
                )
                answers[q["question"]] = recommended["label"]

            return {
                "behavior": "allow",
                "updatedInput": {"questions": input_data["questions"], "answers": answers}
            }

        return {"behavior": "allow", "updatedInput": input_data}

    def _parse_result(self, result: str, schema: dict = None) -> dict:
        """Extract JSON from result"""
        try:
            # Try to find JSON in response
            if "json" in result:
                json_str = result.split("json")[1].split("```")[0]
            elif "{" in result:
                start = result.index("{")
                end = result.rindex("}") + 1
                json_str = result[start:end]
            else:
                return {"raw": result}

            return json.loads(json_str)
        except:
            return {"raw": result}

class CostLimitExceeded(Exception):
    pass
Lead Enrichment Brain
# backend/brain/prompts/enrichment.md

"""
# Lead Enrichment Agent

## Goal
Enrich this lead until confidence >= {target_confidence}%.

## Lead Input
- Name: {lead_name}
- Company: {company_name}
- Current data: {current_data}

## ALS Scoring Factors
Your enrichment directly impacts the Agency Lead Score:

| Factor | Weight | Current Confidence | Target |
|--------|--------|-------------------|--------|
| Company Size | 0.15 | {company_size_conf}% | 70% |
| Industry Fit | 0.20 | {industry_conf}% | 80% |
| Decision Maker | 0.20 | {dm_conf}% | 80% |
| Budget Signals | 0.15 | {budget_conf}% | 60% |
| Timing Signals | 0.10 | {timing_conf}% | 50% |
| Pain Points | 0.15 | {pain_conf}% | 70% |
| Tech Stack | 0.05 | {tech_conf}% | 50% |

## Waterfall Strategy
Try sources in this order until sufficient:

**Apollo API** (already done - data above)
**Company Website** - About, team, careers pages
**LinkedIn** - Company page, key personnel
**News/Press** - Funding, launches, announcements
**Job Postings** - Hiring = budget, roles = priorities
**Podcasts/Interviews** - CEO/CMO quotes = pain points
**Tech Stack Tools** - BuiltWith, Wappalyzer patterns
**Review Sites** - G2, Capterra = their customers
## Rules
- After EACH source, recalculate confidence
- STOP when overall confidence >= {target_confidence}%
- STOP if all sources exhausted
- Prefer recent data (< 6 months)
- Note confidence level for each finding

## Output Schema
Return this exact JSON structure:
"""
# backend/orchestration/tasks/intelligent/enrichment_brain.py

from prefect import task
from brain.client import AgencyOSBrain
from pathlib import Path

ENRICHMENT_PROMPT = Path("backend/brain/prompts/enrichment.md").read_text()

ENRICHMENT_SCHEMA = {
    "lead_id": "string",
    "enrichment_complete": "boolean",
    "overall_confidence": "number (0-100)",
    "fields": {
        "company_size": {
            "value": "string",
            "confidence": "number",
            "source": "string"
        },
        "industry": {
            "value": "string", 
            "confidence": "number",
            "source": "string"
        },
        "decision_maker": {
            "name": "string",
            "title": "string",
            "linkedin": "string",
            "confidence": "number",
            "source": "string"
        },
        "budget_signals": {
            "signals": ["string"],
            "confidence": "number",
            "sources": ["string"]
        },
        "timing_signals": {
            "signals": ["string"],
            "confidence": "number",
            "sources": ["string"]
        },
        "pain_points": {
            "points": ["string"],
            "confidence": "number",
            "sources": ["string"]
        },
        "tech_stack": {
            "tools": ["string"],
            "confidence": "number",
            "source": "string"
        }
    },
    "sources_tried": ["string"],
    "als_recommendation": "number (0-100)",
    "enrichment_notes": "string"
}

@task(retries=2, retry_delay_seconds=30)
async def intelligent_enrichment(
    lead: dict,
    target_confidence: int = 80,
    cost_limit: float = 0.50
) -> dict:
    """
    Use Claude Agent SDK to intelligently enrich a lead
    via waterfall strategy until confidence threshold met.
    """
    brain = AgencyOSBrain(
        max_turns=30,
        cost_limit_usd=cost_limit
    )

    # Build prompt from template
    prompt = ENRICHMENT_PROMPT.format(
        target_confidence=target_confidence,
        lead_name=lead.get("name", "Unknown"),
        company_name=lead.get("company", "Unknown"),
        current_data=lead,
        company_size_conf=lead.get("confidence", {}).get("company_size", 0),
        industry_conf=lead.get("confidence", {}).get("industry", 0),
        dm_conf=lead.get("confidence", {}).get("decision_maker", 0),
        budget_conf=lead.get("confidence", {}).get("budget_signals", 0),
        timing_conf=lead.get("confidence", {}).get("timing_signals", 0),
        pain_conf=lead.get("confidence", {}).get("pain_points", 0),
        tech_conf=lead.get("confidence", {}).get("tech_stack", 0),
    )

    result = await brain.think(
        prompt=prompt,
        tools=["WebSearch", "WebFetch"],
        output_schema=ENRICHMENT_SCHEMA
    )

    # Add metadata
    result["brain_cost_usd"] = brain.total_cost
    result["lead_id"] = lead.get("id")

    return result
The Prefect Flow
# backend/orchestration/flows/lead_enrichment.py

from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta

from orchestration.tasks.deterministic.apollo import enrich_via_apollo
from orchestration.tasks.deterministic.clearbit import enrich_via_clearbit
from orchestration.tasks.deterministic.als_scoring import calculate_als, calculate_confidence
from orchestration.tasks.intelligent.enrichment_brain import intelligent_enrichment

from db.supabase import save_lead, update_lead, get_leads_for_enrichment

@task
def merge_api_data(lead: dict, apollo: dict, clearbit: dict) -> dict:
    """Merge data from multiple API sources"""
    return {
        **lead,
        "company_size": apollo.get("company_size") or clearbit.get("employees"),
        "industry": apollo.get("industry") or clearbit.get("industry"),
        "decision_maker": apollo.get("contact"),
        "funding": clearbit.get("funding"),
        "tech_stack": clearbit.get("tech"),
        # Track confidence per field
        "confidence": {
            "company_size": 90 if apollo.get("company_size") else 0,
            "industry": 85 if apollo.get("industry") else 0,
            "decision_maker": 80 if apollo.get("contact") else 0,
            "budget_signals": 70 if clearbit.get("funding") else 0,
            "timing_signals": 0,  # APIs don't give this
            "pain_points": 0,     # APIs don't give this
            "tech_stack": 75 if clearbit.get("tech") else 0,
        }
    }

@task
def should_use_brain(lead: dict, baseline_als: int, confidence: float) -> bool:
    """Decide if this lead warrants brain enrichment"""

    # High potential but incomplete data
    if baseline_als >= 40 and confidence < 70:
        return True

    # Missing critical fields
    critical_missing = (
        lead["confidence"].get("decision_maker", 0) < 50 or
        lead["confidence"].get("pain_points", 0) < 30
    )
    if baseline_als >= 30 and critical_missing:
        return True

    return False

@flow(name="lead-enrichment-flow")
async def lead_enrichment_flow(
    campaign_id: str,
    batch_size: int = 50,
    brain_budget_per_lead: float = 0.50
):
    """
    Main enrichment flow combining deterministic APIs + intelligent brain.
    """
    # Get leads needing enrichment
    leads = get_leads_for_enrichment(campaign_id, limit=batch_size)

    results = {
        "total": len(leads),
        "api_only": 0,
        "brain_enriched": 0,
        "failed": 0,
        "total_brain_cost": 0.0
    }

    for lead in leads:
        try:
            # ============ DETERMINISTIC LAYER ============

            # Step 1: API enrichment (fast, cheap)
            apollo_data = enrich_via_apollo(lead)
            clearbit_data = enrich_via_clearbit(lead)

            # Step 2: Merge API data
            merged = merge_api_data(lead, apollo_data, clearbit_data)

            # Step 3: Calculate baseline ALS
            baseline_als = calculate_als(merged)
            confidence = calculate_confidence(merged)

            # ============ INTELLIGENT LAYER ============

            # Step 4: Decide if brain needed
            if should_use_brain(merged, baseline_als, confidence):

                # Step 5: Deploy the brain
                brain_result = await intelligent_enrichment(
                    lead=merged,
                    target_confidence=80,
                    cost_limit=brain_budget_per_lead
                )

                # Step 6: Merge brain findings
                final_data = {**merged, **brain_result["fields"]}
                final_als = calculate_als(final_data)

                results["brain_enriched"] += 1
                results["total_brain_cost"] += brain_result.get("brain_cost_usd", 0)

            else:
                final_data = merged
                final_als = baseline_als
                results["api_only"] += 1

            # ============ SAVE ============

            update_lead(
                lead_id=lead["id"],
                enriched_data=final_data,
                als_score=final_als,
                enrichment_method="brain" if should_use_brain(merged, baseline_als, confidence) else "api"
            )

        except Exception as e:
            results["failed"] += 1
            # Log error, continue with next lead

    return results
Email Writing Brain
# backend/orchestration/tasks/intelligent/email_brain.py

from prefect import task
from brain.client import AgencyOSBrain

EMAIL_SCHEMA = {
    "subject_line": "string",
    "body": "string",
    "personalization_hooks": ["string"],
    "call_to_action": "string",
    "tone": "string",
    "estimated_response_rate": "string"
}

@task
async def write_personalized_email(
    lead: dict,
    sequence_position: int,
    campaign_context: dict,
    previous_emails: list = None
) -> dict:
    """
    Brain writes a personalized cold email based on enriched lead data.
    """
    brain = AgencyOSBrain(cost_limit_usd=0.10)

    prompt = f"""
    Write a cold email for this prospect.

    ## Prospect
    - Name: {lead['decision_maker']['name']}
    - Title: {lead['decision_maker']['title']}
    - Company: {lead['company']}
    - Industry: {lead['industry']}
    - Company Size: {lead['company_size']}

    ## Pain Points Found
    {lead.get('pain_points', {}).get('points', ['Unknown'])}

    ## Budget Signals
    {lead.get('budget_signals', {}).get('signals', ['Unknown'])}

    ## Campaign Context
    - Agency Client: {campaign_context['agency_name']}
    - Service Offered: {campaign_context['service']}
    - Value Prop: {campaign_context['value_prop']}

    ## Sequence Position
    Email {sequence_position} of {campaign_context['sequence_length']}

    ## Previous Emails in Sequence
    {previous_emails or 'This is the first email'}

    ## Rules
    - Keep under 150 words
    - One clear CTA
    - Reference specific pain point or signal
    - Sound human, not salesy
    - No "I hope this email finds you well"
    """

    result = await brain.think(
        prompt=prompt,
        tools=[],  # No tools needed, just generation
        output_schema=EMAIL_SCHEMA
    )

    return result
Response Classification Brain
# backend/orchestration/tasks/intelligent/response_brain.py

from prefect import task
from brain.client import AgencyOSBrain

CLASSIFICATION_SCHEMA = {
    "classification": "string (positive|negative|neutral|objection|out_of_office|bounce)",
    "sentiment_score": "number (-1 to 1)",
    "objection_type": "string|null",
    "key_phrases": ["string"],
    "recommended_action": "string",
    "recommended_reply_tone": "string",
    "urgency": "string (high|medium|low)"
}

@task
async def classify_response(
    email_body: str,
    original_outreach: str,
    lead: dict
) -> dict:
    """
    Brain classifies an email response and recommends next action.
    """
    brain = AgencyOSBrain(cost_limit_usd=0.05)

    prompt = f"""
    Classify this email response and recommend next action.

    ## Original Outreach
    {original_outreach}

    ## Their Response
    {email_body}

    ## Lead Context
    - Company: {lead['company']}
    - Decision Maker: {lead['decision_maker']['name']}
    - ALS Score: {lead['als_score']}

    ## Classification Options
    - positive: Interested, wants to talk
    - negative: Not interested, do not contact
    - neutral: Non-committal, needs nurturing
    - objection: Specific concern raised
    - out_of_office: Auto-reply
    - bounce: Delivery failure

    ## If Objection, Common Types
    - timing: "Not right now"
    - budget: "No budget"
    - authority: "Not my decision"
    - need: "We don't need this"
    - competitor: "Using someone else"
    """

    return await brain.think(
        prompt=prompt,
        tools=[],
        output_schema=CLASSIFICATION_SCHEMA
    )
Objection Handling Brain
# backend/orchestration/tasks/intelligent/objection_brain.py

from prefect import task
from brain.client import AgencyOSBrain

@task
async def craft_objection_response(
    objection_type: str,
    their_response: str,
    lead: dict,
    campaign_context: dict
) -> dict:
    """
    Brain crafts a response to handle a specific objection.
    """
    brain = AgencyOSBrain(cost_limit_usd=0.10)

    prompt = f"""
    Craft a reply to handle this objection.

    ## Their Objection
    Type: {objection_type}
    Their words: "{their_response}"

    ## What We Know About Them
    - Pain points: {lead.get('pain_points', {}).get('points', [])}
    - Budget signals: {lead.get('budget_signals', {}).get('signals', [])}
    - Company situation: {lead.get('enrichment_notes', '')}

    ## Objection Handling Strategy

    ### If "timing"
    - Acknowledge timing
    - Offer value now (content, insights)
    - Suggest specific future touchpoint

    ### If "budget"
    - Don't push
    - Reference their funding/hiring signals if any
    - Offer smaller entry point or ROI conversation

    ### If "authority"
    - Ask who is the right person
    - Offer to send materials they can forward
    - Ask for warm intro

    ### If "need"
    - Reference specific pain point we found
    - Share relevant case study
    - Offer diagnostic/audit

    ### If "competitor"
    - Don't trash competitor
    - Highlight differentiator
    - Offer comparison or second opinion

    ## Rules
    - Under 100 words
    - Empathetic, not pushy
    - One clear next step
    - Reference something specific about them
    """

    return await brain.think(
        prompt=prompt,
        tools=[],
        output_schema={
            "reply": "string",
            "tone": "string",
            "next_step": "string",
            "follow_up_days": "number"
        }
    )
Full Sequence Flow
# backend/orchestration/flows/email_sequences.py

from prefect import flow
from orchestration.tasks.intelligent.email_brain import write_personalized_email
from orchestration.tasks.intelligent.response_brain import classify_response
from orchestration.tasks.intelligent.objection_brain import craft_objection_response
from orchestration.tasks.deterministic.salesforge import send_email, check_responses

@flow(name="email-sequence-flow")
async def email_sequence_flow(campaign_id: str):
    """
    Full email sequence with brain at decision points.
    """
    campaign = get_campaign(campaign_id)
    leads = get_leads_for_campaign(campaign_id)

    for lead in leads:
        # Check for responses first
        responses = check_responses(lead["email"])

        if responses:
            for response in responses:
                # 🧠 Classify the response
                classification = await classify_response(
                    email_body=response["body"],
                    original_outreach=response["original"],
                    lead=lead
                )

                if classification["classification"] == "positive":
                    # Move to sales pipeline
                    create_opportunity(lead, classification)

                elif classification["classification"] == "objection":
                    # 🧠 Craft objection handling reply
                    reply = await craft_objection_response(
                        objection_type=classification["objection_type"],
                        their_response=response["body"],
                        lead=lead,
                        campaign_context=campaign
                    )
                    send_email(lead["email"], reply["reply"])

                elif classification["classification"] == "negative":
                    # Respect the no
                    mark_do_not_contact(lead)

        else:
            # No response yet - continue sequence
            sequence_position = get_sequence_position(lead, campaign)

            if sequence_position <= campaign["sequence_length"]:
                # 🧠 Write next email
                email = await write_personalized_email(
                    lead=lead,
                    sequence_position=sequence_position,
                    campaign_context=campaign,
                    previous_emails=get_previous_emails(lead, campaign)
                )

                # Deterministic send
                send_email(
                    to=lead["email"],
                    subject=email["subject_line"],
                    body=email["body"]
                )
Cost Tracking Dashboard
# backend/orchestration/tasks/deterministic/cost_tracking.py

from prefect import task
from db.supabase import supabase

@task
def log_brain_usage(
    campaign_id: str,
    task_type: str,
    lead_id: str,
    cost_usd: float,
    tokens_used: int = None
):
    """Track all brain costs for billing/optimization"""
    supabase.table("brain_usage").insert({
        "campaign_id": campaign_id,
        "task_type": task_type,  # enrichment, email, classification, objection
        "lead_id": lead_id,
        "cost_usd": cost_usd,
        "tokens_used": tokens_used,
        "created_at": "now()"
    }).execute()

# In your flows, after each brain call:
log_brain_usage(
    campaign_id=campaign_id,
    task_type="enrichment",
    lead_id=lead["id"],
    cost_usd=brain_result.get("brain_cost_usd", 0)
)
Summary: Where Brain Lives
Task
Type
Tool
Fetch from Apollo
Deterministic
API call
Fetch from Clearbit
Deterministic
API call
Merge API data
Deterministic
Python
Calculate ALS
Deterministic
Your algorithm
Deep enrichment
🧠 Brain
SDK
Write email
🧠 Brain
SDK
Classify response
🧠 Brain
SDK
Handle objection
🧠 Brain
SDK
Send email
Deterministic
Salesforge API
Check responses
Deterministic
Salesforge API
Save to DB
Deterministic
Supabase
Next Steps
Start with enrichment brain - biggest ROI, easiest to test
Add cost limits and monitoring - track spend per lead
A/B test - brain-enriched vs API-only conversion rates
Iterate prompts - tune based on output quality
Want me to detail any specific piece further?

The Problem with Voice AI Knowledge Bases
Currently, voice AI (ElevenLabs, Vapi, Bland, etc.) requires you to manually populate a knowledge base:
❌ Static FAQ docs
❌ Generic company info
❌ Same script for every call
❌ Falls apart on unexpected questions
Brain-Powered Knowledge Base
What if the SDK pre-builds a dynamic knowledge base for each call based on everything we know about that specific lead?
┌─────────────────────────────────────────────────────────────┐
│                      BEFORE EACH CALL                        │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │   Enriched   │     │    🧠 SDK    │     │  Voice AI   │  │
│  │   Lead Data  │────▶│   Prepares   │────▶│  Knowledge  │  │
│  │              │     │   Call KB    │     │    Base     │  │
│  └──────────────┘     └──────────────┘     └─────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
What Brain Generates Per Call
CALL_KB_SCHEMA = {
    "prospect": {
        "name": "string",
        "pronunciation": "string",  # Brain figures this out
        "title": "string",
        "company": "string",
        "known_pain_points": ["string"],
        "personality_cues": "string"  # From LinkedIn, podcasts, etc.
    },

    "company_context": {
        "what_they_do": "string (1-2 sentences)",
        "recent_news": ["string"],
        "competitors": ["string"],
        "tech_stack": ["string"],
        "company_culture": "string"
    },

    "conversation_hooks": {
        "openers": ["string"],  # Personalized ice breakers
        "pain_point_questions": ["string"],
        "value_bridges": ["string"]  # Connect their pain to our solution
    },

    "objection_responses": {
        "timing": "string",
        "budget": "string",
        "authority": "string",
        "need": "string",
        "competitor": "string"
    },

    "questions_they_might_ask": [
        {
            "question": "string",
            "answer": "string",
            "source": "string"
        }
    ],

    "do_not_mention": ["string"],  # Sensitive topics to avoid

    "meeting_goal": "string",
    "fallback_goal": "string"  # If meeting not possible
}
The Brain Task
# backend/orchestration/tasks/intelligent/voice_brain.py

from prefect import task
from brain.client import AgencyOSBrain

@task
async def prepare_call_knowledge_base(
    lead: dict,
    campaign_context: dict,
    agency_info: dict
) -> dict:
    """
    Brain prepares a comprehensive knowledge base for a voice AI call.
    """
    brain = AgencyOSBrain(
        max_turns=40,
        cost_limit_usd=0.75  # Worth it for a phone call
    )

    prompt = f"""
    Prepare a knowledge base for an AI phone call to this prospect.

    ## Prospect Data (from enrichment)
    Name: {lead['decision_maker']['name']}
    Title: {lead['decision_maker']['title']}
    Company: {lead['company']}
    Industry: {lead['industry']}
    Company Size: {lead['company_size']}

    Pain Points Found: {lead.get('pain_points', {}).get('points', [])}
    Pain Point Sources: {lead.get('pain_points', {}).get('sources', [])}

    Budget Signals: {lead.get('budget_signals', {}).get('signals', [])}
    Timing Signals: {lead.get('timing_signals', {}).get('signals', [])}

    Tech Stack: {lead.get('tech_stack', {}).get('tools', [])}

    Enrichment Notes: {lead.get('enrichment_notes', '')}

    ## Agency We're Calling On Behalf Of
    Name: {agency_info['name']}
    Services: {agency_info['services']}
    Value Prop: {agency_info['value_prop']}
    Case Studies: {agency_info['case_studies']}
    Differentiators: {agency_info['differentiators']}

    ## Your Tasks

**Research further if needed** - Use web search to find:
Recent news about their company
LinkedIn posts from the decision maker
Any podcasts/interviews they've done
Their company's tone/culture

**Generate conversation openers** - Based on:
Something specific about them (not generic)
Recent news or achievement
Shared connection or interest

**Prepare pain point questions** - Questions that:
Let them discover the pain themselves
Reference what we know without being creepy
Build toward our solution naturally

**Write objection responses** - For each common objection:
Acknowledge their concern
Reference specific data about them if relevant
Bridge to value

**Anticipate their questions** - What will they ask about:
Pricing (use ranges, offer to discuss)
Timeline
Case studies (pick relevant ones)
How it works
Who else you work with

**Identify sensitive topics** - Things to avoid:
Recent layoffs?
Bad press?
Competitor drama?

**Name pronunciation** - Research how to pronounce their name correctly

## Output
Return a complete knowledge base the voice AI can reference during the call.
"""

return await brain.think(
 prompt=prompt,
 tools=["WebSearch", "WebFetch"],
 output_schema=CALL_KB_SCHEMA
)
Example Output
For a call to "Marcus Chen, CMO at GrowthStack":
{
"prospect": {
"name": "Marcus Chen",
"pronunciation": "MAR-kus CHEN",
"title": "Chief Marketing Officer",
"company": "GrowthStack",
"known_pain_points": [
"Mentioned on SaaStr podcast that lead response time is killing conversions",
"LinkedIn post complaining about SDR turnover"
],
"personality_cues": "Direct communicator, data-driven, ex-Google so appreciates efficiency"
},

"company_context": {
"what_they_do": "GrowthStack is a sales enablement platform helping B2B teams close faster. Series B, 80 employees.",
"recent_news": [
"Just raised $12M Series B in November",
"Launched AI features last quarter",
"Hiring 5 marketing roles right now"
],
"competitors": ["Gong", "Outreach", "Salesloft"],
"tech_stack": ["HubSpot", "Salesforce", "Intercom"],
"company_culture": "Fast-paced, metrics-obsessed, startup energy"
},

"conversation_hooks": {
"openers": [
"Congrats on the Series B - saw the TechCrunch piece. Sounds like you're scaling the team fast.",
"Caught your SaaStr podcast episode - your point about lead response time really resonated.",
"Noticed you're hiring 5 marketing roles - must be an exciting time at GrowthStack."
],
"pain_point_questions": [
"You mentioned lead response time on the podcast - is that still a priority?",
"With the new funding, how are you thinking about scaling outbound?",
"What's your current setup for responding to inbound leads?"
],
"value_bridges": [
"That response time issue is exactly why agencies use us - we get their leads contacted in under 5 minutes.",
"Instead of hiring 3 more SDRs, our clients typically see similar results with one plus our platform."
]
},

"objection_responses": {
"timing": "Totally get it. With the Series B, timing might actually be perfect - most of our clients implement during growth phases. Would it help if I sent over a 2-minute case study? Then you can loop back when ready.",
"budget": "Makes sense to be careful with the new funding. Quick question - what are you currently spending on SDR salaries plus tools? Our clients typically see 40% cost reduction. Might be worth a 15-minute comparison.",
"authority": "Appreciate you being upfront. Who would typically make this call - would it be you and your VP of Sales together? Happy to set up a brief intro with both.",
"need": "Sounds like you've got a good rhythm going. Out of curiosity, what's your current lead-to-meeting conversion rate? Just want to make sure I'm not wasting your time if you're already crushing it.",
"competitor": "Oh nice, who are you using? Just curious how they're handling the response time piece you mentioned."
},

"questions_they_might_ask": [
{
"question": "What does this cost?",
"answer": "Depends on volume, but most companies our size work with are in the $2,500-5,000/month range. The ROI conversation is more interesting though - want me to walk through that?",
"source": "Pricing tier 2-3"
},
{
"question": "Who else in SaaS do you work with?",
"answer": "Can't name names without permission, but we work with 3 other Series B sales enablement companies. Similar size to you, similar challenges.",
"source": "Case studies"
},
{
"question": "How is this different from just hiring more SDRs?",
"answer": "SDRs are great for complex conversations. But for speed-to-lead and initial qualification? Our AI handles that in under 5 minutes, 24/7, at a fraction of the cost. Your SDRs then focus on the conversations that actually need a human.",
"source": "Value prop"
}
],

"do_not_mention": [
"They had layoffs in 2023 - don't bring up past headcount",
"Competitor Gong just got negative press - don't pile on"
],

"meeting_goal": "Book a 30-minute demo with Marcus and VP of Sales",
"fallback_goal": "Get permission to send case study and follow up next week"
}
Integration with Voice AI
# backend/orchestration/flows/voice_campaigns.py

from prefect import flow, task
from orchestration.tasks.intelligent.voice_brain import prepare_call_knowledge_base
from orchestration.tasks.deterministic.elevenlabs import update_agent_knowledge_base, trigger_call

@flow(name="voice-outreach-flow")
async def voice_outreach_flow(campaign_id: str):
    """
    Prepare brain-powered knowledge bases and trigger calls.
    """
    campaign = get_campaign(campaign_id)
    leads = get_leads_for_calling(campaign_id)

    for lead in leads:
        # 🧠 Brain prepares custom knowledge base
        call_kb = await prepare_call_knowledge_base(
            lead=lead,
            campaign_context=campaign,
            agency_info=campaign["agency"]
        )

        # Push to voice AI platform
        agent_id = update_agent_knowledge_base(
            base_agent_id=campaign["voice_agent_id"],
            custom_kb=call_kb,
            lead_id=lead["id"]
        )

        # Trigger the call
        call_result = trigger_call(
            agent_id=agent_id,
            phone_number=lead["phone"],
            lead_id=lead["id"]
        )

        # Log for analysis
        log_call_attempt(lead["id"], call_kb, call_result)
The Difference
Without Brain
With Brain
"Hi, this is Sarah from XYZ Agency..."
"Hi Marcus, congrats on the Series B..."
Generic objection handling
References their specific situation
Stumbles on unexpected questions
Prepared for likely questions
Same script for everyone
Personalized hooks and bridges
"Let me transfer you to someone who can help"
Knows the answers or graceful fallback
Cost/Benefit
Item
Cost
Brain KB prep per call
~$0.50-0.75
Voice AI call
~$0.10-0.30/min
Total per quality call
~$1-2
vs. human SDR: $50-100/hour = ~$5-10 per quality call
This Is Your Moat
Most AI calling tools use static knowledge bases. Agency OS would have dynamically generated, lead-specific intelligence for every single call.
Want me to detail the ElevenLabs/Vapi integration specifically?