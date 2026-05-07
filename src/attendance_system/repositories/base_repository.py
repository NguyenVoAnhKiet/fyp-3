from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

from attendance_system.core.db import Database


class StorageError(RuntimeError):
    pass


class DuplicateAttendanceError(StorageError):
    pass


@dataclass(slots=True)
class BaseRepository:
    database: Database

    def _validate_query_and_parameters(self, query: str, parameters: Sequence[Any]) -> None:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("SQL query must be a non-empty string")
        if query.count("?") != len(parameters):
            raise ValueError("SQL parameter count does not match placeholders")
        for parameter in parameters:
            if not isinstance(parameter, (int, float, str, bytes, bool, type(None))):
                raise ValueError("Unsupported SQL parameter type")

    @staticmethod
    def require_positive_int(value: int, field_name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{field_name} must be a positive integer")

    @staticmethod
    def require_non_empty_text(value: str, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self.database.session() as connection:
            yield connection

    def fetch_one(self, query: str, parameters: Sequence[Any] = ()) -> sqlite3.Row | None:
        self._validate_query_and_parameters(query, parameters)
        with self.connection() as connection:
            return connection.execute(query, parameters).fetchone()

    def fetch_all(self, query: str, parameters: Sequence[Any] = ()) -> list[sqlite3.Row]:
        self._validate_query_and_parameters(query, parameters)
        with self.connection() as connection:
            return connection.execute(query, parameters).fetchall()

    def execute(self, query: str, parameters: Sequence[Any] = ()) -> int:
        self._validate_query_and_parameters(query, parameters)
        with self.connection() as connection:
            cursor = connection.execute(query, parameters)
            return cursor.lastrowid

