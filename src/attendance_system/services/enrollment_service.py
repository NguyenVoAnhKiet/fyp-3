from __future__ import annotations

from attendance_system.core.db import Database
from attendance_system.repositories.face_reference_repository import (
    FaceReferenceRepository,
    POSE_LABELS,
)
from attendance_system.utils.time_utils import utc_now_iso


class EnrollmentService:
    def __init__(self, database: Database) -> None:
        self.references = FaceReferenceRepository(database)

    def save_face_references(
        self,
        user_id: int,
        pose_embeddings: dict[str, bytes],
        model_name: str,
        vector_length: int,
    ) -> None:
        """Atomically replace all five pose-specific face references for a user
        **and** mark the user as face_registered in a single transaction.

        Args:
            user_id: The user to enroll.
            pose_embeddings: Mapping of pose_label -> raw embedding bytes.
            model_name: Name of the embedding model (e.g. 'SFace').
            vector_length: Dimension of the embedding vector.

        Raises:
            ValueError: If inputs are invalid or pose labels are incomplete.
        """
        # --- validation (mirrors FaceReferenceRepository.replace_all) ---
        self.references.require_positive_int(user_id, "user_id")
        self.references.require_non_empty_text(model_name, "model_name")
        self.references.require_positive_int(vector_length, "vector_length")
        if set(pose_embeddings.keys()) != set(POSE_LABELS):
            raise ValueError(
                f"pose_embeddings must contain exactly all five pose labels: "
                f"{POSE_LABELS}. Got: {set(pose_embeddings.keys())}"
            )
        for pose, emb in pose_embeddings.items():
            if not isinstance(emb, bytes) or len(emb) == 0:
                raise ValueError(
                    f"embedding for pose {pose!r} must be non-empty bytes"
                )

        # --- single transaction ---
        with self.references.database.session() as conn:
            conn.execute(
                "DELETE FROM face_references WHERE user_id = ?",
                (user_id,),
            )
            timestamp = utc_now_iso()
            for pose_label in POSE_LABELS:
                encrypted = self.references._encrypt_embedding(
                    pose_embeddings[pose_label]
                )
                conn.execute(
                    """
                    INSERT INTO face_references
                        (user_id, embedding, model_name, vector_length,
                         pose_label, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        encrypted,
                        model_name,
                        vector_length,
                        pose_label,
                        timestamp,
                    ),
                )
            conn.execute(
                "UPDATE users SET face_registered = 1, updated_at = ? WHERE id = ?",
                (timestamp, user_id),
            )

        self.references._invalidate_cache(str(self.references.database.config.path))
