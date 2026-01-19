# CLAUDE.md — Agency OS Development Protocol

**READ THIS ENTIRE FILE BEFORE WRITING ANY CODE.**

---

## Quick Start

1. **Read slim blueprint:** `PROJECT_BLUEPRINT.md` (~15KB overview)
2. **Check current tasks:** `PROGRESS.md`
3. **Read phase spec:** `docs/phases/PHASE_XX.md` for your phase
4. **Read relevant skill:** `skills/[category]/SKILL.md`
5. **Start coding**

---

## Documentation Structure (NEW)

```
PROJECT_BLUEPRINT.md          ← Start here (slim overview)
│
├── docs/architecture/        ← System design
│   ├── DECISIONS.md          ← Locked tech choices
│   ├── IMPORT_HIERARCHY.md   ← Layer rules (ENFORCED)
│   ├── RULES.md              ← Claude Code rules
│   └── FILE_STRUCTURE.md     ← Complete file tree
│
├── docs/phases/              ← Phase-specific specs
│   ├── PHASE_INDEX.md        ← All phases overview
│   ├── PHASE_01_FOUNDATION.md
│   ├── ...
│   └── PHASE_21_UI_OVERHAUL.md
│
├── docs/specs/               ← Component specs
│   ├── database/             ← Schema definitions
│   ├── engines/              ← Engine specifications
│   ├── integrations/         ← API wrapper specs
│   ├── pricing/              ← Tier pricing model
│   └── phase16/              ← Conversion Intelligence
│
├── skills/                   ← Implementation patterns
│   └── SKILL_INDEX.md        ← Available skills
│
├── docs/e2e/                 ← E2E Testing System (Phase 21)
│   ├── E2E_MASTER.md         ← Testing dashboard & status
│   ├── E2E_INSTRUCTIONS.md   ← How to execute tests
│   ├── J0-J6 journey files   ← Detailed test specs
│   ├── ISSUES_FOUND.md       ← Problems discovered
│   ├── FIXES_APPLIED.md      ← Changes made during testing
│   └── FILES_CREATED.md      ← New files created
│
├── PROGRESS.md               ← Task tracking (active work)
│
└── PROJECT_BLUEPRINT_FULL_ARCHIVE.md  ← Original full blueprint
```

---

## Before Starting Any Task

```
1. Read PROJECT_BLUEPRINT.md (quick overview)
2. Read docs/phases/PHASE_XX.md (your phase details)
3. Read relevant skill in skills/ (implementation patterns)
4. Check PROGRESS.md (what's done, what's next)
5. Ask CEO: "Ready to start [TASK_ID]?"
```

---

## CRITICAL CONSTRAINTS

### 🚫 DO NOT

- **DO NOT** skip reading phase spec before coding
- **DO NOT** proceed past checkpoints without CEO approval
- **DO NOT** use Redis for task queues (use Prefect)
- **DO NOT** use Clerk for auth (use Supabase Auth)
- **DO NOT** import engines from other engines
- **DO NOT** instantiate database sessions inside engines
- **DO NOT** use hard DELETE (use soft delete)
- **DO NOT** create files not in the blueprint/phase spec
- **DO NOT** call paid APIs without CEO approval and cost estimate
- **DO NOT** create E2E testing files outside of `docs/e2e/` (single source of truth)
- **DO NOT** create E2E prompts in `prompts/` — use `docs/e2e/E2E_INSTRUCTIONS.md`

### ✅ DO

- **DO** read the phase spec before each task
- **DO** read relevant skills for implementation patterns
- **DO** complete ONE task fully before the next
- **DO** update PROGRESS.md after each task
- **DO** follow import hierarchy (models → integrations → engines → orchestration)

---

## Import Hierarchy (ENFORCED)

```
Layer 4: src/orchestration/  → Can import ALL below
Layer 3: src/engines/        → models, integrations ONLY
Layer 2: src/integrations/   → models ONLY  
Layer 1: src/models/         → exceptions ONLY
```

