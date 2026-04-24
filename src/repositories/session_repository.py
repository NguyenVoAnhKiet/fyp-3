from __future__ import annotations

from core.db import Database
from utils.time_utils import utc_now_iso

from .base_repository import BaseRepository


class SessionRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def create(
        self,
        subject_name: str,
        class_name: str,
        liveness_threshold_snapshot: float,
        similarity_threshold_snapshot: float,
        status: str = "active",
        start_time: str | None = None,
    ) -> int:
        self.require_non_empty_text(subject_name, "subject_name")
        self.require_non_empty_text(class_name, "class_name")
        self.require_non_empty_text(status, "status")
        if start_time is not None:
            self.require_non_empty_text(start_time, "start_time")
        timestamp = start_time or utc_now_iso()
        return self.execute(
            """
            INSERT INTO sessions(
                subject_name, class_name, status, start_time, end_time,
                liveness_threshold_snapshot, similarity_threshold_snapshot
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subject_name,
                class_name,
                status,
                timestamp,
                None,
                liveness_threshold_snapshot,
                similarity_threshold_snapshot,
            ),
        )

    def get_by_id(self, session_id: int):
        self.require_positive_int(session_id, "session_id")
        return self.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))

    def update_status(self, session_id: int, status: str, end_time: str | None = None) -> None:
        self.require_positive_int(session_id, "session_id")
        self.require_non_empty_text(status, "status")
        if end_time is not None:
            self.require_non_empty_text(end_time, "end_time")
        self.execute(
            "UPDATE sessions SET status = ?, end_time = ? WHERE id = ?",
            (status, end_time, session_id),
        )

    def close(self, session_id: int, end_time: str | None = None) -> None:
        if end_time is not None:
            self.require_non_empty_text(end_time, "end_time")
        self.update_status(session_id, status="closed", end_time=end_time or utc_now_iso())

    def list_active(self):
        return self.fetch_all("SELECT * FROM sessions WHERE status = 'active' ORDER BY id")

