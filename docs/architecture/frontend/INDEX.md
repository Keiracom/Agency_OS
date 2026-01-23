# Frontend Architecture — Agency OS

**Purpose:** UI architecture aligned with backend systems.

---

## Documents

| Doc | Purpose | Backend Alignment | Status |
|-----|---------|-------------------|--------|
| [TECHNICAL.md](TECHNICAL.md) | Tech stack, patterns, API client | foundation/API_LAYER.md | ✅ Complete |
| [DASHBOARD.md](DASHBOARD.md) | Main dashboard, KPIs, reports | business/METRICS.md | ✅ Complete |
| [CAMPAIGNS.md](CAMPAIGNS.md) | Campaign UI pages | business/CAMPAIGNS.md | ✅ Complete |
| [LEADS.md](LEADS.md) | Lead list, detail, ALS display | flows/ENRICHMENT.md | ✅ Complete |
| [SETTINGS.md](SETTINGS.md) | ICP, LinkedIn, client settings | flows/ONBOARDING.md | ✅ Complete |
| [ONBOARDING.md](ONBOARDING.md) | Onboarding flow UI | flows/ONBOARDING.md | ✅ Complete |
| [ADMIN.md](ADMIN.md) | Admin panel (21 pages) | All backend | ✅ Complete |
| [SPEC_ALIGNMENT.md](SPEC_ALIGNMENT.md) | Docs vs code alignment report | All frontend | ⚠️ 50% Aligned |

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

## Phase H: Client Transparency Components

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| EmergencyPauseButton | `components/dashboard/` | Pause all outreach | ✅ Implemented |
| Digest Settings | `/dashboard/settings/digest` | Configure email digest | ✅ API Ready |
| Live Activity Feed | `/dashboard/activity` | Real-time outreach stream | 🔴 Pending |
| Content Archive | `/dashboard/content` | Searchable sent content | 🔴 Pending |
| Best Of Showcase | `/dashboard/showcase` | High-performing examples | 🔴 Pending |

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
