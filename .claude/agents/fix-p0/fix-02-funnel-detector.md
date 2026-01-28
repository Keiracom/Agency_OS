---
name: Fix 02 - Funnel Detector Integration
description: Wires Funnel Detector into pattern_learning_flow.py
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 02: Funnel Detector Not Integrated

## Gap Reference
- **TODO.md Item:** #2
- **Priority:** P0/P1 Critical
- **Location:** `src/orchestration/pattern_learning_flow.py`
- **Issue:** Detector exists but NOT called in `run_all_detectors_task()`

## Pre-Flight Checks

1. Locate funnel detector:
   ```bash
   find src/ -name "*funnel*detector*" -o -name "*detector*funnel*"
   ```

2. Read pattern_learning_flow.py to find `run_all_detectors_task()`

3. Verify funnel detector has same interface as other detectors

## Implementation Steps

1. **Read the funnel detector** to understand its interface:
   - Input parameters
   - Return type
   - Async or sync

2. **Read pattern_learning_flow.py** to see how other detectors are called

3. **Add import** for funnel detector at top of file

4. **Add call** to funnel detector in `run_all_detectors_task()`:
   ```python
   # Example pattern (adjust to match existing style)
   funnel_results = await funnel_detector.detect(db, client_id)
   all_results["funnel"] = funnel_results
   ```

5. **Handle results** same as other detectors

## Acceptance Criteria

- [ ] Funnel detector imported in pattern_learning_flow.py
- [ ] Funnel detector called in run_all_detectors_task()
- [ ] Results included in aggregated detector output
- [ ] No import errors
- [ ] Matches pattern of other detector integrations

## Validation

```bash
# Check import exists
grep -n "funnel" src/orchestration/pattern_learning_flow.py

# Verify no syntax errors
python -m py_compile src/orchestration/pattern_learning_flow.py

# Run type check on file
mypy src/orchestration/pattern_learning_flow.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #2
2. Report: "Fixed #2. Funnel Detector now called in run_all_detectors_task()."
