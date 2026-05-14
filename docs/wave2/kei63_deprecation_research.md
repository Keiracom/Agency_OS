# KEI-63 — Explicit deprecation layer: research + design

**Author:** scout (Sonnet 4.6, research clone)
**Date:** 2026-05-14
**Status:** research-phase deliverable (scout-lane build-pre-research); build phase is Aiden's after KEI-46+47+60 ship per Linear owner field.
**Linear:** [KEI-63](https://linear.app/keiracom/issue/KEI-63)
**Depends on:** KEI-46 (Weaviate), KEI-47 (migration completeness), KEI-60 (environment_hash). All Aiden lane.
**Owner per Linear body:** Aiden — after KEI-56 ships.

Third (and final) deliverable of the discovery-governance trilogy.
Pairs with [KEI-58 staleness research](kei58_staleness_governance_research.md)
and [KEI-55 tier-validation research](kei55_tier_validation_research.md).
This document is intentionally narrower — KEI-63 has two surfaces
(`bd deprecate` + env-hash invalidation), and most of the precedence
+ schema work already lives in KEI-55/KEI-58.

---

## 1. Problem framing

Two related gaps the staleness layer (KEI-58) and tier validation
(KEI-55) don't close on their own:

1. **No explicit "this is now wrong" signal.** Time-based staleness
   (KEI-58) ages a record out gradually. But when an infrastructure
   migration makes a discovery actively incorrect — not just old —
   there's no command to say "kill this immediately".

2. **No environment-change invalidation.** When we migrate off Vultr,
   change container runtimes, or upgrade a major dep version, every
   discovery tied to the old environment is invalidated at once.
   Time-based staleness misses this entirely.

KEI-63 closes both with one explicit command (`bd deprecate`) and one
event-driven sweep (environment hash mismatch detection).

---

## 2. The `bd deprecate` command

User-facing surface is one subcommand on `discoveries_cli.py`
(sibling of `verify` from KEI-58 and `challenge` from KEI-55):

```bash
discoveries_cli.py deprecate disc_8a91c7 \
  --reason "Migrated off Vultr — containerization strategy changed; cgroup v2 path no longer applies."
```

Effect:

1. `status` → `deprecated` on the Weaviate record.
2. `deprecated_by` = agent callsign, `deprecated_at` = NOW(),
   `deprecation_reason` = the `--reason` text.
3. Deprecated records are NEVER injected by `bd claim` / LlamaIndex
   `query()`. Retrieval-path filter (§5 below).
4. Record remains in Weaviate permanently for audit. Never deleted.
5. Audit row written to `public.audit_logs` with the deprecation
   event.

### Tier rules

Aligns with the validation tiers from KEI-55:

| Tier of original     | Deprecation auth required                                    |
|----------------------|--------------------------------------------------------------|
| Tier 1               | Any agent — no approval                                      |
| Tier 2               | Peer CONCUR before deprecation takes effect                  |
| Tier 3               | Dave approval — Slack notification with `bd ratify`/`bd reject` |

The Tier 2 + Tier 3 paths reuse the concur + ratification machinery
from KEI-55. No new governance plumbing — just a flag on the
deprecation row that says "needs CONCUR" / "needs ratify" before the
record's `status` flips.

```sql
-- Pending-deprecation queue (same shape as KEI-55's tier3_pending)
CREATE TABLE IF NOT EXISTS public.deprecation_pending (
    discovery_id   TEXT PRIMARY KEY,
    raised_by      TEXT NOT NULL,
    raised_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason         TEXT NOT NULL,
    tier_required  INT NOT NULL CHECK (tier_required IN (2, 3)),
    expires_at     TIMESTAMPTZ NOT NULL,           -- 48h for Tier 2, 72h for Tier 3
    decision       TEXT CHECK (decision IN ('approved','rejected','expired')),
    decided_by     TEXT,
    decided_at     TIMESTAMPTZ
);
```

The cron in KEI-55 (§7) extends to also flip `deprecation_pending`
rows past `expires_at` to `decision='expired'` so they don't sit
forever.

---

## 3. Environment hash invalidation

Builds directly on KEI-60 (Weaviate persistent storage governance) +
the `src/memory/environment_hash.py` module already merged in PR #850.
That module already computes:

```python
{
    "python": "3.12.2",
    "cognee": "0.7.3",
    "weaviate": "4.5.1",
    # ... etc.
}
```

KEI-63 wraps this with two pieces:

### 3a. `environment_hash` field on every discovery

Already specified in the KEI-58 `context_version` schema (`§3` of the
staleness research doc). Auto-populated at write time. No new field
work for KEI-63 — reuse.

### 3b. Sweep job: detect env mismatches → flag context_changed

```python
# src/governance/env_invalidation_sweep.py
def sweep_environment_invalidations() -> dict[str, int]:
    """Compare every discovery's environment_hash against the current env.

    Discoveries where the hash differs get `status='context_changed'`
    set (orthogonal to 'permanent' — context_changed is a flag, not
    a state). Agents see a strong warning in injection labels.

    Returns: {marked, unchanged, skipped_deprecated}.
    """
    current = environment_hash.compute()
    counters = {"marked": 0, "unchanged": 0, "skipped_deprecated": 0}
    for disc in weaviate.iter_discoveries():
        if disc.status == "deprecated":
            counters["skipped_deprecated"] += 1
            continue
        if disc.environment_hash == current.hash:
            counters["unchanged"] += 1
            continue
        weaviate.update(disc.id, context_changed=True,
                       context_changed_at=datetime.now(UTC),
                       context_changed_from=disc.environment_hash,
                       context_changed_to=current.hash)
        counters["marked"] += 1
    return counters
```

### When the sweep runs

Three triggers:

1. **Manual** — `discoveries_cli env-sweep` for explicit invocation
   after a known migration.
2. **Boot-time on environment_hash change** — `pre_compact_alert.py`
   already computes env hash on every session start (per KEI-60); if
   it has changed since last boot, fire the sweep automatically.
3. **Nightly cron** — backstop. Catches version drift that happens
   over the course of a day without an explicit reboot.

The boot-time trigger (#2) is the highest-leverage one — captures
the moment a deploy actually changes the env, so the staleness
flags are accurate the next time an agent runs `bd claim`.

### context_changed vs deprecated — keep them separate

| Signal              | Source                          | Reversible?     |
|---------------------|---------------------------------|-----------------|
| `context_changed`   | env-hash mismatch sweep         | Yes — `bd verify --action confirm` clears it after the agent decides the discovery is still valid in the new env |
| `deprecated`        | Explicit `bd deprecate` command | No — terminal state, audit-only |

This is the key invariant. The sweep doesn't auto-deprecate, only
flag. Auto-deprecation would silently delete history without an
agent or human ever consciously deciding.

---

## 4. Discovery state ladder — full triad

After KEI-55 + KEI-58 + KEI-63 all ship, the state model is:

```
WRITE (KEI-55) → staging
                   │
        ┌──────────┼──────────┐
        │          │          │
   Tier 1: 24h   Tier 2:    Tier 3:
   unchallenged  peer       Dave ratify
        │       CONCUR        │
        ▼          ▼          ▼
     ┌────────────────────────────┐
     │      permanent             │
     │  (KEI-55 + KEI-58 + KEI-63 │
     │   labels render on inject) │
     └─┬───────────┬─────────────┘
       │           │
   bd deprecate   bd verify     env_hash sweep
   (KEI-63)      (KEI-58)        (KEI-63)
       │           │                 │
       ▼           ▼                 ▼
  ┌─────────┐  ┌────────────┐  ┌────────────────┐
  │deprecated│ │ re-stamped │  │context_changed │
  │  (TERM)  │ │ (verified_ │  │  (flag, not    │
  └─────────┘  │  at=NOW())  │  │   terminal)    │
               └────────────┘  └────────────────┘
```

Terminal states: `deprecated`, `expired`, `superseded`. Everything
else is reachable.

---

## 5. Retrieval-path filter (the read-side guard)

Single function consulted by both `bd claim` injection and
LlamaIndex `query()` (KEI-49). Defined in
`src/retrieval/injection_filter.py`:

```python
def injectable(d: Discovery) -> tuple[bool, list[str]]:
    """Return (allowed_in_injection, list_of_inline_labels).

    Precedence (highest first):
      1. status == 'deprecated'      → (False, [])
      2. status == 'expired'         → (False, [])
      3. status == 'staging'         → (False, [])    # not yet validated
      4. status == 'challenged'      → (True, ['⚠ 1 open challenge'])
      5. context_changed             → (True, ['⚠⚠ Environment changed'])
      6. age_days > 180              → (True, ['⚠⚠ X days old'])
      7. age_days > 90               → (True, ['⚠ X days old'])
      8. age_days > 30               → (True, ['~X days old'])
      9. else                        → (True, [])     # fresh, full trust
    """
```

Tests for `injectable()` live in `tests/retrieval/test_inject_precedence.py`
— 9 cases, one per branch, exhaustive. The precedence order is the
canonical answer to "what happens when multiple flags fire on one
record".

Note: a `context_changed` record CAN also be `stale` (>90d).
`injectable()` returns BOTH labels in that case — agents see all
relevant signals concatenated. The 60-char label-truncation rule
from KEI-58 §11 risk row still applies.

---

## 6. Smoke-test plan (KEI-63 specific)

| # | Scenario                                                                        | Expected                                                                |
|---|---------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| 1 | `discoveries_cli deprecate <id>` on Tier 1 discovery                            | Status='deprecated' immediately, audit_log row written                   |
| 2 | `discoveries_cli deprecate <id>` on Tier 2 discovery                            | `deprecation_pending` row created; status unchanged until peer CONCUR    |
| 3 | Tier 2 deprecation + peer CONCUR within 48h                                     | Status flips to deprecated; pending.decision='approved'                  |
| 4 | Tier 2 deprecation, no CONCUR in 48h                                            | pending.decision='expired'; original status unchanged                    |
| 5 | `discoveries_cli deprecate <id>` on Tier 3 discovery                            | Slack notification fires to #ceo; pending row; status unchanged          |
| 6 | Tier 3 deprecation + Dave ratify within 72h                                     | Status='deprecated'; pending.decision='approved' by 'dave'               |
| 7 | env-hash sweep with mock current_hash ≠ stored_hash                              | discovery flagged context_changed=True with from/to values logged       |
| 8 | env-hash sweep skips deprecated discoveries                                     | sweep counters: skipped_deprecated > 0                                   |
| 9 | Inject-filter on deprecated discovery                                           | (False, [])                                                              |
| 10| Inject-filter on context_changed + 95d old discovery                            | (True, ['⚠⚠ Environment changed', '⚠ 95 days old'])                      |
| 11| `bd verify --action confirm` on context_changed record                          | context_changed=False; verified_at=NOW(); labels clear                   |

---

## 7. Build sequence (when KEI-46+47+60 ship)

Four PRs, each independently verifiable. Ordered by visibility:

1. **PR 1** — Schema additions to Weaviate `discoveries` collection
   (`deprecated_by`, `deprecated_at`, `deprecation_reason`,
   `context_changed`, `context_changed_at`, `context_changed_from`,
   `context_changed_to`) + Supabase `deprecation_pending` table.
   Smoke: SELECT/INSERT cycles.

2. **PR 2** — `discoveries_cli deprecate` subcommand. Tier-1 happy
   path only; Tier-2/3 paths return a "deferred" message and write
   to `deprecation_pending` for the cron to handle later. Smoke:
   case #1 above.

3. **PR 3** — Cron extension (in KEI-55's cron file) to expire
   pending deprecations + flip `deprecation_pending.decision` based
   on CONCUR/ratify state. Smoke: cases #2, #3, #4.

4. **PR 4** — `env_invalidation_sweep.py` + boot-time auto-fire from
   `pre_compact_alert.py`. Inject-filter integration. This is the
   visible deliverable. Smoke: cases #7-#11.

PR 5+ (later, separate KEI): Tier-3 Slack notification + Dave's
`bd ratify` / `bd reject` handlers. Same as KEI-55 PR-6 — could
ship as a combined "Tier-3 governance handlers" PR covering both
the tier-3 promotion path AND the tier-3 deprecation path.

---

## 8. Risks + mitigations (KEI-63 specific)

| Risk                                                              | Likelihood | Mitigation                                                                                  |
|-------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| env-hash sweep marks everything as context_changed on every deploy (false-positive storm) | high       | Only fire sweep on *significant* hash change — diff individual package versions, not the aggregate. Don't mark for patch-version bumps in non-watched packages. |
| Tier 2 deprecation peer-CONCUR race with the original author posting `bd verify --confirm` at the same moment | low | `SELECT FOR UPDATE` on the pending row inside the cron + the verify command; first writer wins. |
| Agent deprecates the wrong record by mistake                       | medium     | `--dry-run` flag on `deprecate` (default off) shows full effect before commit; one-click un-deprecate via `bd undeprecate` (audit-trailed) within 24h. |
| Env-hash mismatch on staging env vs prod env when developer runs sweep locally | medium | Sweep refuses to run unless `AGENCY_OS_ENV` matches the recorded `environment_hash.env` field. |

---

## 9. Open questions for Aiden's build

1. **What counts as a "significant" environment change for the
   automatic sweep?** Major-version bump (e.g. cognee 0.7 → 0.8)
   yes. Patch-version (0.7.3 → 0.7.4) — probably not. Configurable
   via `public.system_config` row `staleness.env_significant_pkgs`?
2. **One CLI or two?** This doc proposes `discoveries_cli deprecate`
   (one subcommand under the existing CLI). Alternative: a separate
   `bd deprecate` command. Both work; one-CLI is cheaper.
3. **Undeprecate window** — 24h proposed for `bd undeprecate`.
   Should this exist at all, or is deprecation truly terminal?
   Argument for: typo-fix in deprecation reason or wrong-record-id
   mistakes. Argument against: terminal is terminal; force the
   author to write a new corrected discovery instead.
4. **Slack notification cap** — if 50 records get auto-flagged
   `context_changed` during a deploy sweep, do we Slack-notify on
   each? Probably no — aggregate notification: "Env sweep flagged
   N records; see `discoveries_cli env-sweep --last`."

---

## 10. Scout handoff note

Trilogy complete:
- [KEI-58 staleness research](kei58_staleness_governance_research.md) — PR #867 → 46a9e87b
- [KEI-55 tier-validation research](kei55_tier_validation_research.md) — PR #870 → ad4d13ff
- KEI-63 deprecation research — this doc

All three referenced cross-spec, designed to ship together. Aiden's
build phase can lift them in any order but should ship KEI-55 first
(it owns the schema additions the other two rely on).

On merge of this PR: tasks-table row `KEI-63` will trip the
`require_verification_before_done()` trigger (build acceptance
criteria require Weaviate). Releasing claim back to `available` so
Aiden can re-claim during the build phase. Linear comment will
document the research delivery.
