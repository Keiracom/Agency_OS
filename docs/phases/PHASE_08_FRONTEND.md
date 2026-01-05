# Phase 8: Frontend

**Status:** ✅ Complete  
**Tasks:** 15  
**Dependencies:** Phase 7 complete  
**Checkpoint:** CEO approval required

---

## Overview

Build the Next.js frontend with Tailwind CSS and shadcn/ui.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| FE-001 | Next.js init | Initialize project | `frontend/package.json`, `frontend/next.config.js` | S |
| FE-002 | Tailwind + shadcn | Styling | `frontend/tailwind.config.js`, UI components | M |
| FE-003 | Supabase auth | Auth integration | `frontend/lib/supabase.ts` | M |
| FE-004 | Layout components | Header, sidebar, footer | `frontend/components/layout/*` | M |
| FE-005 | UI components | Core components | `frontend/components/ui/*` | M |
| FE-006 | Auth pages | Login, signup | `frontend/app/(auth)/*` | M |
| FE-007 | Dashboard home | Activity feed | `frontend/app/dashboard/page.tsx` | L |
| FE-008 | Campaign list | List campaigns | `frontend/app/dashboard/campaigns/page.tsx` | M |
| FE-009 | Campaign detail | Single campaign | `frontend/app/dashboard/campaigns/[id]/page.tsx` | L |
| FE-010 | New campaign | Create with permission mode | `frontend/app/dashboard/campaigns/new/page.tsx` | L |
| FE-011 | Lead list | List with ALS | `frontend/app/dashboard/leads/page.tsx` | M |
| FE-012 | Lead detail | Single lead | `frontend/app/dashboard/leads/[id]/page.tsx` | M |
| FE-013 | Reports page | Campaign metrics | `frontend/app/dashboard/reports/page.tsx` | L |
| FE-014 | Settings page | Client settings | `frontend/app/dashboard/settings/page.tsx` | M |
| FE-015 | Permission mode selector | Mode component | `frontend/components/campaigns/permission-mode-selector.tsx` | M |

---

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **Components:** shadcn/ui
- **Auth:** Supabase Auth
- **Deployment:** Vercel

---

## Page Structure

```
frontend/app/
├── (auth)/
│   ├── login/page.tsx
│   └── signup/page.tsx
├── dashboard/
│   ├── page.tsx              # Dashboard home
│   ├── campaigns/
│   │   ├── page.tsx          # Campaign list
│   │   ├── new/page.tsx      # Create campaign
│   │   └── [id]/page.tsx     # Campaign detail
│   ├── leads/
│   │   ├── page.tsx          # Lead list
│   │   └── [id]/page.tsx     # Lead detail
│   ├── reports/page.tsx      # Reports
│   └── settings/page.tsx     # Settings
├── admin/                    # Platform admin (Phase 10)
└── page.tsx                  # Landing page
```

---

## Permission Modes

```typescript
type PermissionMode = 'autopilot' | 'co_pilot' | 'manual';

// Autopilot: Fully automated, no approvals needed
// Co-Pilot: AI suggests, user approves
// Manual: User controls everything
```

---

## ALS Display Component

```tsx
function ALSBadge({ score, tier }: { score: number; tier: string }) {
  const colors = {
    hot: 'bg-orange-500',      // 85-100
    warm: 'bg-yellow-500',     // 60-84
    cool: 'bg-blue-500',       // 35-59
    cold: 'bg-gray-500',       // 20-34
    dead: 'bg-gray-800',       // <20
  };
  
  return (
    <span className={`${colors[tier]} px-2 py-1 rounded`}>
      {score} ({tier})
    </span>
  );
}
```

---

## Checkpoint 5 Criteria

- [ ] All pages render
- [ ] Auth flow works
- [ ] Dashboard shows real-time data
- [ ] Permission mode selector works
