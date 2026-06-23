from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from attendance_system.core.db import Database, DatabaseConfig
from attendance_system.core.storage_manager import StorageManager


def test_storage_bootstrap_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin@1234")

    database_path = tmp_path / "database.db"
    storage = StorageManager(Database(DatabaseConfig(path=database_path)))

    storage.initialize(admin_username="admin", admin_password="Admin@1234")
    storage.initialize(admin_username="admin", admin_password="Admin@1234")

    with sqlite3.connect(database_path) as connection:
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]

    assert table_count >= 7
