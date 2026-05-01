-- Governance Phase 1 Track A — A3 Frozen-State Registry
-- Tracks files / paths that are temporarily off-limits to edits. The
-- Gatekeeper OPA policy queries this table on every completion-claim
-- and edit attempt; matching paths are denied until unfreeze_artifact
-- sets unfrozen_at.

CREATE TABLE IF NOT EXISTS public.frozen_artifacts (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_path text NOT NULL UNIQUE,
    frozen_by     text NOT NULL,
    frozen_at     timestamptz NOT NULL DEFAULT now(),
    reason        text,
    unfrozen_at   timestamptz NULL
);

-- Active-only lookup index — when an artifact is unfrozen we keep the
-- row for audit, but the gatekeeper only checks rows where unfrozen_at
-- is NULL.
CREATE INDEX IF NOT EXISTS frozen_artifacts_active_path_idx
    ON public.frozen_artifacts (artifact_path)
    WHERE unfrozen_at IS NULL;

CREATE INDEX IF NOT EXISTS frozen_artifacts_frozen_at_idx
    ON public.frozen_artifacts (frozen_at DESC);

COMMENT ON TABLE public.frozen_artifacts IS
    'Edit lock registry. unfrozen_at IS NULL means the artifact is currently frozen.';

COMMENT ON COLUMN public.frozen_artifacts.artifact_path IS
    'Repo-relative path or glob (use ** for tree matches, * for direct children only). Gatekeeper OPA policy matches edited files against this via glob.match with default "/" delimiters.';
