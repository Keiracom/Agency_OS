# SKILL.md — Missing UI Features

**Skill:** Phase 14 Missing UI Components  
**Author:** CTO (Claude)  
**Version:** 1.0  
**Created:** December 27, 2025  
**Phase:** 14

---

## Purpose

Add 4 missing UI features to complete the user dashboard experience. These are isolated components that follow existing patterns.

---

## Prerequisites

- Phase 13 (Frontend-Backend Connection) complete or in progress
- React Query hooks pattern established
- Existing UI components in `frontend/components/ui/`

---

## Tasks Overview

| Task ID | Feature | Est. Hours | Complexity |
|---------|---------|------------|------------|
| MUI-001 | Replies page | 4 | Medium |
| MUI-002 | Meetings widget | 2 | Low |
| MUI-003 | Credits badge | 1 | Low |
| MUI-004 | Content visibility in Lead timeline | 3 | Medium |

---

## MUI-001: Replies Page

**Location:** `frontend/app/dashboard/replies/page.tsx`

**Purpose:** Inbox-style view of all lead replies across campaigns, with intent filtering.

**Reference Pattern:** Copy structure from `frontend/app/dashboard/leads/page.tsx`

### Features Required
- List of replies with lead info, channel icon, timestamp
- Filter by intent type (interested, meeting_request, question, not_interested, etc.)
- Filter by channel (email, sms, linkedin)
- Click to expand full message content
- Quick action buttons: Mark as handled, View lead, Reply

### API Endpoints Needed
```
GET /api/v1/clients/{id}/replies
GET /api/v1/clients/{id}/replies?intent=interested
GET /api/v1/clients/{id}/replies?channel=email
PATCH /api/v1/clients/{id}/replies/{id}/handled
```

### Data Structure
```typescript
interface Reply {
  id: string;
  lead_id: string;
  lead: {
    first_name: string;
    last_name: string;
    email: string;
    company: string;
  };
  campaign_id: string;
  campaign_name: string;
  channel: "email" | "sms" | "linkedin";
  intent: "meeting_request" | "interested" | "question" | "not_interested" | "unsubscribe" | "out_of_office" | "auto_reply";
  content: string;
  received_at: string;
  handled: boolean;
  handled_at: string | null;
}
```

### UI Components
- Use `Badge` for intent type (color-coded)
- Use channel icons from lucide-react (Mail, MessageSquare, Linkedin)
- Use `Card` for each reply item
- Use `Sheet` or `Dialog` for expanded view

### Files to Create
```
frontend/
├── app/dashboard/replies/page.tsx
├── lib/api/replies.ts
└── hooks/use-replies.ts
```

---

## MUI-002: Meetings Widget

**Location:** `frontend/components/dashboard/meetings-widget.tsx`

**Purpose:** Small widget showing upcoming meetings booked via Agency OS, displayed on dashboard home.

**Reference Pattern:** Look at activity feed pattern in `frontend/app/dashboard/page.tsx`

### Features Required
- Show next 3-5 upcoming meetings
- Display: Lead name, company, date/time, meeting type
- "No meetings" empty state
- Link to calendar integration settings

### API Endpoint Needed
```
GET /api/v1/clients/{id}/meetings?upcoming=true&limit=5
```

### Data Structure
```typescript
interface Meeting {
  id: string;
  lead_id: string;
  lead_name: string;
  lead_company: string;
  scheduled_at: string;
  duration_minutes: number;
  meeting_type: "discovery" | "demo" | "follow_up";
  calendar_link: string | null;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
}
```

### UI Components
- Use `Card` with `CardHeader` "Upcoming Meetings"
- Use `Avatar` for lead initials
- Use relative time (e.g., "Tomorrow at 2pm", "In 3 days")
- Calendar icon from lucide-react

### Files to Create
```
frontend/
├── components/dashboard/meetings-widget.tsx
├── lib/api/meetings.ts
└── hooks/use-meetings.ts
```

### Integration Point
Add to `frontend/app/dashboard/page.tsx` in the sidebar/right column area.

---

## MUI-003: Credits Badge

**Location:** `frontend/components/layout/credits-badge.tsx`

**Purpose:** Persistent badge in header showing remaining credits with visual warning when low.

**Reference Pattern:** Look at header component in `frontend/components/layout/header.tsx`

### Features Required
- Show current credits count
- Color coding: Green (>500), Yellow (100-500), Red (<100)
- Tooltip explaining credits
- Link to billing/upgrade page

### API Endpoint Needed
```
GET /api/v1/clients/{id}  # Already returns credits_remaining
```

