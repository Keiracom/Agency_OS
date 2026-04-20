# RE-AUDIT 4: NAMING — f3a/f3b Reference Classification
**Branch:** directive-d1-3-audit-fixes
**Date:** 2026-04-14
**Auditor:** review-5 (Sonnet 4.6)

---

## 1. f3a/f3b Reference Inventory & Classification

All matches from `grep -rn "f3a\|f3b\|F3a\|F3b" src/ --include="*.py" | grep -v __pycache__`:

### src/intelligence/verify_fills.py

| Line | Match | Classification |
|------|-------|----------------|
| 204 | `f3a_output: dict,` | (a) DEFERRED PARAM — NOTE present at line 211 |
| 210 | `f3a_output: Parsed Stage 3 IDENTIFY output dict.` | (a) DEFERRED PARAM docstring |
| 211 | `NOTE: param name retained for caller compatibility...` | NOTE present — COMPLIANT |
| 219–223 | `f3a_output.get(...)` × 3 | (a) DEFERRED PARAM usage — internal to compliant function |

### src/intelligence/gemini_client.py

| Line | Match | Classification |
|------|-------|----------------|
| 21 | `from src.intelligence.comprehend_schema_f3a import ...` | (b) LEGACY IMPORT — schema file still carries f3a name; acceptable pending file rename directive |
| 22 | `from src.intelligence.comprehend_schema_f3b import ...` | (b) LEGACY IMPORT — same |
| 61 | `async def call_f3a(` | (b) DEPRECATED method — `.. deprecated::` docstring present; compliant |
| 189 | `async def call_f3b(` | (b) DEPRECATED method — `.. deprecated::` docstring present; compliant |
| 191 | `f3a_output: dict,` | (a) DEFERRED PARAM with NOTE at line 199 — compliant |
| 198–199 | docstring + NOTE | NOTE present — COMPLIANT |
| 211 | `f3a_output` usage | internal to deprecated method — acceptable |
| 238 | `migrated to call_f3a / call_f3b (themselves legacy — see their deprecation notes)` | (d) LEGACY KEY WITH DEPRECATED NOTE in comment — compliant |

### src/intelligence/prospect_scorer.py

| Line | Match | Classification |
|------|-------|----------------|
| 58 | `f3a_output: dict,` | (a) DEFERRED PARAM — docstring at line 65 describes it correctly |
| 65 | `f3a_output: Stage 3 IDENTIFY output (business identity, DM, enterprise flag).` | Docstring describes semantic, not legacy name — **NO NOTE present** |
| 103–249 | `f3a_output.get(...)` × 10 | (a) DEFERRED PARAM usage — all internal to function |

**FINDING:** `prospect_scorer.py` line 58 is a deferred-param pattern (caller compat) but has NO explicit `NOTE: param name retained for caller compatibility` inline note. The docstring describes the data correctly but does not flag the name as legacy. This is a minor gap — lower severity than a real miss, but inconsistent with the pattern established in `verify_fills.py` and `gemini_client.py`.

### src/intelligence/contact_waterfall.py

| Line | Match | Classification |
|------|-------|----------------|
| 374 | `f3a_linkedin_url: str | None = None,` | (a) DEFERRED PARAM with NOTE at line 384 — COMPLIANT |
| 383–384 | docstring + NOTE | NOTE present — COMPLIANT |
| 395 | `f3a_linkedin_url` usage | internal — acceptable |

### src/orchestration/cohort_runner.py

| Line | Match | Classification |
|------|-------|----------------|
| 151 | `result = await gemini.call_f3a(` | (b) DEPRECATED method call — legitimate active caller cited in gemini_client deprecation doc |
| 208 | `f3a_output=stage3_with_abn,` | (a) DEFERRED PARAM — kwarg to `score_prospect`; no inline comment but param is documented in callee |
| 253 | `result = await gemini.call_f3b(f3a_output=identity, ...)` | (b) DEPRECATED method call — legitimate active caller |
| 272 | `fills = await run_verify_fills(dfs=dfs, f3a_output=identity)` | (a) DEFERRED PARAM kwarg — compliant |
| 288 | `f3a_linkedin_url=dm.get("linkedin_url"),` | (a) DEFERRED PARAM kwarg — compliant |

### src/config/stage_parallelism.py

| Line | Match | Classification |
|------|-------|----------------|
| 210 | `"notes": "... Receives F3a identity + DFS signal bundle..."` | (d) LEGACY KEY IN CONFIG NOTE — descriptive string; not a functional reference |
| 229–230 | `"stage_f3a_comprehend"` key + stage_name `[LEGACY: use stage_3_identify]` | (b) DEPRECATED — LEGACY tag present in value |
| 237–238 | `"stage_f3b_compile"` key + stage_name `[LEGACY: use stage_5_analyse]` | (b) DEPRECATED — LEGACY tag present in value |

