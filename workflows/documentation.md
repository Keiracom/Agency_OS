# SOP: Documentation

**Role:** Documenter  
**Trigger:** New process, changed workflow, knowledge capture  
**Time estimate:** 15-60 minutes

---

## Overview

Keep documentation current, accurate, and useful. Good docs reduce questions and mistakes.

---

## Documentation Types

| Type | Location | Purpose |
|------|----------|---------|
| SOPs | `workflows/` | How to do specific tasks |
| Task tracking | `tasks/` | What needs doing |
| Memory | `memory/` | Daily logs and context |
| Long-term memory | `MEMORY.md` | Curated important info |
| Agent config | `teams/` | Role definitions |
| Codebase docs | `Agency_OS/docs/` | Technical documentation |

---

## Pre-flight Checklist

- [ ] You know what needs documenting
- [ ] You've reviewed existing related docs
- [ ] You understand the audience (Dave, agents, future devs)

---

## Procedure

### 1. Identify What to Document

- New workflow → create SOP in `workflows/`
- Process change → update existing SOP
- Important event → add to `memory/YYYY-MM-DD.md`
- Lasting knowledge → add to `MEMORY.md`
- Task completion → update `tasks/`

### 2. Write Clear Documentation

**Structure:**
- Start with purpose/overview
- Include prerequisites
- Step-by-step procedure
- Expected outputs
- Escalation paths

**Style:**
- Short sentences
- Active voice
- Concrete examples
- No jargon without explanation

### 3. Review for Quality

- [ ] Would someone new understand this?
- [ ] Are the steps actionable?
- [ ] Is anything missing?
- [ ] Is it consistent with other docs?

### 4. Update Cross-references

If the new doc relates to others:
- Link from relevant SOPs
- Update ROLES.md if role-related
- Update BACKLOG.md if task-related

---

## Output

- [ ] Clear, accurate documentation
- [ ] Consistent formatting with existing docs
- [ ] Cross-references updated
- [ ] Summary of what was documented

---

## Memory Guidelines

### Daily Notes (`memory/YYYY-MM-DD.md`)
- Raw events and facts
- Decisions made
- Problems encountered
- Links to artifacts created

### Long-term Memory (`MEMORY.md`)
- Curated, important information
- Patterns and lessons learned
- Key facts about Dave and Agency OS
- Preferences and decisions that should persist

### When to Update MEMORY.md
- New important fact about Dave or the business
- Lesson learned from a mistake
- Key architectural decision
- Preference discovered
- Remove outdated information

---

## Escalation

If you encounter:
- Conflicting information → ask Dave for source of truth
- Sensitive information → ask before documenting
- Major process changes → get approval before updating
