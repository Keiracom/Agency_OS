---
name: Fix 24 - Frontend TECHNICAL.md Update
description: Updates component count and adds /dashboard/archive page
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Fix 24: TECHNICAL.md Outdated

## Gap Reference
- **TODO.md Item:** #24
- **Priority:** P3 Medium (Documentation)
- **Location:** `frontend/TECHNICAL.md`
- **Issue:** Component count 61→70, missing /dashboard/archive page

## Pre-Flight Checks

1. Read current TECHNICAL.md:
   ```bash
   cat frontend/TECHNICAL.md
   ```

2. Count actual components:
   ```bash
   find frontend/components/ -name "*.tsx" -type f | wc -l
   ```

3. Check for /dashboard/archive page:
   ```bash
   ls -la frontend/app/dashboard/archive/
   cat frontend/app/dashboard/archive/page.tsx
   ```

4. List all pages:
   ```bash
   find frontend/app/ -name "page.tsx" -type f
   ```

## Implementation Steps

1. **Get accurate component count:**
   ```bash
   # Count all .tsx files in components/
   find frontend/components/ -name "*.tsx" -type f | wc -l

   # List by subdirectory
   for dir in frontend/components/*/; do
     count=$(find "$dir" -name "*.tsx" -type f | wc -l)
     echo "$dir: $count"
   done
   ```

2. **Update component count in TECHNICAL.md:**
   - Find the section with component count
   - Update from 61 to actual count (70+)

3. **Add /dashboard/archive page documentation:**
   ```markdown
   ### Archive Page (`/dashboard/archive`)

   **Purpose:** View archived campaigns and historical data

   **Components Used:**
   - CampaignArchiveList
   - ArchiveFilters
   - ArchiveStats

   **Features:**
   - List archived campaigns
   - Filter by date range
   - Restore archived campaigns
   - View historical metrics
   ```

4. **Update route table:**
   ```markdown
   | Route | Page | Description |
   |-------|------|-------------|
   | /dashboard | Dashboard | Main dashboard |
   | /dashboard/archive | Archive | Archived campaigns |
   | ... | ... | ... |
   ```

5. **Verify all pages are documented:**
   ```bash
   # List all page routes
   find frontend/app/ -name "page.tsx" -type f | sed 's|frontend/app||; s|/page.tsx||'
   ```

6. **Update any other outdated counts:**
   - Hook count
   - API function count
   - etc.

## Acceptance Criteria

- [ ] Component count updated to accurate number (70+)
- [ ] /dashboard/archive page documented
- [ ] Route table includes archive page
- [ ] All other pages verified in documentation
- [ ] No other outdated counts

## Validation

```bash
# Verify component count in doc matches reality
DOC_COUNT=$(grep -oP '\d+ components' frontend/TECHNICAL.md | grep -oP '\d+')
ACTUAL_COUNT=$(find frontend/components/ -name "*.tsx" -type f | wc -l)
echo "Doc says: $DOC_COUNT, Actual: $ACTUAL_COUNT"

# Verify archive page is documented
grep -n "archive" frontend/TECHNICAL.md

# Check route table
grep -n "dashboard/archive" frontend/TECHNICAL.md
```

## Post-Fix

1. Update TODO.md — delete gap row #24
2. Report: "Fixed #24. TECHNICAL.md updated: component count [X]→[Y], /dashboard/archive documented."
