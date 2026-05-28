"""Shared retrieval dataclasses.

Extracted from ``agent_query`` to break the ``agent_query`` ↔ ``overrides``
import cycle (CodeQL py/cyclic-import): ``overrides`` needs the ``Citation``
type, and ``agent_query`` imports ``overrides`` — importing ``Citation`` from
here instead of from ``agent_query`` removes the back-edge. This module holds
no logic and imports nothing else from ``src.retrieval``, so any module can
depend on it without forming a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    source_id: str
    collection: str
    score: float
    excerpt: str
    parent_path: str = ""
