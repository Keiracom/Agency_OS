# ADMIN DASHBOARD - REMAINING PAGES BUILD PROMPT

> **Copy this into Claude Code to complete the remaining 9 admin pages.**

---

## CONTEXT

The Admin Dashboard is 55% complete. You need to build the remaining 9 pages.

---

## BEFORE YOU START

Read these files:

1. **`skills/frontend/ADMIN_DASHBOARD.md`** — Full specification
2. **`frontend/app/admin/page.tsx`** — Command Center (reference for patterns)
3. **`frontend/components/admin/`** — Available components

---

## EXISTING PAGES (Do not recreate)

```
✅ /admin                          (Command Center)
✅ /admin/revenue                  (Revenue Dashboard)
✅ /admin/clients                  (Client Directory)
✅ /admin/clients/[id]             (Client Detail)
✅ /admin/campaigns                (All Campaigns)
✅ /admin/leads                    (All Leads)
✅ /admin/activity                 (Activity Log)
✅ /admin/costs/ai                 (AI Spend)
✅ /admin/system                   (System Status)
✅ /admin/compliance/suppression   (Suppression List)
✅ /admin/settings                 (Platform Settings)
```

---

## PAGES TO BUILD (9 remaining)

### Priority 1: Operations

| Page | File to Create | Purpose |
|------|----------------|---------|
| Replies | `frontend/app/admin/replies/page.tsx` | Global reply inbox across all clients |

### Priority 2: Costs

| Page | File to Create | Purpose |
|------|----------------|---------|
| Costs Overview | `frontend/app/admin/costs/page.tsx` | Summary of all costs |
| Channel Costs | `frontend/app/admin/costs/channels/page.tsx` | Per-channel spend breakdown |

### Priority 3: System

| Page | File to Create | Purpose |
|------|----------------|---------|
| Errors | `frontend/app/admin/system/errors/page.tsx` | Sentry error log |
| Queues | `frontend/app/admin/system/queues/page.tsx` | Prefect flow monitor |
| Rate Limits | `frontend/app/admin/system/rate-limits/page.tsx` | Resource usage status |

### Priority 4: Compliance

| Page | File to Create | Purpose |
|------|----------------|---------|
| Compliance Overview | `frontend/app/admin/compliance/page.tsx` | Summary of compliance status |
| Bounces | `frontend/app/admin/compliance/bounces/page.tsx` | Bounce/spam tracker |

### Priority 5: Settings

| Page | File to Create | Purpose |
|------|----------------|---------|
| Users | `frontend/app/admin/settings/users/page.tsx` | User management |

---

## PATTERNS TO FOLLOW

Look at existing pages for patterns:

1. **Data fetching:** Use `useEffect` + `fetch` from `/api/v1/admin/*`
2. **Loading states:** Use `useState` for loading
3. **Components:** Import from `@/components/admin/*` and `@/components/ui/*`
4. **Layout:** Pages are wrapped by `layout.tsx` (sidebar + header already included)

---

## API ENDPOINTS AVAILABLE

All these endpoints already exist in `src/api/routes/admin.py`:

```
GET /api/v1/admin/stats
GET /api/v1/admin/clients
GET /api/v1/admin/clients/{id}
GET /api/v1/admin/activity
GET /api/v1/admin/system/status
GET /api/v1/admin/costs/ai
GET /api/v1/admin/suppression
GET /api/v1/admin/alerts
GET /api/v1/admin/revenue
GET /api/v1/admin/campaigns
GET /api/v1/admin/leads
```

If a page needs an endpoint that doesn't exist, create a placeholder that shows "Coming soon" or static data.

---

## PAGE SPECIFICATIONS

### Replies (`/admin/replies`)

Display all replies across all clients:
- Filter by intent (interested, not_interested, meeting_request, etc.)
- Filter by client
- Show: client name, lead email, channel, intent, timestamp
- Link to lead detail

### Costs Overview (`/admin/costs`)

Summary dashboard:
- Total costs MTD
- AI costs vs Channel costs pie chart
- Link to AI Spend and Channel Costs pages

### Channel Costs (`/admin/costs/channels`)

Per-channel breakdown:
- Email (Resend): X sent, $X cost
- SMS (Twilio): X sent, $X cost
- LinkedIn (HeyReach): X actions, $X cost
- Voice (Synthflow): X calls, $X cost
- Mail (Lob): X sent, $X cost

### Errors (`/admin/system/errors`)

Error log:
- Recent errors from Sentry (or placeholder)
- Error count, error type, affected service
- Link to Sentry if available

### Queues (`/admin/system/queues`)

Prefect flow status:
- Flow name, last run, status, next run
- Active/pending/failed counts

### Rate Limits (`/admin/system/rate-limits`)

Resource usage:
- Apollo: X/Y enrichments used
- Email: X/Y per domain
- LinkedIn: X/Y per seat
- SMS: X/Y per number
- Progress bars for each

### Compliance Overview (`/admin/compliance`)

Summary:
- Suppression count
- Bounce rate
- Spam complaints
- DNCR blocks
- Links to Suppression and Bounces pages

### Bounces (`/admin/compliance/bounces`)

Bounce tracker:
- Recent bounces by client
- Bounce rate by client (flag if >5%)
- Spam complaints

### Users (`/admin/settings/users`)

User management:
- List all users across all clients
- Show: name, email, client(s), role, last active
- Actions: view, deactivate

---

## CONSTRAINTS

1. **Reuse components** — Use existing admin components
2. **Match existing style** — Copy patterns from existing pages
3. **Loading states** — Every page needs loading state
4. **Error handling** — Wrap fetches in try/catch
5. **No `: any` types** — Use proper TypeScript interfaces

---

## SUCCESS CRITERIA

All 9 pages created and:
- [ ] Each page loads without errors
- [ ] Each page has loading state
- [ ] Each page uses admin components
- [ ] Each page matches existing style

---

## START

Begin with Priority 1 (Replies), then work through each priority level.

Report progress after each page.

---

**END OF PROMPT**
