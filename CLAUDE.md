# CLAUDE.md — Agency OS Project Config

@IDENTITY.md

@.claude/modules/_project_overview.md

@.claude/modules/_law_step0.md

@.claude/modules/_session_start.md

@.claude/modules/_law_clean_tree.md

@.claude/modules/_law_architecture_first.md

@.claude/modules/_hierarchy.md

@.claude/modules/_completion_discipline.md

@.claude/modules/_mcp_bridge.md

## Supabase — Primary Memory Store (LAW IX)

**Project ID:** jatzvazlbusedwsnqxzr

Session START query:
```sql
SELECT source_type AS type, LEFT(content, 200) AS preview, created_at::date AS date
FROM public.agent_memories
WHERE callsign = '<your_callsign>' AND state != 'archived'
  AND source_type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```

Session END — write daily_log before closing:
```sql
INSERT INTO public.agent_memories (id, callsign, source_type, content, typed_metadata, created_at, valid_from, state)
VALUES (gen_random_uuid(), '<your_callsign>', 'daily_log', '<summary: what was done, PRs, decisions, blockers>', '{}'::jsonb, NOW(), NOW(), 'confirmed');
```

@.claude/modules/_governance_rules.md

@.claude/modules/_dead_references.md

@.claude/modules/_enrichment_path.md

@.claude/modules/_directive_format.md

@.claude/modules/_session_end.md


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
