# SKILL INDEX — Agency OS

**Purpose:** Master index of all skills available for Claude Code agents.  
**Location:** `C:\AI\Agency_OS\skills\`  
**Last Updated:** December 21, 2025

---

## How Skills Work

Skills are structured documentation that Claude Code reads before executing tasks. They provide:
- Detailed specifications
- File structures
- Code patterns
- Implementation order
- Success criteria

**Usage:** Claude Code should read the relevant SKILL.md before starting any related task.

---

## Available Skills

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| Admin Dashboard | `skills/frontend/ADMIN_DASHBOARD.md` | Platform owner dashboard spec | ✅ Complete |
| User Dashboard | `skills/frontend/USER_DASHBOARD.md` | Client-facing dashboard spec | 🔴 Not Started |
| Deployment | `skills/deployment/SKILL.md` | Production deployment procedures | 🔴 Not Started |
| Database | `skills/database/SKILL.md` | Supabase patterns and migrations | 🔴 Not Started |
| Integrations | `skills/integrations/SKILL.md` | Adding new channel integrations | 🔴 Not Started |
| Onboarding | `skills/onboarding/SKILL.md` | New client setup procedures | 🔴 Not Started |
| Troubleshooting | `skills/troubleshooting/SKILL.md` | Common issues and fixes | 🔴 Not Started |
| Agents | `skills/agents/SKILL.md` | QA, Fixer, and agent patterns | 🔴 Not Started |

---

## Skill Template

When creating new skills, use this structure:

```markdown
# SKILL.md — [Skill Name]

**Skill:** [Name]
**Author:** [Who created it]
**Version:** [X.X]
**Created:** [Date]

---

## Purpose

[What this skill enables]

---

## Prerequisites

[What must exist before using this skill]

---

## Specification

[Detailed specification of what to build/do]

---

## Implementation Order

[Step-by-step order]

---

## Success Criteria

[How to know it's done correctly]

---

## Next Steps

[What to do after completing this skill]
```

---

## Skill Priority

For current build phase:

1. **Admin Dashboard** — CEO needs visibility (IN PROGRESS)
2. **Deployment** — Get platform live
3. **User Dashboard** — Expand Phase 8 specs
4. **Troubleshooting** — Prepare for production issues
5. **Others** — As needed

---