**Full details:** `docs/architecture/IMPORT_HIERARCHY.md`

If you need data from another engine, pass it as argument from orchestration layer.

---

## ALS Tiers (CRITICAL)

| Tier | Score | Note |
|------|-------|------|
| Hot | **85-100** | NOT 80-100 |
| Warm | 60-84 | |
| Cool | 35-59 | |
| Cold | 20-34 | |
| Dead | <20 | |

**Full formula:** `docs/specs/engines/SCORER_ENGINE.md`

---

## SDK Integration for Hot Leads (CRITICAL)

**Hot leads (ALS 85+) MUST use SDK-enhanced methods.** SDK provides hyper-personalized content using Claude Agent SDK with web research tools.

### SDK Routing Rules

| Channel | Standard Method | SDK Method | When to Use SDK |
|---------|-----------------|------------|-----------------|
| **Enrichment** | `scout.enrich_lead()` | `scout.enrich_lead_with_sdk()` | Hot + priority signals |
| **Email** | `content.generate_email()` | `content.generate_email_with_sdk()` | ALL Hot leads |
| **Voice KB** | N/A | `voice.generate_voice_kb()` | ALL Hot leads |
| **Voice Call** | `voice.send()` | `voice.create_campaign_assistant_with_kb()` | ALL Hot leads |

### SDK Files Location

```
src/agents/sdk_agents/
├── __init__.py              # Exports all SDK agents
├── sdk_eligibility.py       # Gate functions (should_use_sdk_*)
├── enrichment_agent.py      # Deep research agent
├── email_agent.py           # Personalized email agent
├── voice_kb_agent.py        # Voice knowledge base agent
├── icp_agent.py             # ICP extraction agent
└── sdk_tools.py             # Web search/fetch tools
```

### SDK Eligibility Functions

```python
from src.agents.sdk_agents import (
    should_use_sdk_enrichment,  # Hot + signals → True/False, signals
    should_use_sdk_email,       # Hot → True/False
    should_use_sdk_voice_kb,    # Hot → True/False
)

# Check before content generation
lead_data = {"als_score": 88, ...}
if should_use_sdk_email(lead_data):
    result = await content.generate_email_with_sdk(db, lead_id, campaign_id)
else:
    result = await content.generate_email(db, lead_id, campaign_id)
```

### Priority Signals (for SDK Enrichment)

SDK enrichment triggers for Hot leads with at least ONE signal:
1. **Recent funding** - `company_latest_funding_date` < 90 days
2. **Actively hiring** - `company_open_roles` >= 3
3. **Tech stack match** - `tech_stack_match_score` > 0.8
4. **LinkedIn engaged** - `linkedin_engagement_score` > 70
5. **Referral source** - `source` == "referral"
6. **Sweet spot size** - 50 <= `company_employee_count` <= 500

### SDK Cost Controls

| Agent | Max Cost (AUD) | Max Turns |
|-------|----------------|-----------|
| Enrichment | $1.50 | 8 |
| Email | $0.50 | 3 |
| Voice KB | $2.00 | 3 |

### Database Fields for SDK

Lead model has SDK fields (migration 035):
- `sdk_enrichment` (JSONB) - Enrichment data
- `sdk_signals` (TEXT[]) - Triggered signals
- `sdk_cost_aud` (DECIMAL) - Cost tracking
- `sdk_enriched_at` (TIMESTAMP) - When enriched
- `sdk_voice_kb` (JSONB) - Voice knowledge base
- `sdk_email_content` (JSONB) - Generated email

### ✅ Integration Status (All Fixed)

All orchestration flows now properly route Hot leads to SDK:

| Flow | File | Status |
|------|------|--------|
| Email Outreach | `outreach_flow.py` | ✅ Uses `generate_email_with_sdk()` for Hot |
| Voice Call | `outreach_tasks.py` | ✅ Generates voice KB for Hot before call |
| Enrichment | `enrichment_flow.py` | ✅ SDK enrichment for Hot with signals |
| Pool Enrich | `lead_enrichment_flow.py` | ✅ Full SDK pipeline for Hot leads |

