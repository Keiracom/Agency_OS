"""Shared psycopg fakes for tests/api/webhooks/ — extracted per Sonar
new_duplicated_lines_density.

Single source of truth for the in-memory cursor/connection stand-ins that
intercept psycopg.connect() in webhook dispatch tests (test_linear_webhook_kei228,
test_linear_webhook_part1_title). Mirrors the tests/scripts/_db_mocks.py pattern.
"""

from __future__ import annotations

from typing import Any


class FakeCursor:
    """Minimal psycopg cursor stand-in. Records every execute() call in
    `executed` as [(sql, params), ...]."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...]]] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params or ()))


class FakeConn:
    """Minimal psycopg connection stand-in. Exposes a single FakeCursor via
    `_cur`; flips `committed` on commit()."""

    def __init__(self, raise_on_connect: bool = False) -> None:
        self._cur = FakeCursor()
        self.committed = False

    def __enter__(self) -> FakeConn:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cur

    def commit(self) -> None:
        self.committed = True
