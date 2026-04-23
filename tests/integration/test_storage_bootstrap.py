from __future__ import annotations

import sqlite3
from pathlib import Path

from core.db import Database, DatabaseConfig
from core.storage_manager import StorageManager


def test_storage_bootstrap_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "database.db"
    storage = StorageManager(Database(DatabaseConfig(path=database_path)))

    storage.initialize()
    storage.initialize()

    with sqlite3.connect(database_path) as connection:
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]

    assert table_count >= 7
