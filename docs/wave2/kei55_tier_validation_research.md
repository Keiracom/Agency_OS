# KEI-55 — Discovery validation governance: research + design

**Author:** scout (Sonnet 4.6, research clone)
**Date:** 2026-05-14
**Status:** research-phase deliverable (scout-lane "build-pre-research"); build phase is Aiden's after KEI-46+47 ship per Linear owner field.
**Linear:** [KEI-55](https://linear.app/keiracom/issue/KEI-55)
**Depends on:** KEI-46 Weaviate install, KEI-47 migration completeness — both Aiden lane, not shipped.
**Owner per Linear body:** Aiden (build).

This document is the design spec for KEI-55 — the tiered-CONCUR
validation layer that gates discoveries from `staging` to `permanent`
in Weaviate. Closes the design phase so Aiden can lift the build into
PRs without re-deriving the architecture. Complements the staleness
design (KEI-58, shipped 2026-05-14) and the deprecation design
(KEI-63 — pending scout/Aiden split).

---

## 1. Problem framing: epistemic poisoning

The classic failure mode: Agent A writes a discovery that is wrong
(misread error, hallucinated cause, overconfident generalisation).
Without validation, the record is indexed into the permanent
collection. Agent B pulls it during `bd claim` context injection. B
acts on A's hallucination as fact. The error propagates as
institutional memory and is now harder to remove than to refute —
because no one knows when it was a mistake.

A validation layer must:

1. Keep new discoveries in a staging area where they can be
   reviewed before promotion.
2. Differentiate by **stakes** — a routine technical finding doesn't
   need three peer concurs; a ratified-decision contradiction does.
3. Provide explicit challenge mechanism — peers can fact-check + flag
   without escalating to Dave for trivial things.
4. Auto-expire stale staged discoveries — silence isn't approval.

---

## 2. The three-tier model

KEI-55's Linear body specifies three tiers. This document fleshes
them into concrete promotion rules + state machine.

| Tier | Definition                                                  | Path                       | Auto-promote | Challenge window | Concur required |
|------|-------------------------------------------------------------|----------------------------|--------------|------------------|-----------------|
| 1    | Routine technical finding (verifiable in <5 min)            | staging → permanent (24h)  | yes if unchallenged | 24h           | 0               |
| 2    | Architecture-level decision (use X instead of Y)             | staging → permanent on peer CONCUR | no | 48h (expire)     | 1 peer          |
| 3    | Contradicts a ratified `ceo:rule:*` or KEI decision         | staging → Slack-Dave path  | no           | 72h (expire)     | Dave-approval   |

### Tier assignment

Tier is determined at write time. Source of truth (in order of precedence):

1. **Agent self-declares** — `discoveries_cli write --tier 2 --content "..."`.
   The default is Tier 1 if unspecified.
2. **Trigger keywords** — if the discovery content contains "I propose
   we use X instead of Y" / "architecture decision" / "approach
   change" → bump to Tier 2 unless agent explicitly set Tier 1.
3. **Ratification cross-check** — if the discovery contradicts any
   active `ceo:rule:*` row, force-bump to Tier 3 (override agent
   declaration). The cross-check uses a simple SQL `text similarity`
   match against `public.ceo_memory` rows where `key LIKE 'ceo:rule:%'`.

The third rule is the anti-tier-laundering guard — an agent cannot
mark a contradictory finding as Tier 1 to slip it past review.

---

## 3. State machine

```
                      ┌────────────────────────────────┐
                      │      WRITE                     │
                      │   (discoveries_cli write)      │
                      └────────────────┬───────────────┘
                                       │
                                       ▼
                               ┌───────────────┐
                               │   staging     │
                               │ (validation_  │
                               │  tier = 1|2|3)│
                               └─┬───────────┬─┘
                                 │           │
                  Tier 1: 24h    │           │   Tier 2: 48h / Tier 3: 72h
                  unchallenged   │           │   no concur / no approval
                                 ▼           ▼
                          ┌────────────┐  ┌─────────┐
                          │ permanent  │  │ expired │
                          └─┬───────┬──┘  └─────────┘
                            │       │
                bd challenge │       │ bd verify (KEI-58)
                            ▼       ▼
                       ┌──────────┐ ┌─────────────┐
                       │challenged│ │  re-stamped │
                       │ → tier 2 │ │ (verified_  │
                       │   review │ │  at=NOW())  │
                       └──────────┘ └─────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ depending on the │
                  │ counter-finding: │
                  │   permanent OR   │
                  │   deprecated     │
                  │   (KEI-63)       │
                  └──────────────────┘
```

The four terminal states are: **permanent**, **expired**, **deprecated**
(via KEI-63), and **superseded** (via KEI-58's `bd verify --action update`).

---

## 4. The `bd challenge` command

When agent B disagrees with agent A's discovery, B runs:

```bash
discoveries_cli challenge disc_8a91c7 \
  --counter "Cognee 0.9.1 changed the cap default to 4096; the 8192 path is no longer canonical." \
  --evidence "https://github.com/topoteretes/cognee/pull/2840"
```

This:

1. Writes a `challenge` row to `public.discovery_challenges` with the
   counter-finding text + evidence URL + challenger callsign.
2. Demotes the discovery from `permanent` → `challenged` (a Tier-2
   review state — same governance as a fresh Tier 2 write).
3. Notifies the original author callsign via #execution outbox.
4. Starts a 48h review window. If a third peer CONCURs the counter-
   finding within 48h → original deprecated (via KEI-63), counter
   promoted to permanent. If no concur → original stays permanent
   with `challenge_count` incremented (visible signal: "this has
   been challenged once").

The challenger never wins by default. The bar is "third party
concurs the counter" — exactly the structure that prevents a single
loud disagreement from rewriting institutional memory.

---

## 5. Tier 3 path: Dave approval

Tier 3 discoveries — contradicting `ceo:rule:*` or ratified decisions —
auto-fire a Slack notification to Dave at write time. The notification
format:

```
[TIER-3 DISCOVERY — needs Dave approval]
Discovery ID: disc_a1b2c3
By:           scout (callsign)
Contradicts:  ceo:rule:law_ii  (Australia-first $AUD)
Content:      "Currency display should default to USD for international audiences,
              not AUD."
Evidence:     <evidence URL or text>
Expire:       72h from now (2026-05-17T07:30:00Z)
Approve:      bd ratify disc_a1b2c3   (Dave only)
Reject:       bd reject  disc_a1b2c3 --reason "..."
```

Dave's `bd ratify` (Dave-only, gated by `CALLSIGN=dave` env or peer-
verified Linear identity):
- Promotes discovery to `permanent`.
- Writes a new `ceo:rule:*` row in `public.ceo_memory` with the new
  rule text (or amends the existing rule). The original is preserved
  in an `audit_logs` row, never deleted.

Dave's `bd reject` from same gating:
- Status → `expired`.
- Discovery stays in Weaviate for the audit trail; never injected.

Auto-expire after 72h with no decision: status → `expired`, reason
"Tier 3 timeout — no Dave approval". This avoids the system silently
holding contradictory claims forever.

---

## 6. Storage schema additions

### Weaviate `discoveries` collection — new properties

```python
{
    "validation_tier": "int",         # 1 | 2 | 3
    "status": "text",                  # staging | challenged | permanent | expired | deprecated | superseded
    "staged_at": "date",
    "promoted_at": "date",             # nullable
    "expires_at": "date",              # nullable (set at staging time per tier)
    "challenged_by": "text",           # callsign or NULL
    "challenged_at": "date",
    "challenge_count": "int",
    "tier_assigned_by": "text",        # 'self' | 'keyword' | 'ratification_check'
    "ratification_target": "text"      # e.g. 'ceo:rule:law_ii' if Tier 3; nullable
}
```

### Supabase mirror — challenge + tier log

```sql
CREATE TABLE IF NOT EXISTS public.discovery_challenges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discovery_id    TEXT NOT NULL,
    challenger      TEXT NOT NULL,
    counter_finding TEXT NOT NULL,
    evidence_url    TEXT,
    raised_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    resolution      TEXT CHECK (resolution IN ('upheld','withdrawn','no_concur','superseded')),
    concur_callsigns TEXT[]
);
CREATE INDEX ON public.discovery_challenges (discovery_id);
CREATE INDEX ON public.discovery_challenges (raised_at DESC) WHERE resolved_at IS NULL;

-- Tier-3 escalation queue (Dave-facing)
CREATE TABLE IF NOT EXISTS public.tier3_pending (
    discovery_id    TEXT PRIMARY KEY,
    contradicts_key TEXT NOT NULL,     -- e.g. 'ceo:rule:law_ii'
    raised_by       TEXT NOT NULL,
    raised_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    notified_dave_at TIMESTAMPTZ,
    decision        TEXT CHECK (decision IN ('ratified','rejected','expired'))
);
```

Rationale: keep the challenge + tier-3 escalation rows in Supabase
(not just Weaviate). They're transactional governance state — fast
slice/dice queries ("show me all open challenges from atlas this
month") are cheaper in Postgres than Weaviate REST. Weaviate keeps
the embedding + content + status flag for retrieval-path use.

---

## 7. Promotion cron

A daily cron (initially; tighter cadence later if needed) runs:

```sql
-- Tier 1 auto-promote at 24h
UPDATE weaviate_proxy.discoveries SET
    status='permanent', promoted_at=NOW(), expires_at=NULL
WHERE validation_tier=1
  AND status='staging'
  AND staged_at < NOW() - INTERVAL '24 hours'
  AND id NOT IN (SELECT discovery_id FROM public.discovery_challenges WHERE resolved_at IS NULL);

-- Tier 2 expire at 48h without concur
UPDATE weaviate_proxy.discoveries SET status='expired'
WHERE validation_tier=2
  AND status='staging'
  AND staged_at < NOW() - INTERVAL '48 hours';

-- Tier 3 expire at 72h without Dave ratify
UPDATE weaviate_proxy.discoveries SET status='expired'
WHERE validation_tier=3
  AND status='staging'
  AND staged_at < NOW() - INTERVAL '72 hours';
```

(`weaviate_proxy.discoveries` is a placeholder — the cron actually
talks to Weaviate via the Python client; the SQL is illustrative
for the logic.)

Cron cadence: daily at 03:00 AEST (low-activity window). Materialised
status column on the Supabase mirror tracks transitions so an audit
shows when a Tier 1 was auto-promoted vs explicit-concur'd.

---

## 8. Inject-path filter (the read-side guard)

`bd claim` context injection — and the LlamaIndex `query()` API from
KEI-49 — must filter out any non-permanent discoveries:

```python
def injectable_discoveries(query: str, agent: str) -> list[Discovery]:
    """Retrieval-side filter — only permanent + non-deprecated discoveries surface."""
    raw = weaviate_search(query, k=20)
    return [
        d for d in raw
        if d.status == "permanent"
        and d.deprecated_at is None
        # Note: challenged discoveries STILL injected with a label —
        # better to surface the dispute than hide it.
    ]
```

Challenged discoveries are injected WITH a label
("⚠ This discovery has 1 open challenge — see disc_8a91c7"). Hiding
the dispute would re-introduce the epistemic-poisoning failure mode
the system was built to prevent.

---

## 9. Integration with KEI-58 (staleness) + KEI-63 (deprecation)

The three governance KEIs (KEI-55 / KEI-58 / KEI-63) form a triad:

| KEI    | Owns                          | Trigger                          | Output state           |
|--------|-------------------------------|----------------------------------|------------------------|
| KEI-55 | tier validation               | new discovery write              | staging → permanent OR expired |
| KEI-58 | age + version drift           | time + env-hash mismatch         | staleness flag in injection |
| KEI-63 | explicit invalidation         | `bd deprecate` command           | permanent → deprecated |

Precedence in the injection-path filter:

```
1. status == 'deprecated'   → exclude entirely        (KEI-63)
2. status == 'expired'      → exclude entirely        (KEI-55)
3. status == 'staging'      → exclude entirely        (KEI-55)
4. status == 'challenged'   → include with ⚠ label    (KEI-55)
5. age > threshold OR drift → include with ⚠/⚠⚠ label (KEI-58)
6. status == 'permanent', fresh → include unflagged
```

The injection-path test (`tests/retrieval/test_inject_precedence.py`)
must verify all six rows of this table.

---

## 10. Smoke-test plan

| # | Scenario                                                                         | Expected                                                                |
|---|----------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| 1 | Write Tier 1 → wait 25h → re-query                                                 | status='permanent', no warning                                          |
| 2 | Write Tier 2 → no concur within 48h                                                | status='expired', never injected                                        |
| 3 | Write Tier 2 → peer CONCUR before 48h                                              | status='permanent'                                                      |
| 4 | Write Tier 3 → Dave ratify within 72h                                              | status='permanent', `ceo:rule:*` row written                            |
| 5 | Write Tier 3 → Dave reject                                                         | status='expired', stays in Weaviate (audit), never injected             |
| 6 | Write Tier 3 → 72h timeout                                                         | status='expired', `tier3_pending.decision='expired'`                    |
| 7 | Agent self-declares Tier 1 on content matching ratification keyword                | force-bumped to Tier 3 (ratification cross-check)                       |
| 8 | `discoveries_cli challenge` with 3rd-party CONCUR within 48h                       | original deprecated (KEI-63), counter promoted                          |
| 9 | `discoveries_cli challenge` with no 3rd-party CONCUR                               | original stays permanent, `challenge_count` incremented                 |
| 10| Permanent discovery aged 100d → query                                              | injected WITH KEI-58 staleness label (orthogonal: still passes KEI-55)  |
| 11| Permanent discovery + env_hash mismatch                                            | injected with KEI-58 context-changed warning                            |
| 12| `discoveries_cli challenge` on a staging-state discovery                           | reject — challenge only applies to permanent                            |

---

## 11. Build sequence (when KEI-46+47 ship)

Five PRs, ordered by visibility + verifiability:

1. **PR 1** — Weaviate `discoveries` collection schema: add `validation_tier`,
   `status`, `staged_at`, `promoted_at`, `expires_at`, etc. Migration
   only; no behaviour change. Smoke: schema dump matches spec.

2. **PR 2** — Supabase migrations: `discovery_challenges`,
   `tier3_pending` tables. `system_config` rows for tier thresholds
   (24/48/72 hours). Smoke: INSERT/SELECT cycles.

3. **PR 3** — `discoveries_cli.py` write + show + challenge subcommands
   (KEI-58 already proposes `verify` + `staleness` in the same CLI —
   merge surface). Smoke: write a Tier 2, see staging row, peer CONCUR,
   see permanent transition.

4. **PR 4** — Promotion cron (24h Tier 1, 48h Tier 2, 72h Tier 3
   expire). Initially manual-trigger via CLI; systemd timer in a
   follow-up.

5. **PR 5** — Inject-path filter (`injectable_discoveries()` in
   `src/retrieval/staleness.py`, joins with KEI-58 work). This is
   the visible deliverable: agents now only see permanent +
   non-deprecated content in `bd claim` injections, with challenged
   + stale labels rendered inline.

PR 6+ (later, separate KEIs): Tier-3 Dave Slack notification + `bd
ratify`/`bd reject` handlers. The Slack format is well-defined in
§5 but the build is enough surface area to warrant its own KEI.

---

## 12. Risks + mitigations

| Risk                                                              | Likelihood | Mitigation                                                                                  |
|-------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| Tier inflation — every agent self-declares Tier 1                  | high       | Trigger-keyword bump rule (§2); periodic audit query for "Tier 1 but contains 'architecture'". |
| Anti-tier-laundering bypass (write to skip ratification cross-check)| medium     | Cross-check runs in promotion cron AND at write time; ratification rules use embedding match, not just string LIKE. |
| Challenge spam (vexatious peer disagreement)                       | low        | `challenge_count` visible signal; 3rd-party concur required for upheld — single disagreement doesn't deprecate. |
| Tier 3 Dave-notify storm (every minor disagreement escalates)       | medium     | Pre-filter: Tier 3 only fires if the contradicted rule is high-stakes (`ceo:rule:law_*` and `ceo:rule:law_*-ratified`). |
| Cron OOM on bulk re-classification                                  | low        | Batch the UPDATE in chunks of 500; emit progress log. Initial corpus is small (<10K). |
| Promotion race: peer CONCUR happens during cron expire pass         | medium     | Use `SELECT FOR UPDATE SKIP LOCKED` in the cron (same pattern KEI-22 uses for tasks claim). |

---

## 13. Open questions for Aiden's build

1. **Tier assignment for orchestrator-generated discoveries** — when
   an automated cron writes a discovery (e.g. nightly drift audit
   from KEI-58), what tier? Likely Tier 1 always; flag this in the
   PR-3 review.
2. **Cross-callsign concur rules** — can scout CONCUR a Tier 2 from
   another scout-equivalent clone? Probably not (clones aren't peers
   for governance); only Aiden / Max / Elliot count. Encode this in
   the concur-validity check.
3. **Slack notification channel for Tier 3** — `#ceo` (matches Dave's
   "blocker escalation — #ceo first" rule R13) vs a dedicated
   `#tier3-ratification`. `#ceo` is the lighter-weight default.
4. **Embedding similarity threshold for the ratification cross-check** —
   what cosine score counts as "contradicts"? Start with 0.85 (high
   bar) and tune from the first 90 days of Tier-3 false-positive
   data.

---

## 14. Scout handoff note

Per IDENTITY.md, scout's lane includes "build-pre-research (e.g., design
specs feeding Aiden's PRs)". KEI-55's owner in Linear is Aiden (build);
this design spec falls inside scout's lane as the research-phase
artifact that lets Aiden's PRs land mechanically.

On merge: tasks-table row `KEI-55` will trip the
`require_verification_before_done()` trigger (same pattern as KEI-58)
because the build acceptance criteria require Weaviate-backed
behavioural verification. Releasing the claim back to `available`
after merge so Aiden can re-claim during the build phase.

Linear comment will document the research delivery + release.
