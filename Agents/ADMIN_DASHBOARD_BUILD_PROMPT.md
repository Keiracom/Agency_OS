# ADMIN DASHBOARD BUILD PROMPT — Agency OS v3.0

> **Copy this entire prompt into a Claude Code instance to build the Admin Dashboard.**

---

## IDENTITY

You are building the **Admin Dashboard** for Agency OS v3.0. This is a platform-owner dashboard that provides visibility into all clients, revenue, operations, costs, and system health.

---

## CONTEXT

- **Project:** Agency OS v3.0 — Automated acquisition engine for marketing agencies
- **Current State:** 98/98 build tasks complete, User Dashboard exists in `frontend/app/dashboard/`
- **Your Task:** Build the Admin Dashboard at `frontend/app/admin/`

---

## BEFORE YOU START

Read these files to understand the project:

1. **`skills/frontend/ADMIN_DASHBOARD.md`** — Complete specification (FOLLOW THIS)
2. **`PROJECT_BLUEPRINT.md`** — Architecture rules
3. **`frontend/app/dashboard/`** — Existing patterns to follow
4. **`src/api/routes/`** — Existing API patterns

---

## WHAT YOU'RE BUILDING

| Layer | Location | Purpose |
|-------|----------|---------|
| Database | `supabase/migrations/010_platform_admin.sql` | Add `is_platform_admin` column |
| API | `src/api/routes/admin.py` | Admin-only endpoints |
| Frontend | `frontend/app/admin/*` | Admin pages |
| Components | `frontend/components/admin/*` | Admin components |

---

## CONSTRAINTS

1. **Follow the skill spec** — `skills/frontend/ADMIN_DASHBOARD.md` defines all pages
2. **Match existing patterns** — Copy style from `frontend/app/dashboard/`
3. **Reuse UI components** — Use existing `frontend/components/ui/*`
4. **Admin auth required** — All routes check `is_platform_admin = TRUE`
5. **Soft deletes only** — All queries include `deleted_at IS NULL`
6. **Contract comments** — Every file needs a header comment

---

## IMPLEMENTATION ORDER

Follow this sequence:

```
1. Database migration (is_platform_admin column)
2. Admin API dependency (require_platform_admin)
3. Admin API routes (all endpoints from skill spec)
4. Register routes in main.py
5. Admin layout + sidebar
6. Admin components (KPICard, AlertBanner, etc.)
7. Command Center page (/admin)
8. Remaining pages in priority order from skill spec
```

---

## KEY PAGES (Priority Order)

| Priority | Page | Route |
|----------|------|-------|
| P0 | Command Center | `/admin` |
| P0 | Clients Directory | `/admin/clients` |
| P0 | Client Detail | `/admin/clients/[id]` |
| P0 | AI Spend | `/admin/costs/ai` |
| P0 | System Status | `/admin/system` |
| P1 | All others | See skill spec |

---

## API ENDPOINTS NEEDED

Create these in `src/api/routes/admin.py`:

```
GET  /api/v1/admin/stats           — Command center KPIs
GET  /api/v1/admin/clients         — All clients with health scores
GET  /api/v1/admin/clients/{id}    — Single client detail
GET  /api/v1/admin/activity        — Global activity feed
GET  /api/v1/admin/system/status   — Service health
GET  /api/v1/admin/costs/ai        — AI spend breakdown
GET  /api/v1/admin/suppression     — Suppression list
POST /api/v1/admin/suppression     — Add to suppression
```

See skill spec for full list.

---

## COMPONENTS NEEDED

Create these in `frontend/components/admin/`:

- `AdminSidebar.tsx` — Navigation sidebar
- `AdminHeader.tsx` — Header with alerts
- `KPICard.tsx` — Metric display card
- `AlertBanner.tsx` — System alerts
- `LiveActivityFeed.tsx` — Real-time activity
- `SystemStatusIndicator.tsx` — Service status dots

---

## SUCCESS CRITERIA

Admin dashboard is complete when:

- [ ] Only `is_platform_admin = TRUE` users can access `/admin`
- [ ] Command Center shows MRR, client count, leads today, AI spend
- [ ] System status shows API, Database, Redis, Prefect health
- [ ] Client directory lists all clients with health scores
- [ ] AI spend page shows daily/MTD breakdown
- [ ] All pages follow existing frontend patterns

---

## START

Begin by reading `skills/frontend/ADMIN_DASHBOARD.md`, then execute the implementation order above. Report progress after each major step.

---

**END OF PROMPT**
