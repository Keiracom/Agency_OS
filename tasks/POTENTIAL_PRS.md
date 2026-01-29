# Agency OS - Potential PRs (Quick Wins)

**Generated:** 2026-01-28
**Repository:** /home/elliotbot/clawd/Agency_OS
**Branch:** main

---

## 🚨 P0 - CRITICAL (CI Breaking)

### PR-001: Fix undefined constants in scorer.py

**Impact:** CI failing on every push  
**Effort:** 5 min  
**File:** `src/engines/scorer.py`

**Issue:** Three FUNNEL_* constants are used but never defined, causing ruff F821 errors:
- `FUNNEL_STRONG_WIN_RATE_BOOST` (line 902)
- `FUNNEL_GOOD_DEAL_RATE_BOOST` (line 892)
- `MAX_FUNNEL_BOOST` (line 909)

The comments at line 1904-1907 claim they're defined, but they're not in the constants section.

**Fix:**
```python
# Add after line ~105 (after TIER_COLD = 20):

# Funnel Boost (Phase 24E)
MAX_FUNNEL_BOOST = 12
FUNNEL_HIGH_SHOW_RATE_BOOST = 4
FUNNEL_GOOD_DEAL_RATE_BOOST = 4
FUNNEL_STRONG_WIN_RATE_BOOST = 4
```

---

### PR-002: Fix import sorting in vapi.py

**Impact:** CI lint failure  
**Effort:** 1 min (auto-fix available)  
**File:** `src/integrations/vapi.py`

**Issue:** Import block is unsorted (ruff I001)

**Fix:** `ruff check src/integrations/vapi.py --fix`

---

## 🔴 P1 - HIGH (Deployment Blocker)

### PR-003: Add import test to Dockerfile

**Impact:** Railway crashes silently on import errors  
**Effort:** 5 min  
**File:** `Dockerfile`

**Issue:** Per DEPLOYMENT_ISSUES.md, Railway builds succeed but app crashes silently before uvicorn starts. No Python traceback visible.

**Fix:** Add import test after `COPY src/` line:
```dockerfile
# Test imports at build time to catch errors
RUN python -c "from src.api.main import app; print('Import test passed')"
```

This surfaces Python import errors at build time instead of runtime.

---

## 🟡 P2 - MEDIUM (Code Quality)

### PR-004: Remove `|| true` suppressors from CI

**Impact:** Hides real failures in type-check, tests, and lint  
**Effort:** 30 min (needs verification first)  
**File:** `.github/workflows/ci.yml`

**Issue:** Multiple steps use `|| true` to suppress failures:
- Line 54: mypy (type check)
- Line 118: pytest
- Line 145: npm run lint
- Line 148: npm run type-check

**Risk:** Once removed, you'll see actual errors. May need additional fixes first.

**Suggested approach:**
1. Run each locally to see actual failures
2. Fix blocking issues
3. Remove `|| true` one at a time

---

### PR-005: Complete TODO items in API routes

**Impact:** Missing functionality marked TODO  
**Effort:** 1-4 hours each  
**Files:** Multiple in `src/api/routes/`

**Outstanding TODOs:**
| File | Line | TODO |
|------|------|------|
| `dependencies.py` | ~L20 | "Implement API-level rate limiting" |
| `leads.py` | ~2 places | "Integrate with Prefect enrichment flow" |
| `crm.py` | ~L1 | "Make frontend_url configurable" |
| `webhooks.py` | ~L2 | "Implement signature verification" |
| `webhooks.py` | ~L3 | "Log to Sentry in production" |
| `admin.py` | 3 places | "Implement ai_usage_logs table" |

---

### PR-006: Fix hardcoded URL in crm.py

**Impact:** Hardcoded production URL  
**Effort:** 10 min  
**File:** `src/api/routes/crm.py`

**Issue:**
```python
frontend_url = "https://agency-os-liart.vercel.app"  # TODO: Make configurable
```

**Fix:** Move to `settings.py`:
```python
# In settings.py
FRONTEND_URL: str = "https://agency-os-liart.vercel.app"

# In crm.py
frontend_url = settings.FRONTEND_URL
```

---

## 🟢 P3 - LOW (Nice to Have)

### PR-007: Clean up empty pass statements

**Impact:** Dead code / stubs  
**Effort:** 15 min  
**Files:** ~20 files with bare `pass` statements

Some are intentional (abstract methods), but worth reviewing:
- `src/engines/scout.py` (5 occurrences)
- `src/services/jit_validator.py` (2 occurrences)
- `src/engines/base.py` (3 occurrences)

---

### PR-008: Add mypy strict mode

**Impact:** Better type safety  
**Effort:** 2-4 hours (lots of type annotations needed)  
**File:** `.github/workflows/ci.yml`

Currently mypy runs with `|| true`. Could add proper configuration:
```yaml
# Add mypy.ini with gradual strictness
```

---

## 📊 CI Status Summary

| Job | Status | Issues |
|-----|--------|--------|
| Backend Lint (Ruff) | ❌ FAILING | 5 errors (PR-001, PR-002) |
| Backend Type Check (MyPy) | ⚠️ Suppressed | `|| true` |
| Backend Tests (Pytest) | ⚠️ Suppressed | `|| true` |
| Frontend Check | ⚠️ Partially suppressed | lint/type-check use `|| true` |
| Deploy to Railway | ❌ Blocked by lint | Only runs if lint passes |

**Current CI run:** All failing since lint fails first

---

## 📝 Test Coverage

Test files exist in:
- `tests/test_api/`
- `tests/test_detectors/`
- `tests/test_e2e/`
- `tests/test_engines/`
- `tests/test_flows/`
- `tests/test_services/`
- `tests/test_skills/`

Can't run locally (no pytest installed), but conftest.py looks properly configured.

---

## 🎯 Recommended Priority Order

1. **PR-001** - Fix undefined constants (5 min, unblocks CI)
2. **PR-002** - Fix import sorting (1 min, auto-fixable)
3. **PR-003** - Dockerfile import test (5 min, helps debugging)
4. **PR-006** - Fix hardcoded URL (10 min, config hygiene)
5. **PR-004** - Remove `|| true` (30 min, after PR-001/002)

Total time to fix CI: ~10 minutes (PR-001 + PR-002)

---

## Notes

- Last 5 CI runs: all failing (ruff lint)
- Codebase has 9 `# type: ignore` comments (reasonable)
- No obvious security issues found
- Dockerfile missing import test per DEPLOYMENT_ISSUES.md
- Railway deployment blocked by CI failures
