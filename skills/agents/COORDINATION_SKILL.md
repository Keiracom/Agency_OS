# SKILL.md — Agent Pipeline Coordination

**Skill:** Three-Agent Pipeline for Agency OS  
**Author:** CTO (Claude)  
**Version:** 2.0  
**Created:** December 24, 2025

---

## Overview

The Agency OS development pipeline uses three specialized Claude Code agents working in parallel. Each agent has a specific role and communicates through files.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   BUILDER (Terminal 1)       QA (Terminal 2)        FIXER (Terminal 3)  │
│   ────────────────────      ────────────────       ─────────────────    │
│                                                                         │
│   Creates new files          Scans for issues       Fixes violations    │
│   Completes stubs            Categorizes issues     Documents fixes     │
│   Updates PROGRESS.md        Routes to handler      Skips MISSING       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Responsibilities

| Agent | Primary Job | Reads | Writes |
|-------|-------------|-------|--------|
| **Builder** | Create production code | PROGRESS.md, builder_tasks/, skills/ | src/, frontend/, PROGRESS.md |
| **QA** | Detect issues, route correctly | src/, frontend/, PROGRESS.md, fixer_reports/ | qa_reports/, builder_tasks/ |
| **Fixer** | Fix violations only | qa_reports/, PROGRESS.md, skills/ | src/, frontend/, fixer_reports/ |

---

## Issue Routing

**Critical concept: QA categorizes, then routes to the correct handler.**

```
                         QA AGENT SCANS
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
          MISSING        VIOLATION        INCOMPLETE
              │               │               │
              ▼               ▼               ▼
        builder_tasks/   qa_reports/    builder_tasks/
              │               │               │
              ▼               ▼               ▼
          BUILDER          FIXER          BUILDER
          creates          fixes          completes
```

| Issue Type | Handler | Written To | Example |
|------------|---------|------------|---------|
| MISSING | Builder | builder_tasks/pending.md | File doesn't exist |
| INCOMPLETE | Builder | builder_tasks/pending.md | File has stubs |
| CRITICAL | Fixer | qa_reports/report_*.md | Import hierarchy |
| HIGH | Fixer | qa_reports/report_*.md | Missing contract |
| MEDIUM | (logged) | qa_reports/report_*.md | TODO comment |
| LOW | (logged) | qa_reports/report_*.md | Style issue |

---

## File Structure

```
C:\AI\Agency_OS\
│
├── Agents/
│   ├── Builder Agent/
│   │   ├── BUILDER_AGENT_PROMPT.md     # Copy to start Builder
│   │   ├── BUILDER_CONSTITUTION.md     # Builder rules
│   │   └── builder_tasks/
│   │       └── pending.md              # QA writes, Builder reads
│   │
│   ├── QA Agent/
│   │   ├── QA_AGENT_PROMPT.md          # Copy to start QA
│   │   ├── QA_CONSTITUTION.md          # QA rules
│   │   └── qa_reports/
│   │       ├── report_*.md             # Scan reports
│   │       └── status.md               # Current status
│   │
│   ├── Fixer Agent/
│   │   ├── FIXER_AGENT_PROMPT.md       # Copy to start Fixer
│   │   ├── FIXER_CONSTITUTION.md       # Fixer rules
│   │   └── fixer_reports/
│   │       ├── fixes_*.md              # Fix logs
│   │       ├── status.md               # Fixer status
│   │       └── needs_human.md          # Escalated issues
│   │
│   └── QUICKSTART.md                   # Setup guide
│
├── skills/
│   ├── SKILL_INDEX.md                  # Master index
│   └── agents/
│       ├── BUILDER_SKILL.md            # Builder patterns
│       ├── QA_SKILL.md                 # QA patterns
│       ├── FIXER_SKILL.md              # Fixer patterns
│       └── COORDINATION_SKILL.md       # This file
│
├── PROJECT_BLUEPRINT.md                # Source of truth
└── PROGRESS.md                         # Build status
```

---

## Dynamic Context Detection

**All three agents detect context the same way:**

```
1. READ PROGRESS.md
   └── Find current phase (look for 🟡)
   └── Find active tasks

2. READ skills/SKILL_INDEX.md
   └── Find skill file for current phase

3. READ the relevant skill file
   └── Understand requirements
   └── Apply context-specific patterns
```

This makes the agents work for ANY phase — Admin Dashboard, ICP Discovery, or future builds.

---

## The Complete Loop

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  BUILDER creates code                                                   │
│       │                                                                 │
│       ▼                                                                 │
│  QA scans (every 90 seconds)                                            │
│       │                                                                 │
│       ├──── MISSING/INCOMPLETE ────▶ builder_tasks/pending.md           │
│       │                                      │                          │
│       │                                      ▼                          │
│       │                               BUILDER creates file              │
│       │                                      │                          │
│       │                                      ▼                          │
│       │                               QA verifies (next cycle)          │
│       │                                                                 │
│       └──── VIOLATION ────▶ qa_reports/report_*.md                      │
│                                      │                                  │
│                                      ▼                                  │
│                               FIXER reads report                        │
│                                      │                                  │
│                                      ├── CRITICAL/HIGH → Fix it         │
│                                      │        │                         │
│                                      │        ▼                         │
│                                      │   fixer_reports/fixes_*.md       │
│                                      │        │                         │
│                                      │        ▼                         │
│                                      │   QA verifies (next cycle)       │
│                                      │                                  │
│                                      └── MISSING → Skip (BUILDER_REQ)   │
│                                                                         │
│  LOOP CONTINUES until:                                                  │
│  - Zero MISSING files                                                   │
│  - Zero CRITICAL violations                                             │
│  - Zero HIGH violations                                                 │
│  - 100% fix verification                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Timing Strategy

