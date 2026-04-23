from __future__ import annotations

from pathlib import Path

from repositories.face_reference_repository import FaceReferenceRepository
from repositories.user_repository import UserRepository
from services.enrollment_service import EnrollmentService
from services.settings_service import SettingsService


def test_settings_service_persists_values(database) -> None:
    settings = SettingsService(database)

    settings.set("similarity_threshold", "0.8", "float")

    assert settings.get("similarity_threshold") == "0.8"


def test_enrollment_service_stores_embedding_and_removes_raw_image(database, tmp_path: Path) -> None:
    users = UserRepository(database)
    faces = FaceReferenceRepository(database)
    enrollment = EnrollmentService(database)

    user_id = users.create("SV004", "Nguyen Van D")
    raw_image_path = tmp_path / "raw.jpg"
    raw_image_path.write_bytes(b"raw-image-data")

    enrollment.save_face_reference(user_id, b"derived-embedding", "model-v1", 4, raw_image_path)

    row = faces.get_by_user_id(user_id)
    assert row is not None
    assert row["embedding"] == b"derived-embedding"
    assert not raw_image_path.exists()
