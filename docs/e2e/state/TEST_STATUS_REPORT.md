# E2E Test Status Report

**Generated:** 2026-02-07 (UTC)
**Framework:** pytest 9.0.2 + pytest-asyncio 1.3.0
**Python:** 3.12.3

---

## Executive Summary

| Category | Collected | Passed | Failed | Errors | Notes |
|----------|-----------|--------|--------|--------|-------|
| test_services | 108 | 78 | 30 | 0 | Mock-based unit tests |
| test_skills | 14 | 6 | 8 | 0 | ICP skills failing |
| test_e2e | 50 | 44 | 6 | 0 | Core E2E tests |
| test_api | 22 | 0 | 0 | 22 | Missing `async_client` fixture |
| test_engines | ~50 | - | - | ALL | Missing `apify_client` dependency |
| test_flows | ~30 | - | - | ALL | Missing dependencies |
| live/ | 27 | - | - | - | Require running services |
| integration/ | ~10 | - | - | ALL | Missing `playwright` dependency |
| **TOTAL** | ~311+ | 128 | 44 | ~84 | **41% pass rate (runnable tests)** |

---

## Test Categories

### ✅ Passing (168 tests)

**test_services/** - 78/108 passing
- CRM Push Service: 19/19 ✅
- Deal Service: 15/15 ✅  
- Meeting Service: 24/24 ✅
- Lead Allocator: 10/12 (2 failing)
- Lead Pool: 7/11 (4 failing)
- JIT Validator: 9/15 (6 failing)
- Customer Import: 1/19 (18 failing)

**test_e2e/** - 44/50 passing
- Billing tests: 22/22 ✅
- Rate Limits: 16/18 (2 failing)
- Full Flow: 5/10 (5 failing)

**test_skills/** - 6/14 passing
- Base Skill: 6/6 ✅
- ICP Skills: 0/8 (all failing)

---

### ❌ Failing Tests (38 total)

#### Customer Import Service (18 failures)
**Root Cause:** Tests use wrong mock method names
- `test_process_customer_creates_entry`
- `test_import_from_csv_*` (4 tests)
- `test_is_suppressed_*` (6 tests)
- `test_add_suppression_*` (2 tests)
- `test_get_buyer_signal_*` (5 tests)

#### JIT Validator (6 failures)
**Root Cause:** Tests expect assignment validation that was refactored
- `test_validate_not_assigned`
- `test_validate_max_touches_reached`
- `test_validate_negative_reply`
- `test_validate_in_cooling_period`
- `test_validate_too_recent`
- `test_validate_success`

#### E2E Full Flow (4 failures)
**Root Cause:** Import path `src.engines.scout` doesn't resolve
```
AttributeError: module 'src.engines' has no attribute 'scout'
```
- `test_full_flow_single_lead`
- `test_full_flow_batch_leads`
- `test_flow_with_jit_validation_failure`
- `test_flow_with_inactive_campaign`

#### Lead Pool Service (4 failures)
- `test_create_or_update_existing`
- `test_create_validates_email`
- `test_search_available`
- `test_bulk_create`

#### ICP Skills (2 failures)
- `test_execute_success` - Parser skill not working
- `test_all_skills_registered` - Skill registration issue

---

### 🚫 Collection Errors (12 test files)

These tests cannot be collected due to missing dependencies:

| Test File | Missing Dependency | Install Command |
|-----------|-------------------|-----------------|
| test_api/test_health.py | sentry_sdk | `pip install sentry-sdk` ✅ |
| test_api/test_campaigns.py | sentry_sdk | (same) |
| test_api/test_reports.py | sentry_sdk | (same) |
| test_engines/test_scout.py | apify_client | `pip install apify-client` |
| test_engines/test_scraper_waterfall.py | apify_client | (same) |
| test_engines/test_deep_research.py | apify_client | (same) |
| test_detectors/test_detectors.py | numpy | `pip install numpy` ✅ |
| test_detectors/test_weight_optimizer.py | numpy | (same) |
| test_flows/test_*.py | prefect + supabase | `pip install prefect supabase` |
| integration/test_who_integration.py | playwright | `pip install playwright` |

**Note:** Some dependencies were installed during testing (marked ✅)

---

### ⚠️ Fixture Issues

**test_api/test_leads.py (22 tests)**
- Tests use `async_client` fixture but conftest.py defines `api_client`
- **Fix:** Rename fixture in tests or conftest.py

---

## How to Run Tests

### Full Test Suite (with available dependencies)
```bash
cd /home/elliotbot/clawd/Agency_OS
source .venv/bin/activate
python -m pytest tests/test_services tests/test_skills tests/test_e2e -v
```

### Individual Test Categories
```bash
# Services (unit tests)
pytest tests/test_services/ -v

# E2E (integration tests)
pytest tests/test_e2e/ -v

# Specific test file
pytest tests/test_e2e/test_billing.py -v
```

### Live Tests (require running services)
```bash
# Requires: Backend API, Supabase, Redis
pytest tests/live/ -v
```

---

## Missing Dependencies Summary

To run ALL tests, install:

```bash
pip install \
  apify-client \
  playwright \
  pytest-playwright \
  supabase \
  twilio \
  asyncpg \
  xmltodict
```

After playwright install:
```bash
playwright install chromium
```

---

## Recommended Fixes (Priority Order)

### P0 - Quick Wins
1. **Fix `async_client` → `api_client` fixture mismatch** (22 tests)
   - File: `tests/test_api/test_leads.py`
   - Change: `async_client` → `api_client`

2. **Install missing dependencies** (84+ tests)
   - apify_client, playwright, etc.

### P1 - Test Refactoring
3. **Fix Customer Import Service tests** (18 tests)
   - Tests using wrong mock method signatures

4. **Fix JIT Validator tests** (6 tests)
   - Tests not aligned with current service implementation

### P2 - Module Import Fixes
5. **Fix E2E Full Flow test imports** (4 tests)
   - `src.engines.scout` path not resolving in tests

---

## Environment Requirements

| Service | Required For | Status |
|---------|--------------|--------|
| PostgreSQL | test_flows, integration | Not running |
| Redis | live tests | Not running |
| Backend API | live tests | External (Railway) |
| Supabase | live tests | External (Cloud) |

---

## Comparison to MASTER_EXECUTION_PLAN.md

| Metric | Plan | Actual |
|--------|------|--------|
| Tests passing | 7/47 (15%) | 128/168 runnable (76%) |
| Tests total | 47 | 311+ |
| Status | "40 tests remaining" | 44 failing, 84 erroring |

**Note:** The 7/47 figure from MASTER_EXECUTION_PLAN.md refers to E2E journey tests, not pytest unit tests.

---

*Report generated by E2E test runner subagent*
