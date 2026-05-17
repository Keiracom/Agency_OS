## Autonomous Worker Loop (Dave 2026-05-17 — prime-clone hierarchy abolished)

All 6 agents (elliot, aiden, max, atlas, orion, scout) are EQUAL WORKERS. There is no prime, no clone, no dispatch hierarchy. The queue is the dispatcher.

### Your loop

1. `bd ready` — see eligible KEIs (phase-locked, unassigned + unblocked)
2. `bd claim --id <KEI-NN>` — take the top one (SKIP LOCKED prevents collision)
3. Read the KEI description in Linear — that IS your brief
4. Execute the work
5. `bd complete --evidence <file>` — close with proof (Gate 2)
6. Back to step 1

### What you do NOT do

- Ask "what do you want me to pick up?" — the queue tells you
- Wait for dispatch from anyone — the queue IS the dispatch
- Say "this is addressed to @<callsign>, not me" — if bd ready shows it, it's yours
- Hold for CONCUR before claiming — phase-lock + SKIP LOCKED is the governance
- Post [READY:callsign] and wait — claim, or sleep 60s and re-check, nothing else

### Review pairing stays

Pull requests still need dual approval before merge. Pairing is AD-HOC — whoever is free reviews, not a fixed prime-clone assignment.

### Elliot-specific addendum (orchestrator role retired)

Elliot is a worker like everyone else. Additional responsibility: fleet health monitoring + PR review coordination (queue-state checks, blocker escalation to #ceo, four-store completion verification). NOT task dispatch.
