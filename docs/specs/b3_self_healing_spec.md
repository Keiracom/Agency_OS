# B3 Self-Healing + Enforcement Spec

**Wave:** 2
**Status:** Ratified
**Author:** Architect-0 (claude-opus-4-6) + Aiden peer review amendments
**Date:** 2026-04-21

---

## 1. Purpose

Define the self-healing architecture for Agency OS: how the system detects failures, classifies them, attempts autonomous remediation, escalates when autonomy limits are reached, and enforces governance rules across both code and conversation.

This spec is the SSOT for B4 build work.

---

## 2. Three-Tier Self-Healing Model

| Tier | Name | Actor | Scope | Human gate |
|------|------|-------|-------|------------|
| T1 | Autonomous | Agent (no human in loop) | Known-fix patterns, bounded file set | PR for human merge — NEVER auto-merge |
| T2 | CEO-Assisted | Elliot + Dave | Needs diagnosis, non-registry paths | Elliot proposes, Dave approves |
| T3 | Dave-Only | Dave | Credentials, spend, secrets, infra | Dave acts directly |

---

## 3. Detection: health_check_flow

- **Cadence:** 5-minute Prefect flow (`health_check_flow`)
- **Probes:** Railway service health, Prefect worker status, API key reachability, test suite pass rate, recent flow failure rate
- **Probe watchdog:** If no `health_checks` row written within 15 minutes → Telegram alert to Dave (chat_id 7267788033) and group (chat_id -1003926592540)
- **Output:** Writes a row to `public.health_checks` on every run (pass or fail)

### health_checks Table Schema

```sql
CREATE TABLE public.health_checks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_type     text NOT NULL,          -- 'railway_down', 'api_key_expired', 'flow_failure_rate', etc.
    tier            int NOT NULL,           -- 1, 2, or 3
    description     text NOT NULL,
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    resolved_at     timestamptz,
    fix_pr_url      text,
    escalated_at    timestamptz
);
```

---

## 4. Classification Decision Tree

```
Signal detected
    │
    ├─ Is signal_type in known-fix registry?
    │       ├─ YES → Is fix within T1 guards? ──── YES → T1 attempt
    │       │                                  └── NO  → T2 escalate
    │       └─ NO  → T2 escalate
    │
    ├─ Does fix require credentials / spend / secrets?
    │       └─ YES → T3 (Dave-only)
    │
    └─ Has same signal fired in past 24h without resolution?
            └─ YES → T2 or T3 (no retry spiral)
```

---

## 5. T1 Guards (Non-Negotiable)

T1 autonomous remediation is only permitted when ALL of the following are true:

1. **Known-pattern-registry match** — signal_type exists in registry with a mapped fix function
2. **Fix rate limit** — maximum 1 fix attempt per hour (rolling window)
3. **File limit** — maximum 3 files modified per fix attempt
4. **PR, never merge** — T1 opens a GitHub PR; a human must merge. Auto-merge is permanently forbidden.
5. **Protected file exclusion** — T1 cannot touch any of:
   - Database migrations (`migrations/`, `alembic/`)
   - Environment files (`.env`, `*.env.*`)
   - Secrets (any file in `secrets/`, `credentials/`)
   - `CLAUDE.md` (any instance)
   - `ARCHITECTURE.md`
   - Shared-file allowlist: `src/telegram_bot/memory_listener.py`, `src/telegram_bot/chat_bot.py`, `src/memory/store.py`, `src/telegram_bot/listener_discernment.py`
   - `skills/` directory

---

## 6. T1 → T2 Escalation Triggers

Any one of the following triggers immediate T2 escalation (no retry):

- T1 fix attempt failed once
- signal_type not in known-fix registry
- Fix would touch more than 3 files
- Same signal fired within last 24 hours without resolution (prevents retry spiral)

---

## 7. Known-Fix Registry

The registry seeds on **abstract failure classes**, not literal past bugs. This prevents the registry from becoming a brittle list of one-off patches.

### Seed classes (v1)

| signal_type | Abstract class | T1 fix action |
|-------------|---------------|---------------|
| `import_error` | Missing dependency | Add to `requirements.txt`, open PR |
| `syntax_error` | Python syntax fault | Apply autopep8/ruff fix, open PR |
| `env_var_missing_non_secret` | Missing non-secret env var with known default | Add default to config loader, open PR |
| `test_regression_single` | Single test newly failing, bounded to 1 file | Apply fix to that file, open PR |
| `worker_stale_restart` | Prefect worker not polled in >10min | Trigger Railway restart via API |
| `flow_failure_rate_spike` | Flow failure rate >50% for >15min | Alert T2, do not auto-fix (diagnosis needed) |

New classes added via PR only. Registry lives at `src/self_healing/known_fix_registry.py`.

---

## 8. Hybrid Enforcement Model

Two enforcement surfaces operate in parallel:

### 8.1 Infrastructure Enforcement (code + deploy)

- **CI (GitHub Actions):** lint, test, type-check gates block merge
- **Branch protection:** direct push to `main` blocked; PR + review required
- **Deployment gate:** Railway deploy only from passing CI build
- **Scope:** Catches code-level violations before they ship

### 8.2 Enforcer Bot (conversation + process)

A lightweight Python daemon — NOT a Claude Code clone — that reads the Telegram group via Bot API and checks governance compliance in conversation.

