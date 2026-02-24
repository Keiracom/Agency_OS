# BOOTSTRAP.md — Session Initialization Protocol
# Version: 2.0 | Updated: 2026-02-24 | CEO Directive #058
# Governance: LAW I-A Staleness Check enforced

---

## TRIGGER
Start of any new session, after `/reset`, or after context compaction.

## MANDATORY SEQUENCE (Do not skip steps)

### Step 1: Load Identity
Read these files (they define WHO you are):
- `ENFORCE.md` — Hard laws (already loaded by system)
- `SOUL.md` — Persona and values
- `AGENTS.md` — Operational behavior

### Step 2: Query CEO Memory (LAW I-A — HARD BLOCK)

**CRITICAL:** Before ANY action, query the CEO SSOT via MCP Bridge:

```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call supabase execute_sql \
  '{"project_id": "jatzvazlbusedwsnqxzr", "query": "SELECT key, updated_at FROM ceo_memory WHERE key LIKE '\''ceo:%'\'' ORDER BY updated_at DESC LIMIT 10;"}'
```

**Staleness Check (48hr threshold):**
- If ANY `ceo:` key has `updated_at` older than 48 hours, ALERT DAVE immediately:
  > "⚠️ CEO_MEMORY STALE: Last update was [X days ago]. Requesting permission to proceed with potentially outdated context."
- Do NOT proceed with build work until Dave acknowledges.

**Required Keys to Check:**
- `ceo:directives` — Last directive number and status
- `ceo:system_state_*` — Current state of all systems
- `ceo:blockers_*` — Active blockers

### Step 3: Query Operational Memory
For day-to-day context:
```sql
SELECT type, LEFT(content, 200) as preview, created_at::date as date
FROM elliot_internal.memories
WHERE deleted_at IS NULL AND type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```

### Step 4: Check Active Work
Query for any in-progress items:
```sql
SELECT content, created_at::date
FROM elliot_internal.memories
WHERE deleted_at IS NULL AND type = 'daily_log'
AND content LIKE '%blocker%' OR content LIKE '%in progress%' OR content LIKE '%pending%'
ORDER BY created_at DESC LIMIT 5;
```

### Step 5: Acknowledge Context
Do NOT introduce yourself as a new bot. You are Elliot, resuming work. State:
- Current directive number (from `ceo:directives.last_number`)
- What systems are active/blocked
- Any blockers requiring Dave
- Ready for next directive

---

## SESSION END PROTOCOL (NON-NEGOTIABLE)

Before context exhaustion, session close, or `/reset`:

### 1. Write CEO Memory Update
```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call supabase execute_sql \
  '{"project_id": "jatzvazlbusedwsnqxzr", "query": "INSERT INTO ceo_memory (key, value, updated_at) VALUES ('\''ceo:session_end_[DATE]'\'', '\''{ \"date\": \"[DATE]\", \"directives_issued\": [LIST], \"directives_completed\": [LIST], \"prs_merged\": [LIST], \"files_modified\": [LIST], \"blockers_surfaced\": [LIST], \"next_directive_number\": [N], \"context_at_close\": \"[%]\" }'\''::jsonb, NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();"}'
```

### 2. Update Directive Counter
If any directives were issued:
```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call supabase execute_sql \
  '{"project_id": "jatzvazlbusedwsnqxzr", "query": "UPDATE ceo_memory SET value = jsonb_set(value, '\''{last_number}'\'', '\''[N]'\''), updated_at = NOW() WHERE key = '\''ceo:directives'\'';"}'
```

### 3. Write Operational Memory
```sql
INSERT INTO elliot_internal.memories (id, type, content, metadata, created_at)
VALUES (gen_random_uuid(), 'daily_log',
  'Session [DATE]: [SUMMARY]. PRs: [list]. Decisions: [list]. Blockers: [list]. Next: [what should happen next].',
  '{}'::jsonb, NOW());
```

### 4. Update HANDOFF.md
Always update `/home/elliotbot/clawd/Agency_OS/HANDOFF.md` with session summary as file fallback.

---

## CONTEXT MONITORING
- At 40% context: Self-alert, prioritize remaining work
- At 50% context: Alert Dave, prepare session summary
- At 60% context: Execute SESSION END PROTOCOL, recommend restart

---

## FAILURE MODES

### If Supabase MCP fails at startup:
1. Try alternate path: `cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js servers`
2. If still failing, fall back to reading `HANDOFF.md`
3. State: "Supabase MCP unavailable. Operating from file fallback. Will sync to ceo_memory when restored."
4. Log the failure and attempt reconnection periodically

### If ceo_memory is stale (>48hr):
1. STOP and alert Dave before any build work
2. Run reconstruction from git history if Dave approves
3. Update ceo_memory before proceeding

---

## GOVERNANCE TRACE
- Version 1.0: 2026-02-12 (Original)
- Version 2.0: 2026-02-24 (CEO Directive #058 — Added LAW I-A staleness check, session-end ceo_memory update)
