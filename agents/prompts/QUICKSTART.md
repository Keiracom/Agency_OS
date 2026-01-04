# QUICKSTART — 3-Agent Pipeline

**Purpose:** Get the Builder, QA, and Fixer agents running in parallel  
**Time:** 5 minutes  
**Result:** Continuous quality assurance during development

---

## Overview

Three agents work in parallel:

| Agent | Role | Cycle |
|-------|------|-------|
| **Builder** | Creates production code | On demand |
| **QA** | Detects issues, routes correctly | 90 seconds |
| **Fixer** | Fixes violations only | 2 minutes |

```
Builder creates → QA scans → Routes to:
                              ├── MISSING → Builder creates
                              └── VIOLATION → Fixer fixes → QA verifies
```

---

## Step 1: Start Builder Agent (Terminal 1)

1. Open Claude Code (or Claude Desktop with MCP)
2. Navigate to `C:\AI\Agency_OS`
3. Copy entire contents of:
   ```
   Agents/Builder Agent/BUILDER_AGENT_PROMPT.md
   ```
4. Paste as your first message
5. Give tasks: "Build ICP-001" or "Complete Phase 11"

---

## Step 2: Start QA Agent (Terminal 2)

1. Open **NEW** Claude Code window
2. Navigate to `C:\AI\Agency_OS`
3. Copy entire contents of:
   ```
   Agents/QA Agent/QA_AGENT_PROMPT.md
   ```
4. Paste as first message
5. Agent starts scanning automatically every 90 seconds

---

## Step 3: Start Fixer Agent (Terminal 3)

1. Open **NEW** Claude Code window
2. Navigate to `C:\AI\Agency_OS`
3. Copy entire contents of:
   ```
   Agents/Fixer Agent/FIXER_AGENT_PROMPT.md
   ```
4. Paste as first message
5. Agent starts fixing automatically every 2 minutes

---

## File Structure

```
C:\AI\Agency_OS\
│
├── Agents/
│   ├── Builder Agent/
│   │   ├── BUILDER_AGENT_PROMPT.md     # ← Copy for Terminal 1
│   │   ├── BUILDER_CONSTITUTION.md
│   │   └── builder_tasks/
│   │       └── pending.md              # QA writes missing files here
│   │
│   ├── QA Agent/
│   │   ├── QA_AGENT_PROMPT.md          # ← Copy for Terminal 2
│   │   ├── QA_CONSTITUTION.md
│   │   └── qa_reports/
│   │       ├── report_*.md             # Violation reports
│   │       └── status.md
│   │
│   ├── Fixer Agent/
│   │   ├── FIXER_AGENT_PROMPT.md       # ← Copy for Terminal 3
│   │   ├── FIXER_CONSTITUTION.md
│   │   └── fixer_reports/
│   │       ├── fixes_*.md              # Fix logs
│   │       ├── status.md
│   │       └── needs_human.md          # Escalations
│   │
│   └── QUICKSTART.md                   # This file
│
├── skills/
│   ├── SKILL_INDEX.md
│   └── agents/
│       ├── BUILDER_SKILL.md
│       ├── QA_SKILL.md
│       ├── FIXER_SKILL.md
│       └── COORDINATION_SKILL.md
│
├── PROJECT_BLUEPRINT.md
└── PROGRESS.md
```

---

## How It Works

### Issue Routing

| QA Finds | Routes To | Via |
|----------|-----------|-----|
| MISSING file | Builder | builder_tasks/pending.md |
| INCOMPLETE file | Builder | builder_tasks/pending.md |
| CRITICAL violation | Fixer | qa_reports/report_*.md |
| HIGH violation | Fixer | qa_reports/report_*.md |

### The Loop

```
1. Builder creates code
2. QA scans (90s):
   - Finds MISSING → writes to builder_tasks/
   - Finds VIOLATION → writes to qa_reports/
3. Builder checks builder_tasks/, creates missing files
4. Fixer reads qa_reports/, fixes violations
5. QA verifies Fixer's work (next cycle)
6. Loop continues until clean
```

---

## Quick Commands

**Check Builder tasks (what's missing):**
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
```powershell
Get-ChildItem "Agents/QA Agent/qa_reports/report_*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

**See latest Fixer log:**
```powershell
Get-ChildItem "Agents/Fixer Agent/fixer_reports/fixes_*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

**See escalated issues:**
```bash
cat "Agents/Fixer Agent/fixer_reports/needs_human.md"
```

---

## Success Criteria

The loop is complete when QA reports:

```
MISSING:     0
INCOMPLETE:  0
CRITICAL:    0
HIGH:        0
Verified:    100%
```

---

## Troubleshooting

### Builder not building?
- Check `builder_tasks/pending.md` for tasks
- Builder may be working on different task

### QA not scanning?
- Should output every 90 seconds
- Check if Claude Code window is active

### Fixer not fixing?
- Check `qa_reports/` has CRITICAL/HIGH issues
- Fixer skips MISSING (that's Builder's job)

### Same issue keeps reappearing?
- Check `needs_human.md` for escalations
- May need manual intervention

---

## Dynamic Behavior

All agents detect context dynamically by reading:
1. PROGRESS.md → Current phase
2. SKILL_INDEX.md → Relevant skill file
3. Skill file → Requirements for current build

This means the pipeline works for ANY phase without changing prompts.

---

**Ready? Open 3 terminals and start the loop!**
