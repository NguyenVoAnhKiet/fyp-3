from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from attendance_system.core.bootstrap import main


def test_bootstrap_entry_point_initializes_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "attendance.db"

    # Prevent load_dotenv() inside main() from polluting the process
    # environment with FACE_EMBEDDING_FERNET_KEY (from .env), which would
    # break subsequent tests that rely on unencrypted embedding bytes.
    monkeypatch.setenv("FACE_EMBEDDING_FERNET_KEY", "")

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
