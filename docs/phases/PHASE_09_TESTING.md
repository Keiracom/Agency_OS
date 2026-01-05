# Phase 9: Integration Testing

**Status:** ✅ Complete  
**Tasks:** 5  
**Dependencies:** Phase 8 complete

---

## Overview

End-to-end testing of the complete platform.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| TST-001 | Test config | Pytest fixtures | `tests/conftest.py` | M |
| TST-002 | Mock fixtures | API response mocks | `tests/fixtures/*` | M |
| TST-003 | E2E flow test | Full enrichment → outreach | `tests/test_e2e/test_full_flow.py` | L |
| TST-004 | Billing integration test | Subscription checks | `tests/test_e2e/test_billing.py` | M |
| TST-005 | Rate limit test | Resource-level limits | `tests/test_e2e/test_rate_limits.py` | M |

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── fixtures/
│   ├── apollo_responses.json
│   ├── resend_responses.json
│   └── ...
├── test_engines/
│   ├── test_scout.py
│   ├── test_scorer.py
│   └── ...
├── test_api/
│   ├── test_health.py
│   ├── test_campaigns.py
│   └── ...
├── test_flows/
│   ├── test_campaign_flow.py
│   └── ...
└── test_e2e/
    ├── test_full_flow.py
    ├── test_billing.py
    └── test_rate_limits.py
```

---

## Key Test Scenarios

### Full Flow Test
1. Create client + campaign
2. Upload leads
3. Run enrichment flow
4. Run scoring
5. Run outreach flow
6. Verify activities created

### Billing Test
1. Create client with `subscription_status = 'past_due'`
2. Attempt enrichment
3. Verify billing check blocks enrichment

### Rate Limit Test
1. Send 50 emails from same domain
2. Attempt 51st email
3. Verify rate limit blocks send

---

## Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/test_engines/
pytest tests/test_e2e/

# With coverage
pytest --cov=src --cov-report=html
```
