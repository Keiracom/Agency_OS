"""Shared test fixtures for tests/scripts/ — psycopg connection + cursor mocks.

Extracted from test_tasks_cli.py + test_tool_call_logger.py per Sonar
new_duplicated_lines_density. Single source of truth for the in-memory
fakes that intercept psycopg.connect() in CLI/SDK script tests.
"""

from __future__ import annotations

from typing import Any


class FakeCursor:
    """Minimal psycopg cursor stand-in. Records the last execute() call;
    returns caller-provided fetchall_rows / fetchone_row.
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
        self.last_sql: str = ""
        self.last_params: tuple | None = None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.last_sql = sql
        self.last_params = params

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