**Pattern used in flows:**
```python
# In orchestration flows - SDK routing for Hot leads
from src.agents.sdk_agents import should_use_sdk_email, should_use_sdk_voice_kb

lead_data = {"als_score": lead.als_score, ...}
if should_use_sdk_email(lead_data):  # Hot check (ALS >= 85)
    result = await content.generate_email_with_sdk(...)
else:
    result = await content.generate_email(...)
```

### SDK Enhancement Opportunities (Future)

1. **LinkedIn SDK** - Personalized connection requests for Hot leads
2. **SMS SDK** - Research-informed SMS for Hot leads
3. **Reply Objection Agent** - SDK-powered objection handling
4. **Meeting Prep Agent** - Auto-generate call briefs
5. **ICP Refiner** - Learn from results to improve ICP

---

## Technology Stack (LOCKED)

| Component | Use This | NOT This |
|-----------|----------|----------|
| Orchestration | Prefect | Celery, Redis queues |
| Agent Framework | Pydantic AI | LangChain, CrewAI |
| Auth | Supabase Auth | Clerk, Auth0 |
| Database | Supabase PostgreSQL | Firebase, MongoDB |
| Cache | Redis (Upstash) | Memcached |
| Email | Salesforge | Resend, SendGrid, Smartlead |

**Full details:** `docs/architecture/DECISIONS.md`

---

## Paid API Usage (REQUIRES APPROVAL)

**Before calling ANY paid API, you MUST:**
1. Ask CEO for permission
2. Provide estimated cost
3. Wait for approval

### API Cost Reference

| API | Operation | Cost | Unit |
|-----|-----------|------|------|
| **Apollo** | People Search | 1 credit | per person |
| **Apollo** | Email Reveal | 1 credit | per email |
| **Apollo** | Org Enrichment | 1 credit | per company |
| **Apify** | LinkedIn Profile Scrape | ~$0.01-0.05 | per profile |
| **Apify** | LinkedIn Company Scrape | ~$0.01-0.05 | per company |
| **Apify** | Google Search | ~$0.001 | per search |
| **Clay** | Person Enrichment | 1-5 credits | per person |
| **Anthropic** | Claude API | varies | per token |
| **Salesforge** | Email Send | Included | per mailbox/month |
| **Twilio** | SMS Send | ~$0.01 | per SMS |
| **Twilio** | Voice Call | ~$0.02/min | per minute |

### Example Approval Request

```
"I need to run Apollo search for 25 leads.
Estimated cost: 25 credits (~$25 at $1/credit).
Approve?"
```

**DO NOT proceed without explicit "yes" from CEO.**

### Testing Requirements

- **Prefect Flows:** All E2E testing must go through Prefect flows (not manual Python)
- **Real Data:** Use real APIs - just ask for permission first with cost estimate
- **TEST_MODE:** Ensure TEST_MODE=true on Railway before outreach testing

---

## E2E Testing

### Single Source of Truth

**`docs/e2e/e2e_state.json` is the ONLY place that tracks E2E progress.**

- Do NOT read status from markdown files
- Do NOT update status in markdown files
- Markdown files contain instructions only

### Commands

| Command | Who | Purpose |
|---------|-----|---------|
| `/e2e status` | Anyone | Show current state from JSON |
| `/e2e approve` | CEO | Approve next group (required) |
| `/e2e continue` | Claude | Execute next group (requires approval) |

### Workflow

```
1. /e2e status     → See current state
2. /e2e approve    → CEO approves next group
3. /e2e continue   → Claude executes, updates JSON, STOPS
4. Repeat
```

### Enforcement

- `/e2e continue` REFUSES to run unless status = "approved"
- Claude cannot bypass the approval gate
- One group per command, then STOP

### Files

| File | Purpose |
|------|---------|
| `docs/e2e/e2e_state.json` | **ONLY source of truth** |
| `docs/e2e/e2e_config.json` | Test configuration |
| `docs/e2e/J*_*.md` | Journey instructions (no status) |
| `docs/e2e/ISSUES_FOUND.md` | Issue log |
| `docs/e2e/FIXES_APPLIED.md` | Fix log |

