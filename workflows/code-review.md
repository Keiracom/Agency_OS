# SOP: Code Review

**Role:** Reviewer  
**Trigger:** PR ready for review  
**Time estimate:** 15-60 minutes depending on PR size

---

## Overview

Review code changes for quality, security, and correctness before merge.

---

## Pre-flight Checklist

- [ ] PR has a clear title and description
- [ ] CI passes (if not, send back to Linter)
- [ ] Changes are scoped appropriately (not too big)

---

## Review Checklist

### 1. Correctness
- [ ] Does the code do what the PR says it does?
- [ ] Are edge cases handled?
- [ ] Are error states handled gracefully?

### 2. Security
- [ ] No secrets/credentials in code
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Input validation present
- [ ] Auth checks in place for protected routes

### 3. Performance
- [ ] No obvious N+1 queries
- [ ] No blocking operations in async code
- [ ] Reasonable database query complexity

### 4. Maintainability
- [ ] Code is readable and self-documenting
- [ ] No duplicated logic
- [ ] Follows existing patterns in codebase
- [ ] Appropriate comments for complex logic

### 5. Testing
- [ ] Tests added for new functionality
- [ ] Existing tests still pass
- [ ] Edge cases covered

### 6. Agency OS Specific
- [ ] Follows 4-layer import hierarchy (models → integrations → engines → orchestration)
- [ ] Uses correct terminology (see design spec)
- [ ] ALS scoring logic unchanged unless intentional
- [ ] No hardcoded URLs or credentials

---

## Procedure

### 1. Read the PR

```bash
gh pr view [number]
gh pr diff [number]
```

### 2. Check Files Changed

Focus on:
- `src/` — business logic
- `frontend/src/` — UI changes
- `tests/` — test coverage
- Config files — deployment impact

### 3. Leave Comments

For issues:
```
**Issue:** [description]
**Suggestion:** [how to fix]
**Severity:** blocker / should-fix / nit
```

For questions:
```
**Question:** [what you want to understand]
```

### 4. Make Decision

- **Approve** — Ready to merge
- **Request Changes** — Has blockers
- **Comment** — Questions but no blockers

```bash
gh pr review [number] --approve
gh pr review [number] --request-changes --body "..."
gh pr review [number] --comment --body "..."
```

---

## Output

- [ ] Review comments posted
- [ ] Clear approve/reject decision
- [ ] Summary of findings
- [ ] Any follow-up tasks identified

---

## Escalation

If you encounter:
- Major architecture concerns → discuss with Dave
- Security vulnerabilities → flag immediately
- Breaking changes → ensure Dave is aware before merge
