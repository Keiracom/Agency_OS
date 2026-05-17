# KEI-114 — Customer Dashboard MVP Scope

**Linear:** [KEI-114](https://linear.app/keiracom/issue/KEI-114)
**Parent:** KEI-110 (Dispatcher Product Layer — Part 17)
**Phase:** Product Layer / **Priority:** P1 (first-customer essential, post-Wave-3 bump from P2)

This umbrella scaffold lays out the route group `(dispatcher)/dashboard/` and 4 stub pages. Sub-KEI implementers do the real UI + data wiring on top. Pattern mirrors Scout's KEI-113 onboarding scaffold (PR #953).

---

## Sub-KEI dep graph

```
                  KEI-110 (parent — Part 17)
                          |
                  KEI-114 (this scaffold)
                          |
        +-----------------+-----------------+-----------+
        |                 |                 |           |
   KEI-114A          KEI-114B          KEI-114C     KEI-114D
   (KEI-158)         (KEI-159)         (KEI-160)    (KEI-161)
   Feed Component    Cost Display      Key Mgmt UI  Usage Meter
        |                 |                 |           |
        v                 v                 v           v
   needs:            needs:            needs:       needs:
   KEI-111E (RLS)    KEI-114A first    KEI-111E +   KEI-117A
   KEI-115B (live)                     KEI-116A/B/C (Valkey)
```

Critical-path observation: **KEI-114A (Feed) is the longest chain** because every other tile expects the feed exists to drill into. Start 114A first; 114B/C/D can run in parallel once 114A scaffolds.

---

## Sub-KEI map

| Linear KEI | File | Implementer scope |
|---|---|---|
| KEI-114A / [KEI-158](https://linear.app/keiracom/issue/KEI-158) | `frontend/app/(dispatcher)/dashboard/feed/page.tsx` | Tasks table fetch + Realtime + pagination. Render-path components already exist via Scout's PR #957 (`frontend/components/dispatcher/TaskFeed.tsx`). |
| KEI-114B / [KEI-159](https://linear.app/keiracom/issue/KEI-159) | `frontend/app/(dispatcher)/dashboard/costs/page.tsx` | Cost-per-task breakdown + cumulative AUD spend card. Materialised view or daily-rollup so render isn't a sum-on-every-load. |
| KEI-114C / [KEI-160](https://linear.app/keiracom/issue/KEI-160) | `frontend/app/(dispatcher)/dashboard/keys/page.tsx` | List + rotate + revoke. Plaintext surfaced ONCE at create/rotate; otherwise display lookup-hash prefix only per KEI-116. |
| KEI-114D / [KEI-161](https://linear.app/keiracom/issue/KEI-161) | `frontend/app/(dispatcher)/dashboard/usage/page.tsx` | Live thread counter from Valkey + tier indicator. Colour-banded gauge + upgrade CTA at sustained >80%. |

---

## Out of scope for this PR

- Real data fetching, auth wiring, schema migrations — sub-KEIs.
- The `(dispatcher)` route group base layout — shipped by Scout's PR #953.
- Real Supabase RLS policies — KEI-111E.
- BYO key encryption (pgcrypto) — KEI-116A/B/C.
- Rate-limit Valkey wiring — KEI-117A/B/C.

## Decision: separate route group, not sibling under existing `dashboard/`

`frontend/app/dashboard/` already hosts the Agency_OS-internal dashboard (campaigns, leads, replies, pipeline, etc.). The dispatcher customer-facing dashboard is a different audience with different RLS scope. Scout's PR #953 established `(dispatcher)/` as the customer route group; this PR adds the dashboard subpages under that group. Clean separation, no risk of cross-leak of internal Agency_OS routes into customer view.

## Source

Dave KEI-114 in Wave 3 Part 17 decomposition (P2→P1 bump 3-of-3 ratified 2026-05-17). KEI-114 itself is umbrella scaffold; sub-KEIs do the implementation per Scout's KEI-113 (PR #953) pattern.
