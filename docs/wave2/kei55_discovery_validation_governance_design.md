# KEI-55 — Discovery validation governance (tiered CONCUR, anti-epistemic-poisoning)

**Author:** Aiden (design only per path-C cascade — precedent: KEI-37/38/39/41/42 today)
**Implementer:** Aiden in follow-up PR AFTER Atlas's KEI-46/47/48 Weaviate stack lands
**Beads:** Agency_OS-sud — P1 Urgent
**Linear:** [KEI-55](https://linear.app/keiracom/issue/KEI-55) (Dave's KEI-53 numbering)
**Self-referential anchor:** bd claimed BEFORE branch + commit per `ceo:rule:no_build_without_linear_issue` + KEI-39 4-step protocol (Linear KEI-55 already created by Dave; assignee transfer to aiden + bd mirror + claim + [STARTING] all on record before this file commit).

## Problem — Epistemic Poisoning

A flawed discovery log written by Agent A is indexed as permanent Layer 3 knowledge in Weaviate. Agent B pulls it as fact during bd claim context injection. The hallucination propagates as institutional memory.

Once permanent, removing a poisoned discovery is harder than gating its entry. Validation must happen BEFORE indexing into the permanent collection.

## Design — Tiered validation before permanent indexing

All discoveries enter a `staging` Weaviate collection first. Promotion path depends on the tier:

### Tier 1 — Routine technical finding

**Definition:** Verifiable in <5 minutes by any agent.
- Error codes + their meanings.
- Command-line invocation outcomes.
- File paths + module locations.
- API request/response shapes.
- Tool-version + behaviour observations.

**Promotion path:** `staging` → auto-promotes to `permanent` after 24h if unchallenged.

**Challenge mechanism:** Any agent can run `bd challenge <discovery_id>` with a counter-finding. Triggers immediate Tier 2 review (escalation). Auto-promotion paused until peer CONCUR or staging expiry.

**Rationale:** Tier 1 facts are cheap to verify + costly to gate. Auto-promote with challenge fallback preserves throughput while allowing peer correction.

### Tier 2 — Architecture-level discovery

**Definition:** Claims about system design, approach selection, "use X instead of Y" decisions, design-pattern recommendations.

**Promotion path:** `staging` → requires CONCUR from ONE peer agent before promoting to `permanent`.

**Expiry:** If no CONCUR within 48h, staging entry expires (status=expired). Not promoted. Author can re-submit with peer CONCUR attached if relevant.

**Challenge mechanism:** Peer can CONCUR (promote) OR BLOCK (counter-finding required) on the staging entry. BLOCK requires a counter-finding posted in the same window; both entries stay in staging until peer-CONCUR resolves.

**Rationale:** Architecture decisions have outsized propagation cost. Pay the gate at entry, not at remediation.

### Tier 3 — Contradicts a ratified decision

**Definition:** Discovery that contradicts a `ceo:rule:*` ceo_memory key OR a ratified KEI decision.

**Promotion path:** `staging` → Slack notification to Dave in #ceo → human approval required.

**Expiry:** Auto-expires from staging after 72h without Dave approval.

**Rationale:** Ratified decisions are CEO-level governance. Contradicting them needs CEO-level review. Auto-expiry prevents staging-channel-as-permanent-bypass.

## Discovery log schema additions

Every discovery entry (in both `staging` and `permanent` collections) carries:

```json
{
  "validation_tier": 1 | 2 | 3,
  "context_version": "KEI-44 · Cognee v0.7.3 · 2026-05-13",
  "status": "staging" | "permanent" | "expired" | "challenged",
  "written_by": "<callsign>",
  "written_at": "<ISO timestamp>",
  "validated_by": "<callsign | null>",
  "promoted_at": "<ISO timestamp | null>",
  "challenged_by": "<callsign | null>",
  "challenge_reason": "<string | null>",
  "tier_3_dave_approval": "<approved | rejected | pending | null>"
}
```

## bd challenge command

New CLI subcommand (extension to `bd`):

```
bd challenge <discovery_id> [--reason "<counter-finding-text>"]
```

Behaviour:
- Validates discovery exists in `staging` (rejects challenges on `permanent` — those need explicit override via Dave).
- Inserts challenged_by + challenge_reason + status=challenged in the entry.
- For Tier 1: pauses 24h auto-promotion; triggers Tier 2 peer-CONCUR review.
- For Tier 2: posts BLOCK in the peer-CONCUR window; counter-finding must be submitted alongside.
- For Tier 3: re-triggers Dave notification with both original + challenge text.

Post-merge: bd help surfaces this command. Beads task-start template includes "Discovery from <id> may be challenged via `bd challenge <id>`" hint when injection surfaces a staging discovery.

## Staleness flag

Discoveries older than 90 days appear in bd claim context-injection with a flag prefix:

```
⚠ Discovery from 2025-12-15 (>90 days old) — verify still applies before relying on it.
```

No auto-deletion. Visibility only. Human or agent can explicitly re-verify (write a Tier 1 confirmation discovery) and re-timestamp the original.

**Rationale:** Auto-deletion of stale discoveries risks losing context. Visibility-only forces re-verification without destroying memory.

## Governance trace in Weaviate

Every discovery row stores a complete audit trail:
- `written_by` — original author callsign.
- `written_at` — ISO timestamp.
- `validated_by` — peer who CONCUR'd (Tier 2+ only).
- `promoted_at` — staging→permanent transition timestamp.
- `challenged_by` — peer who challenged (if applicable).
- `challenge_reason` — counter-finding text.
- `tier_3_dave_approval` — approved / rejected / pending / null.

Queryable via Weaviate GraphQL for compliance audits + epistemic-poisoning forensics.

## Composes with

- **KEI-46 Weaviate install (Atlas-lane)** — provides the collections infrastructure.
- **KEI-47 LlamaIndex retrieval (Atlas-lane)** — read-side that respects staging vs permanent.
- **KEI-48 Auto-indexing pipeline** — write-side that routes new discoveries to staging first.
- **KEI-51 agent_profile schema (Aiden-lane)** — capability_weights informs which peer to route Tier 2 CONCUR-request to.
- **KEI-67 CONCUR routing (preferred Atlas/Orion)** — any-available-peer routing applies to Tier 2 CONCUR pool.

## Acceptance criteria

- `staging` and `permanent` collections exist in Weaviate (post-KEI-46 install).
- Tier 1 auto-promotion runs on 24h schedule (systemd timer OR Supabase cron).
- Tier 2 CONCUR gate implemented — peer must explicitly validate via `bd challenge` or direct CONCUR.
- Tier 3 Slack notification fires to #ceo on discovery creation with `validation_tier=3`.
- Staleness flag appears in bd claim injection for discoveries with `written_at < now-90d`.
- `bd challenge <id>` command implemented + integrated.
- 5+ unit tests covering each tier path + challenge mechanism + staleness flag + governance-trace persistence.

## Implementation handoff (follow-up PR)

Files to touch:

1. `scripts/orchestrator/discovery_promote.py` (NEW) — 24h auto-promotion daemon + systemd timer.
2. `src/weaviate/staging_schema.py` (NEW) — staging + permanent collection definitions + discovery-entry schema.
3. `scripts/discovery_challenge.py` (NEW) — bd challenge command implementation.
4. `src/bot_common/discovery_log.py` (NEW or extend) — write-path routes new discoveries to staging by default; agents tag tier when posting.
5. Tier 3 Dave-notification hook in `scripts/slack_relay.py` (extension): when discovery `validation_tier=3` written, fire #ceo post.
6. bd claim context-injection enhancement: surface staleness flag for >90d discoveries.

Estimated total: ~400-500 LoC + tests + systemd unit + docs/runbook for the discovery-flow.

## Out of scope this PR

- Weaviate schema migration (Atlas KEI-46 ships infrastructure).
- LlamaIndex retrieval-side changes (Atlas KEI-47).
- Auto-indexing pipeline (Atlas KEI-48 — staging vs permanent routing happens there).
- CEO-rule contradiction detection logic (Tier 3 trigger) — needs `ceo:rule:*` queryability via Supabase first; can defer to follow-up.

## Sequencing

Per Round-3-ratified architecture cascade:
- Phase 1 (1-2 days): existing KEIs (KEI-22 + KEI-67 + KEI-40 + KEI-44) ship.
- Phase 2 (1 week additive): Redis Streams IPC tier.
- Phase 3 (1 week additive): Supabase Layer-3 enforcement.
- **THIS DESIGN DOC ships now** (design-only, no infrastructure dependency yet).
- **Implementation follows Atlas's KEI-46/47/48 Weaviate stack** landing (gated dependency).

## ceo_memory anchor

`ceo:rule:discovery_validation_governance` (per `ceo:rule:ceo_operational_directives_recorded` — Elliot ratifies the rule entry on implementation PR merge, not on design-doc merge).

## Rollback

`git revert` of the design-doc + delete the bd issue. No code change in this PR; rollback is text-only. Implementation PR (follow-up) has its own rollback path.
