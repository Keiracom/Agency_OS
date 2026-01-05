# Phase 13: Frontend-Backend Integration

**Status:** ✅ Complete  
**Dependencies:** Phases 7-8 complete

---

## Overview

Connect frontend components to backend API endpoints. This phase ensures all UI interactions properly communicate with the FastAPI backend.

---

## Skill Reference

**Primary Skill:** `skills/frontend/FRONTEND_BACKEND_SKILL.md`

This skill provides detailed guidance on:
- API client setup
- Authentication flow
- Real-time subscriptions
- Error handling patterns
- Loading states

---

## Key Integration Points

### Authentication
- Supabase Auth on frontend
- JWT verification on backend
- Membership-based access control

### Campaign Management
- Create/edit campaigns
- Start/pause/complete campaigns
- View campaign metrics

### Lead Management
- View lead lists with ALS tiers
- Individual lead details
- Manual enrichment triggers

### Real-time Updates
- Supabase real-time subscriptions
- Activity feed updates
- Campaign status changes

---

## API Client Pattern

```typescript
// frontend/lib/api.ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function fetchCampaigns(clientId: string) {
  const { data: { session } } = await supabase.auth.getSession()
  
  const response = await fetch(`/api/v1/campaigns`, {
    headers: {
      'Authorization': `Bearer ${session?.access_token}`,
      'X-Client-Id': clientId
    }
  })
  
  return response.json()
}
```

---

## Related Documentation

- **Phase 7 (API):** `docs/phases/PHASE_07_API.md`
- **Phase 8 (Frontend):** `docs/phases/PHASE_08_FRONTEND.md`
- **Frontend Skill:** `skills/frontend/FRONTEND_BACKEND_SKILL.md`
