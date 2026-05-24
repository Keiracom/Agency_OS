"""tei_client.py — thin Python client for the TEI sidecar.

Phase 2 build wave 2 item 2 per Dave-ratified MAL V1
(ceo:memory_abstraction_layer_v1).

CANONICAL KEY ANCHOR — eleven_agreed_positions #1 (verbatim):

  "Embedding model: BGE-small-en-v1.5 (fastembed default lineage, BYOK-
   sovereign, dimension-from-model). V1 implementation: TEI sidecar serving
   BGE-small-en-v1.5 in tenant deployment (zero upstream Hindsight changes;
   Path 3 per Orion PR #1127). Future canonical fix: Path 1 upstream PR to
   Hindsight adding native fastembed provider (~1d implementation + 1-4wk
   upstream review). Per-customer optional upgrade path retained (e.g.
   OpenAI key on customer's own key)."

CONSUMERS:
  - Atlas's Hindsight wrapper layer (in parallel build) — wraps Hindsight's
    Embeddings ABC such that calls route through TEI when configured.
  - KeiracomTenantExtension (PR #1132 merged) — does NOT call this client
    directly; embedding-provider config (env vars + URL) is read by
    Hindsight's RemoteTEIEmbeddings (see PR #1127 §3.2).

API contract (TEI server, per https://huggingface.co/docs/text-embeddings-inference):
  - POST /embed   → request: {"inputs": [str, ...]}; response: [[float, ...], ...]
  - GET  /health  → 200 OK when model loaded
  - GET  /info    → {"model_id": str, "model_type": str, ...}

USAGE:
    client = TEIClient(base_url="http://embed:80")
    vectors = client.embed(["text one", "text two"])   # list[list[float]], 384-dim each
    assert client.dimension == 384
    assert client.healthy()

TESTABILITY: `http_post` + `http_get` are injectable so unit tests don't need
a live TEI container or `httpx`/`requests` in the test path. Integration tests
hit a real running TEI sidecar — skipped when KEIRACOM_TEI_INTEGRATION env
unset, same skip pattern as tests/governance/test_ceo_memory_context_constraint.py.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

DEFAULT_BASE_URL = "http://embed:80"
DEFAULT_MODEL_DIM = 384  # BGE-small-en-v1.5 — pinned per canonical key position 1.
DEFAULT_TIMEOUT_SECONDS = 30
EXPECTED_MODEL_ID = "BAAI/bge-small-en-v1.5"

log = logging.getLogger(__name__)

HTTPGetFn = Callable[[str, float], "_HTTPResponse"]
HTTPPostFn = Callable[[str, dict[str, Any], float], "_HTTPResponse"]


class TEIClientError(RuntimeError):
    """Raised on any TEI-side or transport error."""


class _HTTPResponse:
    """Minimal response shape — status_code + json() — that both stdlib
    urllib and a real httpx.Response can adapt to.
    """

    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8") or "null")

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")


def _default_http_get(url: str, timeout: float) -> _HTTPResponse:
    """Stdlib urllib GET — keeps the module dependency-free.

    Production deployments can inject httpx.get or requests.get for
    connection-pooling + HTTP/2 if needed.
    """
    import urllib.request

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted localhost URL
        return _HTTPResponse(status_code=resp.status, body=resp.read())


def _default_http_post(url: str, payload: dict[str, Any], timeout: float) -> _HTTPResponse:
    """Stdlib urllib POST."""
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return _HTTPResponse(status_code=resp.status, body=resp.read())


class TEIClient:
    """Thin client for the TEI HTTP embedding API.

    Holds connection metadata + injected HTTP transports. Does NOT cache
    vectors — caller's responsibility (Hindsight's bank-level cache covers it).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        http_get: HTTPGetFn | None = None,
        http_post: HTTPPostFn | None = None,
        expected_dim: int = DEFAULT_MODEL_DIM,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.dimension = expected_dim
        self._http_get = http_get or _default_http_get
        self._http_post = http_post or _default_http_post

    def healthy(self) -> bool:
        """True iff GET /health returns 200 OK. Fail-closed on any error."""
        try:
            resp = self._http_get(f"{self.base_url}/health", self.timeout)
            return resp.status_code == 200
        except Exception as exc:
            log.warning("TEIClient.healthy: %s", exc)
            return False

    def info(self) -> dict[str, Any]:
        """GET /info — returns {model_id, model_type, ...}. Raises on transport error."""
        try:
            resp = self._http_get(f"{self.base_url}/info", self.timeout)
        except Exception as exc:
            raise TEIClientError(f"info: transport error: {exc}") from exc
        if resp.status_code != 200:
            raise TEIClientError(f"info: HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """POST /embed → list of dimension-`self.dimension` vectors.

        Validates:
          - empty input list returns empty output (no HTTP call)
          - response shape matches len(texts)
          - each vector matches self.dimension
        """
        if not texts:
            return []
        if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
            raise TEIClientError(f"embed: texts must be list[str], got {type(texts).__name__}")

        payload = {"inputs": texts}
        try:
            resp = self._http_post(f"{self.base_url}/embed", payload, self.timeout)
        except Exception as exc:
            raise TEIClientError(f"embed: transport error: {exc}") from exc
        if resp.status_code != 200:
            raise TEIClientError(f"embed: HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if not isinstance(data, list) or len(data) != len(texts):
            raise TEIClientError(
                f"embed: response shape mismatch — got {len(data) if isinstance(data, list) else type(data).__name__} entries for {len(texts)} inputs"
            )
        for i, vec in enumerate(data):
            if not isinstance(vec, list) or len(vec) != self.dimension:
                raise TEIClientError(
                    f"embed: vector {i} has dimension {len(vec) if isinstance(vec, list) else 'non-list'}; expected {self.dimension}"
                )
        return data

    def verify_model_lineage(self, expected_model_id: str = EXPECTED_MODEL_ID) -> None:
        """Defence-in-depth: assert the loaded model is the expected one.

        Catches accidental model swaps at TEI container upgrade time
        (different model = different vector dimensions = silent schema drift).
        Raises TEIClientError if mismatch.
        """
        info = self.info()
        actual = info.get("model_id", "")
        if actual != expected_model_id:
            raise TEIClientError(
                f"verify_model_lineage: TEI loaded {actual!r}; expected {expected_model_id!r}. "
                f"Vector lineage diverged — Hindsight schema dimension assumes {self.dimension}."
            )
