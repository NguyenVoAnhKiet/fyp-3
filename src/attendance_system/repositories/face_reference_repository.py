from __future__ import annotations

import os
import sqlite3
from typing import Any, ClassVar

from attendance_system.core.db import Database
from attendance_system.utils.time_utils import utc_now_iso

from .base_repository import BaseRepository


class FaceReferenceRepository(BaseRepository):
    # Class-level cache for get_all(), keyed by database path.
    # Invalidated on upsert/delete so that every repository instance
    # (FaceRecognizer, EnrollmentService, UserManagementWidget)
    # shares the same cached data without needing a shared instance.
    _cache_all: ClassVar[dict[str, list[dict[str, Any]]]] = {}

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
        self, user_id: int, embedding: bytes, model_name: str, vector_length: int
    ) -> int:
        self.require_positive_int(user_id, "user_id")
        if not isinstance(embedding, bytes) or len(embedding) == 0:
            raise ValueError("embedding must be non-empty bytes")
        self.require_non_empty_text(model_name, "model_name")
        self.require_positive_int(vector_length, "vector_length")
        timestamp = utc_now_iso()
        encrypted_embedding = self._encrypt_embedding(embedding)
        result = self.execute(
            """
            INSERT INTO face_references(user_id, embedding, model_name, vector_length, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                embedding = excluded.embedding,
                model_name = excluded.model_name,
                vector_length = excluded.vector_length,
                created_at = excluded.created_at
            """,
            (user_id, encrypted_embedding, model_name, vector_length, timestamp),
        )
        self._invalidate_cache(str(self.database.config.path))
        return result

    def get_by_user_id(self, user_id: int) -> sqlite3.Row | None:
        self.require_positive_int(user_id, "user_id")
        row = self.fetch_one(
            "SELECT * FROM face_references WHERE user_id = ?", (user_id,)
        )
        if row is None or not self._fernet_key:
            return row
        decrypted_embedding = self._decrypt_embedding(row["embedding"])
        return self._dict_to_row({**dict(row), "embedding": decrypted_embedding})

    def get_all(self) -> list[dict[str, Any]]:
        """Return all face references, using a class-level cache.

        Cache is keyed by database path so that different databases
        (e.g. per-test tmp directories) do not interfere.
        Invalidated automatically by upsert() and delete_by_user_id().
        """
        cache_key = str(self.database.config.path)
        cached = type(self)._cache_all.get(cache_key)
        if cached is not None:
            return cached

        rows = self.fetch_all("SELECT * FROM face_references")
        if not self._fernet_key:
            result = [dict(r) for r in rows]
        else:
            result = []
            for row in rows:
                decrypted = self._decrypt_embedding(row["embedding"])
                result.append({**dict(row), "embedding": decrypted})

        type(self)._cache_all[cache_key] = result
        return result

    @classmethod
    def _invalidate_cache(cls, database_path: str) -> None:
        cls._cache_all.pop(database_path, None)

    def delete_by_user_id(self, user_id: int) -> None:
        self.require_positive_int(user_id, "user_id")
        self.execute("DELETE FROM face_references WHERE user_id = ?", (user_id,))
        self._invalidate_cache(str(self.database.config.path))
