from __future__ import annotations

import pytest

from attendance_system.repositories.face_reference_repository import FaceReferenceRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.services.settings_service import SettingsService


def test_settings_service_persists_values(database) -> None:
    settings = SettingsService(database)

    settings.set("similarity_threshold", "0.8", "float")

    assert settings.get("similarity_threshold") == "0.8"


def test_enrollment_service_stores_five_pose_embeddings(database) -> None:
    from attendance_system.repositories.face_reference_repository import POSE_LABELS

    users = UserRepository(database)
    faces = FaceReferenceRepository(database)
    enrollment = EnrollmentService(database)

    user_id = users.create("SV004", "Nguyen Van D")
    pose_embeddings = {pose: f"{pose}-emb".encode() for pose in POSE_LABELS}
    enrollment.save_face_references(user_id, pose_embeddings, "model-v1", 8)

    rows = faces.get_by_user_id(user_id)
    assert len(rows) == 5
    for row in rows:
        assert row["embedding"] == f"{row['pose_label']}-emb".encode()

    # Verify face_registered flag
    user = UserRepository(database).get_by_id(user_id)
    assert user is not None
    assert user["face_registered"] == 1


def test_enrollment_atomic_rollback_on_failure(database, monkeypatch) -> None:
    """Simulate a mid-transaction failure and verify nothing is committed."""
    from attendance_system.repositories.face_reference_repository import POSE_LABELS

    users = UserRepository(database)
    faces = FaceReferenceRepository(database)
    enrollment = EnrollmentService(database)

    user_id = users.create("SV011", "Atomicity User")
    pose_embeddings = {pose: f"{pose}-emb".encode() for pose in POSE_LABELS}

    # Make _encrypt_embedding raise on the 3rd call (pose "left")
    # so that the transaction rolls back.
    call_count = [0]

    def _failing_encrypt(embedding: bytes) -> bytes:
        call_count[0] += 1
        if call_count[0] == 3:
            raise RuntimeError("Simulated encryption failure")
        return embedding

    monkeypatch.setattr(enrollment.references, "_encrypt_embedding", _failing_encrypt)

    with pytest.raises(RuntimeError, match="Simulated encryption failure"):
        enrollment.save_face_references(
            user_id, pose_embeddings, model_name="model-v1", vector_length=8,
        )

    # Verify that NO face references were saved and face_registered is still 0
    assert faces.get_by_user_id(user_id) == []
    user = users.get_by_id(user_id)
    assert user is not None
    assert user["face_registered"] == 0
