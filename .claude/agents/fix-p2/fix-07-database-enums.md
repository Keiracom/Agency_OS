---
name: Fix 07 - Database Enums Documentation
description: Documents 5 missing enums in DATABASE.md
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 07: Undocumented Database Enums

## Gap Reference
- **TODO.md Item:** #7
- **Priority:** P2 High
- **Location:** `docs/architecture/foundation/DATABASE.md`
- **Issue:** 5 undocumented enums: ResourceType, ResourceStatus, HealthStatus, SuggestionType, SuggestionStatus

## Pre-Flight Checks

1. Find enum definitions:
   ```bash
   grep -rn "class ResourceType\|class ResourceStatus\|class HealthStatus\|class SuggestionType\|class SuggestionStatus" src/models/
   ```

2. Check if enums are in a shared file:
   ```bash
   grep -rn "ResourceType\|ResourceStatus\|HealthStatus\|SuggestionType\|SuggestionStatus" src/models/enums.py
   ```

3. Verify not already documented:
   ```bash
   grep -n "ResourceType\|ResourceStatus\|HealthStatus\|SuggestionType\|SuggestionStatus" docs/architecture/foundation/DATABASE.md
   ```

## Implementation Steps

1. **Read each enum definition** to extract:
   - Enum name
   - All values
   - Database type (varchar, int, etc.)
   - Usage context

2. **Document each enum** in DATABASE.md format:
   ```markdown
   ### ResourceType
   **Database Type:** VARCHAR
   **Used In:** resource_pool, campaign_resources

   | Value | Description |
   |-------|-------------|
   | email_account | Email sending account |
   | linkedin_profile | LinkedIn automation profile |
   | phone_number | Voice/SMS phone number |
   ```

3. **Add to Enums section** in DATABASE.md (create section if doesn't exist)

4. **Update enum count** in summary

## Enums to Document

| Enum | Expected Location | Likely Values |
|------|-------------------|---------------|
| ResourceType | src/models/enums.py | email_account, linkedin_profile, phone_number, etc. |
| ResourceStatus | src/models/enums.py | active, paused, warming, suspended, etc. |
| HealthStatus | src/models/enums.py | healthy, degraded, unhealthy, etc. |
| SuggestionType | src/models/enums.py | campaign_adjust, pause, budget, etc. |
| SuggestionStatus | src/models/enums.py | pending, approved, rejected, applied |

## Acceptance Criteria

- [ ] ResourceType enum documented with all values
- [ ] ResourceStatus enum documented with all values
- [ ] HealthStatus enum documented with all values
- [ ] SuggestionType enum documented with all values
- [ ] SuggestionStatus enum documented with all values
- [ ] Each includes: database type, where used, all values with descriptions

## Validation

```bash
# Check all 5 enums are documented
for enum in ResourceType ResourceStatus HealthStatus SuggestionType SuggestionStatus; do
  grep -c "$enum" docs/architecture/foundation/DATABASE.md
done

# Should output 5 lines, each with count > 0
```

## Post-Fix

1. Update TODO.md — delete gap row #7
2. Report: "Fixed #7. DATABASE.md now documents all 5 missing enums."
