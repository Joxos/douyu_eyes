from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

import backend.main as main_mod


class _FakeResult:
    def __init__(self, row: dict[str, object]):
        self._row = row

    def mappings(self) -> _FakeResult:
        return self

    def one(self) -> dict[str, object]:
        return self._row


class _FakeConnection:
    def __init__(
        self,
        row: dict[str, object],
        capture_stmt: Callable[[str], None],
    ):
        self._row = row
        self._capture_stmt = capture_stmt

    def execute(self, stmt: str, _params: dict[str, object]) -> _FakeResult:
        self._capture_stmt(stmt)
        return _FakeResult(self._row)


class _FakeSession:
    def __init__(
        self,
        _engine: object,
        row: dict[str, object],
        capture_stmt: Callable[[str], None],
    ):
        self._row = row
        self._capture_stmt = capture_stmt

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    def connection(self) -> _FakeConnection:
        return _FakeConnection(self._row, self._capture_stmt)


def test_current_minute_sql_uses_utc_window(monkeypatch):
    captured_sql: list[str] = []

    def capture_stmt(stmt: str) -> None:
        captured_sql.append(stmt)

    fake_row = {
        "minute_start": "2026-03-11T11:20:00+00:00",
        "minute_end": "2026-03-11T11:21:00+00:00",
        "count": 3,
    }

    original_import_module = main_mod.import_module

    def fake_import_module(name: str):
        if name == "sqlmodel":
            return SimpleNamespace(
                Session=lambda engine: _FakeSession(engine, fake_row, capture_stmt)
            )
        if name == "sqlalchemy":
            return SimpleNamespace(text=lambda sql: sql)
        if name == "backend.db":
            return SimpleNamespace(
                get_engine=lambda: object(),
                ROOM_ID="6979222",
                MSG_TYPE="chatmsg",
            )
        return original_import_module(name)

    monkeypatch.setattr(main_mod, "import_module", fake_import_module)

    data = main_mod.get_current_minute_stats()

    assert data["count"] == 3
    assert captured_sql
    sql = captured_sql[0]
    assert "AT TIME ZONE 'UTC'" in sql
    assert "AT TIME ZONE 'Asia/Shanghai'" not in sql
