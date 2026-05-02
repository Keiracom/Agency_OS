# CLAUDE.md — Agency OS Project Config (Aiden worktree)

@.claude/modules/_project_overview.md

@.claude/modules/_law_step0.md

@.claude/modules/_session_start.md

@.claude/modules/_law_clean_tree.md

@.claude/modules/_law_architecture_first.md

@.claude/modules/_mcp_bridge.md

## Supabase — Primary Memory Store (LAW IX)

**Project ID:** jatzvazlbusedwsnqxzr

Session START query:
```sql
SELECT source_type AS type, LEFT(content, 200) AS preview, created_at::date AS date
FROM public.agent_memories
WHERE callsign = 'aiden' AND state != 'archived'
  AND source_type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```

Session END — write daily_log before closing:
```sql
INSERT INTO public.agent_memories (id, callsign, source_type, content, typed_metadata, created_at, valid_from, state)
VALUES (gen_random_uuid(), 'aiden', 'daily_log', '<summary: what was done, PRs, decisions, blockers>', '{}'::jsonb, NOW(), NOW(), 'confirmed');
```

@.claude/modules/_governance_rules.md

@.claude/modules/_dead_references.md

@.claude/modules/_enrichment_path.md

@.claude/modules/_directive_format.md

@.claude/modules/_session_end.md
