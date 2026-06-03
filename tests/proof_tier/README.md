# Proof Tier — real dependencies, no mocks

Per `gate_roadmap.spike_real_deps_proof` (`10a369b2-…`, phase `1_nucleus`),
this tier runs acceptance checks against REAL dependencies (Testcontainers
Postgres / Weaviate / NATS), **not mocks**.

## Hard rules

1. **No mocks.** Importing `unittest.mock` (or any name aliased to
   `MagicMock`/`AsyncMock`/`Mock`/`patch`) inside `tests/proof_tier/**` is
   refused by `scripts/ci/check_banned_mocks.py`. The CI gate
   `.github/workflows/proof-tier-banned-mocks.yml` runs it on every PR.
2. **Real Postgres.** Tests in this directory spin up a throwaway Postgres
   container (Testcontainers) and apply the relevant migrations
   (`supabase/migrations/`) before exercising the gate.
3. **Verbatim RAISE.** Trigger-rejection tests capture the actual
   PostgreSQL exception message and assert on its text — not a Python-side
   shim. The `pytest -v` output is the proof_run artefact.
4. **Live-not-mock.** A pytest-only attestation (cf. the
   2026-06-03 product_proof_enforcement shape-only flip) does NOT satisfy
   this gate. The container evidence + verbatim RAISE is the proof.

## Acceptance (per `gate_roadmap.spike_real_deps_proof.proof_gate`)

- Live durable-gate rejection test runs against a real Postgres-backed gate
  and pastes the verbatim RAISE.
- A planted mock/stub in the proof tier is rejected by the banned-mocks CI
  check.

## How to run locally

```bash
# Docker daemon must be reachable
docker ps

# Run only the proof tier
PYTHONPATH=. python -m pytest tests/proof_tier/ -v
```

The Postgres container is reused across tests in one pytest session
(scope='session' fixture) for speed.
