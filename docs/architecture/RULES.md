# Rules for Claude Code — Agency OS

**Status:** MANDATORY  
**Violations:** Will be rejected in code review

---

## Absolute Rules (1-10)

1. **Follow the blueprint exactly.** No improvisation.
2. **Never proceed past a checkpoint without CEO approval.**
3. **Never create duplicate systems.** (No Redis workers alongside Prefect)
4. **Never use mock data in production code.**
5. **Never leave incomplete implementations**
6. **Every file must have a contract comment at the top.**
7. **Every implementation must end with verification checklist.**
8. **Update PROGRESS.md after completing each task.**
9. **Before modifying external services, show command and wait for approval.**
10. **If blocked, report immediately with options. Do not guess.**

---

## Architectural Rules (11-20)

11. **Dependency Injection:** Engines accept `db: AsyncSession` as argument
12. **Import Hierarchy:** models → integrations → engines → orchestration
13. **JIT Validation:** All outreach tasks must check client/campaign/lead status
14. **Soft Deletes Only:** Never use hard DELETE
15. **AI Spend Limiter:** All Anthropic calls through spend limiter
16. **Cache Versioning:** All Redis keys include version prefix
17. **Resource-Level Rate Limits:** Rate limits per seat/domain/number
18. **Email Threading:** In-Reply-To headers for follow-ups
19. **Connection Pool Limits:** pool_size=5, max_overflow=10
20. **Webhook-First Architecture:** Cron jobs are safety nets only

---

## Logging Protocol (21-26)

21. **PROGRESS.md updates:** Update status tables only. Max 3 words in Notes column. Keep file under 300 lines total.

22. **Session log:** After each session, append a 5-line entry to `docs/progress/SESSION_LOG.md`:
```
### [Date] — [Brief Title]
**Completed:** [task IDs]
**Summary:** [1-2 sentences]
**Files Changed:** [count or key files]
**Blockers:** [issues or "None"]
**Next:** [next task]
```

23. **Git commits:** Full implementation detail belongs in commit messages, not documentation. Use format:
```
type(scope): description

- Detail 1
- Detail 2

Refs: TASK-001, TASK-002
```

24. **Issues found:** Log to `docs/progress/ISSUES.md` with severity (CRITICAL/WARNING/INFO). Do NOT fix unrelated issues mid-task.

25. **Don't duplicate content:**
    - Task details → Phase spec files
    - Session narrative → SESSION_LOG.md
    - Implementation detail → Git commits
    - PROGRESS.md gets summaries only

26. **Archive monthly:** On the 1st of each month, move previous month's SESSION_LOG entries to `docs/progress/archive/YYYY-MM.md`.

---

## File Contract Comment

Every file must start with:

```python
"""
Contract: [filename]
Purpose: [One line description]
Layer: [1-4] - [models|integrations|engines|orchestration]
Imports: [What this file can import from]
Consumers: [What can import this file]
"""
```

Example:
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

## Verification Checklist

Every implementation must end with a comment block:

```python
# ========================================
# VERIFICATION CHECKLIST
# ========================================
# [ ] Contract comment at top of file
# [ ] No forbidden imports
# [ ] Type hints on all functions
# [ ] Docstrings on public methods
# [ ] Error handling with custom exceptions
# [ ] Logging at appropriate levels
# [ ] Unit tests created
# [ ] PROGRESS.md updated
```

---

## Reference Reading Order

Before starting any task:

1. Read `docs/architecture/DECISIONS.md` — Locked tech choices
2. Read `docs/architecture/IMPORT_HIERARCHY.md` — Layer rules
3. Read relevant phase spec in `docs/phases/` — Task details
4. Read relevant skill in `skills/` — Implementation patterns
5. Check `PROGRESS.md` — Current status

---

## Git Commit Format

```
type(scope): description

Types: feat, fix, docs, style, refactor, test, chore
Scope: phase number or component name

Examples:
feat(phase21): Add landing page hero component
fix(scorer): Correct ALS tier threshold to 85+
docs(blueprint): Extract engine specs to separate files
```

---

## Blocking Situations

If blocked, report with this format:

```
🚫 BLOCKED: [Task ID]

Issue: [What's wrong]
Tried: [What you attempted]
Options:
  A) [Option with tradeoffs]
  B) [Option with tradeoffs]
  C) [Request CEO decision]

Recommendation: [Your suggestion]
```

Do not guess or proceed without resolution.
