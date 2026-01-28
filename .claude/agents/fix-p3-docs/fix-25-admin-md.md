---
name: Fix 25 - Frontend ADMIN.md Endpoint Count
description: Corrects overstated endpoint count in ADMIN.md
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 25: ADMIN.md Endpoint Count Wrong

## Gap Reference
- **TODO.md Item:** #25
- **Priority:** P3 Medium (Documentation)
- **Location:** `frontend/ADMIN.md`
- **Issue:** Overstated endpoint count in doc

## Pre-Flight Checks

1. Read current ADMIN.md:
   ```bash
   cat frontend/ADMIN.md
   ```

2. Find endpoint count claims:
   ```bash
   grep -n "endpoint\|route\|API" frontend/ADMIN.md
   ```

3. Count actual admin endpoints in backend:
   ```bash
   grep -rn "@router\.\|@app\." src/api/routes/admin*.py
   ```

4. Count admin API functions in frontend:
   ```bash
   grep -n "async function\|export function\|export const" frontend/lib/api/admin.ts
   ```

## Implementation Steps

1. **Count actual backend admin endpoints:**
   ```bash
   # Find admin route files
   find src/api/routes/ -name "*admin*"

   # Count route decorators
   grep -c "@router\." src/api/routes/admin.py

   # List all admin endpoints
   grep -n "@router\." src/api/routes/admin.py
   ```

2. **Count actual frontend admin API functions:**
   ```bash
   # Find admin API file
   ls frontend/lib/api/admin.ts

   # Count exported functions
   grep -c "export.*function\|export const.*=" frontend/lib/api/admin.ts
   ```

3. **Update ADMIN.md with correct count:**
   - Find the section with endpoint count
   - Update to accurate number
   - Ensure the endpoint list matches actual endpoints

4. **Verify endpoint list is complete:**
   ```markdown
   ## Admin API Endpoints

   | Endpoint | Method | Description |
   |----------|--------|-------------|
   | /api/v1/admin/users | GET | List all users |
   | /api/v1/admin/users/:id | GET | Get user details |
   | /api/v1/admin/users/:id | PATCH | Update user |
   | /api/v1/admin/clients | GET | List all clients |
   | ... | ... | ... |

   **Total Endpoints: [ACTUAL_COUNT]**
   ```

5. **Cross-reference with frontend API file:**
   - Each backend endpoint should have corresponding frontend function
   - Document any mismatches

## Acceptance Criteria

- [ ] Endpoint count matches actual backend routes
- [ ] Endpoint table lists all admin endpoints
- [ ] Each endpoint has method, path, description
- [ ] Frontend API functions match backend endpoints
- [ ] No overcounting or undercounting

## Validation

```bash
# Count backend admin endpoints
BACKEND_COUNT=$(grep -c "@router\." src/api/routes/admin.py)

# Check doc count
DOC_COUNT=$(grep -oP '\d+ endpoint' frontend/ADMIN.md | grep -oP '\d+')

# Compare
echo "Backend: $BACKEND_COUNT, Doc says: $DOC_COUNT"

# These should match
if [ "$BACKEND_COUNT" == "$DOC_COUNT" ]; then
  echo "PASS: Counts match"
else
  echo "FAIL: Counts don't match"
fi
```

## Post-Fix

1. Update TODO.md — delete gap row #25
2. Report: "Fixed #25. ADMIN.md endpoint count corrected from [X] to [Y]."
