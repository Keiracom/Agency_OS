---
name: Fix 01 - File Structure Documentation
description: Updates FILE_STRUCTURE.md with missing ~50% of files
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Fix 01: FILE_STRUCTURE.md Missing Files

## Gap Reference
- **TODO.md Item:** #1
- **Priority:** P0/P1 Critical
- **Location:** `docs/architecture/foundation/FILE_STRUCTURE.md`
- **Issue:** Services (22), agents (13+), detectors (8), intelligence (2+) undocumented. Actual: 199 files, Documented: 135

## Pre-Flight Checks

1. Read current FILE_STRUCTURE.md
2. Inventory actual files in src/
3. Calculate exact gap

```bash
# Count actual files
find src/ -name "*.py" -type f | wc -l

# Count documented vs actual
grep -c "\.py" docs/architecture/foundation/FILE_STRUCTURE.md
```

## Implementation Steps

1. **Scan all directories:**
   ```bash
   find src/services/ -name "*.py" -type f
   find src/agents/ -name "*.py" -type f
   find src/detectors/ -name "*.py" -type f
   ```

2. **For each undocumented file, add entry with:**
   - File path
   - One-line purpose
   - Layer assignment
   - Key exports

3. **Update totals** at top of FILE_STRUCTURE.md

4. **Maintain alphabetical order** within sections

## Acceptance Criteria

- [ ] All src/services/*.py files documented
- [ ] All src/agents/*.py files documented
- [ ] All src/detectors/*.py files documented
- [ ] All src/intelligence/*.py files documented
- [ ] File count in doc matches actual count
- [ ] Each entry has: path, purpose, layer, exports

## Validation

```bash
# Count documented files
grep -c "src/" docs/architecture/foundation/FILE_STRUCTURE.md

# Count actual Python files
find src/ -name "*.py" -type f | wc -l

# These should match (within 5% for __init__.py files)
```

## Post-Fix

1. Update TODO.md — delete gap row #1
2. Report: "Fixed #1. FILE_STRUCTURE.md now documents [X] files (was 135)."