### UI Components
- Use `Badge` with dynamic variant
- Use `Tooltip` for explanation
- Use `Coins` icon from lucide-react

### Implementation
```typescript
function CreditsBadge() {
  const { client } = useClient();
  
  const variant = 
    client.credits_remaining > 500 ? "default" :
    client.credits_remaining > 100 ? "warning" : "destructive";
  
  return (
    <Tooltip content="Credits remaining this month">
      <Badge variant={variant} className="gap-1">
        <Coins className="h-3 w-3" />
        {client.credits_remaining.toLocaleString()}
      </Badge>
    </Tooltip>
  );
}
```

### Files to Create/Modify
```
frontend/
├── components/layout/credits-badge.tsx  # NEW
└── components/layout/header.tsx         # ADD credits badge
```

---

## MUI-004: Content Visibility in Lead Timeline

**Location:** `frontend/app/dashboard/leads/[id]/page.tsx`

**Purpose:** Show actual message content (email body, SMS text, LinkedIn message) in the lead activity timeline, not just "Email sent".

**Reference Pattern:** Expand existing timeline in lead detail page.

### Current State
```
[Email icon] Email sent - Dec 25, 2025 10:30 AM
[SMS icon] SMS sent - Dec 27, 2025 2:15 PM
```

### Target State
```
[Email icon] Email sent - Dec 25, 2025 10:30 AM
  Subject: Quick question about your marketing
  "Hi Sarah, I noticed TechCorp recently expanded into..."
  [Expand] [Copy]

[SMS icon] SMS sent - Dec 27, 2025 2:15 PM
  "Hi Sarah, did you get my email? Would love to chat..."
  [Copy]
```

### Features Required
- Expandable content section under each activity
- Show subject line for emails
- Truncate long content with "Show more"
- Copy button for content
- Different styling for sent vs received

### Data Already Available
Activities already have `metadata` field containing:
```typescript
metadata: {
  subject?: string;      // Email subject
  body?: string;         // Full content
  preview?: string;      // First 100 chars
  template_id?: string;  // If from template
}
```

### UI Components
- Use `Collapsible` from shadcn for expand/collapse
- Use `Button` with copy icon
- Use `cn()` for conditional styling (sent = right aligned, received = left)

### Files to Modify
```
frontend/
└── app/dashboard/leads/[id]/page.tsx  # Modify timeline section
```

### Implementation Notes
- Check if `activity.metadata.body` exists before showing expand
- Use `useState` to track which activities are expanded
- Limit preview to 100 chars, full content on expand

---

## Implementation Order

```
1. MUI-003: Credits Badge (1 hour) — Quick win, adds polish
2. MUI-002: Meetings Widget (2 hours) — Self-contained component
3. MUI-004: Content Visibility (3 hours) — Enhances existing page
4. MUI-001: Replies Page (4 hours) — Largest, save for last
```

---

## Success Criteria

### MUI-001 Complete When:
- [ ] Replies page accessible at `/dashboard/replies`
- [ ] List shows all replies with lead info
- [ ] Filters work (intent, channel)
- [ ] Expand shows full content
- [ ] Mark as handled updates state

### MUI-002 Complete When:
- [ ] Widget displays on dashboard home
- [ ] Shows next 5 meetings
- [ ] Empty state when no meetings
- [ ] Click navigates to lead

### MUI-003 Complete When:
- [ ] Badge visible in header
- [ ] Color changes based on credit level
- [ ] Tooltip shows explanation
- [ ] Click goes to billing

### MUI-004 Complete When:
- [ ] Timeline shows content preview
- [ ] Expand reveals full content
- [ ] Copy button works
- [ ] Sent vs received styled differently

---

## Backend Endpoints to Verify

Before building, check these endpoints exist:

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /clients/{id}/replies` | 🔴 May need creating | Check webhooks.py |
| `GET /clients/{id}/meetings` | 🔴 May need creating | New endpoint |
| `GET /clients/{id}` | ✅ Exists | Returns credits_remaining |
| `GET /clients/{id}/leads/{id}/activities` | ✅ Exists | Has metadata field |

If endpoints don't exist, create them following patterns in `src/api/routes/`.

---

## Navigation Updates

Add "Replies" to sidebar navigation:

```typescript
// frontend/components/layout/sidebar.tsx
const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Campaigns", href: "/dashboard/campaigns", icon: Megaphone },
  { name: "Leads", href: "/dashboard/leads", icon: Users },
  { name: "Replies", href: "/dashboard/replies", icon: MessageSquare }, // ADD THIS
  { name: "Reports", href: "/dashboard/reports", icon: BarChart },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];
```

---

**END OF MISSING UI SKILL**
