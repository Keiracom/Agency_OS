# Development Review Process

**Effective:** 2026-01-20

## Roles

| Role | Person | Responsibility |
|------|--------|----------------|
| CEO | David | Final approval authority |
| CTO | Claude | Technical reviewer, quality gatekeeper |
| Dev Team | Claude (dev mode) | Implementation |

## Process Flow

```
┌─────────────────┐
│  Dev Team       │
│  Produces Work  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CTO Review     │
│  - Strengths    │
│  - Gaps/Issues  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Approved?│
    └────┬────┘
         │
    No ──┤
         │
         ▼
┌─────────────────┐
│  Dev Revises    │◄──────┐
│  & Resubmits    │       │
└────────┬────────┘       │
         │                │
         ▼                │
┌─────────────────┐       │
│  CTO Re-review  │───────┘
└────────┬────────┘   (loop until approved)
         │
    Yes ─┤
         │
         ▼
┌─────────────────┐
│  CTO Compiles   │
│  Final Report   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CEO Review     │
│  Final Sign-off │
└─────────────────┘
```

## Step Advancement

- CEO says **"continue"** to advance to each next step
- CTO presents each step visibly before moving on
- Process pauses at each step for CEO visibility

## Quality Standards

1. **Best effort first** - No deliberate mistakes
2. **Self-critique** - CTO reviews own work for errors before presenting
3. **Honest assessment** - Genuine strengths and genuine gaps identified
4. **Iteration until right** - No rushing to approval

## Report Format (Final to CEO)

```markdown
## CTO Technical Report

### Summary
[Brief overview of what was built/changed]

### Strengths
- [What's working well]

### Issues Found & Resolved
- [Issues discovered during review and how they were fixed]

### Final State
- [Current status, files changed, tested]

### Recommendation
[CTO recommendation for CEO approval]
```
