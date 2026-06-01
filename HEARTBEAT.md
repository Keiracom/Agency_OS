# Elliot HEARTBEAT — Session continuation anchor

**Last update:** 2026-06-01T20:57Z

## PHASE 1 — Active (constraints apply)

- temporal_chain crash-recovery proof MUST pass before dispatcher_retirement
- Dispatcher stays up until temporal_chain proven
- Enforcement layer NOT in place until meg5 (2026-06-15) + u7ds (2026-06-22)
- General fleet stays on Claude Max OAuth (NOT permanent API path migration)

## Completed — DO NOT RE-RAISE

- PR #1389 MERGED (1e4a03b08) — Nova/Orion/Atlas personas rebuilt to production depth (1136/924/1043 tokens). Migration live in Supabase.
- PR #1388 MERGED — kept on main (Dave decision 2026-06-01).
- Agency_OS-xjtn: IN_PROGRESS — build done, proof gate pending Dave confirm.

## Open Gates — Awaiting Dave Response

1. Agency_OS-xjtn proof gate: two chain runs (Case A real artifact, Case B empty→Orion REJECTS). Claude Max flat-rate, no incremental cost. Dave confirm needed.
2. Dispatcher crash-injection proof (Scout on hold): needs dispatcher.service start + A$0.25 auth. Dave "go" needed.
3. Temporal crash-recovery Option B: build (~50 lines, Atlas) before proof. Dave sequencing call needed.

## Architecture SSOT

- Temporal server: 45.76.114.137:7233 UP
- Dispatcher: active (running) since 2026-06-01 06:59 UTC
- DISPATCHER_AGENT_COMMAND: src.keiracom_system.vault.agent_cold_start (verify api_ prefix before spawning)
- Work-loop bridge + consumer: active since 2026-05-29

## Resume Instructions

1. Read IDENTITY.md and this file only.
2. Run fleet sweep: `bd ready` + `ls /tmp/telegram-relay-*/outbox/`
3. Dispatch cleared work — no paid chain runs without Dave confirm.
4. Post #ceo ONLY on real state change — NOT on idle watchdog cycles.
