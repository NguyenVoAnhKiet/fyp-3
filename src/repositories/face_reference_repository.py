from __future__ import annotations

from datetime import datetime, timezone

from core.db import Database

from .base_repository import BaseRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FaceReferenceRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def upsert(self, user_id: int, embedding: bytes, model_name: str, vector_length: int) -> int:
        timestamp = _utc_now()
        return self.execute(
            """
            INSERT INTO face_references(user_id, embedding, model_name, vector_length, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                embedding = excluded.embedding,
                model_name = excluded.model_name,
                vector_length = excluded.vector_length
            """,
            (user_id, embedding, model_name, vector_length, timestamp),
        )

    def get_by_user_id(self, user_id: int):
        return self.fetch_one("SELECT * FROM face_references WHERE user_id = ?", (user_id,))

    def delete_by_user_id(self, user_id: int) -> None:
        self.execute("DELETE FROM face_references WHERE user_id = ?", (user_id,))

