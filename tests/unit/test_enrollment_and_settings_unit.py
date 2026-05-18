from __future__ import annotations

from attendance_system.repositories.face_reference_repository import FaceReferenceRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.services.settings_service import SettingsService


def test_settings_service_persists_values(database) -> None:
    settings = SettingsService(database)

    settings.set("similarity_threshold", "0.8", "float")

    assert settings.get("similarity_threshold") == "0.8"


def test_enrollment_service_stores_embedding(database) -> None:
    users = UserRepository(database)
    faces = FaceReferenceRepository(database)
    enrollment = EnrollmentService(database)

    user_id = users.create("SV004", "Nguyen Van D")

    enrollment.save_face_reference(user_id, b"derived-embedding", "model-v1", 4)

    row = faces.get_by_user_id(user_id)
    assert row is not None
    assert row["embedding"] == b"derived-embedding"
