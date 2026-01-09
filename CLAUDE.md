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

## Technology Stack (LOCKED)

| Component | Use This | NOT This |
|-----------|----------|----------|
| Orchestration | Prefect | Celery, Redis queues |
| Agent Framework | Pydantic AI | LangChain, CrewAI |
| Auth | Supabase Auth | Clerk, Auth0 |
| Database | Supabase PostgreSQL | Firebase, MongoDB |
| Cache | Redis (Upstash) | Memcached |
| Email | Resend + Salesforge | SendGrid, Smartlead |

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
| **Resend** | Email Send | $0.001 | per email |
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
| Full original blueprint | `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` |
