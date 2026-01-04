# FULL CODEBASE QA AUDIT — Agency OS v3.0

> **Paste this entire prompt into Claude Code for a complete codebase scan.**

---

## MISSION

Perform a **comprehensive audit of the ENTIRE Agency OS codebase**. Do NOT rely on PROGRESS.md or assume anything is complete. Scan every file independently and generate a full QA report.

---

## WORKING DIRECTORY

```
cd C:\AI\Agency_OS
```

---

## SCAN SCOPE

Audit ALL files in these directories:

```
src/                    # All Python backend code
frontend/app/           # All Next.js pages
frontend/components/    # All React components
frontend/lib/           # All utility libraries
tests/                  # All test files
supabase/migrations/    # All SQL migrations
```

---

## CRITICAL CHECKS (Must Fix)

### 1. Import Hierarchy Violations

The import hierarchy is: `models → integrations → engines → orchestration`

```bash
# Models should NEVER import from engines or orchestration
grep -rn "from src.engines" src/models/
grep -rn "from src.orchestration" src/models/

# Integrations should NEVER import from engines or orchestration
grep -rn "from src.engines" src/integrations/
grep -rn "from src.orchestration" src/integrations/

# Engines should NEVER import from other engines or orchestration
grep -rn "from src.engines\." src/engines/
grep -rn "from src.orchestration" src/engines/
```

### 2. Hardcoded Secrets

```bash
grep -rn "api_key\s*=\s*['\"][^'\"]*['\"]" src/
grep -rn "password\s*=\s*['\"][^'\"]*['\"]" src/
grep -rn "sk-" src/
grep -rn "sk_live" src/
grep -rn "sk_test" src/
```

### 3. Wrong Database Port (Should be 6543, not 5432 for app code)

```bash
grep -rn "port.*5432" src/
grep -rn ":5432" src/
```

### 4. Session Instantiation in Engines (Engines should receive db as argument)

```bash
grep -rn "AsyncSessionLocal()" src/engines/
grep -rn "get_db_session()" src/engines/
grep -rn "async with.*Session" src/engines/
```

### 5. Hard Deletes (Should use soft delete with deleted_at)

```bash
grep -rn "\.delete(" src/api/
grep -rn "\.delete(" src/engines/
grep -rn "DELETE FROM" src/
```

### 6. Wrong Pool Settings (Should be pool_size=5, max_overflow=10)

```bash
grep -rn "pool_size" src/
# Verify values are correct
```

---

## HIGH PRIORITY CHECKS

### 7. Missing Contract Comments

Every Python file in `src/` should start with a docstring containing:
- FILE:
- PURPOSE:
- PHASE:
- TASK:
- DEPENDENCIES:
- RULES APPLIED:

Check the first 20 lines of each .py file for this pattern.

### 8. TypeScript Any Types

```bash
grep -rn ": any" frontend/app/
grep -rn ": any" frontend/components/
grep -rn ": any" frontend/lib/
grep -rn "<any>" frontend/
```

### 9. Console.log in Production Code

```bash
grep -rn "console.log" frontend/app/
grep -rn "console.log" frontend/components/
```

### 10. Missing Error Handling in Frontend

Check for fetch calls without try/catch or .catch()

---

## MEDIUM PRIORITY CHECKS

### 11. TODO/FIXME Comments

```bash
grep -rn "TODO" src/
grep -rn "FIXME" src/
grep -rn "XXX" src/
grep -rn "HACK" src/
```

### 12. Incomplete Implementations

```bash
grep -rn "pass$" src/
grep -rn "\.\.\.," src/
grep -rn "NotImplementedError" src/
grep -rn "raise NotImplementedError" src/
```

### 13. Print Statements (Should use logging)

```bash
grep -rn "^[[:space:]]*print(" src/
```

---

## STRUCTURAL CHECKS

### 14. Required Files Exist

Verify these files exist and are not empty:

**Backend Core:**
- [ ] src/config/settings.py
- [ ] src/exceptions.py
- [ ] src/integrations/supabase.py
- [ ] src/integrations/redis.py
- [ ] src/api/main.py
- [ ] src/api/dependencies.py

**Models (all 8):**
- [ ] src/models/base.py
- [ ] src/models/client.py
- [ ] src/models/user.py
- [ ] src/models/membership.py
- [ ] src/models/campaign.py
- [ ] src/models/lead.py
- [ ] src/models/activity.py
- [ ] src/models/conversion_patterns.py

**Engines (all 12):**
- [ ] src/engines/base.py
- [ ] src/engines/scout.py
- [ ] src/engines/scorer.py
- [ ] src/engines/allocator.py
- [ ] src/engines/email.py
- [ ] src/engines/sms.py
- [ ] src/engines/linkedin.py
- [ ] src/engines/voice.py
- [ ] src/engines/mail.py
- [ ] src/engines/closer.py
- [ ] src/engines/content.py
- [ ] src/engines/reporter.py
- [ ] src/engines/icp_scraper.py
- [ ] src/engines/content_utils.py

**Detectors (Phase 16):**
- [ ] src/detectors/base.py
- [ ] src/detectors/who_detector.py
- [ ] src/detectors/what_detector.py
- [ ] src/detectors/when_detector.py
- [ ] src/detectors/how_detector.py
- [ ] src/detectors/weight_optimizer.py

