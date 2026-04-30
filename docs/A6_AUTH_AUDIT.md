# A6 auth refinement — R7 audit findings (2026-04-30)

Audit performed before code changes per the dispatch instruction.

## ✅ Demo bypass — already works end-to-end (no fix needed)

| Step | Where | Status |
|---|---|---|
| 1. `?demo=true` in URL | `frontend/middleware.ts:67-83` | Sets `agency_os_demo` cookie (httpOnly off so server + client both read it). Removes cookie when `?demo=false`. |
| 2. Cookie read on server | `frontend/app/dashboard/layout.tsx:23,82-83` | `cookies().get("agency_os_demo")?.value === "true"` short-circuits the three auth/onboarding/membership redirects. |
| 3. Demo client context | `frontend/app/dashboard/layout.tsx:loadDemoContext()` | Looks up the row named "Demo Agency" via `createServerClient` → falls back to a static `{ id: "demo-agency", tier: "ignition", credits: 1250 }` stub if the row is unreachable. |
| 4. Demo user metadata | same | `userData = { email: "demo@keiracom.com", fullName: "Demo Investor" }` injected into the `<DashboardLayout>` props. |

**No gap found.** Plumbing landed in PR #451 and is on current main.

## ✅ Per-tenant data scoping — already in place

`useDashboardV4` (the central data hook) reads the active client via:

```ts
import { useClient } from "./use-client";
…
const { clientId } = useClient();
…
queryKey: ["dashboard-v4", clientId],
queryFn: async () => {
  if (!clientId) throw new Error("No client ID");
  const [metrics, hotLeads, …] = await Promise.all([
    fetchHotLeads(clientId),               // /api/v1/leads?client_id=…
    fetchUpcomingMeetings(clientId),       // /api/v1/meetings?client_id=…
    fetchWarmReplies(clientId),
    fetchDashboardV4Metrics(clientId),
    …
  ]);
  …
},
enabled: !!clientId,
```

Every fetch helper passes `client_id` as a query param to the API. Demo mode supplies `clientId="demo-agency"` (or the live "Demo Agency" UUID when the row exists), so the same scoping path works for demo viewers — they only see Demo Agency rows.

`usePipelineData` and `useLeads` also read `clientId` and scope to the active tenant.

**No gap found.** No new scoping plumbing required for this PR.

## ❌ Login / signup chrome — generic shadcn defaults

| Surface | Before | After |
|---|---|---|
| `(auth)/layout.tsx` | `bg-muted/30` Tailwind default | Cream background + soft amber radial gradients + Playfair "AgencyOS" brand mark with amber italic OS accent + JetBrains Mono "Agency Desk" eyebrow + footer "Try the demo →" link |
| `login/LoginClient.tsx` | shadcn `<Card>` + `<Input>` + `<Button>` | Cream/amber rounded panel + Playfair "Welcome back" headline with amber italic emphasis + mono uppercase labels + cream-bg JetBrains Mono inputs + ink primary button + cream Google secondary button |
| `signup/page.tsx` | shadcn `<Card>` + 4 generic fields | Same treatment as login — Playfair headline "Create your account" with amber italic, mono labels, cream-bg mono inputs, shared `<Field>` helper component |

## Deliverables in this PR

1. `frontend/app/(auth)/layout.tsx` — repalleted shell with brand mark + "Try the demo →" footer link (single-click investor bypass).
2. `frontend/app/(auth)/login/LoginClient.tsx` — same auth logic (`signInWithPassword`, `signInWithOAuth`), new chrome.
3. `frontend/app/(auth)/signup/page.tsx` — same auth logic (`signUp` + email confirmation flow), new chrome.

Demo bypass + per-tenant scoping verifications **left untouched** because both already work on current main.
