-- KEI-97: add excluded_callsign column to public.tasks
-- Author-exclusion for REVIEW-PR tasks: the PR author cannot auto-claim
-- the review task for their own PR. bd ready filters this column out.

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS excluded_callsign TEXT;

COMMENT ON COLUMN public.tasks.excluded_callsign IS
  'KEI-97: callsign that cannot auto-claim this task (e.g. PR author for review tasks). bd ready filters where excluded_callsign IS NULL OR excluded_callsign != current_callsign.';
