from __future__ import annotations

import sqlite3
from pathlib import Path

from attendance_system.core.bootstrap import main


def test_bootstrap_entry_point_initializes_database(tmp_path: Path) -> None:
    database_path = tmp_path / "attendance.db"

    exit_code = main(["--database-path", str(database_path)])

    assert exit_code == 0
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"users", "admin_credentials", "face_references", "sessions", "recognition_events", "attendance_records", "system_settings"}.issubset(table_names)
