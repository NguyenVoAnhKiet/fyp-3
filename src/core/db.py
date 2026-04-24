from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(slots=True)
class DatabaseConfig:
    path: Path
    timeout: float = 5.0

    def __post_init__(self) -> None:
        if any(part == ".." for part in self.path.parts):
            raise ValueError("Database path must not contain parent-directory traversal segments")


class Database:
    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config

    def connect(self) -> sqlite3.Connection:
        self.config.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.config.path,
            timeout=self.config.timeout,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
