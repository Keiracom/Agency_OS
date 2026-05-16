"""Local-CPU embedding model singleton.

Picks `BAAI/bge-small-en-v1.5` per Scout's design spec (§4): 384-dim, runs
on CPU, no API spend, no cross-vendor data exfil. The model is lazily
loaded on first call to `get_embed_model()` so import-time cost stays
zero (matters for the 200ms cold-start budget mentioned in §6).

Override via env `AGENCY_OS_EMBEDDING_MODEL` for tests or migration to
a different local model. Switching to OpenAI's text-embedding-3-small is
deliberately not supported here — that decision belongs at the design
layer, not the runtime layer.
"""

from __future__ import annotations

import os
import threading
from typing import Any

_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
_EMBED_MODEL: Any | None = None
_LOCK = threading.Lock()


def _resolve_model_name() -> str:
    return os.environ.get("AGENCY_OS_EMBEDDING_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL


def get_embed_model() -> Any:
    """Return a process-global HuggingFaceEmbedding instance."""
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    with _LOCK:
        if _EMBED_MODEL is not None:
            return _EMBED_MODEL
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        _EMBED_MODEL = HuggingFaceEmbedding(model_name=_resolve_model_name())
        return _EMBED_MODEL


def reset_embed_model() -> None:
    """Test-only: drop the cached model so the next call re-resolves env."""
    global _EMBED_MODEL
    with _LOCK:
        _EMBED_MODEL = None
