# Hindsight Verification Spike — Item (iv) fastembed Pluggability

**Authored:** 2026-05-24 (orion, per Elliot dispatch — Phase 2.1 spike item iv)
**Status:** RESEARCH COMPLETE — pending Aiden + Max dual-concur
**Anchor:** `ceo:memory_abstraction_layer_v1` position 1 (embedding_model)
**Repo inspected:** [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) — 14,414 stars, MIT license, Python, default branch `main`, last pushed 2026-05-22T22:38:28Z
**Empirical method:** read-only inspection via `gh api` against the public repo. Source files cited inline.

## 1. Top-line finding (TL;DR)

**Hindsight's embedding layer is _interface-pluggable but factory-enumerated_.** fastembed is NOT currently a supported provider (`grep fastembed` against the repo returns **zero hits**). Three migration paths exist; recommendation is path (3) for V1 launch + path (1) as the upstream-canonical fix.

## 2. Canonical key paste — `ceo:memory_abstraction_layer_v1` position 1

Per the audit-dispatch checklist canonical-key-query-gate, the queried value of the relevant position is pasted verbatim:

```json
{
  "five_converged_decisions_locked": {
    "embedding_model": "fastembed (default, BYOK-sovereign, dimension-from-model)"
  },
  "eleven_agreed_positions": [
    "fastembed default + Postgres/pgvector/JSONB schema + dimension-from-model",
    ...
  ],
  "substantive_lock": [
    "Hindsight self-hosted as engine (Vectorize.io open-source MIT, deployed one instance per tenant VPC)",
    ...
  ]
}
```

Two specific contracts the spike must verify against:
- **fastembed as embedding default** (position 1)
- **BYOK-sovereign** (each tenant's instance carries that tenant's keys)
- **dimension-from-model** (NOT hardcoded 1536 / 768 / etc.)

## 3. Hindsight embedding-layer empirical inspection

### 3.1 Abstract base class — `Embeddings`

