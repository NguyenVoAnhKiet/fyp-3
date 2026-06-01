from __future__ import annotations

from attendance_system.repositories.face_reference_repository import FaceReferenceRepository, POSE_LABELS
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.services.settings_service import SettingsService


def test_settings_and_enrollment_flow(database) -> None:
    users = UserRepository(database)
    settings = SettingsService(database)
    enrollment = EnrollmentService(database)

    user_id = users.create("SV007", "Nguyen Van G")
    settings.set("liveness_threshold", "0.6", "float")

    pose_embeddings = {pose: f"{pose}-vec".encode() for pose in POSE_LABELS}
    enrollment.save_face_references(user_id, pose_embeddings, "model-v2", 8)

    assert settings.get("liveness_threshold") == "0.6"
    rows = FaceReferenceRepository(database).get_by_user_id(user_id)
    assert len(rows) == 5
    for row in rows:
        assert row["embedding"] == f"{row['pose_label']}-vec".encode()
