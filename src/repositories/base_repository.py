from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Sequence

from core.db import Database


class StorageError(RuntimeError):
    pass


class DuplicateAttendanceError(StorageError):
    pass


@dataclass(slots=True)
class BaseRepository:
    database: Database

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self.database.session() as connection:
            yield connection

    def fetch_one(self, query: str, parameters: Sequence[Any] = ()) -> sqlite3.Row | None:
        with self.connection() as connection:
            return connection.execute(query, parameters).fetchone()

    def fetch_all(self, query: str, parameters: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self.connection() as connection:
            return connection.execute(query, parameters).fetchall()

    def execute(self, query: str, parameters: Sequence[Any] = ()) -> int:
        with self.connection() as connection:
            cursor = connection.execute(query, parameters)
            return cursor.lastrowid