**Design constraints:**
- Model: `gpt-4o-mini` per check (not Claude — avoids circular dependency)
- Volume: ~50 checks/day
- Cost: ~$1.50/month AUD-equivalent
- Checks: Step 0 RESTATE presence, callsign discipline (LAW XVII), claim/release on shared files, directive acknowledgement
- On violation: posts governance alert to group, logs to `elliot_internal.governance_debt`
- Does NOT take autonomous action; it surfaces and logs

**What the enforcer bot does NOT do:**
- It does not execute code
- It does not merge PRs
- It does not modify files
- It is not a self-healing agent

---

## 9. Dead Code Management (R1-R7)

Seven governance rules for managing dead code discovered during audits or refactors.

| Rule | Name | Description |
|------|------|-------------|
| R1 | Tag before delete | Dead code must be tagged `# DEAD: <reason> <date>` before any delete PR |
| R2 | 7-day hold | Tagged dead code waits 7 calendar days before deletion (allows peer review) |
| R3 | Audit trail | Deletion PR must reference the audit or directive that identified the code as dead |
| R4 | No silent removal | Deleted code must appear in PR diff — no squash-hiding |
| R5 | Test coverage check | If dead code had tests, tests must be removed or repurposed in same PR |
| R6 | Registry deregister | If dead code had a known-fix registry entry, that entry must be removed in same PR |
| R7 | Salvage-before-delete | Before deleting, evaluate whether the logic is reusable in a different context. If yes, extract to a utility module first. Delete only the original dead location. |

---

## 10. Surfacing Mechanisms

How self-healing signals and governance state surface to humans:

### 10.1 Problem-Domain Tags

Every health_check signal carries a `problem_domain` field:
- `infra` — Railway, Prefect, Redis
- `pipeline` — Stage-level failures
- `enrichment` — API key, quota, rate limit
- `governance` — Process violations (enforcer bot)
- `test` — Test regression

### 10.2 triggers_on Field

Every known-fix registry entry carries a `triggers_on` list: the exact `signal_type` values that activate the fix. This makes the registry queryable.

### 10.3 Inline Pointer Comments

In any file that interacts with self-healing (health_check_flow, known_fix_registry, enforcer bot), include a comment at the top:

```python
# Self-healing: see docs/specs/b3_self_healing_spec.md
```

### 10.4 Phase-Boundary Check

At every pipeline stage boundary (stage N → stage N+1), the orchestrator emits a `phase_boundary` health_check row. This gives the watchdog continuous signal even during long-running flows.

---

## 11. Example Scenarios (from 2026-04-21 session)

**Scenario A — Import error in stage script**
- Stage 5 fails with `ModuleNotFoundError: dateparser`
- health_check_flow detects `flow_failure_rate` spike → writes `import_error` signal
- Registry match: `import_error` → add to requirements.txt
- T1 guard check: 1 file, rate limit clear, not protected → T1 opens PR
- Elliot reviews PR → merges → Railway redeploys → signal resolves

**Scenario B — ISO string passed to asyncpg datetime column**
- Stage 6 crashes: `asyncpg.exceptions.DataError: invalid input for query argument $3: '2026-04-21T...'`
- health_check_flow: `syntax_error` class? No. `test_regression_single`? No. Not in registry.
- Escalates to T2 immediately
- Elliot diagnoses, writes fix, opens PR, Dave merges

**Scenario C — Paused deployment (scout chain)**
- 4 Prefect deployments paused (intelligence-flow et al.) — wired to dead scout.py
- health_check_flow: detects paused deployments, emits `flow_failure_rate` (not a T1 class)
- Surfaces to T2: Elliot reviews, confirms intentional (Dave ratified 2026-04-21), documents in audit

---

## 12. Dependencies for B4 Build

B4 must implement:

1. `public.health_checks` table (migration)
2. `health_check_flow` Prefect deployment (5-min cadence)
3. `src/self_healing/known_fix_registry.py` with v1 seed classes
4. `src/self_healing/t1_handler.py` — guard enforcement + PR opening via GitHub API
5. `src/self_healing/escalation.py` — T2/T3 Telegram alert formatting
6. Enforcer bot daemon (`src/enforcer_bot/main.py`) — Telegram reader + gpt-4o-mini checks
7. Probe watchdog: cron or Railway scheduled job checking health_checks recency
8. CI gate: health_check_flow must pass in staging before any production deploy

---

## 13. Aiden Peer Review Amendments (incorporated)

The following 5 amendments from Aiden's peer review are incorporated into this spec:

**Amendment 1 — Probe watchdog recency check**
Added to §3: if no health_checks row within 15 minutes, Telegram alert fires. Prevents silent watchdog death.

**Amendment 2 — Registry seeds on abstract classes, not literal bugs**
Clarified in §7: the registry is a taxonomy of failure classes. Literal past bugs are not registered; their abstract class is. This prevents registry bloat and brittleness.

**Amendment 3 — Enforcer bot uses gpt-4o-mini, not Claude**
Clarified in §8.2: enforcer bot must not use Claude Code SDK (circular dependency risk). gpt-4o-mini at ~50 checks/day costs ~$1.50/mo AUD.

**Amendment 4 — R7 salvage-before-delete**
Added R7 to §9: before deleting dead code, evaluate reuse. Extract to utility if reusable. Delete original only.

**Amendment 5 — Phase-boundary health_check rows**
Added to §10.4: orchestrator emits a `phase_boundary` health_check at every stage boundary, giving the watchdog continuous signal during long flows, not just at failure.
