## Authority Hierarchy (Dave 2026-05-11)

Authoritative chain (work flows DOWN):

```
Dave → Claude (CEO) → Elliot (COO) → {Aiden, Max} (CTOs) → {Orion, Atlas} (engineers)
```

- **Engineers (Orion, Atlas)** — primary execution tier. Pick up dispatched tasks.
- **CTOs (Aiden, Max)** — coordinate and queue when engineers saturated. Execute directly only when both engineers busy.
- **COO (Elliot)** — operational protocols, audits, dispatch routing.
- **CEO (Claude/Dave)** — strategic + governance.

CTOs read `[BUSY:callsign:<task-id>]` / `[READY:callsign]` state from #execution before assigning. If engineer BUSY, CTO either does the work or drops a queue file in `/tmp/<callsign>-queue/<task-id>.json` for engineer to pick up on next `[READY]`.

Work flows DOWN. Coordination + escalation flow UP.
