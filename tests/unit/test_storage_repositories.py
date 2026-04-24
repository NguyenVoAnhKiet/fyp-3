from __future__ import annotations

import sqlite3

import pytest

from repositories.attendance_repository import AttendanceRepository
from repositories.face_reference_repository import FaceReferenceRepository
from repositories.session_repository import SessionRepository
from repositories.system_setting_repository import SystemSettingRepository
from repositories.user_repository import UserRepository


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


def test_face_reference_repository_persists_derived_embedding(database) -> None:
    users = UserRepository(database)
    faces = FaceReferenceRepository(database)

    user_id = users.create("SV002", "Nguyen Van B")
    faces.upsert(user_id, b"embedding-bytes", "model-v1", 4)

    row = faces.get_by_user_id(user_id)
    assert row is not None
    assert row["embedding"] == b"embedding-bytes"
    assert row["model_name"] == "model-v1"


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


def test_face_reference_get_returns_row_with_encryption_enabled(database, monkeypatch) -> None:
    fernet_module = pytest.importorskip("cryptography.fernet")
    monkeypatch.setenv("FACE_EMBEDDING_FERNET_KEY", fernet_module.Fernet.generate_key().decode("utf-8"))

    users = UserRepository(database)
    faces = FaceReferenceRepository(database)
    user_id = users.create("SV006", "Encrypted User")

    faces.upsert(user_id, b"embedding-bytes", "model-v1", 4)

    row = faces.get_by_user_id(user_id)

    assert isinstance(row, sqlite3.Row)
    assert row["embedding"] == b"embedding-bytes"
