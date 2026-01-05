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
| Email | Resend + Smartlead | SendGrid |

**Full details:** `docs/architecture/DECISIONS.md`

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

At end of session, update PROGRESS.md:

```markdown
## Session: [DATE]

### Completed
- [TASK_ID]: [Brief description]

### Next
- [TASK_ID]: [Description]

### Blockers
- [Any issues]
```

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