| Agent | Cycle | Why |
|-------|-------|-----|
| Builder | On demand | Human-driven, builds tasks |
| QA | 90 seconds | Fast detection, frequent scans |
| Fixer | 2 minutes | Time to fix + QA can verify |

```
Time    Builder         QA              Fixer
────────────────────────────────────────────────────────
0:00    Building...     Scan #1         (waiting)
1:30    Building...     Report #1 ✓     (waiting)
2:00    Building...     Scan #2         Fix #1 start
3:00    Building...     (processing)    (fixing)
3:30    Building...     Report #2 ✓     Fix #1 done
4:00    Building...     Scan #3         Fix #2 start
                        (verifies #1)
```

---

## Starting the Pipeline

### Terminal 1: Builder Agent

```
1. Open Claude Code
2. Copy entire contents of: Agents/Builder Agent/BUILDER_AGENT_PROMPT.md
3. Paste as first message
4. Give tasks: "Build ICP-001" or "Complete Phase 11"
```

### Terminal 2: QA Agent

```
1. Open NEW Claude Code window
2. Copy entire contents of: Agents/QA Agent/QA_AGENT_PROMPT.md
3. Paste as first message
4. Agent runs automatically every 90 seconds
```

### Terminal 3: Fixer Agent

```
1. Open NEW Claude Code window
2. Copy entire contents of: Agents/Fixer Agent/FIXER_AGENT_PROMPT.md
3. Paste as first message
4. Agent runs automatically every 2 minutes
```

---

## Communication Protocol

Agents communicate ONLY through files:

| From | To | Via | Content |
|------|----|-----|---------|
| Builder | QA | src/, frontend/ | Code to scan |
| QA | Builder | builder_tasks/pending.md | Missing/incomplete files |
| QA | Fixer | qa_reports/report_*.md | Violations to fix |
| Fixer | QA | fixer_reports/fixes_*.md | Fixes to verify |
| Fixer | src/, frontend/ | Fixed code | Applied repairs |

**No direct communication.** Each agent reads/writes specific locations.

---

## Conflict Resolution

### Builder and Fixer both editing same file?

**Resolution:** 
- Fixer makes surgical fixes with `# FIXED by fixer-agent` markers
- Builder works around markers, doesn't remove them
- If conflict, Fixer's fix takes priority (it's correcting violations)

### QA reports issue that Builder just fixed?

**Resolution:**
- QA's next cycle (90 seconds) will see the new code
- Issue auto-resolves if code is correct

### Fixer breaks something?

**Resolution:**
- QA's next scan catches the regression
- Reports as `REGRESSION` — Fixer must re-fix

### Same issue keeps reopening?

**Resolution:**
- After 3 failed attempts, Fixer escalates to `needs_human.md`
- Human (CEO) reviews and decides

---

## Success Criteria

The pipeline is complete when QA reports:

```
MISSING files:     0
INCOMPLETE files:  0
CRITICAL issues:   0
HIGH issues:       0
Fixes verified:    100%
Skill compliance:  100%
```

---

## Monitoring Commands

**Check Builder tasks:**
```bash
cat "Agents/Builder Agent/builder_tasks/pending.md"
```

**Check QA status:**
```bash
cat "Agents/QA Agent/qa_reports/status.md"
```

**Check Fixer status:**
```bash
cat "Agents/Fixer Agent/fixer_reports/status.md"
```

**See latest QA report:**
```bash
ls -t "Agents/QA Agent/qa_reports/"report_*.md | head -1 | xargs cat
```

**See latest Fixer log:**
```bash
ls -t "Agents/Fixer Agent/fixer_reports/"fixes_*.md | head -1 | xargs cat
```

**See escalated issues:**
```bash
cat "Agents/Fixer Agent/fixer_reports/needs_human.md"
```

---

## Emergency Stop

If something goes wrong:

1. **Stop Fixer first** — Prevent more code changes
2. **Stop QA** — Stop generating new reports
3. **Review status files** — Understand what happened
4. **Fix manually if needed** — CEO intervention
5. **Clear pending tasks** — Reset builder_tasks/pending.md
6. **Restart agents** — Resume pipeline

---

## Best Practices

1. **Let the pipeline work** — Don't manually fix if Fixer is running
2. **Check builder_tasks/** — Before starting new work
3. **Trust the markers** — `# FIXED by fixer-agent` shows what changed
4. **Review escalations** — Check needs_human.md daily
5. **Monitor trends** — Issue counts should decrease
6. **Clean shutdown** — Wait for 0 issues before stopping

---

## Skill Dependencies

All agents read skills dynamically:

| Agent | Reads First | Then Reads |
|-------|-------------|------------|
| Builder | BUILDER_SKILL.md | Current phase skill |
| QA | QA_SKILL.md | Current phase skill |
| Fixer | FIXER_SKILL.md | Current phase skill |

When building a new phase, create a skill file for it:
- Phase 11 ICP → `skills/icp/ICP_SKILL.md`
- Phase 12 Onboarding → `skills/onboarding/ONBOARDING_SKILL.md`

---

## Troubleshooting

### Builder not picking up tasks

1. Check `builder_tasks/pending.md` has content
2. Verify Builder agent is running
3. Builder may be working on different task

### QA not finding issues

1. Check `qa_reports/` for recent reports
2. Verify files exist in `src/` and `frontend/`
3. QA agent may be between cycles

### Fixer not fixing

1. Check `qa_reports/` has CRITICAL or HIGH issues
2. Check Fixer isn't marking everything as BUILDER_REQ
3. Fixer may be between cycles

### Loop never ends

1. Check for escalations in `needs_human.md`
2. Some issues may need manual intervention
3. Verify agents aren't stuck on same issue

---
