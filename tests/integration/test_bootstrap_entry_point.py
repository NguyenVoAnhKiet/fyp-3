from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

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
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin@1234")

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


def test_bootstrap_entry_point_requires_admin_credentials_for_fresh_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "missing-admin-env.db"
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("FACE_EMBEDDING_FERNET_KEY", "")

    with (
        patch("attendance_system.core.bootstrap.load_dotenv", return_value=False),
        pytest.raises(ValueError, match="ADMIN_USERNAME and ADMIN_PASSWORD"),
    ):
        main(["--database-path", str(database_path)])

    with sqlite3.connect(database_path) as connection:
        has_admin_table = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name = 'admin_credentials'"
        ).fetchone()[0]
        count = 0
        if has_admin_table:
            count = connection.execute(
                "SELECT COUNT(*) FROM admin_credentials"
            ).fetchone()[0]
    assert count == 0
