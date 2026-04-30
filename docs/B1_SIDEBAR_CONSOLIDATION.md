# B1 sidebar consolidation — R7 audit (2026-04-30)

## Bug confirmed
Two layout shells rendered simultaneously on every dashboard route:
- `app/dashboard/layout.tsx` wrapped children in `DashboardLayout`
  (rich 232px sidebar from `components/layout/dashboard-layout.tsx`)
- Each `/dashboard/*` page also imported `<AppShell>` from
  `components/layout/AppShell.tsx` (72px icon rail)
→ Result: every dashboard sub-route rendered **two sidebars**.

## Importer audit
- **AppShell**: 15 importers across `app/(marketing)`, `app/dashboard`,
  `/leads`, `/campaigns`, `/billing`, `/settings`. 10 of them are
  under `/dashboard` — those are the routes that double-shell.
- **DashboardLayout**: 1 importer (`app/dashboard/layout.tsx`).
- The other "DashboardLayout" matches in the audit are unrelated:
  `components/dashboard-v2/DashboardLayout.tsx` is a different
  component in a parallel folder; `header.tsx` only mentions the name
  in a JSDoc comment.

→ Conclusion: AppShell is the canonical shell (15× usage); the
former dashboard-layout was a wrapper around 1 caller.

## Fix
1. **Sidebar** — nav sections rewritten to match /demo's three-block
   structure:
     Workspace · Home / Pipeline / Feed / Meetings
     Report    · Progress
     Account   · Settings
   Footer accepts an optional `user` prop (initials/name/role) so the
   avatar block reflects the real tenant when one is in scope; falls
   back to the Maya placeholder on marketing pages.
2. **AppShell** — rewritten as the single canonical shell. Now uses
   `<Sidebar>` (rich 232 ↔ 72 collapsible) instead of its inline
   72px rail. Manages mobile drawer + collapsed state + body-scroll
   lock. Renders MobileTopbar + BottomNav. Reads optional user/client
   props OR falls back to context (`useAppShellContext()`) so server-
   fetched auth context can flow down without prop threading.
3. **AppShellContext** (NEW) — tiny context provider that lets the
   server `app/dashboard/layout.tsx` hand the user + client objects
   to whichever AppShell renders below. Sub-routes get the same
   tenant context as before, just without the double shell.
4. **`app/dashboard/layout.tsx`** — stops wrapping children in
   `DashboardLayout`. Just runs the auth/onboarding/membership gates,
   resolves the user + client, then `<AppShellProvider>` hands them
   to the children. Each child sub-route's existing `<AppShell>` now
   renders the only sidebar.
5. **`components/layout/dashboard-layout.tsx`** — deleted.
6. **`DashboardNav` + `DemoModeBanner`** — removed from the dashboard
   server layout. The consolidated Sidebar covers the primary nav,
   BottomNav (PR #458) covers mobile sub-nav, and AppShell renders
   the consolidated `DemoBanner` directly.
7. **`KillSwitch`** — already absent from main after the P3 cleanup
   chain. No action.

## Single-sidebar verification
- `app/dashboard/layout.tsx` no longer renders any layout chrome —
  just `<AppShellProvider>` around children.
- Each dashboard sub-route imports `<AppShell>` and renders one
  Sidebar.
- Marketing routes (`app/leads`, `app/campaigns`, `app/billing`,
  `app/settings`) keep their existing `<AppShell>` import; they were
  never under `/dashboard` so the double-shell bug never applied to
  them, and they pick up the new rich Sidebar automatically.

## Tests
- `pnpm run build` — exit 0
- All routes resolve in build output
- No `ignoreBuildErrors` bypass

## Files
- `frontend/components/layout/AppShell.tsx` — rewritten as canonical shell
- `frontend/components/layout/AppShellContext.tsx` — NEW context bridge
- `frontend/components/layout/sidebar.tsx` — Workspace/Report/Account sections + user-prop footer
- `frontend/app/dashboard/layout.tsx` — server gate only, AppShellProvider wrapper
- `frontend/components/layout/dashboard-layout.tsx` — DELETED
- `docs/B1_SIDEBAR_CONSOLIDATION.md` — this file
