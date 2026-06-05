from __future__ import annotations

import os
import sqlite3
from typing import Any

from attendance_system.core.db import Database
from attendance_system.utils.time_utils import utc_now_iso

from .base_repository import BaseRepository


POSE_LABELS: tuple[str, ...] = ("center", "right", "left", "up", "down")


class FaceReferenceRepository(BaseRepository):

    def __init__(self, database: Database) -> None:
        super().__init__(database)
        self._fernet_key = os.getenv("FACE_EMBEDDING_FERNET_KEY")

    def _get_fernet(self):
        if not self._fernet_key:
            return None
        try:
            from cryptography.fernet import Fernet
        except ImportError as error:
            raise RuntimeError(
                "cryptography package is required when FACE_EMBEDDING_FERNET_KEY is set"
            ) from error
        return Fernet(self._fernet_key.encode("utf-8"))

    def _encrypt_embedding(self, embedding: bytes) -> bytes:
        fernet = self._get_fernet()
        if fernet is None:
            return embedding
        return fernet.encrypt(embedding)

    def _decrypt_embedding(self, embedding: bytes) -> bytes:
        fernet = self._get_fernet()
        if fernet is None:
            return embedding
        return fernet.decrypt(embedding)

    @staticmethod
    def _dict_to_row(payload: dict[str, object]) -> sqlite3.Row:
        columns = list(payload.keys())
        placeholders = ", ".join("? AS " + column for column in columns)
        with sqlite3.connect(":memory:") as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                f"SELECT {placeholders}", tuple(payload[column] for column in columns)
            ).fetchone()

    def upsert(
        self, user_id: int, embedding: bytes, model_name: str, vector_length: int,
        pose_label: str = "center",
    ) -> int:
        self.require_positive_int(user_id, "user_id")
        if not isinstance(embedding, bytes) or len(embedding) == 0:
            raise ValueError("embedding must be non-empty bytes")
        self.require_non_empty_text(model_name, "model_name")
        self.require_positive_int(vector_length, "vector_length")
        if pose_label not in POSE_LABELS:
            raise ValueError(f"pose_label must be one of {POSE_LABELS}, got {pose_label!r}")
        timestamp = utc_now_iso()
        encrypted_embedding = self._encrypt_embedding(embedding)
        result = self.execute(
            """
            INSERT INTO face_references(user_id, embedding, model_name, vector_length, pose_label, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, pose_label) DO UPDATE SET
                embedding = excluded.embedding,
                model_name = excluded.model_name,
                vector_length = excluded.vector_length,
                created_at = excluded.created_at
            """,
            (user_id, encrypted_embedding, model_name, vector_length, pose_label, timestamp),
        )
        return result

    def get_by_user_id(self, user_id: int) -> list[dict[str, Any]]:
        """Return all face reference rows for the given user (list of dicts)."""
        self.require_positive_int(user_id, "user_id")
        rows = self.fetch_all(
            "SELECT * FROM face_references WHERE user_id = ? ORDER BY pose_label",
            (user_id,),
        )
        if not rows:
            return []
        if not self._fernet_key:
            return [dict(r) for r in rows]
        result = []
        for row in rows:
            decrypted = self._decrypt_embedding(row["embedding"])
            result.append({**dict(row), "embedding": decrypted})
        return result

    def get_by_user_id_and_pose(self, user_id: int, pose_label: str) -> sqlite3.Row | None:
        """Return a single face reference for the given user and pose label."""
        self.require_positive_int(user_id, "user_id")
        if pose_label not in POSE_LABELS:
            raise ValueError(f"pose_label must be one of {POSE_LABELS}, got {pose_label!r}")
        row = self.fetch_one(
            "SELECT * FROM face_references WHERE user_id = ? AND pose_label = ?",
            (user_id, pose_label),
        )
        if row is None or not self._fernet_key:
            return row
        decrypted_embedding = self._decrypt_embedding(row["embedding"])
        return self._dict_to_row({**dict(row), "embedding": decrypted_embedding})

    def replace_all(
        self,
        user_id: int,
        pose_embeddings: dict[str, bytes],
        model_name: str,
        vector_length: int,
    ) -> None:
        """Atomically delete all existing references for a user and insert the five pose rows."""
        self.require_positive_int(user_id, "user_id")
        self.require_non_empty_text(model_name, "model_name")
        self.require_positive_int(vector_length, "vector_length")
        if set(pose_embeddings.keys()) != set(POSE_LABELS):
            raise ValueError(
                f"pose_embeddings must contain exactly all five pose labels: {POSE_LABELS}. "
                f"Got: {set(pose_embeddings.keys())}"
            )
        for pose, emb in pose_embeddings.items():
            if not isinstance(emb, bytes) or len(emb) == 0:
                raise ValueError(f"embedding for pose {pose!r} must be non-empty bytes")

        timestamp = utc_now_iso()
        with self.connection() as conn:
            conn.execute("DELETE FROM face_references WHERE user_id = ?", (user_id,))
            for pose_label in POSE_LABELS:
                encrypted = self._encrypt_embedding(pose_embeddings[pose_label])
                conn.execute(
                    """
                    INSERT INTO face_references(user_id, embedding, model_name, vector_length, pose_label, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, encrypted, model_name, vector_length, pose_label, timestamp),
                )

    def save_enrollment(
        self,
        user_id: int,
        pose_embeddings: dict[str, bytes],
        model_name: str,
        vector_length: int,
    ) -> None:
        """Atomically replace all five pose-specific face references for a user
        **and** mark the user as face_registered in a single transaction.

        Single repository method that owns the full enrollment write so callers
        (e.g. ``EnrollmentService``) do not need to open their own transaction
        or reach into private methods. Validation mirrors ``replace_all``.

        Args:
            user_id: The user to enroll.
            pose_embeddings: Mapping of pose_label -> raw embedding bytes.
                Must contain exactly all five :data:`POSE_LABELS`.
            model_name: Name of the embedding model (e.g. 'SFace').
            vector_length: Dimension of the embedding vector.

        Raises:
            ValueError: If inputs are invalid or pose labels are incomplete.
        """
        self.require_positive_int(user_id, "user_id")
        self.require_non_empty_text(model_name, "model_name")
        self.require_positive_int(vector_length, "vector_length")
        if set(pose_embeddings.keys()) != set(POSE_LABELS):
            raise ValueError(
                f"pose_embeddings must contain exactly all five pose labels: {POSE_LABELS}. "
                f"Got: {set(pose_embeddings.keys())}"
            )
        for pose, emb in pose_embeddings.items():
            if not isinstance(emb, bytes) or len(emb) == 0:
                raise ValueError(f"embedding for pose {pose!r} must be non-empty bytes")

        timestamp = utc_now_iso()
        with self.connection() as conn:
            conn.execute("DELETE FROM face_references WHERE user_id = ?", (user_id,))
            for pose_label in POSE_LABELS:
                encrypted = self._encrypt_embedding(pose_embeddings[pose_label])
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

    def get_all(self) -> list[dict[str, Any]]:
        """Return all face references as a list of dicts (decrypted if fernet key is set)."""
        rows = self.fetch_all("SELECT * FROM face_references")
        if not self._fernet_key:
            return [dict(r) for r in rows]
        result = []
        for row in rows:
            decrypted = self._decrypt_embedding(row["embedding"])
            result.append({**dict(row), "embedding": decrypted})
        return result

    def delete_by_user_id(self, user_id: int) -> None:
        self.require_positive_int(user_id, "user_id")
        self.execute("DELETE FROM face_references WHERE user_id = ?", (user_id,))
