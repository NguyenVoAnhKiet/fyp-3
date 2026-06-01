from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

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


@patch("attendance_system.core.schema._migrate_attendance_records_cascade_to_setnull")
def test_attendance_records_migration_failure_logs_and_raises(
    mock_migrate,
    tmp_path: Path,
    caplog,
) -> None:
    """Migration failure must be logged and re-raised (no silent suppression)."""
    database_path = tmp_path / "migration_fail.db"
    storage_manager = StorageManager(Database(DatabaseConfig(path=database_path)))

    # Create schema first with old-style attendance_records (CASCADE)
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            face_registered INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            liveness_threshold_snapshot REAL NOT NULL,
            similarity_threshold_snapshot REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            UNIQUE (session_id, user_id),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.close()

    # Make the migration function raise
    mock_migrate.side_effect = RuntimeError("Simulated migration failure")

    # Act — initialize should log warning and propagate the exception
    with caplog.at_level(logging.WARNING, logger="attendance_system.core.schema"):
        with pytest.raises(RuntimeError, match="Simulated migration failure"):
            storage_manager.initialize()

    # Assert — error was logged
    assert any("MIGRATION" in record.message for record in caplog.records), (
        "Migration failure was not logged"
    )
