# AGENT QUICK START GUIDE

## The Continuous QA-Fixer Loop

This system creates a self-healing codebase through continuous monitoring and repair.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                        THE LOOP                                 │
│                                                                 │
│   ┌──────────┐    writes code    ┌──────────┐                   │
│   │ BUILDER  │──────────────────▶│  src/    │                   │
│   └──────────┘                   └────┬─────┘                   │
│                                       │                         │
│                              scans every 90s                    │
│                                       ▼                         │
│                                 ┌──────────┐                    │
│                                 │    QA    │                    │
│                                 │  AGENT   │                    │
│                                 └────┬─────┘                    │
│                                      │                          │
│              ┌───────────────────────┼───────────────────────┐  │
│              │                       │                       │  │
│              ▼                       ▼                       │  │
│       ┌─────────────┐         ┌─────────────┐                │  │
│       │ qa_reports/ │         │   verifies  │                │  │
│       │ (issues)    │         │fixer_reports│                │  │
│       └──────┬──────┘         └─────────────┘                │  │
│              │                       ▲                       │  │
│     reads every 2min                 │                       │  │
│              ▼                       │                       │  │
│        ┌──────────┐           ┌──────┴──────┐                │  │
│        │  FIXER   │──────────▶│fixer_reports│                │  │
│        │  AGENT   │  writes   │   (logs)    │                │  │
│        └────┬─────┘           └─────────────┘                │  │
│             │                                                │  │
│             │ fixes code                                     │  │
│             ▼                                                │  │
│       ┌──────────┐                                           │  │
│       │  src/    │◀──────────────────────────────────────────┘  │
│       └──────────┘                                              │
│                                                                 │
│   Loop continues until: 0 CRITICAL, 0 HIGH, 100% verified       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## How It Works

| Step | Agent | Action | Output |
|------|-------|--------|--------|
| 1 | Builder | Writes code | src/ files |
| 2 | QA | Scans src/ for issues | qa_reports/report_*.md |
| 3 | Fixer | Reads QA report, fixes issues | src/ fixes + fixer_reports/fixes_*.md |
| 4 | QA | Verifies fixes via fixer_reports/ | Updated qa_reports/ |
| 5 | Repeat until clean | | |

---

## Terminal Setup

You need **3 separate Claude Code terminals**:

### Terminal 1: Builder Agent
- Your main development agent
- Builds features per PROJECT_BLUEPRINT.md
- Updates PROGRESS.md

### Terminal 2: QA Agent
1. Open new Claude Code instance
2. Copy entire contents of `Agents\QA_AGENT_PROMPT.md`
3. Paste as first message
4. Agent runs continuously (90 second cycles)

### Terminal 3: Fixer Agent
1. Open new Claude Code instance
2. Copy entire contents of `Agents\FIXER_AGENT_PROMPT.md`
3. Paste as first message
4. Agent runs continuously (2 minute cycles)

---

## File Locations

```
C:\AI\Agency_OS\Agents\
├── QA_CONSTITUTION.md         # QA rules
├── FIXER_CONSTITUTION.md      # Fixer rules
├── QA_AGENT_PROMPT.md         # ← Copy for QA terminal
├── FIXER_AGENT_PROMPT.md      # ← Copy for Fixer terminal
├── QUICKSTART.md              # This file
│
├── qa_reports/                # QA writes here
│   ├── report_*.md            # Scan reports (issues found)
│   └── status.md              # Current status
│
└── fixer_reports/             # Fixer writes here
    ├── fixes_*.md             # Fix logs (what was fixed)
    ├── status.md              # Fixer status
    └── needs_human.md         # Escalated issues
```

---

## The Feedback Loop

```
QA finds issue          →  Writes to qa_reports/
                              ↓
Fixer reads qa_reports/ →  Fixes code + writes to fixer_reports/
                              ↓
QA reads fixer_reports/ →  Verifies fix worked
                              ↓
                         Issue RESOLVED or RE-OPENED
```

### Issue Lifecycle

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│   NEW   │────▶│ FIXING  │────▶│ VERIFYING│────▶│ RESOLVED │
└─────────┘     └─────────┘     └────┬─────┘     └──────────┘
                                     │
                                     │ if failed
                                     ▼
                               ┌───────────┐
                               │ RE-OPENED │──▶ back to FIXING
                               └───────────┘
```

---

## Timing

| Agent | Cycle | Waits For |
|-------|-------|-----------|
| QA | 90 seconds | Nothing (runs first) |
| Fixer | 2 minutes | QA to write report |

This ensures:
- QA always has fresh reports for Fixer
- Fixer has time to work before next QA scan
- QA can verify Fixer's work in next cycle

---

## Success Criteria

The loop is complete when QA reports:

```
CRITICAL issues: 0
HIGH issues: 0
Fixes verified: 100%
```

---

## Troubleshooting

### QA not finding Fixer's work
- Check fixer_reports/ has recent fixes_*.md files
- Fixer must write logs EVERY cycle

### Fixer not seeing QA issues
- Check qa_reports/ has recent report_*.md files
- Fixer should read the LATEST report

### Issues keep reopening
- Fixer's fix may be incomplete
- Check fixer_reports/ for the fix details
- QA report will say STILL_BROKEN with reason

### Loop seems stuck
1. Stop both agents
2. Read latest qa_reports/status.md
3. Read latest fixer_reports/status.md
4. Identify the blocker
5. Restart agents

---

## Manual Intervention

Some issues require human review. Check:

```
C:\AI\Agency_OS\Agents\fixer_reports\needs_human.md
```

These are issues Fixer couldn't safely fix.

---

## Quick Commands

**Check QA status:**
```bash
cat Agents/qa_reports/status.md
```

**Check Fixer status:**
```bash
cat Agents/fixer_reports/status.md
```

**See latest QA report:**
```bash
ls -t Agents/qa_reports/report_*.md | head -1 | xargs cat
```

**See latest Fixer log:**
```bash
ls -t Agents/fixer_reports/fixes_*.md | head -1 | xargs cat
```

**See escalated issues:**
```bash
cat Agents/fixer_reports/needs_human.md
```

---

**Ready? Open 3 terminals and start the loop!**
