from __future__ import annotations

from datetime import datetime, timezone

from core.db import Database

from .base_repository import BaseRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        timestamp = start_time or _utc_now()
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
        return self.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))

    def update_status(self, session_id: int, status: str, end_time: str | None = None) -> None:
        self.execute(
            "UPDATE sessions SET status = ?, end_time = ? WHERE id = ?",
            (status, end_time, session_id),
        )

    def close(self, session_id: int, end_time: str | None = None) -> None:
        self.update_status(session_id, status="closed", end_time=end_time or _utc_now())

    def list_active(self):
        return self.fetch_all("SELECT * FROM sessions WHERE status = 'active' ORDER BY id")

