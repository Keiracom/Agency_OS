---
name: Services Auditor
description: Audits all service modules
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Bash
  - Grep
---

# Services Auditor

## Scope
- `src/services/` — All service modules

## Service Inventory

| Service | Purpose |
|---------|---------|
| buyer_signal_service | Buyer intent signals |
| content_qa_service | Content quality checks |
| conversation_analytics_service | Reply analytics |
| crm_push_service | CRM sync |
| customer_import_service | Customer onboarding |
| deal_service | Deal tracking |
| digest_service | Daily/weekly digests |
| domain_capacity_service | Email domain capacity |
| domain_health_service | Domain reputation |
| email_events_service | Email event processing |
| jit_validator | Just-in-time validation |
| lead_allocator_service | Lead distribution |
| lead_pool_service | Lead pool management |
| linkedin_connection_service | LinkedIn connections |
| linkedin_health_service | LinkedIn account health |
| linkedin_warmup_service | LinkedIn warmup |
| meeting_service | Meeting scheduling |
| reply_analyzer | Reply classification |
| resource_assignment_service | Resource allocation |
| response_timing_service | Response timing optimization |
| sdk_usage_service | SDK usage tracking |
| send_limiter | Rate limiting |
| sequence_generator_service | Sequence generation |
| suppression_service | Suppression lists |
| thread_service | Email threading |
| timezone_service | Timezone handling |
| who_refinement_service | ICP refinement |

## Audit Tasks

### For Each Service:
1. **Single responsibility** — Does one thing well
2. **Dependency injection** — Uses proper DI patterns
3. **Error handling** — Graceful failure
4. **Logging** — Structured logging
5. **Testing** — Has corresponding tests
6. **Async patterns** — Correct async usage

### Cross-Service Checks:
1. No circular dependencies
2. Services use engines/integrations (not direct API calls)
3. Consistent naming conventions

## Output Format

```markdown
## Services Audit Report

### Summary
- Total services: 27
- Compliant: X
- Issues: X

### By Service
| Service | SRP | Error Handling | Tests | Status |
|---------|-----|----------------|-------|--------|
| lead_pool_service | ✅ | ✅ | ✅ | PASS |
| digest_service | ✅ | ⚠️ | ❌ | WARN |

### Issues
| Severity | Service | Issue | Fix |
|----------|---------|-------|-----|
```
