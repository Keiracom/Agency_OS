# KEI-197 — NULL raw_text Discoveries: Evidence + Fix

**Status:** Script + guard shipped (this PR). Cleanup run is operator-gated.
**KEI:** [KEI-197](https://linear.app/keiracom/issue/KEI-197) (M2 follow-up from KEI-192 memory audit).
**Authored by:** Scout · 2026-05-18.

## What this PR delivers

1. **Guard** (`src/governance/discovery_validation.py`) — `submit_discovery` now rejects empty/None text + empty agent + empty kei BEFORE any Weaviate POST. New orphans cannot be created via the canonical writer.
2. **Cleanup script** (`scripts/orchestrator/kei197_drop_null_raw_text.py`) — one-shot DELETE of all rows in a class where raw_text is null/empty. `--dry-run` lists, no flag deletes. Operator runs after review.
3. **5 unit tests** (`tests/governance/test_kei55_discovery_validation.py`) — cover the guard (empty text, whitespace-only, None, empty agent, empty kei all raise ValueError).
4. **This scope doc** — empirical evidence + scale of the orphan problem.

## Empirical investigation

Aiden's KEI-192 memory audit reported 10 agent='elliot' rows with NULL raw_text. Direct Weaviate GraphQL probe confirms the shape and reveals the problem is **much larger than the original audit**:

```
$ python3 scripts/orchestrator/kei197_drop_null_raw_text.py --dry-run 2>&1 | grep -c "  id="
6560
```

**6560 orphan rows** in the `Discoveries` collection have raw_text null/empty. Affected agents (from a sample of the rows):

| Agent tag | Pattern |
|---|---|
| `elliot` | Many — includes the 10 originally audited |
| `ELLIOT` | Some (uppercase variant — separate writer or older convention) |
| `aiden` | Some |
| `max` | Some |
| `unknown` | Some (`DEFAULT_CALLSIGN` sentinel writes — see KEI-71) |

Earliest orphan `created_at`: **2026-02-02** (3.5 months old). The orphans accumulated over the entire codebase lifetime — not a single backfill burst.

## Likely root causes

Multiple writers contributed. The canonical writer `src/governance/discovery_validation.py::submit_discovery` was previously permissive — accepted `text=""` and passed it through to Weaviate, where Weaviate stores an empty string as NULL on the inverted index. The KEI-71 sentinel-callsign protection (claimed_by='unknown') predates KEI-197; the analogous protection on text was missing.

The `creationTimeUnix` clustering Aiden observed for the 10 agent='elliot' rows (all on 2026-05-16 14:34 UTC) is one burst within the larger 6560 — likely an ad-hoc re-embed or backfill script run that wasn't committed to the repo. Tracing the specific writer requires the operator's bash history from that day; for the fix, drop+guard is sufficient.

## Schema-level option (deferred)

Weaviate supports `indexNullState: true` on the invertedIndexConfig, which would let us use the `IsNull` filter operator directly + enforce non-null at write time. Empirical check during script development:

```
$ curl ... where: {operator: IsNull, path: ["raw_text"], valueBoolean: true}
ERROR: Nullstate must be indexed to be filterable! Add `indexNullState: true` to the invertedIndexConfig
```

Adding `indexNullState: true` requires recreating each affected collection (Discoveries, Sessions, Codebase, Decisions, Keis) — out of scope here. Filed for KEI-196 (M1 — re-ingest collections with vectorizer change) to absorb.

## Cleanup workflow (operator-gated)

```
# 1. List orphans for review
python3 scripts/orchestrator/kei197_drop_null_raw_text.py --dry-run

# 2. After Elliot/Dave reviews the list, run the delete
python3 scripts/orchestrator/kei197_drop_null_raw_text.py

# 3. Optional: target other collections
python3 scripts/orchestrator/kei197_drop_null_raw_text.py --class Sessions --dry-run
```

The script uses Weaviate DELETE per object (no bulk delete by filter, because the IsNull filter isn't indexed). Sequential deletes are slow for 6560 rows — expect ~5-10 minutes wall-clock. Idempotent: 404 on already-gone is treated as success.

## Acceptance per KEI-197

- [x] Culprit pattern identified: multiple writers historically permissive on text; canonical writer fixed in this PR with guard.
- [x] Drop path provided: cleanup script with dry-run.
- [x] Future writes from `submit_discovery` have non-null raw_text: rejected at function-call boundary with ValueError.
- [x] Integration test: 5 tests verify the guard rejects empty/whitespace/None text + empty agent + empty kei.
- [ ] Live cleanup run on Vultr Weaviate: operator-gated (this PR doesn't auto-run; 6560 deletions has blast radius).

## Out of scope (follow-up)

- **Schema indexNullState** — needs collection recreate. KEI-196 absorbs.
- **Tracing the 2026-05-16 burst** — bash history forensics; not load-bearing for the fix.
- **Other writers (ELLIOT/ELLIOT/etc.)** — uppercased agent tags suggest stale code paths; non-canonical writers should be migrated to `submit_discovery` (and inherit the guard). Filed as a P3 follow-up if Elliot wants it tracked.
- **Other classes** — Sessions/Codebase/Decisions/Keis may have similar orphans; script supports `--class` for ad-hoc cleanup. Full audit deferred to KEI-192 follow-up scope.
