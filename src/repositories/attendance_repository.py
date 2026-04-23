from __future__ import annotations

from datetime import datetime, timezone

import sqlite3

from core.db import Database

from .base_repository import BaseRepository, DuplicateAttendanceError


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AttendanceRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def record(self, session_id: int, user_id: int, status: str, recorded_at: str | None = None) -> int:
        timestamp = recorded_at or _utc_now()
        try:
            return self.execute(
                """
                INSERT INTO attendance_records(session_id, user_id, status, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, status, timestamp),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateAttendanceError("Attendance record already exists for this session and user") from error

    def get(self, session_id: int, user_id: int):
        return self.fetch_one(
            "SELECT * FROM attendance_records WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )

    def correct(
        self,
        session_id: int,
        user_id: int,
        new_status: str,
        recorded_at: str | None = None,
        details: str | None = None,
    ) -> int:
        current = self.get(session_id, user_id)
        if current is None:
            raise LookupError("Attendance record not found")

        timestamp = recorded_at or _utc_now()
        with self.connection() as connection:
            connection.execute(
                "UPDATE attendance_records SET status = ?, recorded_at = ? WHERE session_id = ? AND user_id = ?",
                (new_status, timestamp, session_id, user_id),
            )
            cursor = connection.execute(
                """
                INSERT INTO recognition_events(
                    session_id, user_id, event_time, result, details
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, timestamp, "correction", details),
            )
            return cursor.lastrowid

    def list_by_session(self, session_id: int):
        return self.fetch_all("SELECT * FROM attendance_records WHERE session_id = ? ORDER BY id", (session_id,))

