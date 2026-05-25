# Keiracom System — TEI sidecar (BGE-small-en-v1.5 embeddings)

Phase 2 build wave 2 item 2. Path 3 from PR #1127 — TEI sidecar serving the same `BAAI/bge-small-en-v1.5` model fastembed default uses. Zero upstream Hindsight changes; ships V1 with full BYOK-sovereign + dimension-from-model contract per `ceo:memory_abstraction_layer_v1` eleven_agreed_positions #1.

## What's here

| Path | Purpose |
|---|---|
| `docker-compose.tei.yml` | Per-tenant sidecar — CPU image, named volume for model cache, healthcheck, restart policy |
| `scripts/install_tei_sidecar.sh` | Idempotent bring-up + health + model-lineage + /embed round-trip verify |
| `../../src/keiracom_system/embeddings/tei_client.py` | Thin stdlib-only Python client (urllib transport, swappable for httpx/requests via injection) |
| `../../tests/keiracom_system/embeddings/test_tei_client.py` | 14 unit + 1 integration test (opt-in via `KEIRACOM_TEI_INTEGRATION=1`) |

## Quick start

```bash
# Bring up sidecar (per-tenant docker-compose project)
bash infra/keiracom_system/embeddings/scripts/install_tei_sidecar.sh --project-name keiracom-tei-<tenant_id>

# Configure Hindsight to use it
export HINDSIGHT_API_EMBEDDINGS_PROVIDER=tei
export HINDSIGHT_API_EMBEDDINGS_TEI_URL=http://embed:80

# Verify integration tests pass against live sidecar
KEIRACOM_TEI_INTEGRATION=1 python3 -m pytest tests/keiracom_system/embeddings/
```

## Path 3 (this PR) vs Path 1 (upstream PR)

- **Path 3 ships V1** — uses Hindsight's existing `provider=tei` config. TEI serves the same model fastembed targets. No upstream PR needed. Diverges from the literal "fastembed default" canonical-key phrasing but preserves the dimension-from-model + BYOK-sovereign contracts.
- **Path 1 is the long-term canonical fix** — upstream PR to `vectorize-io/hindsight` adding native `FastembedEmbeddings` provider. ~150-200 LoC + tests; 1-4 week review cycle. **Filed as separate P2 KEI** to track upstream work.
- **Transition** — at Path 1 landing, switch deployment config `HINDSIGHT_API_EMBEDDINGS_PROVIDER=tei` → `fastembed`. Config-only change; no schema migration (same dimension, same model lineage).

## Vector lineage pin

Model: `BAAI/bge-small-en-v1.5` — 384 dims, MIT licence, ~33MB ONNX.

Pinning the model id everywhere (compose command, install script verify step, `EXPECTED_MODEL_ID` constant in `tei_client.py`, `test_client_defaults_match_canonical_key` test) so any accidental upgrade or swap fails loudly rather than silently drifting the pgvector schema dimension downstream in Hindsight.
