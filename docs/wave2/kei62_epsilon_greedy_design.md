# KEI-62 — Epsilon-greedy exploration for pull-model affinity routing (DESIGN)

**Author:** Max (design only — per Dave dispatch via Elliot ts ~1778721000)
**Linear:** [KEI-64](https://linear.app/keiracom/issue/KEI-64) (Dave's KEI-62, numbering offset +2)
**Beads:** Agency_OS-gsy — P1 IN_PROGRESS
**Path:** (C) DESIGN-DOC-FIRST per triple-bot ratify ts ~1778721280 (Elliot + Aiden + Max)
**Depends on:** [KEI-51 / Linear KEI-53](https://linear.app/keiracom/issue/KEI-53) (agent_profile Supabase schema, Aiden-lane)
**Self-applies:** `ceo:rule:no_build_without_linear_issue` — Linear KEI-64 transitioned Backlog → Todo + claim comment + bd claim Agency_OS-gsy BEFORE branch open.

## Dave verbatim (canonical source — Linear KEI-64 description)

> The personalised `bd ready --agent=[callsign]` system ranks KEIs by capability affinity. Over time, agents become hyper-specialised: Max's cognee affinity hits 0.99, Atlas's infrastructure affinity hits 0.99. When workload composition shifts (a sprint of React/Tailwind frontend work, or a period of heavy research), hyper-specialised agents sit idle or deprioritise critical work because their profile says they shouldn't touch it.
>
> This creates execution bottlenecks and single points of failure — if Max crashes during a Cognee sprint, no other agent has meaningful context to continue.

## Problem framing

Pull-model affinity routing (KEI-51) gives each agent a capability_weights map. Without exploration, weights asymptote to specialisation. Four failure modes:

1. **Sprint-shift starvation** — workload composition changes; specialists sit idle.
2. **Single point of failure** — specialist crashes, no cross-trained backup.
3. **Echo-chamber lock-in** — affinity → 1.0 → only affinity-domain claims → reinforces affinity. Positive-feedback runaway.
4. **Cold-start trap** — new domain has 0 affinity for everyone; no agent claims; KEI rots.

Epsilon-greedy + affinity-cap + skill-gap-detection breaks all four.

## Part 1 — Epsilon-greedy in bd_ready hook

```python
# scripts/orchestrator/bd_ready_personalised.py (post-KEI-51 ship)
import random

EXPLORATION_RATE = 0.20  # ~every 5th claim
EXPLORATION_PRIORITY_FLOOR = "HIGH"  # only HIGH/URGENT eligible for exploration
EXPLORATION_LIMIT = 3
EXPLOITATION_LIMIT = 10

def bd_ready(agent_callsign: str, claim_count: int) -> list[KEI]:
    if random.random() < EXPLORATION_RATE:
        return get_high_priority_unclaimed_keis(min_priority=EXPLORATION_PRIORITY_FLOOR, limit=EXPLORATION_LIMIT)
    return get_affinity_ranked_keis(agent_callsign, limit=EXPLOITATION_LIMIT)
```

**Design notes:**
- `random.random()` is non-cryptographic; statistical 20% is sufficient.
- Exploration limited to HIGH/URGENT priority — no wasted cross-training on LOW.
- `claim_count` parameter reserved for future logic (e.g. forced exploration after N exploitation claims).

## Part 2 — Affinity updater (on_bd_complete hook)

```python
# scripts/orchestrator/agent_profile_updater.py (post-KEI-51 ship)
NORMAL_INCREASE_FACTOR = 1.02
NORMAL_CAP = 0.99
EXPLORATION_INCREASE_FACTOR = 1.05
EXPLORATION_CAP = 0.80
INITIAL_WEIGHT = 0.1

def on_bd_complete(agent_callsign: str, kei_tags: list[str], was_exploration: bool) -> None:
    profile = get_agent_profile(agent_callsign)
    for tag in kei_tags:
        current = profile.capability_weights.get(tag, INITIAL_WEIGHT)
        if was_exploration:
            new_weight = min(current * EXPLORATION_INCREASE_FACTOR, EXPLORATION_CAP)
        else:
            new_weight = min(current * NORMAL_INCREASE_FACTOR, NORMAL_CAP)
        profile.capability_weights[tag] = new_weight
    update_agent_profile(agent_callsign, profile)
```

**Design notes:**
- Exploration completions get higher increase factor (5% vs 2%) but lower cap (0.80 vs 0.99).
- Cap differential prevents exploration domains from becoming hard specialisations (avoids re-creating the lock-in problem on cross-trained tags).
- `was_exploration` flag must be stored at claim time (in agent_profile.last_claim_was_exploration boolean or on the bd-claim record itself).

## Part 3 — Skill-gap detection (systemd timer + alerter)

```python
# scripts/orchestrator/skill_gap_check.py (systemd timer every 5min)
UNCLAIMED_THRESHOLD_MINUTES = 30
PROGRESSIVE_REDUCTION_PER_INTERVAL = 0.1
CEO_ALERT_THRESHOLD_MINUTES = 120

def skill_gap_check() -> None:
    urgent_unclaimed = get_keis_unclaimed_over(minutes=UNCLAIMED_THRESHOLD_MINUTES, min_priority="HIGH")
    for kei in urgent_unclaimed:
        elapsed = kei.minutes_unclaimed
        threshold_reduction = (elapsed // UNCLAIMED_THRESHOLD_MINUTES) * PROGRESSIVE_REDUCTION_PER_INTERVAL
        reassign_with_lowered_threshold(kei, threshold_reduction)
        if elapsed > CEO_ALERT_THRESHOLD_MINUTES:
            alert_ceo(f"KEI {kei.id} unclaimed for {elapsed} minutes — skill gap")
```

**Design notes:**
- Timer interval 5min, threshold 30min — matches KEI-45 idle-daemon cadence pattern (consistency reduces operator surprise).
- Progressive reduction: every 30min unclaimed lowers threshold by 0.1 → after 2hr, any agent with affinity > 0.0 eligible (effectively any agent).
- CEO alert at 2hr is the manual-intervention escalation.

## Part 4 — Affinity caps in profile schema

Hard ceilings prevent runaway specialisation:

| Cap | Value | Rationale |
|---|---|---|
| Normal-domain cap | 0.99 | Strong specialisation allowed; exploration roll still routes 20% away |
| Exploration-domain cap | 0.80 | Cross-trained but not so strong that exploration stops routing further |
| Initial weight | 0.10 | All-cold start; small chance to be picked + affinity-ranking visible |

Caps enforced inside `on_bd_complete` (Part 2). No separate enforcer; the `min(current * factor, cap)` line is the gate.

## KEI-51 schema requirements (Aiden-lane prerequisite)

Aiden's KEI-51 (Linear KEI-53) agent_profile Supabase migration should include these columns to support KEI-62:

```sql
CREATE TABLE public.agent_profile (
    callsign         TEXT PRIMARY KEY,
    capability_weights JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {tag: weight} map; KEI-62 reads/writes
    exploration_count INTEGER NOT NULL DEFAULT 0,            -- counter for telemetry; KEI-62 increments
    last_claim_was_exploration BOOLEAN,                      -- KEI-62 sets at claim time; reads at complete time
    last_explored_at TIMESTAMPTZ,                            -- last exploration claim timestamp (telemetry + cooldown if needed)
    skill_gap_alerts_received INTEGER NOT NULL DEFAULT 0,    -- count of CEO alerts this agent triggered (telemetry)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX agent_profile_callsign_idx ON public.agent_profile (callsign);
```

`capability_weights` JSONB shape: `{"cognee": 0.85, "infrastructure": 0.25, "frontend": 0.10, ...}` keyed by tag.

Per Aiden commitment ts ~1778721270, KEI-51 PR will include these fields; no stub-then-replace.

## Acceptance criteria (verbatim from Linear KEI-64)

1. **Exploration fires at ~20% rate** — 100-call statistical test (`scripts/test_kei62_exploration_rate.py` simulates 100 bd_ready calls, counts exploration-mode results, asserts 15 < count < 25 for 95% CI).
2. **Exploration claims complete successfully + update affinity correctly** — integration test claim → mark complete with `was_exploration=True` → assert capability_weight changed by `*1.05` and capped at 0.80.
3. **Skill-gap alert fires after 30min unclaimed HIGH/URGENT** — test creates HIGH-priority KEI with `created_at` 31min ago, runs `skill_gap_check()`, asserts alert function called.
4. **Affinity caps enforced** — unit test sets capability_weight to 0.8 on exploration tag + completes 5 more exploration claims; asserts weight stays at 0.8 (not 0.84).
5. **30-day operational target** — Supabase audit query 30 days post-ship: `SELECT callsign, jsonb_object_keys(capability_weights) FROM agent_profile WHERE jsonb_object_keys(capability_weights) AS k AND (capability_weights->>k)::float > 0.3 GROUP BY callsign HAVING COUNT(DISTINCT k) >= 3` — all 6 callsigns present.

## Sequencing chain

```
1. Max KEI-62 design doc (this PR)        ← Path (C), now
2. Aiden KEI-51 agent_profile schema       ← Aiden post PR #843 + #847 + KEI-55
   - Incorporates KEI-62 schema requirements verbatim (capability_weights + exploration_count + last_claim_was_exploration + last_explored_at + skill_gap_alerts_received)
3. Max KEI-62 algorithm implementation     ← Post KEI-51 ship
   - bd_ready_personalised.py + agent_profile_updater.py + skill_gap_check.py
   - 5-row acceptance test suite
   - systemd timer unit for skill_gap_check
```

## Out of scope (deferred KEIs)

- **KEI-51 / Linear KEI-53**: agent_profile schema + ingestion. Aiden-lane. Prerequisite for KEI-62 algorithm implementation.
- **KEI-49 / Linear KEI-51**: capability_weights initial seeding pipeline (load from bd-claim history + Linear historical assignments). Aiden-lane.
- **bd ready `--agent=` CLI flag**: today's `bd ready` doesn't take per-agent filter. Either KEI-51 piece OR separate small KEI.
- **Cryptographic exploration roll**: `random.random()` non-crypto is sufficient. If audit ever requires deterministic per-agent exploration seed, separate KEI.

## ceo_memory anchor

`ceo:rule:epsilon_greedy_exploration_pull_model` to be backfilled by Elliot per `ceo:rule:ceo_operational_directives_recorded` once this design doc ratifies via triple-bot + lands on main. Key value: pointer to this doc path + 4-part summary + acceptance signals.

## Compose with existing rules

- `ceo:rule:pull_model_task_claim` (ratified earlier today): KEI-62 is the exploration-policy half of the pull-model. Pull-claim atomic → affinity-rank-or-explore branch fires inside bd_ready.
- `ceo:rule:no_build_without_linear_issue`: self-applied (this design doc has Linear KEI-64 + bd Agency_OS-gsy filed BEFORE branch open).
- KEI-39 4-step claim protocol: applied to this doc itself (claim → Linear → [STARTING] → execute).
