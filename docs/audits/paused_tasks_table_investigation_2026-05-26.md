# paused_tasks Table Investigation — Read-Only Audit

**Audit:** DRIFT-MAJOR #2 from `ratified_runtime_alignment_sweep_2026-05-26.md` §6
**Dispatcher:** Elliot (reassigned from Atlas)
**Auditor:** scout
**KEI:** Agency_OS-zw3k (P0, read-only)
**Date:** 2026-05-26 UTC
**Type:** Read-only investigation
**Verdict:** **(c) Deferred to Phase A8 build — and the implementation KEI was never filed.**

---

## 1. The claim under audit

From `ratified_runtime_alignment_sweep_2026-05-26.md` line 102:

> `eph.paused_tasks` — canonical claim: "paused_tasks Postgres table with 7-day TTL + dead-letter to Elliot; PR #1140". Runtime probe: `SELECT FROM information_schema.tables WHERE table_name ILIKE '%paused%'` → empty result set. **DRIFT-MAJOR**.

Sweep recommended next action (line 187): "Either run the missing migration OR confirm the table lives on a non-Supabase host."

Dispatch frames three hypotheses:
- (a) migration committed but never applied
- (b) table living on non-Supabase host (Hindsight's Postgres)
- (c) deferred to Phase A8 build

---

## 2. Evidence collected

### 2.1 PR #1140 metadata

```
$ gh pr view 1140 --json title,state,mergedAt,files,additions,deletions
title:    "[AIDEN] docs(architecture): ephemeral agent system scoping
           (V1 criterion 1, Agency_OS-dbwt)"
state:    MERGED
mergedAt: 2026-05-25T05:19:04Z
files:    docs/architecture/ephemeral_agent_system_scoping.md  (only file)
additions: 241
deletions: 0
```

PR body verbatim (excerpt):

> V1 completion criterion 1 scoping doc — ephemeral agent system replaces tmux. Per Dave-authorised dispatch 2026-05-25 post-wave-2-close. **Scoping, not implementation** — ~5 pages of architecture proposal.

This is a single doc-only PR. No SQL, no migration, no accessor code.

### 2.2 What the scoping doc actually says about `paused_tasks`

`docs/architecture/ephemeral_agent_system_scoping.md`:

- **Line 98** — `paused_tasks` introduced as a design concept: state-snapshot lives in the `paused_pending_decision` event payload + "persisted to a `paused_tasks` table (new — see §7 implementation pieces)".
- **Line 102** — 7-day TTL + dead-letter described as a design property.
- **Line 124** — "Add `paused_tasks` Postgres table (see §7)" — instruction to a future implementer, not a record of work done.
- **Line 154** (§7 implementation pieces, item #2):

  > **`paused_tasks` Postgres table + migration** — see §5 state-snapshot. ~50 LoC SQL + ~100 LoC accessor. P1.

§7 prologue verbatim:

> Each becomes a separate engineer-tier KEI dispatched post-merge. Not bundling here per `feedback_split_orthogonal_scope`.

PR #1140 explicitly scopes `paused_tasks` as a P1 follow-up engineer-tier KEI. The PR itself did not — and was never intended to — land the migration.

### 2.3 Supabase migrations directory

```
$ ls supabase/migrations/ | grep -i "paus\|ephem"
050_emergency_pause.sql
```

Only match is `050_emergency_pause.sql` — unrelated (emergency-pause control, not the paused-task queue from §5 of the scoping doc).

```
$ grep -rn "paused_tasks" supabase/
(no output)
```

Zero references to `paused_tasks` anywhere under `supabase/`. The table is not unapplied — it was never authored.

Most recent migrations (sorted):

```
20260524_0scg_ceo_memory_context_not_null.sql
20260525_keiracom_tenant_metering.sql
20260525_keiracom_tenants.sql
```

PR #1140 merged 2026-05-25 05:19 UTC. No follow-up `paused_tasks` migration landed on 2026-05-25 or 2026-05-26.

### 2.4 Engineer-tier follow-up KEIs

§7 of the scoping doc names 7 implementation pieces to be filed as separate KEIs. Current bd state:

```
$ bd list | grep -i "paus\|ephem\|spawn"
○ Agency_OS-dbwt  P1  V1 criterion 1 architecture scoping: ephemeral agent system replaces tmux
○ Agency_OS-p4ya  P1  V1 CRITERION 1 — Ephemeral agent system replaces tmux (architectural backbone)
○ Agency_OS-wc6r  P1  Phase A8 — Ephemeral agent foundation
○ Agency_OS-zw3k  P0  [ATLAS] paused_tasks table missing investigation — DRIFT-MAJOR from sweep PR #1167
```

What exists: the scoping doc KEI (`dbwt`), the V1 criterion 1 epic (`p4ya`), the Phase A8 foundation umbrella (`wc6r`), and this read-only investigation (`zw3k`).

What does **NOT** exist: any of the 7 engineer-tier KEIs from §7. In particular **§7 piece #2 (`paused_tasks` Postgres table + migration) was never filed** after PR #1140 merged. The post-merge dispatch the scoping doc anticipated did not happen.

---

## 3. Verdict

**(c) Deferred to Phase A8 build — with one procedural gap.**

PR #1140 is a 241-line scoping document. It explicitly defers the `paused_tasks` table to a post-merge engineer-tier KEI (§7 piece #2, P1, ~50 LoC SQL + ~100 LoC accessor). No migration was ever written, no SQL exists anywhere in the repo, and the host question is moot until the engineer-tier KEI runs.

Hypothesis (a) is ruled out — there is no committed-but-unapplied migration. The migration file does not exist.

Hypothesis (b) is ruled out as a current claim — the design is Supabase-native by inheritance from the rest of the ephemeral-agent architecture (which composes from `agent_memories`, `ceo_memory`, the inbox JSON layer — all Supabase). The scoping doc does not specify "non-Supabase host" anywhere; that hypothesis came from the sweep PR's "or" framing, not from §7 text.

**Procedural finding**: §7 of the scoping doc says each implementation piece "becomes a separate engineer-tier KEI dispatched post-merge". One day post-merge, none of the 7 KEIs has been filed. This is the actual gap — not a runtime substrate gap, but a follow-up-dispatch gap.

---

## 4. Re-classification of DRIFT-MAJOR #2 in the sweep

The sweep PR #1167 §6 lists `eph.paused_tasks` as **DRIFT-MAJOR — same family as `eph.docker_container`; PR design merged but runtime artefact missing**.

This is a mis-classification on close inspection. The DRIFT-MAJOR family is meant for "canonical claim says X, runtime quietly does Y" — i.e. ratified, then drifted (e.g. Cognee marked retired but services running). `paused_tasks` is a different shape: **ratified-but-unbuilt**. The scoping doc itself flags it as a P1 implementation piece pending engineer-tier dispatch.

The DRIFT family taxonomy needs a third bucket:
- **DRIFT-MAJOR (ratified-then-drifted)**: canonical updated but runtime quietly does the old thing (`eph.docker_container`, `mem.cognee_retired`).
- **DRIFT-MAJOR (ratified-but-unbuilt)**: canonical asserts existence but the artefact was deferred to a follow-up KEI that didn't ship (`eph.paused_tasks`).

The runtime impact differs: ratified-then-drifted means something is actively running counter to canonical; ratified-but-unbuilt means a follow-up dispatch was forgotten. Both are real, but they take different fixes.

---

## 5. Source of the misleading canonical claim

The string "paused_tasks Postgres table with 7-day TTL + dead-letter to Elliot; PR #1140" originated in my own sweep audit `ratified_runtime_alignment_sweep_2026-05-26.md` (line 102). I cited PR #1140 as the source of the canonical claim. PR #1140 is the **design source**, not an implementation source — citing it as the canonical proof of substrate is the error.

If a `ceo_memory` key or any downstream artefact inherits this exact phrasing, it needs correcting to: "paused_tasks Postgres table — DESIGNED in PR #1140 §5 + §7 piece #2; implementation deferred to a P1 engineer-tier KEI (not yet filed) as part of Phase A8 ephemeral foundation (`Agency_OS-wc6r`)."

I will flag this to Elliot for canonical-source repair.

---

## 6. Recommended next actions (no implementation by scout — read-only)

1. **File the missing engineer-tier KEIs from §7** of `ephemeral_agent_system_scoping.md` — at minimum piece #2 (`paused_tasks` table + migration, P1, ~150 LoC), and ideally all 7 — as children of `Agency_OS-wc6r` (Phase A8 ephemeral foundation). Engineer-tier (Atlas/Orion/Nova) dispatch. ~5 min per filing.

2. **Correct the canonical claim** wherever the "PR #1140" phrasing has propagated. Replace with the "DESIGNED in PR #1140; implementation deferred to Phase A8 KEI (TBD-filed)" formulation from §5 above. If the claim is also in `ceo_memory` under `ceo:memory_abstraction_layer_v1` or any criterion 1 artefact, that needs the same correction.

3. **Re-classify the sweep PR #1167 DRIFT-MAJOR #2 entry** to "ratified-but-unbuilt" once a third taxonomy bucket is agreed. This is a doc-PR-level patch to `ratified_runtime_alignment_sweep_2026-05-26.md`.

4. **Audit the other 6 §7 pieces** for the same shape — are dispatcher package, inbox JSON schema, systemd unit templates, spawn-with-context composer, cutover checklist, and decommission tracking each filed as their own KEI? Quick grep against `bd list` suggests no; worth a confirming pass.

---

## 7. Notes (audit-dispatch checklist compliance per Viktor write-gate)

Per the orchestrator dispatch protocol, this audit pastes the relevant canonical context inline. The dispatch did not name a specific `ceo:*` key to query, but the closest canonical surfaces are:

- `ceo:memory_abstraction_layer_v1` — would be the natural home for paused_tasks state-snapshot canonical phrasing (not queried; recommend Elliot/Aiden cross-check on review).
- The sweep PR #1167 audit doc itself — quoted verbatim in §1 and §4 above.
- PR #1140's body + the scoping doc §5 + §7 — quoted verbatim in §2.1 and §2.2.

No canonical key was contradicted by this finding; the issue is that the canonical phrasing in the sweep doc over-attributes existence to PR #1140 when PR #1140 only designed the table.

---

**Verdict: (c).** No migration exists, none was ever written, the scoping doc explicitly scopes `paused_tasks` as a P1 post-merge engineer-tier KEI, and the KEI was never filed. The procedural fix is filing the §7 KEIs (especially #2) and correcting the canonical phrasing.
