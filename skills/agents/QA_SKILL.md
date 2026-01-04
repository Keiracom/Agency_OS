# SKILL.md — QA Agent

**Skill:** QA Agent for Agency OS  
**Author:** CTO (Claude)  
**Version:** 2.0  
**Created:** December 24, 2025

---

## Purpose

The QA Agent scans code for issues and routes them to the correct handler:
- **MISSING/INCOMPLETE** → Builder (creates files)
- **VIOLATION** → Fixer (fixes code)

---

## Dynamic Context Detection

Every cycle, detect what to check:

```python
# Pseudocode
1. Read PROGRESS.md
   - Find current phase
   - Find tasks in progress (🟡)
   - Find tasks marked complete (🟢)

2. Read skills/SKILL_INDEX.md
   - Find skill file for current phase

3. Read the skill file
   - Get list of required files
   - Get list of required patterns
   - Get context-specific checks
```

---

## Issue Categories

| Category | Handler | Write To | Trigger |
|----------|---------|----------|---------|
| MISSING | Builder | builder_tasks/pending.md | File doesn't exist |
| INCOMPLETE | Builder | builder_tasks/pending.md | File has stubs/placeholders |
| CRITICAL | Fixer | qa_reports/report_*.md | Architecture violation |
| HIGH | Fixer | qa_reports/report_*.md | Standards violation |
| MEDIUM | Fixer | qa_reports/report_*.md | Quality issue |
| LOW | Fixer | qa_reports/report_*.md | Style issue |

---

## General Checks (Always Run)

### CRITICAL Checks

```bash
# Import hierarchy violations (Rule 12)
grep -rn "from src.engines" src/models/
grep -rn "from src.orchestration" src/models/
grep -rn "from src.orchestration" src/engines/
grep -rn "from src.engines\." src/engines/  # Cross-engine

# Hardcoded secrets
grep -rn "api_key\s*=\s*['\"][^'\"]*['\"]" src/
grep -rn "password\s*=\s*['\"][^'\"]*['\"]" src/
grep -rn "sk-[a-zA-Z0-9]" src/
grep -rn "secret\s*=\s*['\"][^'\"]*['\"]" src/

# Wrong database port (should be 6543)
grep -rn ":5432" src/
grep -rn "port.*5432" src/

# Hard deletes
grep -rn "\.delete\(" src/
grep -rn "DELETE FROM" src/

# Session instantiation in engines
grep -rn "AsyncSessionLocal\(\)" src/engines/
```

### HIGH Checks

```bash
# Missing contract comments (check first 10 lines for docstring)
# Python files without FILE: in first 10 lines
for f in $(find src -name "*.py" ! -name "__init__.py"); do
  if ! head -10 "$f" | grep -q "FILE:"; then
    echo "Missing contract: $f"
  fi
done

# Wrong pool settings
grep -rn "pool_size" src/ | grep -v "pool_size=5"
grep -rn "max_overflow" src/ | grep -v "max_overflow=10"

# TypeScript any types
grep -rn ": any" frontend/app/
grep -rn ": any" frontend/components/
grep -rn "<any>" frontend/

# Missing soft delete filters in queries
grep -rn "\.select\(" src/api/ | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  if ! grep -q "deleted_at" "$file"; then
    echo "Missing soft delete check: $file"
  fi
done
```

### MEDIUM Checks

```bash
# TODO/FIXME comments
grep -rn "TODO" src/ frontend/
grep -rn "FIXME" src/ frontend/

# Console.log in production
grep -rn "console\.log" frontend/app/
grep -rn "console\.log" frontend/components/

# Print statements in Python
grep -rn "^[^#]*print\(" src/
```

---

## Missing File Detection

### Check PROGRESS.md vs Actual Files

```bash
# For each task marked 🟢 in PROGRESS.md
# Extract the file path from the "Files Created" column
# Check if file exists

# Example logic:
grep "🟢" PROGRESS.md | while read line; do
  file=$(echo "$line" | grep -oP '\`[^\`]+\`' | tr -d '\`')
  if [ -n "$file" ] && [ ! -f "$file" ]; then
    echo "MISSING: $file (task shows complete but file doesn't exist)"
  fi
done
```

