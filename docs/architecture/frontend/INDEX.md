# Frontend Architecture — Agency OS

**Purpose:** UI architecture aligned with backend systems.

---

## Documents

| Doc | Purpose | Backend Alignment | Status |
|-----|---------|-------------------|--------|
| [TECHNICAL.md](TECHNICAL.md) | Tech stack, patterns, API client | foundation/API_LAYER.md | ✅ Complete |
| [DASHBOARD.md](DASHBOARD.md) | Main dashboard, KPIs, reports | business/METRICS.md | 🔴 Not created |
| [CAMPAIGNS.md](CAMPAIGNS.md) | Campaign UI pages | business/CAMPAIGNS.md | 🔴 Not created |
| [LEADS.md](LEADS.md) | Lead list, detail, ALS display | flows/ENRICHMENT.md | 🔴 Not created |
| [SETTINGS.md](SETTINGS.md) | ICP, LinkedIn, client settings | flows/ONBOARDING.md | 🔴 Not created |
| [ONBOARDING.md](ONBOARDING.md) | Onboarding flow UI | flows/ONBOARDING.md | 🔴 Not created |
| [ADMIN.md](ADMIN.md) | Admin panel (21 pages) | All backend | ✅ Complete |

---

## Page Summary

| Section | Pages | Purpose |
|---------|-------|---------|
| Dashboard | 11 | Client workspace |
| Admin | 22 | Platform management |
| Onboarding | 4 | New client setup |
| Auth | 3 | Login, signup |
| Marketing | 3 | Public pages |

---

## Tech Stack

- Next.js 14 (App Router)
- React Query (server state)
- Shadcn/ui + Tailwind (styling)
- Supabase Auth (JWT)

---

## Cross-References

- [Master Index](../ARCHITECTURE_INDEX.md)
- [TODO.md](../TODO.md) — Gaps and priorities
