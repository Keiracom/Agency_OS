# Frontend Technical Architecture — Agency OS

**Purpose:** Defines the Next.js 14 frontend architecture, component structure, state management patterns, and API integration layer for Agency OS.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-22

---

## Overview

Agency OS frontend is a Next.js 14 application using the App Router pattern. It provides a multi-tenant SaaS dashboard for agency clients to manage campaigns, leads, and outreach, plus a platform admin interface for system-wide operations.

The frontend follows a React Query-first approach for server state management, with Shadcn/ui (Radix primitives) for consistent UI components. Authentication is handled via Supabase Auth with JWT tokens passed to the FastAPI backend.

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Framework | Next.js | 14.0.4 | App Router, SSR/SSG |
| UI Library | React | 18.2.0 | Component model |
| Language | TypeScript | 5.9.3 | Type safety (strict) |
| Styling | Tailwind CSS | 3.4.19 | Utility-first CSS |
| Components | Shadcn/ui + Radix | Various | Accessible UI primitives |
| Server State | TanStack React Query | 5.17.0 | Data fetching/caching |
| Forms | React Hook Form | 7.49.0 | Form state management |
| Validation | Zod | 3.22.0 | Schema validation |
| Auth | Supabase Auth | 2.39.0 | JWT authentication |
| Charts | Recharts | 2.15.4 | Data visualization |
| Icons | Lucide React | 0.303.0 | Icon library |

---

