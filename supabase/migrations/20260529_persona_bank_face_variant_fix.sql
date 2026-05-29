-- 20260529_persona_bank_face_variant_fix.sql
-- Removes the persona_bank shape asymmetry that would 404 chain_orchestrator
-- on Face spawns. Pre-fix the face row stored variant=NULL while all other
-- callsign rows stored variant=<callsign>; a uniform caller pattern
-- (variant=callsign for every role) would miss face. 1-row UPDATE, idempotent.
--
-- Pre-fix:   (role='face', tier='standard', variant=NULL)
-- Post-fix:  (role='face', tier='standard', variant='face')
--
-- After this lands every persona_bank lookup is uniform: callers always pass
-- variant=<callsign>. The src/dispatcher/main.py::_fetch_persona handler's
-- IS NULL branch stays (still serves any future single-variant role) but is
-- not on the V1 chain path. UNIQUE(role,tier,variant) is preserved.
--
-- Idempotent: the WHERE-IS-NULL guard makes re-applies a no-op once the row
-- has been flipped to variant='face'.

BEGIN;

UPDATE public.persona_bank
SET variant = 'face'
WHERE role = 'face' AND tier = 'standard' AND variant IS NULL;

COMMIT;
