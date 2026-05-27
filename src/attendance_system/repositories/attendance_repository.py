from __future__ import annotations

import sqlite3

from attendance_system.core.db import Database
from attendance_system.utils.time_utils import utc_now_iso

from .base_repository import BaseRepository, DuplicateAttendanceError


class AttendanceRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def record(self, session_id: int, user_id: int, status: str, recorded_at: str | None = None) -> int:
        self.require_positive_int(session_id, "session_id")
        self.require_positive_int(user_id, "user_id")
        self.require_non_empty_text(status, "status")
        if recorded_at is not None:
            self.require_non_empty_text(recorded_at, "recorded_at")
        timestamp = recorded_at or utc_now_iso()
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

    def get(self, session_id: int, user_id: int) -> sqlite3.Row | None:
        self.require_positive_int(session_id, "session_id")
        self.require_positive_int(user_id, "user_id")
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
        self.require_positive_int(session_id, "session_id")
        self.require_positive_int(user_id, "user_id")
        self.require_non_empty_text(new_status, "new_status")
        if recorded_at is not None:
            self.require_non_empty_text(recorded_at, "recorded_at")
        timestamp = recorded_at or utc_now_iso()
        with self.connection() as connection:
            current = connection.execute(
                "SELECT id FROM attendance_records WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if current is None:
                raise LookupError("Attendance record not found")
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
        self.require_positive_int(session_id, "session_id")
        return self.fetch_all("SELECT * FROM attendance_records WHERE session_id = ? ORDER BY id", (session_id,))

    def get_records_with_users(self, session_id: int):
        self.require_positive_int(session_id, "session_id")
        return self.fetch_all(
            """
            SELECT ar.*, u.full_name, u.student_id,
                   s.subject_name, s.class_name
            FROM attendance_records ar
            JOIN users u ON ar.user_id = u.id
            JOIN sessions s ON ar.session_id = s.id
            WHERE ar.session_id = ?
            ORDER BY u.full_name ASC
            """,
            (session_id,),
        )

