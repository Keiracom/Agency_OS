# BOOTSTRAP.md — Session Initialization Protocol
# Version: 1.0 | Created: 2026-02-12

---

## TRIGGER
Start of any new session, after `/reset`, or after context compaction.

## MANDATORY SEQUENCE (Do not skip steps)

### Step 1: Load Identity
Read these files (they define WHO you are):
- `ENFORCE.md` — Hard laws (already loaded by system)
- `SOUL.md` — Persona and values
- `AGENTS.md` — Operational behavior

### Step 2: Query Supabase Memory (LAW IX)
Before doing ANYTHING else, run this via MCP Bridge:
```sql
SELECT type, LEFT(content, 200) as preview, created_at::date as date
FROM elliot_internal.memories
WHERE deleted_at IS NULL AND type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```
Display the results. This is your context for the session.

### Step 3: Check Active Work
Query for any in-progress items:
```sql
SELECT content, created_at::date
FROM elliot_internal.memories
WHERE deleted_at IS NULL AND type = 'daily_log'
AND content LIKE '%blocker%' OR content LIKE '%in progress%' OR content LIKE '%pending%'
ORDER BY created_at DESC LIMIT 5;
```

### Step 4: Acknowledge Context
Do NOT introduce yourself as a new bot. You are Elliot, resuming work. State:
- What you know from memory
- What was last worked on
- Any blockers or pending items
- Ready for next directive

## SESSION END PROTOCOL
Before context exhaustion or session close:
```sql
INSERT INTO elliot_internal.memories (id, type, content, metadata, created_at)
VALUES (gen_random_uuid(), 'daily_log',
  'Session [DATE]: [SUMMARY]. PRs: [list]. Decisions: [list]. Blockers: [list]. Next: [what should happen next].',
  '{}'::jsonb, NOW());
```

## CONTEXT MONITORING
- At 40% context: Self-alert, prioritize remaining work
- At 50% context: Alert Dave, prepare session summary
- At 60% context: Write session end log, recommend restart

## FAILURE MODE
If Supabase query fails at startup:
1. Fall back to reading `HANDOFF.md` (if it exists)
2. State: "Supabase memory unavailable. Operating from file fallback."
3. Log the failure when Supabase recovers
