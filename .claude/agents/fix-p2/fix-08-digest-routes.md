---
name: Fix 08 - Digest Routes Documentation
description: Documents digest.py routes in API_LAYER.md
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 08: Digest Routes Undocumented

## Gap Reference
- **TODO.md Item:** #8
- **Priority:** P2 High
- **Location:** `docs/architecture/foundation/API_LAYER.md`
- **Issue:** GET/PATCH /digest/settings, GET /digest/preview, GET /digest/history not documented

## Pre-Flight Checks

1. Find digest routes:
   ```bash
   grep -n "digest" src/api/routes/*.py
   find src/api/routes/ -name "*digest*"
   ```

2. Read the digest route file to catalog all endpoints

3. Verify not already in API_LAYER.md:
   ```bash
   grep -n "digest" docs/architecture/foundation/API_LAYER.md
   ```

## Implementation Steps

1. **Read digest.py routes** to extract for each endpoint:
   - HTTP method
   - Path
   - Request body schema
   - Response schema
   - Auth requirements
   - Description

2. **Document in API_LAYER.md format:**
   ```markdown
   ### Digest Endpoints

   #### GET /api/v1/digest/settings
   **Auth:** Required
   **Description:** Retrieve digest settings for current user

   **Response:**
   ```json
   {
     "frequency": "daily|weekly",
     "enabled": true,
     "time": "09:00",
     "timezone": "Australia/Sydney"
   }
   ```

   #### PATCH /api/v1/digest/settings
   **Auth:** Required
   **Description:** Update digest settings

   **Request Body:**
   ```json
   {
     "frequency": "weekly",
     "enabled": true
   }
   ```

   #### GET /api/v1/digest/preview
   **Auth:** Required
   **Description:** Preview next digest content

   #### GET /api/v1/digest/history
   **Auth:** Required
   **Description:** List past digest deliveries
   **Query Params:** limit, offset
   ```

3. **Add to appropriate section** in API_LAYER.md

4. **Update endpoint count** if tracked

## Acceptance Criteria

- [ ] GET /digest/settings documented
- [ ] PATCH /digest/settings documented
- [ ] GET /digest/preview documented
- [ ] GET /digest/history documented
- [ ] Each includes: method, path, auth, request/response schemas

## Validation

```bash
# Check all 4 endpoints documented
grep -c "/digest/" docs/architecture/foundation/API_LAYER.md
# Should return >= 4

# Check specific endpoints
grep -n "digest/settings\|digest/preview\|digest/history" docs/architecture/foundation/API_LAYER.md
```

## Post-Fix

1. Update TODO.md — delete gap row #8
2. Report: "Fixed #8. API_LAYER.md now documents 4 digest endpoints."
