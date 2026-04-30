# Frontend build verification — elliot/dashboard-rebuild-pr4 (2026-04-29)

Verifying the dispatched fix-list against the current branch tip.

## Commands run

```
cd frontend
rm -rf .next node_modules/.cache         # critical — see "Stale cache" below
pnpm run build       # → exit 0 (full route tree compiled, no type errors)
npx tsc --noEmit     # → exit 0 (zero output)
pnpm run build       # second run, stable → exit 0
```

## Dispatched fix-list status

| # | Item | Status |
|---|------|--------|
| 1 | LucideIcon type mismatch (ProspectDetailCard + SystemHealth) | ✅ Already fixed by commit `ddbfc08a fix(frontend): lucide-react icon names + duplicate mode prop`. Both files now `import type { LucideIcon }` and use it for icon props. |
| 2 | Missing hook exports `useLinkedInConnect` / `useLinkedInVerify2FA` | ✅ Resolved — `hooks/use-linkedin.ts` documents these as "removed — credential-based" and no callers reference them in `app/`, `components/`, `hooks/`, or `lib/`. |
| 3 | `useLiveActivityFeed.test.ts` JSX in `.ts` extension | ✅ Renamed to `.tsx` (file present at `lib/__tests__/useLiveActivityFeed.test.tsx`). The earlier 4 pre-existing tsc errors I called out in PR1-3 are gone. |
| 4 | API route `pipeline/stream/route.ts` export format | ✅ Verified — exports `dynamic = "force-dynamic"` + `async function GET(request)`. Build compiles the route as `ƒ /api/pipeline/stream` (server-rendered on demand). |
| 5 | `welcome/page.tsx` Supabase type narrowing | ✅ Compiles + types check; route appears in build output as `○ /welcome`. |
| 6 | `MeetingsCalendar.tsx` Map iterator | ✅ Compiles + types check; calendar route appears in build output as `ƒ /dashboard/meetings`. |

## Stale cache caveat

The first build attempt failed with:

```
Error: ENOENT: no such file or directory, open '/.next/build-manifest.json'
```

This was **not** a TypeScript error. The compile + lint + type-check phases
all succeeded; the ENOENT fired during the "Collecting page data" phase
because of a stale `.next` directory from earlier branch switches.
Wiping `.next` and `node_modules/.cache` fixed it on the first re-run, and a
second consecutive build also passed clean.

CI should run `rm -rf .next` (or use a fresh checkout) to avoid this
flakiness on long-lived branches.

## Result

- `pnpm run build` — **exit 0**, full app route tree compiled
- `npx tsc --noEmit` — **exit 0**, zero output
- No `ignoreBuildErrors` bypass added or required

PR #448 (`elliot/dashboard-rebuild-pr4`) is build-clean as of branch tip
`6c16e089`.
