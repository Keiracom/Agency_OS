"""Shared test fixtures for tests/scripts/ — psycopg connection + cursor mocks.

Extracted from test_tasks_cli.py + test_tool_call_logger.py per Sonar
new_duplicated_lines_density. Single source of truth for the in-memory
fakes that intercept psycopg.connect() in CLI/SDK script tests.
"""

from __future__ import annotations

from typing import Any


class FakeCursor:
    """Minimal psycopg cursor stand-in. Records every execute() call;
    `last_sql`/`last_params` point at the most recent call (backward-compat
    with tests that only need the last call); `executed` is the full
    [(sql, params), ...] history (used by tests that exercise multi-execute
    paths, e.g. KEI-61's mark_done which does UPDATE then INSERT).
    """

    def __init__(
        self,
        fetchall_rows: list[tuple] | None = None,
        fetchone_row: tuple | None = None,
        description: list[tuple] | None = None,
    ) -> None:
        self._all = fetchall_rows or []
        self._one = fetchone_row
        self.description = [type("col", (), {"name": c[0]})() for c in (description or [])]
        self.executed: list[tuple[str, tuple | None]] = []

    @property
    def last_sql(self) -> str:
        return self.executed[-1][0] if self.executed else ""

    @property
    def last_params(self) -> tuple | None:
        return self.executed[-1][1] if self.executed else None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[tuple]:
        return self._all

    def fetchone(self) -> tuple | None:
        return self._one

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


class FakeConn:
    """Minimal psycopg connection stand-in. Counts commits; returns the cursor."""

    def __init__(self, cur: FakeCursor) -> None:
        self._cur = cur
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return self._cur

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> FakeConn:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


def make_patch_connect(monkeypatch: Any) -> Any:
    """Return a builder fn that installs a fake psycopg.connect.

    Used as the body of test fixtures across tests/scripts/* to dedupe
    the `monkeypatch.setattr(psycopg, 'connect', ...)` boilerplate.
    Sets a placeholder DATABASE_URL so `_dsn()` succeeds when called.

        @pytest.fixture
        def patch_connect(mod, monkeypatch):
            return make_patch_connect(monkeypatch)
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    def _patch(cur: FakeCursor) -> FakeCursor:
        import psycopg

        monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: FakeConn(cur))
        return cur

    return _patch