### Check Skill Requirements vs Actual Files

```bash
# Read the current skill file
# Extract all file paths mentioned
# Check if each exists

# Example for Admin Dashboard skill:
ls frontend/app/admin/page.tsx 2>/dev/null || echo "MISSING: Command Center page"
ls frontend/app/admin/clients/page.tsx 2>/dev/null || echo "MISSING: Clients page"
ls frontend/components/admin/AdminSidebar.tsx 2>/dev/null || echo "MISSING: AdminSidebar"
# ... etc
```

### Incomplete File Detection

```bash
# Python stubs
grep -rn "^\s*pass$" src/
grep -rn "raise NotImplementedError" src/
grep -rn "\.\.\." src/  # Ellipsis

# TypeScript stubs
grep -rn "throw new Error\(['\"]Not implemented" frontend/
grep -rn "// TODO" frontend/
```

---

## Report Template

```markdown
# QA REPORT - Agency OS v3.0

**Report ID:** QA-YYYYMMDD-HHMM
**Timestamp:** [ISO 8601]
**Cycle:** [N]

---

## CONTEXT

**Current Phase:** [X] - [Name]
**Active Skill:** [path]
**Tasks In Progress:** [count]
**Tasks Complete:** [count]

---

## SUMMARY

| Category | Count | Handler |
|----------|-------|---------|
| MISSING | X | Builder |
| INCOMPLETE | X | Builder |
| CRITICAL | X | Fixer |
| HIGH | X | Fixer |
| MEDIUM | X | (logged) |

---

## BUILDER TASKS

*Written to: Agents/Builder Agent/builder_tasks/pending.md*

### Missing Files

| Task ID | File | Reason |
|---------|------|--------|
| [ID] | [path] | [why expected] |

### Incomplete Files

| Task ID | File | Line | Issue |
|---------|------|------|-------|
| [ID] | [path] | [N] | Contains `pass` |

---

## FIXER TASKS

### CRITICAL

#### CRIT-001: Import Hierarchy Violation

- **Location:** src/engines/scout.py:12
- **Rule:** Rule 12
- **Evidence:**
```
from src.engines.scorer import calculate_score
```
- **Fix:** Remove import, pass data from orchestration

### HIGH

#### HIGH-001: Missing Contract Comment

- **Location:** src/models/lead.py:1
- **Rule:** Code Standards
- **Evidence:** File starts with `from sqlalchemy...`
- **Fix:** Add contract comment header

---

## FIXER VERIFICATION

| Issue | File | Claimed Fix | Status |
|-------|------|-------------|--------|
| CRIT-001 | src/x.py | Removed import | ✅ VERIFIED |
| HIGH-001 | src/y.py | Added header | ❌ STILL_BROKEN |

---

## SKILL COMPLIANCE

**Skill:** [name]

| Requirement | Status |
|-------------|--------|
| [file/component] | ✅ / ❌ |

**Compliance:** X/Y (Z%)

---
```

---

## Builder Tasks File Format

```markdown
# PENDING BUILDER TASKS

**Last Updated:** [timestamp]

---

## MISSING FILES

| Task ID | Required File | Reason | Skill |
|---------|---------------|--------|-------|
| ICP-011 | src/engines/icp_scraper.py | Task 🟡 but file missing | skills/icp/ICP_SKILL.md |

## INCOMPLETE FILES

| Task ID | File | Issue | Line |
|---------|------|-------|------|
| ICP-003 | src/agents/skills/website_parser.py | Contains `pass` | 45 |

---

**Builder:** Create these files, then remove from this list.
```

---

## Timing

- **Cycle:** 90 seconds
- **Priority:** MISSING → CRITICAL → HIGH → Verification → MEDIUM

---

## Never Do

- ❌ Modify source code
- ❌ Modify fixer_reports/
- ❌ Create files (only report missing)
- ❌ Report same issue twice in same report
- ❌ Skip context detection

---
