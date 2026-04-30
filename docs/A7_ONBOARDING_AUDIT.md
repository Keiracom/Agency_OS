# A7 onboarding refinement — R7 audit findings (2026-04-30)

Audit performed before code changes per the dispatch instruction.

## Sub-task 1 — Design-skin onboarding pages

### Pre-existing state
All four pages (`agency` / `crm` / `linkedin` / `service-area`) already
implement the **cream / ink / amber** palette and the **Playfair /
DM Sans / JetBrains Mono** type stack. The catch: they do it via
**inline `style={{ backgroundColor: "#F7F3EE", … }}` props** instead
of Tailwind tokens.

This is consistent with the explicit exclusion in the A1 token
codemod ("DO NOT touch frontend/app/onboarding/step-1 through step-5
— inline styles, no Tailwind tokens"), and means the visual output
already matches the /demo design without any chrome work.

### Action this PR
**Targeted migration** of the highest-leverage element across all
four pages: the outer `<div>` wrapper. Each page had:
```jsx
<div
  style={{ backgroundColor: "#F7F3EE", color: "#0C0A08", minHeight: "100vh" }}
  className="flex items-center justify-center px-4 py-16"
>
```
Now:
```jsx
<div className="min-h-screen flex items-center justify-center px-4 py-16 bg-cream text-ink">
```

Inner inline-style sites (button accents, error banners, headlines)
left untouched — they already render correctly. A future codemod
can finish the migration (~140 inline style sites across the four
pages) without changing visual output.

## Sub-task 2 — First-batch trigger

### Pre-existing state
**Not wired.** `service-area/page.tsx`'s `handleConfirm()` POSTs
`{ service_area, finalize: true }` to `/api/v1/onboarding/confirm`
then immediately `router.push("/dashboard")`. No pipeline trigger.

The backend `confirm_icp` endpoint at
`src/api/routes/onboarding.py:693` reads `request.job_id` and updates
the client's ICP fields — does NOT have `service_area` or `finalize`
in its `ConfirmICPRequest` model, so the frontend's "finalize" flag
is currently a no-op at the backend (the `service_area` value is
similarly ignored).

### Action this PR
Added a **fire-and-forget** POST to `/api/v1/pipeline/trigger`
immediately after the `confirm_icp` save succeeds:

```ts
void fetch(`${API_BASE}/api/v1/pipeline/trigger`, {
  method: "POST", credentials: "include",
  body: JSON.stringify({ source: "onboarding_finalize" }),
}).catch(() => { /* non-fatal */ });
```

Wrapped in `void` + `.catch()` so a 404 (endpoint not yet deployed)
or 5xx never blocks dashboard entry. Operator can retrigger from
within the dashboard if the first call dropped.

**Backend follow-up needed** (out of scope for this PR): implement
`POST /api/v1/pipeline/trigger` that resolves `client_id` from the
auth cookie and queues a pipeline run for that tenant.

## Sub-task 3 — `/welcome` retire

### Pre-existing state
`/welcome/page.tsx` was 862 lines: a celebratory founding-member
landing page with tier card, founding-position counter, tier rate
display, sub-state branching for "no subscription / no onboarding /
complete". Most of the visual surface is bespoke and out of scope
for the dashboard rebuild.

### Action this PR
Replaced with a **redirect-only stub** (~95 lines including comments)
that preserves the original destination logic:

| User state | Destination |
|---|---|
| `agency_os_demo=true` cookie | `/onboarding/step-1?demo=true` |
| no Supabase user | `/` |
| no membership | `/` |
| `deposit_paid = false` | `/` |
| `deposit_paid = true`, onboarding complete | `/dashboard` |
| `deposit_paid = true`, onboarding incomplete | `/onboarding/crm` |

The visual placeholder is a minimal cream "Loading your next step…"
card with the Playfair brand mark, shown only during the brief
state-resolution before the redirect fires.

The full prior implementation is preserved in git history — recover
with `git show <prev-sha>:frontend/app/welcome/page.tsx` if the
founding-member program ships again and needs the celebratory copy.

## Verification
```
pnpm run build  →  exit 0
```

## Files touched
- `frontend/app/onboarding/agency/page.tsx` — outer wrapper migration
- `frontend/app/onboarding/crm/page.tsx` — outer wrapper migration
- `frontend/app/onboarding/linkedin/page.tsx` — outer wrapper migration
- `frontend/app/onboarding/service-area/page.tsx` — outer wrapper migration + first-batch trigger
- `frontend/app/welcome/page.tsx` — 862 → ~95 lines (redirect stub)
- `docs/A7_ONBOARDING_AUDIT.md` — this file
