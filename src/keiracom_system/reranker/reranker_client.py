"""reranker_client.py — thin Python client for the cross-encoder reranker sidecar.

Wave 2 dispatch Agency_OS-0thg. Hindsight's recall layer fuses ANN + BM25 +
graph + temporal hits into a top-50 candidate list. This client posts that
list (with the original query) to the TEI /rerank endpoint and returns the
candidates sorted by cross-encoder relevance score — caller typically keeps
the top 5..10 for the LLM context.

API contract (TEI /rerank, per HuggingFace text-embeddings-inference docs):
  POST /rerank
    body: {"query": str, "texts": [str, ...]}
    response: [{"index": int, "score": float, "text": str|null}, ...]
  GET /health  → 200 OK when model loaded
  GET /info    → {"model_id": str, "model_type": "Reranker", ...}

Mirrors src/keiracom_system/embeddings/tei_client.py — same injectable
HTTP transport pattern so unit tests don't need a live TEI container.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# TEI host port. "http://reranker:80" only resolves inside the Docker network;
# host-process callers (Hindsight) must reach the published port on localhost.
# 8091 (not 8090): Weaviate owns 8090 on the fleet host — see
# docker-compose.reranker.yml port mapping.
DEFAULT_BASE_URL = "http://localhost:8091"
DEFAULT_TIMEOUT_SECONDS = 30
EXPECTED_MODEL_ID = "BAAI/bge-reranker-base"
DEFAULT_TOP_K_RETURNED = 10
DEFAULT_TOP_K_INPUT = 50  # Hindsight recall returns this many candidates.

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RerankHit:
    """One reranked candidate. `index` indexes back into the caller's texts list."""

    index: int
    score: float
    text: str | None = None


class RerankClientError(RuntimeError):
    """Raised on any reranker-side or transport error."""


class _HTTPResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8") or "null")

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")


HTTPGetFn = Callable[[str, float], _HTTPResponse]
HTTPPostFn = Callable[[str, dict[str, Any], float], _HTTPResponse]


def _default_http_get(url: str, timeout: float) -> _HTTPResponse:
    import urllib.request

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted localhost URL
        return _HTTPResponse(status_code=resp.status, body=resp.read())


def _default_http_post(url: str, payload: dict[str, Any], timeout: float) -> _HTTPResponse:
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


class RerankerClient:
    """Thin client for the TEI HTTP reranker API.

    Caller is responsible for assembling the candidate text list from the
    recall layer (Hindsight's bank-level cache covers caching).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        http_get: HTTPGetFn | None = None,
        http_post: HTTPPostFn | None = None,
        expected_model_id: str = EXPECTED_MODEL_ID,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.expected_model_id = expected_model_id
        self._http_get = http_get or _default_http_get
        self._http_post = http_post or _default_http_post

    def healthy(self) -> bool:
        """True iff GET /health returns 200 OK. Fail-closed on any error."""
        try:
            resp = self._http_get(f"{self.base_url}/health", self.timeout)
            return resp.status_code == 200
        except Exception as exc:
            log.warning("RerankerClient.healthy: %s", exc)
            return False

    def info(self) -> dict[str, Any]:
        """GET /info → {model_id, model_type, ...}. Raises on transport error."""
        try:
            resp = self._http_get(f"{self.base_url}/info", self.timeout)
        except Exception as exc:
            raise RerankClientError(f"info: transport error: {exc}") from exc
        if resp.status_code != 200:
            raise RerankClientError(f"info: HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def verify_model_lineage(self) -> None:
        """Defence-in-depth: assert the loaded model matches expected_model_id.

        Catches accidental model swaps at TEI container upgrade time. A
        different reranker = different relevance distribution = silent
        quality regression downstream of recall.
        """
        info = self.info()
        actual = info.get("model_id", "")
        if actual != self.expected_model_id:
            raise RerankClientError(
                f"verify_model_lineage: reranker loaded {actual!r}; "
                f"expected {self.expected_model_id!r}."
            )

    def rerank(
        self,
        query: str,
        texts: list[str],
        top_k: int = DEFAULT_TOP_K_RETURNED,
        return_text: bool = False,
    ) -> list[RerankHit]:
        """POST /rerank, return at most top_k hits sorted by descending score.

        Validates:
          - empty texts returns []
          - all entries in texts are str
          - response shape (list of {index, score})
          - returned indices are within range of texts
        """
        if not texts:
            return []
        if not isinstance(query, str) or not query:
            raise RerankClientError("rerank: query must be a non-empty string")
        if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
            raise RerankClientError(f"rerank: texts must be list[str], got {type(texts).__name__}")
        if top_k < 1:
            raise RerankClientError(f"rerank: top_k must be >= 1, got {top_k}")

        payload: dict[str, Any] = {"query": query, "texts": texts, "return_text": return_text}
        try:
            resp = self._http_post(f"{self.base_url}/rerank", payload, self.timeout)
        except Exception as exc:
            raise RerankClientError(f"rerank: transport error: {exc}") from exc
        if resp.status_code != 200:
            raise RerankClientError(f"rerank: HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if not isinstance(data, list):
            raise RerankClientError(f"rerank: response not a list, got {type(data).__name__}")

        hits = self._parse_hits(data, n_texts=len(texts))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    @staticmethod
    def _parse_hits(data: list[Any], n_texts: int) -> list[RerankHit]:
        out: list[RerankHit] = []
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                raise RerankClientError(f"rerank: row {i} not a dict")
            idx = row.get("index")
            score = row.get("score")
            if not isinstance(idx, int) or not (0 <= idx < n_texts):
                raise RerankClientError(f"rerank: row {i} index {idx} out of range [0, {n_texts})")
            if not isinstance(score, (int, float)):
                raise RerankClientError(
                    f"rerank: row {i} score is not numeric: {type(score).__name__}"
                )
            text = row.get("text") if isinstance(row.get("text"), str) else None
            out.append(RerankHit(index=int(idx), score=float(score), text=text))
        return out