## Folder Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── (auth)/             # Auth route group (login, signup)
│   ├── (marketing)/        # Marketing pages (about, pricing, how-it-works)
│   ├── admin/              # Platform admin pages (22 pages)
│   ├── api/                # API routes (if any)
│   ├── auth/               # Auth callback handler
│   ├── dashboard/          # Client dashboard pages (11 pages)
│   ├── onboarding/         # Onboarding flow (4 pages)
│   ├── logo-showcase/      # Logo showcase page
│   ├── globals.css         # Global styles
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing page
│   └── providers.tsx       # React Query + Auth providers
│
├── components/             # React components (61 total)
│   ├── admin/              # Admin-specific components (8)
│   ├── campaigns/          # Campaign components
│   ├── communication/      # Communication viewers
│   ├── dashboard/          # Dashboard widgets (4)
│   ├── generated/          # Generated components (v0)
│   ├── landing/            # Landing page components (6)
│   ├── layout/             # Layout components (4)
│   ├── leads/              # Lead-specific components
│   ├── marketing/          # Marketing components (3)
│   ├── onboarding/         # Onboarding components (4)
│   └── ui/                 # Shadcn/ui primitives (24+)
│
├── hooks/                  # Custom React hooks (12)
├── lib/                    # Utilities + API client
│   ├── api/                # API endpoint wrappers (9 files)
│   ├── supabase.ts         # Supabase client
│   └── utils.ts            # Utility functions
│
├── public/                 # Static assets
└── types/                  # TypeScript types (currently empty)
```

---

## Code Locations

### Pages (42 Total)

| Route | File | Purpose |
|-------|------|---------|
| **Root** | | |
| `/` | `app/page.tsx` | Landing page |
| `/logo-showcase` | `app/logo-showcase/page.tsx` | Logo showcase |
| **Auth (3)** | | |
| `/login` | `app/(auth)/login/page.tsx` | User login |
| `/signup` | `app/(auth)/signup/page.tsx` | User registration |
| `/auth/callback` | `app/auth/callback/` | OAuth callback handler |
| **Marketing (3)** | | |
| `/about` | `app/(marketing)/about/page.tsx` | About page |
| `/how-it-works` | `app/(marketing)/how-it-works/page.tsx` | Product explanation |
| `/pricing` | `app/(marketing)/pricing/page.tsx` | Pricing tiers |
| **Dashboard (11)** | | |
| `/dashboard` | `app/dashboard/page.tsx` | Main dashboard |
| `/dashboard/campaigns` | `app/dashboard/campaigns/page.tsx` | Campaign list |
| `/dashboard/campaigns/new` | `app/dashboard/campaigns/new/page.tsx` | Create campaign |
| `/dashboard/campaigns/[id]` | `app/dashboard/campaigns/[id]/page.tsx` | Campaign detail |
| `/dashboard/leads` | `app/dashboard/leads/page.tsx` | Lead list |
| `/dashboard/leads/[id]` | `app/dashboard/leads/[id]/page.tsx` | Lead detail |
| `/dashboard/replies` | `app/dashboard/replies/page.tsx` | Reply inbox |
| `/dashboard/reports` | `app/dashboard/reports/page.tsx` | Analytics reports |
| `/dashboard/settings` | `app/dashboard/settings/page.tsx` | Client settings |
| `/dashboard/settings/icp` | `app/dashboard/settings/icp/page.tsx` | ICP configuration |
| `/dashboard/settings/linkedin` | `app/dashboard/settings/linkedin/page.tsx` | LinkedIn settings |
| **Admin (22)** | | |
| `/admin` | `app/admin/page.tsx` | Admin dashboard |
| `/admin/activity` | `app/admin/activity/page.tsx` | Activity log |
| `/admin/campaigns` | `app/admin/campaigns/page.tsx` | All campaigns |
| `/admin/clients` | `app/admin/clients/page.tsx` | Client list |
| `/admin/clients/[id]` | `app/admin/clients/[id]/page.tsx` | Client detail |
| `/admin/leads` | `app/admin/leads/page.tsx` | All leads |
| `/admin/replies` | `app/admin/replies/page.tsx` | All replies |
| `/admin/revenue` | `app/admin/revenue/page.tsx` | Revenue metrics |
| `/admin/costs` | `app/admin/costs/page.tsx` | Cost overview |
| `/admin/costs/ai` | `app/admin/costs/ai/page.tsx` | AI costs breakdown |
| `/admin/costs/channels` | `app/admin/costs/channels/page.tsx` | Channel costs |
| `/admin/compliance` | `app/admin/compliance/page.tsx` | Compliance overview |
| `/admin/compliance/bounces` | `app/admin/compliance/bounces/page.tsx` | Bounce management |
| `/admin/compliance/suppression` | `app/admin/compliance/suppression/page.tsx` | Suppression list |
| `/admin/settings` | `app/admin/settings/page.tsx` | Admin settings |
| `/admin/settings/users` | `app/admin/settings/users/page.tsx` | User management |
| `/admin/system` | `app/admin/system/page.tsx` | System status |
| `/admin/system/errors` | `app/admin/system/errors/page.tsx` | Error log |
| `/admin/system/queues` | `app/admin/system/queues/page.tsx` | Queue status |
| `/admin/system/rate-limits` | `app/admin/system/rate-limits/page.tsx` | Rate limit status |
| **Onboarding (4)** | | |
| `/onboarding` | `app/onboarding/page.tsx` | Onboarding start |
| `/onboarding/linkedin` | `app/onboarding/linkedin/page.tsx` | LinkedIn connection |
| `/onboarding/manual-entry` | `app/onboarding/manual-entry/page.tsx` | Manual ICP entry |
| `/onboarding/skip` | `app/onboarding/skip/page.tsx` | Skip onboarding |

### Components (61 Total)

| Category | Count | Components |
|----------|-------|------------|
| **UI Primitives** | 24 | button, input, label, card, badge, avatar, dropdown-menu, toaster, toast, select, table, tabs, progress, dialog, switch, separator, skeleton, textarea, loading-skeleton, error-state, empty-state, tooltip, collapsible, alert-dialog |
| **Admin** | 8 | AdminSidebar, AdminHeader, KPICard, AlertBanner, SystemStatusIndicator, LiveActivityFeed, ClientHealthIndicator |
| **Dashboard** | 4 | ActivityTicker, CapacityGauge, CoPilotView, meetings-widget |
| **Landing** | 6 | HeroSection, TypingDemo, HowItWorksTabs, HowItWorksCarousel, DashboardDemo, ActivityFeed, SocialProofBar |
| **Layout** | 4 | dashboard-layout, header, sidebar, credits-badge |
| **Onboarding** | 4 | LinkedInCredentialForm, LinkedInTwoFactor, LinkedInConnecting, LinkedInSuccess |
| **Marketing** | 3 | waitlist-form, floating-founding-spots, founding-spots |
| **Generated** | 3 | agency-os-hero, ai-email-writer, how-it-works-section |
| **Other** | 5 | permission-mode-selector, icp-progress-banner, icp-review-modal, ALSScorecard, TranscriptViewer |

### Hooks (12 Total)

| Hook | File | Purpose |
|------|------|---------|
| `use-leads` | `hooks/use-leads.ts` | Lead data fetching |
| `use-campaigns` | `hooks/use-campaigns.ts` | Campaign data fetching |
| `use-client` | `hooks/use-client.ts` | Client data fetching |
| `use-reports` | `hooks/use-reports.ts` | Report data fetching |
| `use-admin` | `hooks/use-admin.ts` | Admin data fetching |
| `use-replies` | `hooks/use-replies.ts` | Reply data fetching |
| `use-meetings` | `hooks/use-meetings.ts` | Meeting data fetching |
| `use-linkedin` | `hooks/use-linkedin.ts` | LinkedIn integration |
| `use-deep-research` | `hooks/use-deep-research.ts` | SDK deep research |
| `use-icp-job` | `hooks/use-icp-job.ts` | ICP job polling |
| `use-toast` | `hooks/use-toast.ts` | Toast notifications |
| `use-scroll-animation` | `hooks/use-scroll-animation.tsx` | Scroll animations |

### API Layer (9 Files)

| File | Purpose |
|------|---------|
| `lib/api/index.ts` | Central API client with JWT auth |
| `lib/api/types.ts` | TypeScript type definitions (350+ lines) |
| `lib/api/campaigns.ts` | Campaign API endpoints |
| `lib/api/leads.ts` | Lead API endpoints |
| `lib/api/admin.ts` | Admin API endpoints |
| `lib/api/reports.ts` | Report API endpoints |
| `lib/api/replies.ts` | Reply API endpoints |
| `lib/api/meetings.ts` | Meeting API endpoints |
| `lib/api/linkedin.ts` | LinkedIn API endpoints |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                       │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │   Component  │───▶│  React Hook  │───▶│     React Query          │  │
│  │  (e.g. Page) │    │ (use-leads)  │    │ (useQuery/useMutation)   │  │
│  └──────────────┘    └──────────────┘    └─────────────┬────────────┘  │
│                                                         │               │
│                                          ┌──────────────▼────────────┐  │
│                                          │      API Client           │  │
│                                          │   (lib/api/index.ts)      │  │
│                                          │  + JWT from Supabase Auth │  │
│                                          └──────────────┬────────────┘  │
└─────────────────────────────────────────────────────────┼───────────────┘
                                                          │
                                                          │ HTTP + Bearer Token
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                                 │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  API Router  │───▶│  Auth Deps   │───▶│     Service Layer        │  │
│  │              │    │ (JWT verify) │    │                          │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Request Flow Example

```
1. User clicks "Create Campaign" button
2. Component calls useCampaigns().createCampaign(data)
3. Hook wraps useMutation() from React Query
4. API client (lib/api/campaigns.ts) formats request
5. index.ts adds JWT token from Supabase session
6. fetch() sends POST to /api/v1/campaigns
7. FastAPI validates token, processes request
8. Response returns, React Query caches result
9. UI updates via query invalidation
```

---

## State Management Pattern

| State Type | Solution | Example |
|------------|----------|---------|
| **Server State** | React Query | Lead list, campaign data |
| **Form State** | React Hook Form + Zod | Campaign creation form |
| **Auth State** | Supabase Auth | User session, JWT |
| **UI State** | React useState | Modal open/closed |
| **Route State** | Next.js App Router | URL params, search params |

**No global client store (Redux/Zustand) is used.** All persistent state lives on the server and is accessed via React Query.

### React Query Configuration

```typescript
// app/providers.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

