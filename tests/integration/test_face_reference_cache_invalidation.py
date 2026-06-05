"""
End-to-end cache invalidation tests for CachingFaceReferenceRepository.

These tests use a real SQLite database (the ``database`` fixture) and prove
that the wrapper's invalidation contract holds through:

- ``EnrollmentService.save_face_references`` (via injected wrapper)
- Direct ``upsert`` / ``replace_all`` / ``delete_by_user_id`` calls
- ``FaceRecognizer.identify()`` consuming the cache

Unlike the unit tests (which use a stub), these tests exercise real SQL +
Fernet encryption, so a regression in either layer is caught here.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from attendance_system.repositories.caching_face_reference_repository import (
    CachingFaceReferenceRepository,
)
from attendance_system.repositories.face_reference_repository import (
    FaceReferenceRepository,
    POSE_LABELS,
)
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.ai_pipeline import FaceRecognizer
from attendance_system.services.enrollment_service import EnrollmentService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_embedding(seed: int, length: int = 128) -> bytes:
    """Return a deterministic float32 embedding with ``length`` dims, where the
    ``seed``-th dimension is 1.0 (and others are 0). This makes cosine
    similarity easy to assert on (1.0 for the same seed, ~0.0 for different)."""
    emb = np.zeros(length, dtype=np.float32)
    idx = seed % length
    emb[idx] = 1.0
    return emb.tobytes()


def _seed_user(database, student_id: str, name: str) -> int:
    """Create a real user row and return its id."""
    return UserRepository(database).create(student_id, name)


# ---------------------------------------------------------------------------
# 1. The contract invariant: every write path invalidates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("write_name,write_call", [
    ("upsert", lambda inner, uid: inner.upsert(
        uid, _make_embedding(1), "SFace", 128, "center"
    )),
    ("replace_all", lambda inner, uid: inner.replace_all(
        uid, {p: _make_embedding(1) for p in POSE_LABELS}, "SFace", 128
    )),
    ("delete_by_user_id", lambda inner, uid: inner.delete_by_user_id(uid)),
    ("save_enrollment", lambda inner, uid: inner.save_enrollment(
        uid, {p: _make_embedding(1) for p in POSE_LABELS}, "SFace", 128
    )),
])
def test_every_write_invalidates_real_cache(database, write_name, write_call):
    """For every public write method, the next get_all() reflects the change."""
    inner = FaceReferenceRepository(database)
    wrapper = CachingFaceReferenceRepository(inner)

    uid = _seed_user(database, "SV100", "Alice")

    # Populate cache (empty result)
    assert wrapper.get_all() == []

    # Run the write through the wrapper — must invalidate
    write_call(wrapper, uid)

    # The write changed DB state — get_all must reflect it (cache miss → fresh)
    after = wrapper.get_all()
    if write_name == "delete_by_user_id":
        assert after == []
    else:
        assert len(after) >= 1
        assert any(r["user_id"] == uid for r in after)


# ---------------------------------------------------------------------------
# 2. Full enrollment flow → identify → re-enroll → identify with new embedding
# ---------------------------------------------------------------------------


@patch("cv2.FaceRecognizerSF.create")
def test_reenrollment_replaces_cached_embedding(mock_sface_create, database):
    """Re-enrollment must update what identify() sees.

    The wrapper is injected into EnrollmentService so that the
    save_face_references call goes through the caching layer,
    which invalidates the cache on every write.  The next
    identify() then reads fresh from the database.
    """
    users = UserRepository(database)
    uid = users.create("SV201", "Bob")

    # Wire the wrapper into EnrollmentService (production-style)
    face_refs_wrapper = CachingFaceReferenceRepository(
        FaceReferenceRepository(database)
    )
    enrollment = EnrollmentService(database, references=face_refs_wrapper)

    # --- 1st enrollment: embedding #5 ---
    pose_emb_v1 = {p: _make_embedding(5) for p in POSE_LABELS}
    enrollment.save_face_references(uid, pose_emb_v1, "SFace", 128)
    # Cache populated by the write-then-invalidate + next get_all
    cached_v1 = face_refs_wrapper.get_all()
    assert len(cached_v1) == 5
    assert any(
        np.frombuffer(r["embedding"], dtype=np.float32)[5] == 1.0
        for r in cached_v1
    )

    # --- 2nd enrollment: embedding #42 (different) ---
    pose_emb_v2 = {p: _make_embedding(42) for p in POSE_LABELS}
    enrollment.save_face_references(uid, pose_emb_v2, "SFace", 128)

    # After re-enrollment, the wrapper's cache was invalidated.
    # The stored embedding should now match v2, not v1.
    cached_v2 = face_refs_wrapper.get_all()
    assert len(cached_v2) == 5
    assert any(
        np.frombuffer(r["embedding"], dtype=np.float32)[42] == 1.0
        for r in cached_v2
    )
    assert not any(
        np.frombuffer(r["embedding"], dtype=np.float32)[5] == 1.0
        for r in cached_v2
    )

    # --- Verify via FaceRecognizer.identify() ---
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    # Live embedding is #42 (matches v2, not v1)
    live_emb = np.zeros(128, dtype=np.float32)
    live_emb[42] = 1.0
    mock_sface.feature.return_value = [live_emb[np.newaxis]]

    recognizer = FaceRecognizer(
        database, "fake.onnx", face_refs=face_refs_wrapper
    )
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    result = recognizer.identify(dummy_frame, dummy_face, threshold=0.9)
    assert result is not None
    assert result.user_id == uid


# ---------------------------------------------------------------------------
# 3. Delete user via wrapper → identify returns no match for that user
# ---------------------------------------------------------------------------


@patch("cv2.FaceRecognizerSF.create")
def test_delete_user_invalidates_cache(mock_sface_create, database):
    """User deletion via the wrapper must invalidate the cache (the whole point
    of the wrapper: admin UI user-delete must propagate to the recognizer)."""
    users = UserRepository(database)
    inner = FaceReferenceRepository(database)
    wrapper = CachingFaceReferenceRepository(inner)

    # Enroll two users
    uid_alice = users.create("SV301", "Alice")
    uid_bob = users.create("SV302", "Bob")
    for uid in (uid_alice, uid_bob):
        inner.save_enrollment(
            uid,
            {p: _make_embedding(uid) for p in POSE_LABELS},
            "SFace",
            128,
        )

    # Populate cache
    assert len(wrapper.get_all()) == 10  # 2 users × 5 poses

    # Delete Alice
    wrapper.delete_by_user_id(uid_alice)
    remaining = wrapper.get_all()
    assert all(r["user_id"] != uid_alice for r in remaining)
    assert any(r["user_id"] == uid_bob for r in remaining)

    # Verify via identify: live embedding matches Bob, not Alice
    mock_sface = MagicMock()
    mock_sface_create.return_value = mock_sface
    live_emb = np.zeros(128, dtype=np.float32)
    live_emb[uid_bob] = 1.0
    mock_sface.feature.return_value = [live_emb[np.newaxis]]

    recognizer = FaceRecognizer(
        database, "fake.onnx", face_refs=wrapper
    )
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_face = np.zeros((1, 15), dtype=np.float32)
    result = recognizer.identify(dummy_frame, dummy_face, threshold=0.9)
    assert result is not None
    assert result.user_id == uid_bob  # Alice is gone from cache; Bob still there


# ---------------------------------------------------------------------------
# 4. Documentation test: external DB writes are NOT auto-invalidated
# ---------------------------------------------------------------------------


def test_external_db_modification_not_detected(database):
    """Documents the limit: writes that bypass the wrapper (e.g. raw SQL
    against face_references) leave the cache stale until the next wrapper
    write invalidates it. This is intentional — the wrapper can only know
    about writes it sees. The test pins the current behaviour so anyone
    changing it does so deliberately.
    """
    users = UserRepository(database)
    inner = FaceReferenceRepository(database)
    wrapper = CachingFaceReferenceRepository(inner)

    uid = users.create("SV401", "Charlie")
    # Populate cache (empty)
    wrapper.get_all()

    # External write (bypassing the wrapper)
    inner.save_enrollment(
        uid,
        {p: _make_embedding(7) for p in POSE_LABELS},
        "SFace",
        128,
    )

    # Cache is stale: get_all returns the OLD snapshot (empty)
    stale = wrapper.get_all()
    assert stale == []

    # But a wrapper invalidation fixes it
    wrapper.invalidate()
    fresh = wrapper.get_all()
    assert any(r["user_id"] == uid for r in fresh)