**Integrations (all 13):**
- [ ] src/integrations/anthropic.py
- [ ] src/integrations/apollo.py
- [ ] src/integrations/apify.py
- [ ] src/integrations/clay.py
- [ ] src/integrations/resend.py
- [ ] src/integrations/postmark.py
- [ ] src/integrations/twilio.py
- [ ] src/integrations/heyreach.py
- [ ] src/integrations/synthflow.py
- [ ] src/integrations/lob.py
- [ ] src/integrations/redis.py
- [ ] src/integrations/supabase.py
- [ ] src/integrations/serper.py

**API Routes:**
- [ ] src/api/routes/health.py
- [ ] src/api/routes/campaigns.py
- [ ] src/api/routes/leads.py
- [ ] src/api/routes/webhooks.py
- [ ] src/api/routes/webhooks_outbound.py
- [ ] src/api/routes/reports.py
- [ ] src/api/routes/admin.py
- [ ] src/api/routes/onboarding.py
- [ ] src/api/routes/campaign_generation.py
- [ ] src/api/routes/patterns.py
- [ ] src/api/routes/meetings.py
- [ ] src/api/routes/replies.py

**Orchestration:**
- [ ] src/orchestration/worker.py
- [ ] src/orchestration/flows/campaign_flow.py
- [ ] src/orchestration/flows/enrichment_flow.py
- [ ] src/orchestration/flows/outreach_flow.py
- [ ] src/orchestration/flows/reply_recovery_flow.py
- [ ] src/orchestration/flows/onboarding_flow.py
- [ ] src/orchestration/flows/pattern_learning_flow.py
- [ ] src/orchestration/flows/pattern_backfill_flow.py
- [ ] src/orchestration/tasks/enrichment_tasks.py
- [ ] src/orchestration/tasks/scoring_tasks.py
- [ ] src/orchestration/tasks/outreach_tasks.py
- [ ] src/orchestration/tasks/reply_tasks.py
- [ ] src/orchestration/schedules/scheduled_jobs.py

**Agents & Skills:**
- [ ] src/agents/base_agent.py
- [ ] src/agents/cmo_agent.py
- [ ] src/agents/content_agent.py
- [ ] src/agents/reply_agent.py
- [ ] src/agents/icp_discovery_agent.py
- [ ] src/agents/campaign_generation_agent.py
- [ ] src/agents/skills/base_skill.py
- [ ] src/agents/skills/website_parser.py
- [ ] src/agents/skills/service_extractor.py
- [ ] src/agents/skills/value_prop_extractor.py
- [ ] src/agents/skills/portfolio_extractor.py
- [ ] src/agents/skills/industry_classifier.py
- [ ] src/agents/skills/company_size_estimator.py
- [ ] src/agents/skills/icp_deriver.py
- [ ] src/agents/skills/als_weight_suggester.py
- [ ] src/agents/skills/messaging_generator.py
- [ ] src/agents/skills/sequence_builder.py
- [ ] src/agents/skills/campaign_splitter.py
- [ ] src/agents/skills/industry_researcher.py

---

## REPORT FORMAT

Generate a report at: `Agents/QA Agent/qa_reports/FULL_AUDIT_REPORT.md`

```markdown
# FULL CODEBASE QA AUDIT REPORT

**Generated:** [timestamp]
**Auditor:** Claude Code QA Agent
**Scope:** Complete codebase scan

---

## EXECUTIVE SUMMARY

| Category | Count | Severity |
|----------|-------|----------|
| Import Hierarchy Violations | X | CRITICAL |
| Hardcoded Secrets | X | CRITICAL |
| Wrong Database Port | X | CRITICAL |
| Session Instantiation in Engines | X | CRITICAL |
| Hard Deletes | X | CRITICAL |
| Wrong Pool Settings | X | CRITICAL |
| Missing Contract Comments | X | HIGH |
| TypeScript Any Types | X | HIGH |
| Console.log Statements | X | HIGH |
| TODO/FIXME Comments | X | MEDIUM |
| Incomplete Implementations | X | MEDIUM |
| Print Statements | X | MEDIUM |
| Missing Files | X | CRITICAL |

**Overall Status:** [PASS/FAIL]

---

## CRITICAL ISSUES

### Issue 1: [Title]
- **File:** [path]
- **Line:** [number]
- **Evidence:** [code snippet]
- **Fix Required:** [description]

[Repeat for each issue]

---

## HIGH PRIORITY ISSUES

[Same format]

---

## MEDIUM PRIORITY ISSUES

[Same format]

---

## FILE EXISTENCE CHECK

| File | Exists | Has Contract | Lines |
|------|--------|--------------|-------|
| src/engines/scout.py | ✅ | ✅ | 525 |
| ... | ... | ... | ... |

---

## RECOMMENDATIONS

1. [Recommendation 1]
2. [Recommendation 2]

---

## FOR FIXER AGENT

Issues requiring code changes (copy to Fixer Agent):

| ID | File | Line | Issue | Severity |
|----|------|------|-------|----------|
| CRIT-001 | ... | ... | ... | CRITICAL |

---

**END OF REPORT**
```

---

## EXECUTION INSTRUCTIONS

1. Run each grep command listed above
2. Check file existence for each required file
3. Read first 20 lines of each .py file to check for contract comments
4. Compile all findings into the report format
5. Save report to `Agents/QA Agent/qa_reports/FULL_AUDIT_REPORT.md`
6. Print summary to console

---

## START NOW

Begin the full codebase audit. Do not skip any checks. Report everything you find.
