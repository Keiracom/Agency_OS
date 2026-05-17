-- KEI-151: ENFORCER abolished (Dave 2026-05-17)
-- Mechanical gates (phase-lock, SKIP LOCKED, verification trigger, CI gate,
-- Gate 2 evidence, Gate 4 heartbeat) now handle governance.
-- Advisory ENFORCER becomes dead code — deprecate all enforcer-enforced rules.

UPDATE public.governance_rules
SET
    active = false,
    deprecated_at = NOW(),
    deprecated_reason = 'Dave 2026-05-17 KEI-151 — ENFORCER abolished, mechanical gates handle governance',
    deprecated_by = 'elliot'
WHERE id IN (
    'rule-r2-coordinate',
    'rule-r3-evidence',
    'rule-r4-claim-before-touch',
    'rule-r6-citation',
    'rule-r8-dispatch-coordination',
    'rule-r9-directive-initiative',
    'rule-step-0-restate',
    'rule-three-way-concur',
    'rule-close-loop-to-ceo',
    'rule-kei-72-step-0-gate'
);
