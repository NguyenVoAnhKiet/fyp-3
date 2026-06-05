"""Unit tests for ``attendance_system.services.ai_pipeline``.

Covers ``LivenessChecker`` and ``FaceRecognizer`` ONNX wrappers.  After
plan 0005, ``LivenessChecker.check()`` requires an explicit ``threshold``
— no default — so this file also asserts the threshold is plumbed
through (see ``test_liveness_checker_bypass``).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import cv2

from attendance_system.services.ai_pipeline import LivenessChecker, FaceRecognizer, LivenessResult, RecognitionResult


# ==============================================================================
# LivenessChecker Tests
# ==============================================================================

def test_liveness_checker_bypass():
    """LivenessChecker should bypass checks if model_path is None.

    Plan 0005: ``threshold`` is now required (no default).  The bypass
    path ignores the threshold anyway, but the caller must still pass
    a value.
    """
    checker = LivenessChecker(None)
    dummy_img = np.zeros((128, 128, 3), dtype=np.uint8)
    result = checker.check(dummy_img, threshold=0.3)

    assert result.is_real is True
    assert result.score == 1.0


@patch("onnxruntime.InferenceSession")
def test_liveness_checker_real_face(mock_session_cls):
    """LivenessChecker should return is_real=True when logit_diff > threshold."""
    # Mock session setup
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_session.get_inputs.return_value = [mock_input]
    # index 0 = real (10.0), index 1 = spoof (0.0) -> logit_diff = 10.0
    mock_session.run.return_value = [np.array([[10.0, 0.0]], dtype=np.float32)]
    mock_session_cls.return_value = mock_session
    
    checker = LivenessChecker(Path("fake.onnx"))
    dummy_img = np.zeros((128, 128, 3), dtype=np.uint8)
    # threshold 0.5 -> logit_threshold 0.0. 10.0 > 0.0 -> True
    result = checker.check(dummy_img, threshold=0.5)
    
    assert result.is_real is True
    assert result.score == 10.0


@patch("onnxruntime.InferenceSession")
def test_liveness_checker_spoof_face(mock_session_cls):
    """LivenessChecker should return is_real=False when logit_diff < threshold."""
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_session.get_inputs.return_value = [mock_input]
    # index 0 = real (0.0), index 1 = spoof (10.0) -> logit_diff = -10.0
    mock_session.run.return_value = [np.array([[0.0, 10.0]], dtype=np.float32)]
    mock_session_cls.return_value = mock_session
    
    checker = LivenessChecker(Path("fake.onnx"))
    dummy_img = np.zeros((128, 128, 3), dtype=np.uint8)
    # threshold 0.5 -> logit_threshold 0.0. -10.0 < 0.0 -> False
    result = checker.check(dummy_img, threshold=0.5)
    
    assert result.is_real is False
    assert result.score == -10.0


@pytest.mark.parametrize("shape", [
    (100, 100, 3),  # Square
    (200, 100, 3),  # Portrait
    (100, 200, 3),  # Landscape
    (500, 500, 3),  # Large
    (50, 50, 3),    # Small
    (300, 400, 3),  # 3:4 Aspect Ratio
    (400, 300, 3),  # 4:3 Aspect Ratio
])
def test_liveness_preprocess_output_shape(shape):
    """LivenessChecker._preprocess should always return [1, 3, 128, 128] float32."""
    checker = LivenessChecker(None)
    face_img = np.zeros(shape, dtype=np.uint8)
    processed = checker._preprocess(face_img)
    
    assert processed.shape == (1, 3, 128, 128)
    assert processed.dtype == np.float32
    assert processed.min() >= 0.0
    assert processed.max() <= 1.0


def test_liveness_checker_is_enabled_property():
    """LivenessChecker.is_enabled reflects whether a model is loaded."""
    # Disabled case — model_path=None
    disabled = LivenessChecker(model_path=None)
    assert not disabled.is_enabled

    # Enabled case requires a real ONNX file — not tested here.
    # The existing test_liveness_checker_real_face already verifies
    # that a mocked session proceeds to inference correctly.


# ==============================================================================
# FaceRecognizer Tests
# ==============================================================================

def test_cosine_similarity_edge_cases():
    """FaceRecognizer._cosine_similarity should handle various vector relationships."""
    a = np.array([1, 0, 0], dtype=np.float32)
    
    # Identical
    assert pytest.approx(FaceRecognizer._cosine_similarity(a, a)) == 1.0
    
    # Orthogonal
    b = np.array([0, 1, 0], dtype=np.float32)
    assert pytest.approx(FaceRecognizer._cosine_similarity(a, b)) == 0.0
    
    # Opposite
    c = np.array([-1, 0, 0], dtype=np.float32)
    assert pytest.approx(FaceRecognizer._cosine_similarity(a, c)) == -1.0
    
    # Zero vector
    z = np.zeros(3, dtype=np.float32)
    assert FaceRecognizer._cosine_similarity(a, z) == -1.0


def test_average_embeddings():
    """FaceRecognizer.average_embeddings should return normalized mean."""
    e1 = np.array([1, 0, 0], dtype=np.float32)
    e2 = np.array([0, 1, 0], dtype=np.float32)
    
    avg = FaceRecognizer.average_embeddings([e1, e2])
    # Expected mean: [0.5, 0.5, 0]. Normalized: [1/sqrt(2), 1/sqrt(2), 0]
    expected = 1.0 / np.sqrt(2)
    assert pytest.approx(avg[0]) == expected
    assert pytest.approx(avg[1]) == expected
    assert pytest.approx(np.linalg.norm(avg)) == 1.0

    # Empty list
    with pytest.raises(ValueError, match="Empty embeddings list"):
        FaceRecognizer.average_embeddings([])


@patch("cv2.FaceRecognizerSF.create")
def test_identify_no_refs(mock_sface_create, database):
    """identify() should return None when no references exist in DB."""
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    # get_embedding will return a vector
    mock_sface.feature.return_value = [np.random.rand(1, 128).astype(np.float32)]
    
    recognizer = FaceRecognizer(database, "fake.onnx")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    
    result = recognizer.identify(dummy_frame, dummy_face)
    assert result is None


@patch("cv2.FaceRecognizerSF.create")
def test_identify_match_success(mock_sface_create, database):
    """identify() should return RecognitionResult on match with pose label."""
    # 1. Setup DB: user + pose-specific face references
    from attendance_system.repositories.user_repository import UserRepository
    from attendance_system.repositories.face_reference_repository import FaceReferenceRepository, POSE_LABELS
    
    user_repo = UserRepository(database)
    u_id = user_repo.create("S001", "Alice")
    
    face_repo = FaceReferenceRepository(database)
    # Embedding: [1, 0, 0, ...] for all poses
    emb = np.zeros(128, dtype=np.float32)
    emb[0] = 1.0
    pose_embeddings = {pose: emb.tobytes() for pose in POSE_LABELS}
    face_repo.replace_all(u_id, pose_embeddings, "SFace", 128)
    
    # 2. Mock SFace
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    # feature returns [1, 0, 0, ...]
    mock_sface.feature.return_value = [emb[np.newaxis]]
    
    recognizer = FaceRecognizer(database, "fake.onnx")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    
    # 3. Identify
    result = recognizer.identify(dummy_frame, dummy_face, threshold=0.9)
    assert result is not None
    assert result.user_id == u_id
    assert result.full_name == "Alice"
    assert result.similarity == 1.0
    assert result.matched_pose_label in POSE_LABELS


@patch("cv2.FaceRecognizerSF.create")
def test_identify_below_threshold(mock_sface_create, database):
    """identify() should return None if similarity < threshold."""
    from attendance_system.repositories.user_repository import UserRepository
    from attendance_system.repositories.face_reference_repository import FaceReferenceRepository, POSE_LABELS
    
    u_id = UserRepository(database).create("S001", "Alice")
    # Stored: [1, 0, 0, ...]
    stored_emb = np.zeros(128, dtype=np.float32)
    stored_emb[0] = 1.0
    pose_embeddings = {pose: stored_emb.tobytes() for pose in POSE_LABELS}
    FaceReferenceRepository(database).replace_all(u_id, pose_embeddings, "SFace", 128)
    
    # Mock live embedding: [0, 1, 0, ...] (similarity = 0.0)
    live_emb = np.zeros(128, dtype=np.float32)
    live_emb[1] = 1.0
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    mock_sface.feature.return_value = [live_emb]
    
    recognizer = FaceRecognizer(database, "fake.onnx")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    
    result = recognizer.identify(dummy_frame, dummy_face, threshold=0.5)
    assert result is None


@patch("cv2.FaceRecognizerSF.create")
def test_identify_skips_corrupt_embeddings_gracefully(mock_sface_create, database):
    """identify() should skip any invalid or corrupt stored embeddings and not crash."""
    from attendance_system.repositories.user_repository import UserRepository
    from attendance_system.repositories.face_reference_repository import FaceReferenceRepository, POSE_LABELS
    
    # User 1: valid embedding
    user_repo = UserRepository(database)
    u_id_1 = user_repo.create("S001", "Alice")
    face_repo = FaceReferenceRepository(database)
    valid_emb = np.zeros(128, dtype=np.float32)
    valid_emb[0] = 1.0
    pose_embeddings_1 = {pose: valid_emb.tobytes() for pose in POSE_LABELS}
    face_repo.replace_all(u_id_1, pose_embeddings_1, "SFace", 128)
    
    # User 2: corrupt embedding bytes (e.g. wrong size)
    u_id_2 = user_repo.create("S002", "Bob")
    corrupt_emb = b"short_bytes"
    
    # We bypass replace_all checks to insert corrupt data directly into DB
    with database.session() as conn:
        for pose in POSE_LABELS:
            conn.execute(
                "INSERT INTO face_references(user_id, embedding, model_name, vector_length, pose_label, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (u_id_2, corrupt_emb, "SFace", 128, pose, "2026-04-24T09:00:00Z"),
            )
            
    # Mock SFace live feature to return [1, 0, 0, ...]
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    mock_sface.feature.return_value = [valid_emb[np.newaxis]]
    
    recognizer = FaceRecognizer(database, "fake.onnx")
    # No cache invalidation needed: FaceRecognizer now reads fresh from DB
    # each time (caching is handled by the CachingFaceReferenceRepository
    # wrapper, which is not used here).
    
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    
    # identify() should skip u_id_2 and match u_id_1
    result = recognizer.identify(dummy_frame, dummy_face, threshold=0.9)
    assert result is not None
    assert result.user_id == u_id_1


def test_face_reference_repository_cache_invalidation(database):
    """CachingFaceReferenceRepository cache should be invalidated on every write path."""
    from attendance_system.repositories.user_repository import UserRepository
    from attendance_system.repositories.face_reference_repository import (
        FaceReferenceRepository,
        POSE_LABELS,
    )
    from attendance_system.repositories.caching_face_reference_repository import (
        CachingFaceReferenceRepository,
    )

    users = UserRepository(database)
    faces = CachingFaceReferenceRepository(FaceReferenceRepository(database))

    u_id = users.create("S003", "Charlie")
    emb = np.zeros(128, dtype=np.float32).tobytes()

    cache_key = str(database.config.path)

    # 1. Initially cache is empty
    assert cache_key not in faces._cache

    # 2. get_all caches the results
    faces.get_all()
    assert cache_key in faces._cache

    # 3. upsert invalidates cache
    faces.upsert(u_id, emb, "model-v1", 128, "center")
    assert cache_key not in faces._cache

    # 4. get_all caches again
    faces.get_all()
    assert cache_key in faces._cache

    # 5. replace_all invalidates cache
    pose_embeddings = {pose: emb for pose in POSE_LABELS}
    faces.replace_all(u_id, pose_embeddings, "model-v1", 128)
    assert cache_key not in faces._cache

    # 6. get_all caches again
    faces.get_all()
    assert cache_key in faces._cache

    # 7. delete_by_user_id invalidates cache
    faces.delete_by_user_id(u_id)
    assert cache_key not in faces._cache


@patch("onnxruntime.InferenceSession")
def test_liveness_checker_nan_inf(mock_session_cls):
    """LivenessChecker.check() should handle NaN or Inf outputs from ONNX without crashing."""
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_session.get_inputs.return_value = [mock_input]
    
    # 1. Test NaN output
    mock_session.run.return_value = [np.array([[np.nan, 0.0]], dtype=np.float32)]
    mock_session_cls.return_value = mock_session
    
    checker = LivenessChecker(Path("fake.onnx"))
    dummy_img = np.zeros((128, 128, 3), dtype=np.uint8)
    
    result = checker.check(dummy_img, threshold=0.5)
    assert result.is_real is False
    assert np.isnan(result.score)
    
    # 2. Test Inf output
    mock_session.run.return_value = [np.array([[np.inf, 0.0]], dtype=np.float32)]
    result = checker.check(dummy_img, threshold=0.5)
    assert result.is_real is True
    assert result.score == np.inf
    
    # 3. Test -Inf output
    mock_session.run.return_value = [np.array([[-np.inf, 0.0]], dtype=np.float32)]
    result = checker.check(dummy_img, threshold=0.5)
    assert result.is_real is False
    assert result.score == -np.inf