---

## Task Completion Protocol

```
1. Read task in phase spec
2. Read any relevant skill
3. Create file(s) with contract comment
4. Write test if specified
5. Run test to verify
6. Update PROGRESS.md
7. Report: "Completed [TASK_ID]. Ready for [NEXT_TASK_ID]?"
```

---

## File Contract Comment

Every file must start with:

```python
"""
Contract: src/engines/scorer.py
Purpose: Calculate ALS (Agency Lead Score) for leads
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only
"""
```

---

## Session Handoff

At end of session, append to `docs/progress/SESSION_LOG.md`:

```markdown
### [Date] — [Brief Title]
**Completed:** [task IDs]
**Summary:** [1-2 sentences]
**Files Changed:** [count or key files]
**Blockers:** [issues or "None"]
**Next:** [next task]
```

---

## Logging Protocol

**Where to log what:**

| Content Type | Location | Max Size |
|--------------|----------|----------|
| Status updates | `PROGRESS.md` | 300 lines |
| Session summaries | `docs/progress/SESSION_LOG.md` | 5 lines per session |
| Issues found | `docs/progress/ISSUES.md` | Log and continue |
| Implementation detail | Git commit messages | Unlimited |

**Rules:**
- PROGRESS.md = roadmap + status only (no narratives)
- Don't fix unrelated issues mid-task — log to ISSUES.md
- Full protocol: `docs/architecture/RULES.md` rules 21-26

---

## Getting Help

If unsure:
```
"I'm about to [action].
The spec says [X].
I interpret this as [Y].
Is this correct?"
```

DO NOT guess. ASK.

---

## Reference Quick Links

| Need | Location |
|------|----------|
| Architecture decisions | `docs/architecture/DECISIONS.md` |
| Import rules | `docs/architecture/IMPORT_HIERARCHY.md` |
| Claude Code rules | `docs/architecture/RULES.md` |
| Phase details | `docs/phases/PHASE_INDEX.md` |
| Database schema | `docs/specs/database/SCHEMA_OVERVIEW.md` |
| Engine specs | `docs/specs/engines/ENGINE_INDEX.md` |
| Integration specs | `docs/specs/integrations/INTEGRATION_INDEX.md` |
| Skills | `skills/SKILL_INDEX.md` |
| Task tracking | `PROGRESS.md` |
| **E2E Testing** | `docs/e2e/E2E_MASTER.md` |
| E2E Instructions | `docs/e2e/E2E_INSTRUCTIONS.md` |
| **Financial Advisor Agent** | `xero/data/pay/CLAUDE.md` |
| Full original blueprint | `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` |

---

## Australian Financial Advisor Agent

For Australian tax, accounting, or Xero questions, read `xero/data/pay/advisor.py` and use it.

Covers: Tax, super, GST, BAS, payroll, deductions, Xero API, and 284 topics across 21 modules.

---

## Production Infrastructure Access

### Railway CLI (Backend/Prefect)

**First-time setup or when session expires:**
```bash
railway login
```
This opens a browser for authentication. User must run this manually in their terminal.

**Common commands (after login):**
```bash
# Check auth status
railway whoami

# View project status
railway status

# List variables for a service
railway variables --service prefect-server --kv

# Set a variable
railway variables --service prefect-server --set "VAR_NAME=value"

# Redeploy a service
railway redeploy --service prefect-server --yes

# View logs
railway logs --service prefect-server
```

**Available services:**
- `agency-os` - Main FastAPI backend
- `prefect-server` - Prefect UI/API server
- `prefect-worker` - Prefect flow executor

**Project ID:** `fef5af27-a022-4fb2-996b-cad099549af9`

### Supabase (Database)

**Direct API access (no CLI auth needed):**
```bash
# Query with service role key
curl -X GET "https://jatzvazlbusedwsnqxzr.supabase.co/rest/v1/TABLE_NAME" \
  -H "apikey: SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer SERVICE_ROLE_KEY"
```

