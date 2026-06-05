from __future__ import annotations

from attendance_system.core.db import Database
from attendance_system.repositories.caching_face_reference_repository import (
    CachingFaceReferenceRepository,
)
from attendance_system.repositories.face_reference_repository import (
    FaceReferenceRepository,
)


class EnrollmentService:
    """Thin service that delegates face-reference enrollment to the repository.

    The atomic write (DELETE old + INSERT 5 pose rows + UPDATE users.face_registered)
    is owned by ``FaceReferenceRepository.save_enrollment``. This service is
    kept as a seam for future pre/post hooks (audit log, broadcast events, etc.)
    but currently performs no extra work.

    The injected ``references`` attribute accepts either a bare
    ``FaceReferenceRepository`` or the ``CachingFaceReferenceRepository`` wrapper.
    Both expose ``save_enrollment`` with the same signature.
    """

    def __init__(
        self,
        database: Database,
        references: FaceReferenceRepository | CachingFaceReferenceRepository | None = None,
    ) -> None:
        self.database = database
        # Default to a bare repo for backward-compat with existing tests that
        # don't inject a wrapper. Production wires CachingFaceReferenceRepository
        # in main.py to benefit from cache invalidation on every enrollment.
        self.references = references if references is not None else FaceReferenceRepository(database)

    def save_face_references(
        self,
        user_id: int,
        pose_embeddings: dict[str, bytes],
        model_name: str,
        vector_length: int,
    ) -> None:
        """Atomically replace all five pose-specific face references for a user
        and mark the user as face_registered.

        See ``FaceReferenceRepository.save_enrollment`` for the full contract
        and validation rules.
        """
        self.references.save_enrollment(user_id, pose_embeddings, model_name, vector_length)