---

## Authentication Pattern

### Flow

```
1. User enters credentials on /login
2. Supabase Auth validates, returns JWT
3. JWT stored in browser (cookie/localStorage)
4. API client reads JWT on every request
5. Backend validates JWT with Supabase public key
6. Multi-tenant context derived from memberships table
```

### Auth Components

| Layer | Implementation |
|-------|----------------|
| **Provider** | `@supabase/auth-helpers-nextjs` |
| **Client** | `lib/supabase.ts` (createBrowserClient) |
| **Token Access** | `supabase.auth.getSession()` |
| **Route Protection** | Server components check session |

### Role System

| Role | Access |
|------|--------|
| `owner` | Full client access + billing |
| `admin` | Full client access |
| `member` | Limited access (campaigns, leads) |
| `viewer` | Read-only access |
| `is_platform_admin` | Superuser flag (admin routes) |

---

## Key Rules

1. **React Query for ALL server data** — Never use raw useState for data that comes from the backend. Always use useQuery/useMutation.

2. **No direct fetch calls** — All API requests go through `lib/api/index.ts` to ensure consistent auth headers and error handling.

3. **Shadcn/ui for UI primitives** — Use existing components from `components/ui/`. Don't create custom buttons, inputs, cards, etc.

4. **Tailwind only** — No CSS modules, no styled-components, no inline styles. Use Tailwind utility classes.

