from __future__ import annotations

import sqlite3
from pathlib import Path

from attendance_system.core.db import Database, DatabaseConfig
from attendance_system.core.storage_manager import StorageManager


def test_storage_initialization_creates_required_tables_and_persists_data(tmp_path: Path) -> None:
    database_path = tmp_path / "database.db"
    storage_manager = StorageManager(Database(DatabaseConfig(path=database_path)))

    storage_manager.initialize()

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"users", "admin_credentials", "face_references", "sessions", "recognition_events", "attendance_records", "system_settings"}.issubset(table_names)

        connection.execute(
            "INSERT INTO system_settings(setting_key, setting_value, value_type, updated_at) VALUES (?, ?, ?, ?)",
            ("liveness_threshold", "0.5", "float", "2026-04-24T00:00:00Z"),
        )
        connection.commit()

    storage_manager.initialize()

    with sqlite3.connect(database_path) as connection:
        value = connection.execute(
            "SELECT setting_value FROM system_settings WHERE setting_key = ?",
            ("liveness_threshold",),
        ).fetchone()[0]

    assert value == "0.5"
