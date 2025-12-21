# CLAUDE.md — Agency OS Development Protocol

**READ THIS ENTIRE FILE BEFORE WRITING ANY CODE.**

---

## STOP. READ THE BLUEPRINT FIRST.

Before doing ANYTHING:
1. Open `PROJECT_BLUEPRINT.md`
2. Read PART 9 (Rules for Claude Code)
3. Read the current phase you're working on
4. Only then proceed

---

## CRITICAL CONSTRAINTS

### 🚫 DO NOT

- **DO NOT** read `.env` or connect to any external services until explicitly told
- **DO NOT** skip ahead to future phases
- **DO NOT** install packages not listed in the blueprint
- **DO NOT** create files not listed in the blueprint
- **DO NOT** use Redis for task queues (use Prefect)
- **DO NOT** use Clerk for auth (use Supabase Auth)
- **DO NOT** write your own agent framework (use Pydantic AI)
- **DO NOT** import engines from other engines
- **DO NOT** instantiate database sessions inside engines
- **DO NOT** use hard DELETE (use soft delete with deleted_at)
- **DO NOT** proceed past checkpoints without CEO approval

### ✅ DO

- **DO** read the blueprint before each task
- **DO** complete ONE task fully before starting the next
- **DO** write the test file alongside the implementation
- **DO** update PROGRESS.md after each task
- **DO** ask for clarification if something is ambiguous
- **DO** follow the exact file structure in PART 2
- **DO** use the exact packages listed in PART 4

---

## EXECUTION PROTOCOL

### Starting a New Session

```
1. Read CLAUDE.md (this file)
2. Read PROGRESS.md to see what's done
3. Read PROJECT_BLUEPRINT.md for context
4. Identify the NEXT incomplete task
5. Ask CEO: "Ready to start [TASK_ID]?"
6. Wait for approval before coding
```

### Completing a Task

```
1. Read the task row in the blueprint
2. Read any related engine/schema specs in PART 5-8
3. Create the file(s) listed
4. Write the test file if specified
5. Run the test to verify
6. Add contract comment at top of each file
7. Add verification checklist at bottom
8. Update PROGRESS.md
9. Report completion: "Completed [TASK_ID]. Ready for [NEXT_TASK_ID]?"
```

### At Checkpoints

```
1. STOP completely
2. Report: "Checkpoint [N] reached. Awaiting CEO approval."
3. DO NOT proceed until CEO says "APPROVED"
```

---

## FILE TEMPLATES

### Contract Comment (Top of Every File)

```python
"""
FILE: src/engines/scout.py
PURPOSE: Enrich leads via Cache → Apollo+Apify → Clay waterfall
PHASE: 4 (Engines)
TASK: ENG-002
DEPENDENCIES: 
  - src/integrations/redis.py
  - src/integrations/apollo.py
  - src/integrations/clay.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 16: Cache versioning (v1 prefix)
  - Rule 4: Validation threshold 0.70
"""
```

### Verification Checklist (Bottom of Every File)

```python
# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (not instantiated)
# [x] No imports from other engines
# [x] Soft delete check in queries (deleted_at IS NULL)
# [x] Test file created: tests/test_engines/test_scout.py
# [x] All functions have type hints
# [x] All functions have docstrings
```

---

## TECHNOLOGY STACK (LOCKED)

| Component | Use This | NOT This |
|-----------|----------|----------|
| Orchestration | Prefect (self-hosted) | Celery, Redis queues, custom workers |
| Agent Framework | Pydantic AI | LangChain, CrewAI, custom agents |
| Auth | Supabase Auth | Clerk, Auth0, custom JWT |
| Database | Supabase PostgreSQL | Firebase, MongoDB, custom |
| Cache | Redis (Upstash) | Memcached, local cache |
| Email | Resend | SendGrid, Mailgun |
| API | FastAPI | Flask, Django |

---

## IMPORT HIERARCHY (ENFORCED)

```
ALLOWED IMPORTS:

src/models/*.py
  ├── Can import: src/exceptions.py
  └── Cannot import: engines, integrations, orchestration

src/integrations/*.py
  ├── Can import: src/models/*, src/exceptions.py
  └── Cannot import: engines, orchestration

src/engines/*.py
  ├── Can import: src/models/*, src/integrations/*, src/exceptions.py
  └── Cannot import: other engines, orchestration

src/orchestration/*.py
  ├── Can import: everything above
  └── This is the glue layer
```

If you need data from another engine, **pass it as an argument** from the orchestration layer.

---

## COMMON MISTAKES TO AVOID

### ❌ Wrong: Instantiating session in engine
```python
class ScoutEngine:
    def __init__(self):
        self.db = AsyncSessionLocal()  # WRONG
```

### ✅ Correct: Session passed by caller
```python
class ScoutEngine:
    async def enrich(self, db: AsyncSession, domain: str):  # CORRECT
        ...
```

---

### ❌ Wrong: Importing another engine
```python
# In scorer.py
from src.engines.allocator import get_channels  # WRONG
```

### ✅ Correct: Data passed from orchestration
```python
# In enrichment_flow.py
channels = await allocator.get_channels(db, als_result)
score = await scorer.score(db, lead, channels)  # Pass data
```

---

### ❌ Wrong: Hard delete
```python
await db.delete(campaign)  # WRONG
```

### ✅ Correct: Soft delete
```python
campaign.deleted_at = datetime.utcnow()  # CORRECT
await db.commit()
```

---

## SESSION HANDOFF

At the end of every session, update PROGRESS.md with:

```markdown
## Session: [DATE]

### Completed
- [TASK_ID]: [Brief description]

### Current State
- Last completed task: [TASK_ID]
- Next task: [TASK_ID]
- Blockers: [Any issues]

### Files Modified
- path/to/file.py - [what changed]
```

---

## ASKING FOR HELP

If you're unsure about anything:

```
"I'm about to [action]. 
The blueprint says [X]. 
I interpret this as [Y]. 
Is this correct, or should I [Z]?"
```

DO NOT guess. DO NOT assume. ASK.

---

## THE GOLDEN RULE

**Complete one task. Verify it works. Update progress. Then move to the next.**

No parallelization. No skipping ahead. No assumptions.

---

## ACKNOWLEDGMENT

Before starting ANY work, respond with:

```
"I have read CLAUDE.md and PROJECT_BLUEPRINT.md.
Current phase: [N]
Next task: [TASK_ID]
Ready to proceed?"
```

Wait for CEO approval before writing any code.