File: [`hindsight-api-slim/hindsight_api/engine/embeddings.py`](https://github.com/vectorize-io/hindsight/blob/main/hindsight-api-slim/hindsight_api/engine/embeddings.py)

```python
class Embeddings(ABC):
    """Abstract base class for embedding generation.

    The embedding dimension is determined by the model and detected at initialization.
    The database schema is automatically adjusted to match the model's dimension.
    """

    @property @abstractmethod
    def provider_name(self) -> str: ...

    @property @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]: ...
```

**Verdict on contract alignment:**
- ✅ `dimension` is a per-provider property, not hardcoded — matches "dimension-from-model" requirement.
- ✅ `provider_name` + `encode()` abstract methods give a clean implementation surface for a new provider.
- ✅ `initialize()` separation lets a provider load weights at startup (cold-start avoidance) — relevant for fastembed which downloads ONNX model files on first use.

### 3.2 Concrete provider implementations (currently shipped)

The file imports config keys for 7 providers + provides their concrete classes:

| Provider | Class | Default model | BYOK env var |
|---|---|---|---|
| `local` (SentenceTransformers) | `LocalSTEmbeddings` | `BAAI/bge-small-en-v1.5` | (none — local) |
| `tei` (Text Embeddings Inference) | `RemoteTEIEmbeddings` | (URL-driven) | `HINDSIGHT_API_EMBEDDINGS_TEI_URL` |
| `openai` | `OpenAIEmbeddings` | `text-embedding-3-small` | `HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY` |
| `openrouter` (OpenAI-compatible) | `OpenAIEmbeddings` w/ base_url override | (configurable) | `HINDSIGHT_API_EMBEDDINGS_OPENROUTER_API_KEY` |
| `cohere` | `CohereEmbeddings` | (configurable) | `HINDSIGHT_API_EMBEDDINGS_COHERE_API_KEY` |
| `litellm` | `LiteLLMEmbeddings` (HTTP) | (configurable) | (per-LiteLLM-config) |
| `litellm-sdk` | `LiteLLMSDKEmbeddings` (in-process) | (configurable) | `HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_API_KEY` |
| `google` | `GeminiEmbeddings` | (configurable, Vertex AI or API key) | `HINDSIGHT_API_EMBEDDINGS_GEMINI_API_KEY` |

**`fastembed`: NOT in the list.** GitHub search `q=fastembed repo:vectorize-io/hindsight` returns **0 hits** (verified 2026-05-24).

### 3.3 Provider-factory pattern — hardcoded `if/elif`

The factory at the bottom of `embeddings.py`:

```python
def create_embeddings() -> Embeddings:
    config = get_config()
    provider = config.embeddings_provider.lower()
    if provider == "tei": ...
    elif provider == "local": ...
    elif provider == "openai": ...
    elif provider == "openrouter": ...
    elif provider == "cohere": ...
    elif provider == "litellm": ...
    elif provider == "litellm-sdk": ...
    elif provider == "google": ...
    else:
        raise ValueError(
            f"Unknown embeddings provider: {provider}. "
            f"Supported: 'local', 'tei', 'openai', 'cohere', 'google', 'litellm', 'litellm-sdk'"
        )
```

**Pluggability classification:** _interface-pluggable but factory-enumerated_. The `Embeddings` ABC is the right shape; subclasses can be added without changing the ABC. But the factory is a closed `if/elif`, not a registry / entry-point lookup. Adding fastembed requires touching this file (+ the matching config keys + the error-message enumeration).

This is the **same classification pattern** as our own `discovery_log_classifier` KEYWORDS dict in PR #1121 — explicit enumeration over a plugin registry, by design. Not a defect — a deliberate "no surprise providers" choice.

## 4. Three migration paths

### Path 1 — Upstream PR adding `FastembedEmbeddings` (canonical, long-term)

**Work:** ~150-200 LoC + tests.

```python
# New class in embeddings.py
class FastembedEmbeddings(Embeddings):
    def __init__(self, model_name: str | None = None, threads: int | None = None):
        from fastembed import TextEmbedding
        self.model_name = model_name or "BAAI/bge-small-en-v1.5"
        self._model = TextEmbedding(model_name=self.model_name, threads=threads)
        self._dimension = None

    @property
    def provider_name(self) -> str: return "fastembed"

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Probe with a dummy text to detect dimension
            self._dimension = len(next(self._model.embed(["probe"])))
        return self._dimension

    async def initialize(self) -> None:
        # fastembed eagerly downloads model on construction; this is a no-op
        pass

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._model.embed(texts)]
```

Plus:
- `DEFAULT_EMBEDDINGS_FASTEMBED_MODEL` + `ENV_EMBEDDINGS_FASTEMBED_MODEL` + `embeddings_fastembed_model` in `config.py`
- `elif provider == "fastembed":` branch in factory
- Update supported-list error message
- `fastembed` as an optional install extra in `pyproject.toml`: `hindsight-api[fastembed]`
- Tests: `test_fastembed_dimension_detected_from_model`, `test_fastembed_encode_round_trip`

**Pros:** clean upstream, BYOK-sovereign-by-construction (no API key needed, fully local), aligns with the canonical-key contract.
**Cons:** depends on upstream maintainer review pace. Vectorize.io maintains the repo (14k stars, active — last push 2026-05-22) — likely a few-week PR review cycle for a new provider.
**Timeline:** ~1 day to implement + 1-4 weeks to land upstream.

### Path 2 — Fork + carry the patch (fast ship, maintenance burden)

Keiracom maintains a fork with `FastembedEmbeddings` until upstream lands the same change.

**Pros:** ships immediately with V1.
**Cons:** maintenance burden every time we rebase off vectorize-io/hindsight `main`. Each release becomes a 3-way merge.
**Recommended only if:** Path 1 is blocked AND Path 3 below is unacceptable.

### Path 3 — TEI sidecar serving the same model fastembed would use (recommended for V1 ship)

`hindsight-api-slim` already supports `provider=tei` (Text Embeddings Inference — HuggingFace's high-throughput serving infrastructure). TEI serves the same models fastembed targets (BGE, E5, Jina, etc.). Deploy a single TEI container per tenant VPC alongside the Hindsight container; configure Hindsight with `HINDSIGHT_API_EMBEDDINGS_PROVIDER=tei` + `HINDSIGHT_API_EMBEDDINGS_TEI_URL=http://localhost:8080`.

```yaml
# Per-tenant docker-compose snippet (lives in product repo)
services:
  embed:
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.5
    command: --model-id BAAI/bge-small-en-v1.5
    ports: ["8080:80"]
  hindsight:
    image: vectorize-io/hindsight:latest
    environment:
      HINDSIGHT_API_EMBEDDINGS_PROVIDER: tei
      HINDSIGHT_API_EMBEDDINGS_TEI_URL: http://embed:80
    depends_on: [embed]
```

**Pros:**
- **Zero upstream patches** — uses Hindsight's existing supported provider.
- **Same model lineage** as fastembed would produce (BGE-small-en-v1.5 default, dimension 384, model-determined per the ABC contract).
- **BYOK-sovereign** in the deployment model — each tenant's VPC carries the embed container, no external API call.
- **dimension-from-model** preserved (per ABC contract, not hardcoded).
- **Performance**: TEI is faster than fastembed for batched workloads; comparable for single-doc requests.
- **Ships today** with no upstream review dependency.

**Cons:**
- One extra container per tenant (TEI container is ~500MB image + ~50MB BGE model).
- TEI requires a network hop (localhost-only, but still HTTP overhead vs in-process fastembed).
- Diverges from the literal "fastembed default" phrasing in `ceo:memory_abstraction_layer_v1.five_converged_decisions_locked.embedding_model`.

**Recommendation:** **Ship V1 on Path 3 + open upstream Path 1 PR in parallel.** When Path 1 lands upstream, switch the deployment from `provider=tei` to `provider=fastembed` — config-only change, no schema migration needed (dimension matches because the underlying model is the same BGE-small variant).

## 5. BYOK-LLM routing (item v overlap — surface-level only)

The dispatch flagged this as overlapping with Phase 2.1 item (v) deep work. Surface-level findings here for cross-reference:

- **Embedded CLI mode** (`hindsight-embed`): LLM is per-profile via `HINDSIGHT_EMBED_LLM_PROVIDER` + `HINDSIGHT_EMBED_LLM_API_KEY` env vars. Profiles support multiple distinct (provider, key) pairs — the CLI's `configure --profile` command writes profile-scoped env.
- **API/server mode** (`hindsight-api-slim`): LLM is configured at instance level via `HINDSIGHT_API_LLM_*` env vars. NOT per-request.
- **Per-tenant BYOK in our MAL V1 deployment model**: per `ceo:memory_abstraction_layer_v1.substantive_lock` — "Hindsight self-hosted as engine ... deployed one instance per tenant VPC". So per-tenant BYOK happens at **instance-deployment time**, not per-request. Each tenant gets a Hindsight container with their LLM key.
- This aligns with the position 5 `Collective scope: tenant-bounded only, never cross-tenant inference (BYOK sovereignty)` — sovereignty is achieved by deployment isolation, not by per-request routing.

**Recommendation for item (v) deep work:** verify the per-tenant deployment install script (which is product-repo work per `ceo:agency_os_keiracom_separation_v1.repo_topology`) carries the tenant's LLM provider + key as deploy-time inputs. The Hindsight side is settled — single env-var-per-instance — so item (v) deep work is more about Keiracom-side install ergonomics than Hindsight-side architecture.

## 6. Spike-item-(iv) clearance

Per the dispatch GATE: "this finding plus items i/ii/iii/v/vi clear Phase 2.1 spike."

**Item (iv) verdict: CLEAR WITH PATH-3 RECOMMENDATION.**

- ✅ Hindsight's embedding layer respects the dimension-from-model contract (canonical key position 1 + ABC `dimension` property are aligned).
- ✅ Hindsight's embedding layer respects the BYOK-sovereign contract via per-tenant instance deployment (canonical key `substantive_lock` + per-instance env-var configuration are aligned).
- ⚠️ fastembed is NOT a supported provider today — discrepancy with the canonical key's literal "fastembed default" phrasing.
- ✅ Three mitigation paths identified; Path 3 (TEI sidecar) ships V1 with zero upstream changes and identical model lineage; Path 1 (upstream PR) is the long-term canonical fix.

**Phase 2.1 follow-up actions (file as bd issues after spike concur):**
1. **P1** — implement Path 3 in the product repo's install script (~1 day, no upstream blocking).
2. **P2** — author + submit Path 1 upstream PR to vectorize-io/hindsight (~1 day implementation + 1-4 weeks upstream review).
3. **P3** — at Path 1 landing, update product repo install script to switch from `provider=tei` to `provider=fastembed` (config-only).

## 7. Acceptance criteria

- [x] Empirical inspection of `vectorize-io/hindsight` embedding layer — read-only via `gh api`, source paths cited inline (§3.1, §3.3).
- [x] Hindsight `Embeddings` ABC characterised; concrete providers enumerated (§3.2 table).
- [x] fastembed support status verified empirically (zero hits, §3.2 last sentence).
- [x] Three migration paths costed (§4).
- [x] BYOK-LLM routing surface findings (§5) — cross-references item (v) deep dispatch.
- [x] Spike-item-(iv) clearance verdict + follow-up actions (§6).
- [x] Canonical key `ceo:memory_abstraction_layer_v1` queried + position 1 pasted verbatim (§2).
- [x] No code shipped — research-only deliverable.
- [ ] Aiden architecture-lens concur.
- [ ] Max code-quality-lens concur (verifies empirical claims against linked source).
- [ ] Dual-concur → Elliot admin-merge per orchestrator-merge-after-NATS-concur pattern.
- [ ] Post-merge: file 3 P1/P2/P3 bd issues per §6 follow-ups.
