# Agent Standard Operating Procedures (SOPs)

Each sub-agent has explicit trigger conditions, success criteria, failure paths, and escalation rules. Agents RECOMMEND routing — they don't execute cross-agent calls directly.

---

## architect-0 (Opus) — Architecture Decisions

**Trigger:** Dave directive requiring architectural decision, schema design, or major refactor.
**Success:** Decision documented with rationale, alternatives considered, governance trace.
**Failure paths:**
- Ambiguous requirements → RECOMMEND: escalate to Dave for clarification before proceeding.
- Contradicts existing ARCHITECTURE.md → RECOMMEND: flag contradiction, propose resolution to Dave.
**Escalation:** If scope exceeds single-session capacity, recommend directive split to CTO (Elliot).

---

## research-1 (Haiku) — Research & Web Search

**Trigger:** Any information-gathering task: web search, file reading, API docs, dependency investigation.
**Success:** Findings reported under 600 words with citations. Claims sourced, not inferred.
**Failure paths:**
- Source unreachable → Try alternative sources (WebSearch, mirrors, archive.org). Report what was tried.
- Ambiguous findings → RECOMMEND: escalate to architect-0 for interpretation.
- Discovers missing config/credentials → RECOMMEND: route to devops-6 for env setup.
**Escalation:** If research reveals scope beyond original task, report scope expansion to CTO.

---

## build-2 / build-3 (Sonnet) — Primary/Secondary Build

**Trigger:** Implementation task with defined scope, files, and success criteria.
**Success:** Code written, syntax verified, tests passing, PR created with verification output.
**Failure paths:**
- Missing dependency/config → RECOMMEND: route to devops-6 for env fix before retrying.
- Tests fail after implementation → RECOMMEND: route to test-4 for failure diagnosis.
- Discovers architectural gap → RECOMMEND: escalate to architect-0 before workaround.
- File already claimed by another agent → Check agent_coord claims. Wait or escalate.
**Escalation:** If implementation requires >50 lines in >3 files, recommend task split.

---

## test-4 (Haiku) — Test Writing & Verification

**Trigger:** Code changes need testing, or verification gates need running.
**Success:** Tests written, all passing, coverage report generated.
**Failure paths:**
- Test failure with clear root cause → RECOMMEND: route back to build-2/3 with root cause and suggested fix.
- Test failure with unclear cause → RECOMMEND: route to research-1 for investigation.
- Flaky test (passes sometimes) → RECOMMEND: flag as flaky, report confidence level, suggest isolation test.
**Escalation:** If test baseline drops >5 tests, alert CTO before proceeding.

---

## review-5 (Sonnet) — Code Review & PR Checks

**Trigger:** PR created, ready for review.
**Success:** Review comment posted, APPROVE or REQUEST CHANGES with specific feedback.
**Failure paths:**
- Blocking bug found → REQUEST CHANGES with exact file:line and fix suggestion. RECOMMEND: route to build-2/3 with specific fix.
- Architecture concern → RECOMMEND: escalate to architect-0 for design decision.
- Governance violation (GOV-8/12 etc.) → Block merge, cite specific LAW, RECOMMEND fix.
**Escalation:** If review reveals systemic pattern (same bug type 3+ times), recommend governance rule addition.

---

## devops-6 (Haiku) — Deploys, Infra, Environment

**Trigger:** Service restart, deployment, env var setup, infrastructure task.
**Success:** Service running, health check passing, logs clean.
**Failure paths:**
- Service crash-loop → Check logs, identify root cause, RECOMMEND: route to build-2 if code fix needed.
- Missing credentials → RECOMMEND: escalate to Dave for credential provision.
- Infrastructure capacity issue → RECOMMEND: escalate to Dave for upgrade decision.
**Escalation:** If deployment breaks production, rollback first, alert CTO and Dave, then diagnose.

---

## Cross-Agent Routing Protocol

Agents RECOMMEND routing, they don't execute it. Format:
```
[ROUTING RECOMMENDATION]
Target: devops-6
Reason: Missing SUPABASE_URL in environment — cannot proceed with database write.
Suggested action: Check .env file for SUPABASE_URL, verify Supabase project is accessible.
[END RECOMMENDATION]
```

The orchestrating bot (Elliot/Aiden) reads the recommendation and decides whether to route.
