from __future__ import annotations

from time import perf_counter
from unittest.mock import patch, MagicMock
import numpy as np

from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.ai_pipeline import FaceRecognizer


def test_basic_crud_operations_complete_quickly(database) -> None:
    users = UserRepository(database)

    start = perf_counter()
    user_id = users.create("SV009", "Nguyen Van I")
    users.get_by_id(user_id)
    duration = perf_counter() - start

    assert duration < 1.0


@patch("cv2.FaceRecognizerSF.create")
def test_identify_performance_benchmark(mock_sface_create, database) -> None:
    from attendance_system.repositories.face_reference_repository import FaceReferenceRepository, POSE_LABELS
    faces = FaceReferenceRepository(database)
    
    # Insert 1000 users and 5000 face references
    with database.session() as conn:
        for i in range(1, 1001):
            conn.execute(
                "INSERT INTO users (id, student_id, full_name, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (i, f"SV{i:04d}", f"User {i}", "2026-04-24T09:00:00Z", "2026-04-24T09:00:00Z")
            )
            emb = np.random.rand(128).astype(np.float32).tobytes()
            for pose in POSE_LABELS:
                conn.execute(
                    "INSERT INTO face_references (user_id, embedding, model_name, vector_length, pose_label, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (i, emb, "SFace", 128, pose, "2026-04-24T09:00:00Z")
                )
    
    # No cache invalidation needed: FaceRecognizer reads fresh from DB
    # each time (caching is handled by CachingFaceReferenceRepository
    # wrapper, which is not used in this benchmark).
    
    # Setup mock SFace
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    live_emb = np.random.rand(128).astype(np.float32)
    mock_sface.feature.return_value = [live_emb[np.newaxis]]
    
    recognizer = FaceRecognizer(database, "fake.onnx")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    
    # Measure latency
    start = perf_counter()
    recognizer.identify(dummy_frame, dummy_face, threshold=0.0)
    duration = perf_counter() - start
    
    print(f"\nBenchmark: identify() with 1000 users (5000 references) took {duration * 1000:.2f} ms")
    assert duration < 2.0