5. **Server components for auth** — Use Next.js server components to check authentication before rendering protected routes.

6. **Client components for interactivity** — Add "use client" directive only when hooks or browser APIs are needed.

7. **Hooks wrap React Query** — Custom hooks in `hooks/` should be thin wrappers around React Query, not contain business logic.

8. **Types from API layer** — Import types from `lib/api/types.ts`, don't duplicate type definitions in components.

9. **Zod for form validation** — All forms use React Hook Form with Zod schemas. Never validate manually.

10. **Invalidate, don't refetch** — After mutations, invalidate query keys so React Query refetches automatically.

---

## Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Required | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Required | Supabase anonymous key |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI backend URL |

### Production URLs

| Environment | API URL |
|-------------|---------|
| Development | `http://localhost:8000` |
| Production | `https://agency-os-production.up.railway.app` |

---

## Component Patterns

### Page Component

```typescript
// app/dashboard/campaigns/page.tsx
"use client";

import { useCampaigns } from "@/hooks/use-campaigns";
import { LoadingSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";

export default function CampaignsPage() {
  const { data, isLoading, error } = useCampaigns();

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorState error={error} />;

  return <CampaignList campaigns={data} />;
}
```

### Custom Hook

```typescript
// hooks/use-campaigns.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignApi } from "@/lib/api/campaigns";

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: campaignApi.list,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: campaignApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}
```

### Form Component

```typescript
// components/campaigns/CampaignForm.tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { campaignSchema, type CampaignFormData } from "@/lib/api/types";

export function CampaignForm({ onSubmit }) {
  const form = useForm<CampaignFormData>({
    resolver: zodResolver(campaignSchema),
    defaultValues: { name: "", status: "draft" },
  });

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* Form fields using Shadcn/ui components */}
    </form>
  );
}
```

---

## Cross-References

- [Frontend Index](INDEX.md) — All frontend docs
- [API Layer](../foundation/API_LAYER.md) — Backend API routes and auth
- [Database](../foundation/DATABASE.md) — Data models (SQLAlchemy)

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
