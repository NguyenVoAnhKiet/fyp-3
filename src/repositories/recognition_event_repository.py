from __future__ import annotations

from core.db import Database

from .base_repository import BaseRepository


class RecognitionEventRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def create(
        self,
        session_id: int,
        user_id: int | None,
        event_time: str,
        result: str,
        liveness_score: float | None = None,
        similarity_score: float | None = None,
        details: str | None = None,
    ) -> int:
        self.require_positive_int(session_id, "session_id")
        if user_id is not None:
            self.require_positive_int(user_id, "user_id")
        self.require_non_empty_text(event_time, "event_time")
        self.require_non_empty_text(result, "result")
        return self.execute(
            """
            INSERT INTO recognition_events(
                session_id, user_id, event_time, result, liveness_score, similarity_score, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, event_time, result, liveness_score, similarity_score, details),
        )

    def list_by_session(self, session_id: int):
        self.require_positive_int(session_id, "session_id")
        return self.fetch_all("SELECT * FROM recognition_events WHERE session_id = ? ORDER BY id", (session_id,))