**Connection strings (from `config/RAILWAY_ENV_VARS.txt`):**
- REST API: `https://jatzvazlbusedwsnqxzr.supabase.co`
- Database (pooler): `postgresql://postgres.jatzvazlbusedwsnqxzr:PASSWORD@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres`

### Vercel (Frontend)

**Commands:**
```bash
cd frontend
vercel whoami
vercel env ls
vercel --prod  # Deploy
```

### Production URLs

| Service | URL |
|---------|-----|
| Backend API | https://agency-os-production.up.railway.app |
| Health Check | https://agency-os-production.up.railway.app/api/v1/health/ready |
| Prefect UI | https://prefect-server-production-f9b1.up.railway.app |
| Frontend | https://agency-os-liart.vercel.app |
| Supabase | https://jatzvazlbusedwsnqxzr.supabase.co |

### Troubleshooting

**Railway "Unauthorized" error:**
1. User runs `railway login` in their terminal (not Claude)
2. Browser opens for OAuth
3. Claude can then use Railway CLI

**Prefect flow runs disappearing:**
- Cause: SQLite default loses data on container restart
- Fix: Set `PREFECT_API_DATABASE_CONNECTION_URL` to PostgreSQL on prefect-server service

---

## Sentry Error Tracking

### Checking for Errors (Claude Workflow)

When asked to check for errors or debug production issues:

```bash
# Query recent errors via Sentry API
curl -s "https://sentry.io/api/0/projects/david-stephens-1q/agency-os-backend/issues/?query=is:unresolved" \
  -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" | jq '.[] | {title, culprit, count, lastSeen}'
```

Or use WebFetch:
```
URL: https://sentry.io/api/0/projects/david-stephens-1q/agency-os-backend/issues/
Header: Authorization: Bearer <SENTRY_AUTH_TOKEN from config/RAILWAY_ENV_VARS.txt>
```

### What Sentry Captures

| Component | What's tracked |
|-----------|---------------|
| **API (FastAPI)** | All exceptions, 500 errors, request context |
| **Prefect Worker** | Flow failures, task errors |
| **Integrations** | Apollo/Resend/etc API failures with context |
| **Frontend** | JavaScript errors, user actions before crash |

### Sentry Dashboard

- **Issues:** https://david-stephens-1q.sentry.io/issues/
- **Project Settings:** https://david-stephens-1q.sentry.io/settings/projects/agency-os-backend/

### Adding Custom Error Tracking

For business logic errors that don't throw exceptions:

```python
from src.integrations.sentry_utils import capture_business_error

# Example: Lead score anomaly
if lead.score > 100:
    capture_business_error(
        "scoring_anomaly",
        f"Lead score exceeded maximum: {lead.score}",
        context={"lead_id": str(lead.id), "score": lead.score}
    )
```

---

## CI/CD Pipeline

### What Runs on Every PR/Push

| Job | Tool | What it checks |
|-----|------|----------------|
| `backend-lint` | Ruff | Code style, imports, common bugs |
| `backend-typecheck` | MyPy | Type annotations |
| `backend-test` | Pytest | Unit/integration tests |
| `frontend-check` | ESLint + TSC | Lint + types + build |

### Auto-Deploy on Main

When code is merged to `main`:
1. All checks must pass
2. Railway automatically deploys `agency-os` service
3. Vercel automatically deploys frontend (configured separately)

### GitHub Secrets Required

Add these in GitHub repo → Settings → Secrets → Actions:

| Secret | Where to get it |
|--------|-----------------|
| `RAILWAY_TOKEN` | https://railway.app/account/tokens → Create token |

### Running Checks Locally

```bash
# Lint
ruff check src/

# Format
ruff format src/

# Type check
mypy src/ --ignore-missing-imports

# Tests
pytest tests/ -v
```

### Workflow File

`.github/workflows/ci.yml` - edit to add/remove checks
