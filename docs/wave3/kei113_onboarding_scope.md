# KEI-113 — Dispatcher Onboarding Flow: Scope + Scaffold

**Status:** Scaffold landed (this PR). Sub-KEIs implement on top.
**Parent:** [KEI-110](https://linear.app/keiracom/issue/KEI-110) — Dispatcher Product Layer (Part 17).
**Authored by:** Scout · 2026-05-17.

## What this PR delivers

A skeleton for the dispatcher onboarding journey. Four stub Next.js pages in a new
`frontend/app/(dispatcher)/` route group + a layout wrapper, plus this scope doc.
No logic — the sub-KEIs land the real implementation against these stubs.

Created files:

| Path | Sub-KEI | Logic owner |
|---|---|---|
| `frontend/app/(dispatcher)/layout.tsx` | scaffold | this PR |
| `frontend/app/(dispatcher)/signup/page.tsx` | KEI-113A (KEI-154) | signup form + Supabase signUp + email-verify redirect |
| `frontend/app/(dispatcher)/verify-email/page.tsx` | KEI-113A (KEI-154) | "check your email" prompt + post-verify redirect |
| `frontend/app/(dispatcher)/onboarding/byo-key/page.tsx` | KEI-113B (KEI-155) | API key input + `pgp_sym_encrypt` on store |
| `frontend/app/(dispatcher)/onboarding/first-task/page.tsx` | KEI-113C (KEI-156) | task form + Prefect enqueue + pending state |
| `frontend/app/(dispatcher)/dashboard/page.tsx` | KEI-113D + KEI-114 family | feed + cost + key mgmt + thread gauge |

## Why a separate `(dispatcher)` route group

The existing `frontend/app/(auth)/signup/page.tsx` and `frontend/app/onboarding/*`
were built for the internal Agency_OS app (agency users onboarding their own
clients — agency/CRM/LinkedIn steps). The Part 17 Dispatcher is a separate
**customer-facing** product: external companies submit tasks to Keiracom. Two
distinct audiences, two distinct flows. The `(dispatcher)` Next.js route group
keeps them cleanly separated without forcing a second Next.js app.

## Dependency graph (what the sub-KEIs need)

```
KEI-111B  (Supabase Auth + RLS)         ──→  KEI-113A (signup UI)
                                              │
KEI-116A  (pgcrypto schema, KEI-167)    ──┐   │
KEI-116B  (encrypt-on-insert, KEI-168)  ──┼──→ KEI-113B (BYO key)
KEI-116C  (SHA-256 lookup, KEI-169)     ──┘   │
                                              ↓
KEI-115E  (LiteLLM router, KEI-166)     ──→  KEI-113C (first task)
                                              │
KEI-114A  (task feed UI, KEI-158)       ──┐   │
KEI-114B  (cost breakdown, KEI-159)     ──┼── ↓
KEI-114C  (API key mgmt UI, KEI-160)    ──┼──→ KEI-113D (dashboard populate)
KEI-114D  (thread gauge, KEI-161)       ──┘   ↓
                                          end of onboarding
```

**Build order suggestion** (so each sub-KEI claimer is unblocked):

1. **KEI-111B** auth layer (Supabase Auth + RLS) — gates 113A
2. **KEI-116A/B/C** pgcrypto schema + encrypt + lookup hash — gate 113B
3. **KEI-113A** signup UI on auth foundation
4. **KEI-113B** BYO key on auth + pgcrypto
5. **KEI-115E** LiteLLM router (or stub) — gates 113C
6. **KEI-113C** first-task submission
7. **KEI-114A-D** dashboard pieces in parallel
8. **KEI-113D** wire dashboard populate on completion

## Out of scope for this PR

- Auth wiring (KEI-111B) — needs Supabase Auth schema, RLS, session middleware
- Crypto layer (KEI-116A/B/C) — needs `pgcrypto` extension + key rotation infra
- Task feed (KEI-114A) — needs the dashboard chrome
- Prefect enqueue (KEI-113C logic) — needs LiteLLM router (KEI-115E)
- Real signup form / BYO-key form / task form — sub-KEI scope
- Tests on stubs — placeholder pages are render-only, no logic to test
- Backend endpoints (`/api/dispatcher/*`) — sub-KEIs add as needed

## Acceptance for this scaffold

- [x] `frontend/app/(dispatcher)/{signup,verify-email,onboarding/byo-key,onboarding/first-task,dashboard}/page.tsx` render placeholder content
- [x] `frontend/app/(dispatcher)/layout.tsx` shell present
- [x] Frontend build still passes (no logic = no regressions)
- [x] Scope doc captures the dep graph + sequencing for sub-KEI claimers
- [x] All 4 sub-KEIs (KEI-154/155/156/157) have a target file to implement against

## Reference

- Parent: KEI-110 Dispatcher Product Layer (Linear).
- Sub-KEIs: KEI-154/155/156/157 (this scaffold's downstream).
- Wave 3 filing: Elliot ts ~1779028xxx — "Part 17 product layer fully decomposed. Linear KEI-145 through KEI-172."
