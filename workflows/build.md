# SOP: Build (Feature/Fix)

**Role:** Builder  
**Trigger:** Task assigned from backlog  
**Time estimate:** Varies by task

---

## Overview

Implement features or fix bugs according to task specifications.

---

## Pre-flight Checklist

- [ ] Task is clearly defined in BACKLOG.md
- [ ] You understand the acceptance criteria
- [ ] You've reviewed relevant existing code
- [ ] You know which files need changes

---

## Procedure

### 1. Understand the Task

Read:
- Task description in BACKLOG.md
- Related documentation
- Existing code that will be modified
- Any linked issues or specs

### 2. Plan the Work

Before coding:
- List files to modify
- Identify dependencies
- Note potential risks
- Estimate complexity

### 3. Implement

```bash
# Create feature branch
git checkout -b [type]/[short-description]
# e.g., fix/voice-retry-logic, feat/als-enhancement

# Make changes
# Follow existing patterns
# Keep commits atomic and well-described
```

#### Code Standards

**Python (Backend):**
- Type hints on all functions
- Docstrings for public functions
- Follow existing patterns in the file
- Respect 4-layer hierarchy: models → integrations → engines → orchestration

**TypeScript (Frontend):**
- Proper typing (no `any` unless necessary)
- Follow existing component patterns
- Use existing UI components from Aceternity/MagicUI

### 4. Test Locally

```bash
# Run relevant tests
pytest tests/[relevant_test_file].py

# Check linting
ruff check src/

# Frontend checks
cd frontend && npm run lint && npx tsc --noEmit
```

### 5. Create PR

```bash
git add -A
git commit -m "[type]: [description]"
git push origin [branch-name]

gh pr create \
  --title "[Type]: [Description]" \
  --body "## Summary
[What this PR does]

## Task
[Link to BACKLOG.md task]

## Changes
- [file1]: [what changed]
- [file2]: [what changed]

## Testing
- [ ] [How to verify this works]

## Checklist
- [ ] Code follows existing patterns
- [ ] Tests added/updated
- [ ] No new lint errors"
```

---

## Output

- [ ] Working code that meets acceptance criteria
- [ ] PR created with clear description
- [ ] Tests pass
- [ ] Task updated in BACKLOG.md
- [ ] Summary reported to main session

---

## Common Patterns

### Adding Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_external_api():
    ...
```

### Adding a New API Route

1. Add route in `src/api/routes/`
2. Add to router in `src/api/main.py`
3. Add tests in `tests/api/`
4. Update OpenAPI docs if needed

### Modifying Prefect Flows

1. Update flow in `src/orchestration/flows/`
2. Test locally with `prefect server start`
3. Deploy will happen automatically on merge

---

## Escalation

If you encounter:
- Unclear requirements → ask for clarification
- Architecture decisions → discuss with Dave
- Breaking changes → flag and get approval
- External API issues → document and investigate
