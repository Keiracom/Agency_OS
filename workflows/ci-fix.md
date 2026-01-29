# SOP: CI Fix

**Role:** Linter  
**Trigger:** CI pipeline fails  
**Time estimate:** 15 min - 2 hours depending on error count

---

## Overview

Fix code style and type errors so CI passes. This unblocks all other work.

---

## Pre-flight Checklist

- [ ] CI is actually failing (check GitHub Actions)
- [ ] You have the repo cloned and up to date
- [ ] You understand what checks are failing

---

## Procedure

### 1. Identify Failures

```bash
# Check recent CI runs
gh run list --limit 5

# Get details on latest failure
gh run view [run-id] --log-failed
```

### 2. Fix Ruff (Python) Errors

```bash
cd Agency_OS

# See all errors
ruff check src/

# Auto-fix what's possible
ruff check src/ --fix

# For remaining errors, fix manually
# Common issues:
# - Unused imports → delete them
# - Line too long → break into multiple lines
# - Missing newline at EOF → add it
```

### 3. Fix TypeScript Errors

```bash
cd Agency_OS/frontend

# See all errors
npx tsc --noEmit

# Common fixes:
# - "No overload matches" → check function signature
# - "Type X not assignable to Y" → fix the type or cast
# - Missing imports → add them
```

### 4. Verify Locally

```bash
# Run the same checks CI runs
ruff check src/
cd frontend && npx tsc --noEmit
```

### 5. Create PR

```bash
git checkout -b fix/ci-lint-errors
git add -A
git commit -m "fix: resolve CI lint and type errors"
git push origin fix/ci-lint-errors
gh pr create --title "Fix CI pipeline" --body "Resolves lint and type errors blocking CI"
```

---

## Output

- [ ] All ruff checks pass
- [ ] All TypeScript checks pass  
- [ ] PR created and ready for review
- [ ] Summary of changes in PR description

---

## Escalation

If you encounter:
- Errors that require logic changes → escalate to Builder
- Errors in generated/third-party code → document and skip
- Conflicting style rules → ask Dave for preference