---

## 2. CLAUDE.md Dead-Ref Table Verification

Command: `grep -A 2 "HunterIO\|Apify" CLAUDE.md`

```
| Apify (GMB scraping) | Bright Data GMB Web Scraper (gd_m8ebnr0q2qlklc02fz). EXCEPTION: Apify harvestapi/linkedin-profile-scraper active in Pipeline F v2.1 for L2 LinkedIn verification. Apify facebook-posts-scraper active for Stage 9 social. |
| HunterIO (email verify) | Leadmagic ($0.015/email). EXCEPTION: Hunter email-finder active in Pipeline F v2.1 as L2 email fallback (score >= 70). |
```

**STATUS: COMPLIANT WITH NOTED EXCEPTIONS**

Both dead references are present in the table. Both carry EXCEPTION clauses that ratify their continued use in Pipeline F v2.1. The exceptions are scoped (specific scrapers, specific stage conditions) rather than blanket reversals. This is acceptable — the dead-ref table is not a prohibition list but a replacement-first directive; EXCEPTION clauses satisfy governance if the rationale is scoped.

---

## 3. call_f3a / call_f3b Deprecation Verification

Command: `grep -B 1 -A 3 "deprecated" src/intelligence/gemini_client.py`

Both methods carry proper Sphinx-style deprecation docstrings:

```
.. deprecated::
    Method name retained for compatibility. Use call_stage3_identify() when available
    (Directive C filename rename). Active callers: cohort_runner.py:151.
```

```
.. deprecated::
    Method name retained for compatibility. Use call_stage7_analyse() when available
    (Directive C filename rename). Active callers: cohort_runner.py:250.
```

**STATUS: COMPLIANT** — deprecation notes are present on both methods, forward path named, active callers documented.

---

## 4. New f3a/f3b References Introduced by D1.3 Commits

Command: `git diff main..directive-d1-3-audit-fixes -- '*.py' | grep "+.*f3a\|+.*f3b" | grep -v "NOTE\|deprecated\|DEPRECATED\|param name"`

Two lines pass the filter:

```
+        migrated to call_f3a / call_f3b (themselves legacy — see their deprecation notes)
+            f3a_output=stage3_with_abn,
```

**Line 1:** `"migrated to call_f3a / call_f3b (themselves legacy..."` — this is a comment/docstring string, not a functional reference. It explicitly points at the deprecation notes. Classification: (d) LEGACY KEY WITH DEPRECATED NOTE. CLEAR.

**Line 2:** `f3a_output=stage3_with_abn,` — this is the kwarg passed to `score_prospect()` in `cohort_runner.py`. The change replaces `f3a_output=domain_data.get("stage3", {})` with `f3a_output=stage3_with_abn` (a dict that has `serp_abn` injected). This is a bug-fix that enriches the payload; it does not introduce a new naming reference — the kwarg name was already present pre-D1.3. Classification: (a) DEFERRED PARAM — existing caller-compat kwarg, same name unchanged. CLEAR.

**STATUS: NO NEW REAL f3a/f3b REFERENCES INTRODUCED BY D1.3**

---

## 5. Summary Table

| Check | Result | Severity |
|-------|--------|----------|
| f3a/f3b refs in src/ — real misses | 0 real misses | PASS |
| prospect_scorer.py line 58 — missing NOTE | NOTE absent; docstring present but not flagged as legacy | LOW (inconsistency, not a miss) |
| CLAUDE.md dead-ref table — HunterIO | Present with scoped EXCEPTION | PASS |
| CLAUDE.md dead-ref table — Apify | Present with scoped EXCEPTION | PASS |
| call_f3a deprecation note | Present — Sphinx `.. deprecated::` with forward path | PASS |
| call_f3b deprecation note | Present — Sphinx `.. deprecated::` with forward path | PASS |
| New f3a/f3b refs from D1.3 commits | 0 new real references (2 lines — both compliant) | PASS |

---

## 6. Action Required

**prospect_scorer.py line 58** — add `NOTE: param name retained for caller compatibility (scripts use f3a_output= kwarg).` to the docstring for consistency with the established pattern in `verify_fills.py` and `gemini_client.py`. This is a LOW severity documentation gap only; no functional impact.

All other checks PASS. The naming audit finds no governance violations and no new technical debt introduced by the D1.3 fix commits.
