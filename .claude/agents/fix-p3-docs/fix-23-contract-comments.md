---
name: Fix 23 - Contract Comments Compliance
description: Improves contract comment compliance to >90%
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Fix 23: Contract Comments ~50% Compliance

## Gap Reference
- **TODO.md Item:** #23
- **Priority:** P3 Medium (Documentation)
- **Location:** Codebase-wide
- **Issue:** Rule 6 inconsistently applied (~50% compliance)

## Pre-Flight Checks

1. Check current compliance:
   ```bash
   # Count files with contract comments
   grep -rl "Contract:" src/ | wc -l

   # Count total Python files
   find src/ -name "*.py" -type f | wc -l
   ```

2. List files missing contract comments:
   ```bash
   for f in $(find src/ -name "*.py" -type f); do
     if ! grep -q "Contract:" "$f"; then
       echo "$f"
     fi
   done
   ```

3. Review contract comment format in RULES.md:
   ```bash
   grep -A 10 "contract comment\|Contract:" docs/architecture/foundation/RULES.md
   ```

## Implementation Steps

1. **Define contract comment template:**
   ```python
   """
   Contract: {file_path}
   Purpose: {one_line_purpose}
   Layer: {layer_number} - {layer_name}
   Imports: {what_this_file_imports}
   Consumers: {what_uses_this_file}
   """
   ```

2. **Prioritize files by importance:**
   - Tier 1: All files in src/models/ (critical)
   - Tier 2: All files in src/engines/ (critical)
   - Tier 3: All files in src/orchestration/ (critical)
   - Tier 4: All files in src/services/ (important)
   - Tier 5: All files in src/agents/ (important)
   - Tier 6: All files in src/integrations/ (important)
   - Tier 7: All files in src/api/ (important)
   - Tier 8: All other files

3. **For each file without contract comment:**
   - Read the file
   - Determine its purpose from code
   - Identify its layer from IMPORT_HIERARCHY.md
   - Identify what it imports
   - Identify what uses it (grep for imports)
   - Add contract comment as first docstring

4. **Example additions:**
   ```python
   # src/engines/scorer.py
   """
   Contract: src/engines/scorer.py
   Purpose: Calculate ALS (Agency Lead Score) for leads
   Layer: 3 - engines
   Imports: models, integrations
   Consumers: orchestration only
   """

   # src/models/lead.py
   """
   Contract: src/models/lead.py
   Purpose: Lead data model with all lead attributes
   Layer: 1 - models
   Imports: exceptions only
   Consumers: ALL layers
   """
   ```

5. **Skip __init__.py files** (optional, low value)

## Acceptance Criteria

- [ ] All src/models/*.py have contract comments
- [ ] All src/engines/*.py have contract comments
- [ ] All src/orchestration/*.py have contract comments
- [ ] All src/services/*.py have contract comments
- [ ] All src/agents/*.py have contract comments
- [ ] All src/integrations/*.py have contract comments
- [ ] All src/api/routes/*.py have contract comments
- [ ] Overall compliance >90%

## Validation

```bash
# Count files with contract comments
WITH_CONTRACT=$(grep -rl "Contract:" src/ | wc -l)

# Count total Python files (excluding __init__.py)
TOTAL=$(find src/ -name "*.py" -type f ! -name "__init__.py" | wc -l)

# Calculate percentage
echo "Compliance: $WITH_CONTRACT / $TOTAL"
echo "Percentage: $(( WITH_CONTRACT * 100 / TOTAL ))%"

# Should be >90%
```

## Post-Fix

1. Update TODO.md — delete gap row #23
2. Report: "Fixed #23. Contract comment compliance improved from ~50% to [X]%."
