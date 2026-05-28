# Keiracom System — Cross-encoder reranker sidecar (BAAI/bge-reranker-base)

Wave 2 dispatch `Agency_OS-0thg` (paired with Wave 1 Go sidecar `Agency_OS-2c7m`). Hindsight's recall layer fuses ANN + BM25 + graph + temporal hits into a top-50 candidate list; this sidecar reranks them with a cross-encoder so the LLM context window only spends tokens on the 5..10 candidates that actually answer the query. Same TEI deployment pattern as the embeddings sidecar at `../embeddings/`.

## What's here

| Path | Purpose |
|---|---|
| `docker-compose.reranker.yml` | TEI container — `BAAI/bge-reranker-base`, CPU image, model-cache volume, healthcheck, restart policy |
| `keiracom-reranker-sidecar.service` | systemd unit wrapping `docker compose up` — same shape as Wave 1 Go sidecar unit |
| `scripts/install_reranker_sidecar.sh` | Idempotent bring-up + `/health` + `/info` lineage check + `/rerank` round-trip probe |
| `scripts/install-systemd.sh` | Idempotent install + enable + restart of the systemd unit |
| `../../src/keiracom_system/reranker/reranker_client.py` | Stdlib-only Python client (`RerankerClient.rerank(query, texts, top_k=10)`) |
| `../../tests/keiracom_system/reranker/test_reranker_client.py` | 18 unit + 1 integration test (opt-in via `KEIRACOM_RERANKER_INTEGRATION=1`) |

## Quick start

```bash
# Bring up the sidecar (idempotent — re-run safe)
bash infra/keiracom_system/reranker/scripts/install_reranker_sidecar.sh \
  --project-name keiracom-reranker-<tenant_id>

# Live smoke test
curl -fsS -X POST http://localhost:8091/rerank \
  -H 'content-type: application/json' \
  -d '{"query":"what is rust","texts":["rust is a programming language","cats meow"]}'

# Configure callers (Hindsight reranker stage, retrieval orchestrator, etc.)
export KEIRACOM_RERANKER_URL=http://reranker:80
```

## Install as systemd service

```bash
bash infra/keiracom_system/reranker/scripts/install-systemd.sh
systemctl --user status keiracom-reranker-sidecar
```

## Integration with the retrieval pipeline

Hindsight's recall layer returns the top-50 hits per `src/retrieval/orchestrator.py`. The reranker stage feeds the same query + the top-50 candidate texts into `RerankerClient.rerank(...)`; the orchestrator keeps the top-`k_returned` (5..10 by default) before constructing the LLM context.

```python
from src.keiracom_system.reranker import RerankerClient

client = RerankerClient(base_url="http://reranker:80")
hits = client.rerank(query, candidate_texts, top_k=10)
top_indices = [h.index for h in hits]
```

`RerankerClient.healthy()` lets callers degrade gracefully when the sidecar is unreachable — falling back to the raw ANN-score order is documented as the bypass path in `src/retrieval/orchestrator.py`. Callers that want defence-in-depth on model identity call `verify_model_lineage()` once at startup.

## Wave 2 dispatch deliverables (Agency_OS-0thg)

1. **Cross-encoder reranker sidecar** — TEI server bound to `BAAI/bge-reranker-base`, on port `8091` (8090 is Weaviate on the fleet host; `8080` is the embeddings sidecar — all three coexist).
2. **Same deployment pattern as Wave 1** — `keiracom-reranker-sidecar.service` user-scope systemd unit + `scripts/install-systemd.sh`. Restart policy `on-failure`, append-only log to `~/clawd/logs/keiracom-reranker-sidecar.log`.
3. **`/rerank` endpoint** — TEI exposes it natively (`POST /rerank` with `{query, texts}`); the Python client wraps it with input validation, score-sort, top-k truncation, and lineage verification.
4. **Recall top-50 → reranker → top 5..10** — the client's `top_k` parameter defaults to 10; orchestrator caller is responsible for passing in the top-50 ANN-fused candidates.

## Vector / model lineage pin

Model: `BAAI/bge-reranker-base` — ~278MB cross-encoder, MIT licence. Pinned in:
- `docker-compose.reranker.yml` `--model-id` flag
- `scripts/install_reranker_sidecar.sh` `EXPECTED_MODEL` env default
- `src/keiracom_system/reranker/reranker_client.EXPECTED_MODEL_ID`
- the `test_default_expected_model_id_constant` unit test

Any accidental swap during a TEI upgrade fails loud at `RerankerClient.verify_model_lineage()` rather than silently regressing relevance downstream of recall.
