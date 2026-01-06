# Agency OS Development Handoff

## Team Structure

| Role | Entity | Responsibilities |
|------|--------|------------------|
| **CEO** | Dave | Decision maker, runs tests, provides screenshots, approves direction |
| **CTO / Prompt Engineer** | Claude Desktop | Diagnoses issues, writes CC prompts, reads files via MCP (read-only), coordinates workflow |
| **DevOps / Developer** | Claude Code (CC) | Executes all file changes, runs commands, applies migrations, deploys |

## Workflow Rules

1. **Claude Desktop NEVER modifies files directly** — only writes prompts for CC
2. **CC handles ALL execution** — file edits, migrations, deployments, investigations
3. **Dave handles ALL manual testing** — browser tests, screenshots, confirmations
4. **Claude Desktop has MCP read-only access** — can read files to inform prompts but cannot write

## Communication Flow
```
Dave (reports issue/screenshot)
    ↓
Claude Desktop (diagnoses, writes CC prompt)
    ↓
Dave (pastes prompt into CC)
    ↓
CC (executes, reports results)
    ↓
Dave (pastes CC output back)
    ↓
Claude Desktop (interprets, next steps)
```

## Before Starting Work

### Required Reading

- `CLAUDE.md` — Development rules, architecture, coding standards
- `PROJECT_BLUEPRINT.md` — System architecture, component relationships
- `PROGRESS.md` — Current status, completed tasks, blockers

### Key Directories

- `docs/phases/` — Phase specifications
- `docs/specs/engines/` — Engine documentation
- `docs/specs/integrations/` — Integration specs
- `supabase/migrations/` — Database migrations
- `config/` — Environment configuration

## CC Prompt Structure

Every prompt to Claude Code should follow this format:

```markdown
## Task
[One sentence: what needs to be done]

## Context
[Why this is needed, what triggered it]

## Pre-Read (if needed)
[Files CC should read before making changes]

## Investigation Steps (for debugging)
[Numbered steps to diagnose]

## Fix Required (for changes)
[Specific changes needed]

## Commands to Run (if applicable)
[Exact commands]

## Constraints
- [What NOT to do]
- [Boundaries and limitations]

## Deliverable
1. [What CC should report back]
2. [Expected outputs]
```

## Current Session Context

### What's Working

- ✅ Signup flow (with trigger fix)
- ✅ Auto-provisioning (user → client → membership)
- ✅ Login redirects to onboarding
- ✅ Vercel deployment with correct env vars
- ✅ Railway backend healthy

### Current Blocker

- ❌ ICP Discovery returning 404 — under investigation

### Recent Fixes Applied

- Migration 017: Fixed handle_new_user() trigger with public. schema qualification
- Vercel env vars: NEXT_PUBLIC_API_URL, Supabase URL/key configured
- Frontend reports.ts: Fixed API endpoint URLs and response transformations

## Test Accounts

| Email | Password | Status |
|-------|----------|--------|
| dvidstephens@gmail.com | [user's password] | Active, needs ICP onboarding |
| david.stephens@keiracom.com | N/A (Google OAuth) | Existing account |

## Key URLs

| Environment | URL |
|-------------|-----|
| Frontend (Prod) | https://agency-os-liart.vercel.app |
| Backend (Prod) | https://agency-os-production.up.railway.app |
| Health Check | https://agency-os-production.up.railway.app/api/v1/health |
| Supabase | https://jatzvazlbusedwsnqxzr.supabase.co |

## Quick Reference: Common Issues

| Symptom | Likely Cause | First Check |
|---------|--------------|-------------|
| "Failed to fetch" | Wrong API URL or CORS | Vercel env vars, browser console |
| "Not Found" (404) | Route mismatch FE↔BE | Compare frontend API call vs backend route |
| "Database error" | Migration not applied or trigger failure | Supabase logs, migration status |
| Auth errors | Token/session issues | Supabase Auth logs |
