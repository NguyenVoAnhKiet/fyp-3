from __future__ import annotations

from attendance_system.repositories.face_reference_repository import FaceReferenceRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.services.settings_service import SettingsService


def test_settings_and_enrollment_flow(database) -> None:
    users = UserRepository(database)
    settings = SettingsService(database)
    enrollment = EnrollmentService(database)

    user_id = users.create("SV007", "Nguyen Van G")
    settings.set("liveness_threshold", "0.6", "float")

    enrollment.save_face_reference(user_id, b"face-vector", "model-v2", 8)

    assert settings.get("liveness_threshold") == "0.6"
    assert FaceReferenceRepository(database).get_by_user_id(user_id)["embedding"] == b"face-vector"
