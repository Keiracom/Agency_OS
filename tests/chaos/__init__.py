"""KEI-132 — chaos harness.

`tests/chaos/` runs every PR in a dedicated CI job. Failures BLOCK the PR
(no `|| true` mask). Purpose: catch real production failure modes (DB
stalls, network partitions, resource exhaustion) in CI before they hit
prod, without requiring a full chaos engineering platform.

Scope rules:
  - Tests must complete deterministically (no flaky waits, no real network).
  - Real-infrastructure scenarios (live DB, live Redis) are marked
    `@pytest.mark.chaos_db` / `@pytest.mark.chaos_redis` and skip when the
    backing service isn't reachable — CI runs the mock variants.
  - Each scenario must include a NEGATIVE control (happy path also passes
    under the chaos wrapper) so regressions in the wrapper itself surface.

See tests/chaos/README.md for the scenario catalogue and how to add new ones.
"""
