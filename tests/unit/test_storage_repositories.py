from __future__ import annotations

import sqlite3

import pytest

from attendance_system.repositories.attendance_repository import AttendanceRepository
from attendance_system.repositories.face_reference_repository import FaceReferenceRepository
from attendance_system.repositories.session_repository import SessionRepository
from attendance_system.repositories.system_setting_repository import SystemSettingRepository
from attendance_system.repositories.user_repository import UserRepository


def test_user_repository_crud(database) -> None:
    users = UserRepository(database)

    user_id = users.create("SV001", "Nguyen Van A")

    row = users.get_by_id(user_id)
    assert row is not None
    assert row["student_id"] == "SV001"

    users.update(user_id, full_name="Nguyen Van A Updated", is_active=False)
    row = users.get_by_id(user_id)
    assert row["full_name"] == "Nguyen Van A Updated"
    assert row["is_active"] == 0


def test_system_setting_repository_upsert_and_get(database) -> None:
    settings = SystemSettingRepository(database)

    settings.upsert("liveness_threshold", "0.5", "float")
    settings.upsert("liveness_threshold", "0.7", "float")

    row = settings.get("liveness_threshold")
    assert row is not None
    assert row["setting_value"] == "0.7"


def test_face_reference_repository_persists_pose_embeddings(database) -> None:
    from attendance_system.repositories.face_reference_repository import POSE_LABELS

    users = UserRepository(database)
    faces = FaceReferenceRepository(database)

    user_id = users.create("SV002", "Nguyen Van B")
    pose_embeddings = {pose: f"{pose}-data".encode() for pose in POSE_LABELS}
    faces.replace_all(user_id, pose_embeddings, "model-v1", 8)

    rows = faces.get_by_user_id(user_id)
    assert len(rows) == 5
    for row in rows:
        assert row["embedding"] == f"{row['pose_label']}-data".encode()
        assert row["model_name"] == "model-v1"
        assert row["vector_length"] == 8

    # Single-pose lookup
    row = faces.get_by_user_id_and_pose(user_id, "center")
    assert row is not None
    assert row["embedding"] == b"center-data"


def test_session_and_attendance_repositories_create_records(database) -> None:
    users = UserRepository(database)
    sessions = SessionRepository(database)
    attendance = AttendanceRepository(database)

    user_id = users.create("SV003", "Nguyen Van C")
    session_id = sessions.create("AI", "CTK42", 0.5, 0.8)

    attendance.record(session_id, user_id, "success")

    row = attendance.get(session_id, user_id)
    assert row is not None
    assert row["status"] == "success"


def test_repository_rejects_invalid_identifier_input(database) -> None:
    users = UserRepository(database)

    with pytest.raises(ValueError):
        users.get_by_id(0)


def test_sql_injection_payload_is_not_executed(database) -> None:
    users = UserRepository(database)
    malicious_student_id = "SV005'; DROP TABLE users; --"

    user_id = users.create(malicious_student_id, "Injection Test")

    inserted = users.get_by_id(user_id)
    fetched = users.get_by_student_id(malicious_student_id)

    assert inserted is not None
    assert fetched is not None
    assert fetched["id"] == inserted["id"]


def test_schema_migration_adds_pose_label_to_existing_face_references(tmp_path) -> None:
    """Verify that initialize_schema upgrades an old face_references table that
    lacks the pose_label column and UNIQUE(user_id, pose_label) constraint."""
    import sqlite3
    from attendance_system.core.db import Database, DatabaseConfig
    from attendance_system.core.schema import initialize_schema

    db_path = tmp_path / "old_schema.db"

    # --- build a DB with the OLD face_references (no pose_label) ---
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            face_registered INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # Old face_references: no pose_label, no UNIQUE, no DEFAULT
    conn.execute("""
        CREATE TABLE IF NOT EXISTS face_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            model_name TEXT NOT NULL,
            vector_length INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # Pre-populate with an existing user and face reference
    conn.execute(
        "INSERT INTO users (student_id, full_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        ("LEGACY001", "Legacy User", "2025-01-01T00:00:00", "2025-01-01T00:00:00"),
    )
    conn.execute(
        "INSERT INTO face_references (user_id, embedding, model_name, vector_length, created_at) VALUES (?, ?, ?, ?, ?)",
        (1, b"legacy-embed", "old-model", 4, "2025-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()

    # --- run schema initialization (applies migration) ---
    db = Database(DatabaseConfig(path=db_path))
    with db.session() as connection:
        initialize_schema(connection)

    # --- verify migration ---
    with db.connect() as connection:
        columns = [col[1] for col in connection.execute("PRAGMA table_info(face_references)")]
        assert "pose_label" in columns, "pose_label column should exist after migration"

        # Existing row should have been preserved with pose_label = 'center'
        row = connection.execute(
            "SELECT * FROM face_references WHERE user_id = 1"
        ).fetchone()
        assert row is not None
        assert row["embedding"] == b"legacy-embed"
        assert row["pose_label"] == "center"

        # UNIQUE(user_id, pose_label) constraint should be enforced
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO face_references (user_id, embedding, model_name, vector_length, pose_label, created_at) "
                "VALUES (1, ?, ?, ?, ?, ?)",
                (b"new-emb", "m2", 8, "center", "2025-06-01T00:00:00"),
            )


def test_face_reference_get_returns_row_with_encryption_enabled(database, monkeypatch) -> None:
    fernet_module = pytest.importorskip("cryptography.fernet")
    monkeypatch.setenv("FACE_EMBEDDING_FERNET_KEY", fernet_module.Fernet.generate_key().decode("utf-8"))

    users = UserRepository(database)
    faces = FaceReferenceRepository(database)
    from attendance_system.repositories.face_reference_repository import POSE_LABELS

    user_id = users.create("SV006", "Encrypted User")
    pose_embeddings = {pose: f"{pose}-emb".encode() for pose in POSE_LABELS}
    faces.replace_all(user_id, pose_embeddings, "model-v1", 8)

    rows = faces.get_by_user_id(user_id)
    assert len(rows) == 5
    for row in rows:
        assert row["pose_label"] in POSE_LABELS
        assert row["embedding"] == f"{row['pose_label']}-emb".encode()
