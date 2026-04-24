from __future__ import annotations

import os
import sqlite3

from core.db import Database
from utils.time_utils import utc_now_iso

from .base_repository import BaseRepository


class FaceReferenceRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)
        self._fernet_key = os.getenv("FACE_EMBEDDING_FERNET_KEY")

    def _encrypt_embedding(self, embedding: bytes) -> bytes:
        if not self._fernet_key:
            return embedding
        try:
            from cryptography.fernet import Fernet
        except ImportError as error:
            raise RuntimeError("cryptography package is required when FACE_EMBEDDING_FERNET_KEY is set") from error
        return Fernet(self._fernet_key.encode("utf-8")).encrypt(embedding)

    def _decrypt_embedding(self, embedding: bytes) -> bytes:
        if not self._fernet_key:
            return embedding
        try:
            from cryptography.fernet import Fernet
        except ImportError as error:
            raise RuntimeError("cryptography package is required when FACE_EMBEDDING_FERNET_KEY is set") from error
        return Fernet(self._fernet_key.encode("utf-8")).decrypt(embedding)

    @staticmethod
    def _dict_to_row(payload: dict[str, object]) -> sqlite3.Row:
        columns = list(payload.keys())
        placeholders = ", ".join("? AS " + column for column in columns)
        with sqlite3.connect(":memory:") as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(f"SELECT {placeholders}", tuple(payload[column] for column in columns)).fetchone()

    def upsert(self, user_id: int, embedding: bytes, model_name: str, vector_length: int) -> int:
        self.require_positive_int(user_id, "user_id")
        if not isinstance(embedding, bytes) or len(embedding) == 0:
            raise ValueError("embedding must be non-empty bytes")
        self.require_non_empty_text(model_name, "model_name")
        self.require_positive_int(vector_length, "vector_length")
        timestamp = utc_now_iso()
        encrypted_embedding = self._encrypt_embedding(embedding)
        return self.execute(
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

    def get_by_user_id(self, user_id: int) -> sqlite3.Row | None:
        self.require_positive_int(user_id, "user_id")
        row = self.fetch_one("SELECT * FROM face_references WHERE user_id = ?", (user_id,))
        if row is None or not self._fernet_key:
            return row
        decrypted_embedding = self._decrypt_embedding(row["embedding"])
        return self._dict_to_row({"embedding": decrypted_embedding, **dict(row)})

    def delete_by_user_id(self, user_id: int) -> None:
        self.require_positive_int(user_id, "user_id")
        self.execute("DELETE FROM face_references WHERE user_id = ?", (user_id,))

