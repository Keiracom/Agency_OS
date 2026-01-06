# CC Prompt: ICP Phase 1B - Async UX (Frontend)

## Context

You are working on Agency OS, a multi-channel client acquisition SaaS for Australian marketing agencies. The ICP extraction takes 2-3 minutes, and currently users stare at a loading screen the entire time. We need to redirect them to the dashboard immediately and show progress there.

### Current Flow (Bad UX)
```
1. User enters website URL on /onboarding
2. User waits on "Analyzing" screen for 2-3 minutes
3. User sees ICP results
4. User confirms
5. User redirected to /dashboard
```

### Desired Flow (Good UX)
```
1. User enters website URL on /onboarding
2. User IMMEDIATELY redirected to /dashboard (within 1 second)
3. Dashboard shows "Setting up your profile..." banner with progress
4. User can explore dashboard features while waiting
5. When extraction completes, banner updates to "✅ Your ICP is ready!"
6. User clicks banner → ICP review modal/drawer opens
7. User confirms ICP from modal
8. Banner disappears, dashboard fully active
```

---

## Reference Files

Read these files to understand the current implementation:

| File | Purpose |
|------|---------|
| `frontend/app/onboarding/page.tsx` | Current onboarding flow with blocking wait |
| `frontend/app/dashboard/page.tsx` | Dashboard page (destination) |
| `frontend/components/` | Existing UI components |
| `src/api/routes/onboarding.py` | Backend endpoints (already async with job_id) |

### Backend Endpoints (Already Working)

These endpoints exist and work - no backend changes needed:

```
POST /api/v1/onboarding/analyze
  Request: { website_url: string }
  Response: { job_id: UUID, status: "pending", message: string }

GET /api/v1/onboarding/status/{job_id}
  Response: { 
    job_id, status, current_step, completed_steps, 
    total_steps, progress_percent, error_message 
  }

GET /api/v1/onboarding/result/{job_id}
  Response: ICPProfile (full profile data)

POST /api/v1/onboarding/confirm
  Request: { job_id: UUID, adjustments?: {...} }
  Response: { success: true }
```

---

## Tasks

### Task 1: Update Onboarding Page to Redirect Immediately

**File:** `frontend/app/onboarding/page.tsx`

**Requirements:**
1. After calling `/analyze` and receiving `job_id`, immediately redirect to `/dashboard`
2. Pass `job_id` via URL parameter: `/dashboard?icp_job={job_id}`
3. Remove the "analyzing" step entirely from onboarding page
4. Keep the "input" step (URL entry form)

### Task 2: Create ICP Progress Banner Component

**File:** `frontend/components/icp-progress-banner.tsx` (new file)

**Requirements:**
1. Create a dismissible banner component that shows at top of dashboard
2. States to handle:
   - `pending/running`: "Setting up your profile..." with progress bar and current step
   - `completed`: "✅ Your ICP is ready! Click to review" (clickable)
   - `failed`: "❌ ICP extraction failed. Try again" with retry button
3. Progress bar showing `progress_percent` from status endpoint
4. Current step text from `current_step` field
5. Animate smoothly between states

### Task 3: Create ICP Review Modal/Drawer

**File:** `frontend/components/icp-review-modal.tsx` (new file)

**Requirements:**
1. Create a slide-over drawer (from right) or modal that shows the extracted ICP
2. Reuse the ICP display UI from current onboarding review step
3. Include "Confirm ICP" button that calls `/confirm` endpoint
4. Include "Edit" option to adjust fields before confirming
5. On confirm success, close modal and remove banner

### Task 4: Add ICP Job Polling to Dashboard

**File:** `frontend/app/dashboard/page.tsx`

**Requirements:**
1. Check URL for `icp_job` parameter on mount
2. If present, show ICP progress banner
3. Poll `/status/{job_id}` every 3 seconds while status is `pending` or `running`
4. When `completed`, fetch result and enable "review" click on banner
5. Store job state in React state or context
6. Persist job_id to localStorage so refresh doesn't lose it

### Task 5: Handle Edge Cases

**Requirements:**
1. If user refreshes dashboard during extraction, recover job_id from localStorage
2. If user navigates away and back, continue showing progress
3. If extraction fails, show error state with "Try Again" that links back to /onboarding
4. If user already has confirmed ICP (check client data), don't show banner

---

## UI Specifications

### Progress Banner (Running State)
```
┌────────────────────────────────────────────────────────────────┐
│ 🔄 Setting up your profile...  [████████░░░░░░░░] 52%         │
│    Extracting services from website                      [×]   │
└────────────────────────────────────────────────────────────────┘
```

### Progress Banner (Complete State)
```
┌────────────────────────────────────────────────────────────────┐
│ ✅ Your ICP is ready!  [Review Now →]                    [×]   │
└────────────────────────────────────────────────────────────────┘
```

### Progress Banner (Failed State)
```
┌────────────────────────────────────────────────────────────────┐
│ ❌ Couldn't analyze your website.  [Try Again]           [×]   │
└────────────────────────────────────────────────────────────────┘
```

---

## Constraints

1. Use existing UI components from `frontend/components/ui/` (shadcn)
2. Follow existing styling patterns (Tailwind classes)
3. Use existing Supabase auth pattern for API calls
4. Polling interval: 3 seconds (not too aggressive)
5. Don't break existing dashboard functionality
6. Mobile responsive - banner should work on mobile

---

## Testing

**Test Flow:**
1. Go to /onboarding
2. Enter `https://www.dilate.com.au`
3. Click "Discover My ICP"
4. Should redirect to /dashboard within 1 second
5. Banner should appear showing progress
6. User can click around dashboard while waiting
7. After 2-3 minutes, banner should update to "ready" state
8. Click banner → modal opens with ICP
9. Confirm → modal closes, banner disappears

**Edge Cases to Test:**
- Refresh during extraction (should recover)
- Multiple tabs (should not duplicate)
- Fast completion (should still show briefly then update)
- Failure state (should show retry option)

---

## Success Criteria

- [ ] User redirected to dashboard within 1 second of starting extraction
- [ ] Progress banner visible on dashboard during extraction
- [ ] Progress updates every 3 seconds via polling
- [ ] "Ready" state shows when extraction completes
- [ ] ICP review modal opens on banner click
- [ ] Confirm button saves ICP and dismisses banner
- [ ] Job state persists across page refresh
- [ ] Failed state shows retry option
- [ ] Existing dashboard features still work during extraction
