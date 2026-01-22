# Development Review Process

**Effective:** 2026-01-20
**Updated:** 2026-01-20 (Added due diligence audit requirement)

## Roles

| Role | Person | Responsibility |
|------|--------|----------------|
| CEO | David | Final approval authority |
| CTO | Claude | Technical reviewer, quality gatekeeper, code auditor |
| Dev Team | Claude (dev mode) | Implementation |

## Process Flow

```
┌─────────────────────┐
│  STEP 0: DUE        │
│  DILIGENCE AUDIT    │
│  (Audit codebase    │
│  before ANY work)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Dev Team           │
│  Produces Work      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CTO Review         │
│  - Strengths        │
│  - Gaps/Issues      │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │Approved?│
      └────┬────┘
           │
      No ──┤
           │
           ▼
┌─────────────────────┐
│  Dev Revises        │◄──────┐
│  & Resubmits        │       │
└──────────┬──────────┘       │
           │                  │
           ▼                  │
┌─────────────────────┐       │
│  CTO Re-review      │───────┘
└──────────┬──────────┘   (loop until approved)
           │
      Yes ─┤
           │
           ▼
┌─────────────────────┐
│  CTO CODE CHECK     │
│  (All code reviewed │
│  before going live) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CTO Compiles       │
│  Final Report       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CEO Review         │
│  Final Sign-off     │
└─────────────────────┘
```

## Step Advancement

- CEO says **"continue"** to advance to each next step
- CTO presents each step visibly before moving on
- Process pauses at each step for CEO visibility

## Due Diligence Audit (Step 0)

**BEFORE any architecture/implementation work begins:**

1. **Read the spec** — Understand what needs to be built
2. **Audit existing code** — Search codebase for related files, services, models
3. **Identify what exists** — Document current state (tables, models, services)
4. **Identify what's missing** — Gap between spec and current state
5. **Present audit findings** — Show CEO before dev work starts

This prevents:
- Duplicate implementations
- Breaking existing functionality
- Missing integration points
- Wasted effort on already-built features

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
