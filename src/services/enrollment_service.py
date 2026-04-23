from __future__ import annotations

from pathlib import Path

from core.db import Database

from repositories.face_reference_repository import FaceReferenceRepository


class EnrollmentService:
    def __init__(self, database: Database) -> None:
        self.references = FaceReferenceRepository(database)

    def save_face_reference(
        self,
        user_id: int,
        embedding: bytes,
        model_name: str,
        vector_length: int,
        raw_image_path: Path | None = None,
    ) -> int:
        reference_id = self.references.upsert(
            user_id=user_id,
            embedding=embedding,
            model_name=model_name,
            vector_length=vector_length,
        )
        if raw_image_path is not None and raw_image_path.exists():
            raw_image_path.unlink()
        return reference_id

