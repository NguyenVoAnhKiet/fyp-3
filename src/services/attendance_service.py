from __future__ import annotations

import sqlite3

from core.db import Database

from repositories.attendance_repository import AttendanceRepository
from repositories.recognition_event_repository import RecognitionEventRepository
from repositories.session_repository import SessionRepository
from repositories.user_repository import UserRepository


class AttendanceService:
    def __init__(self, database: Database) -> None:
        self.sessions = SessionRepository(database)
        self.attendance = AttendanceRepository(database)
        self.events = RecognitionEventRepository(database)
        self.users = UserRepository(database)

    def start_session(
        self,
        subject_name: str,
        class_name: str,
        liveness_threshold_snapshot: float,
        similarity_threshold_snapshot: float,
        start_time: str | None = None,
    ) -> int:
        return self.sessions.create(
            subject_name=subject_name,
            class_name=class_name,
            liveness_threshold_snapshot=liveness_threshold_snapshot,
            similarity_threshold_snapshot=similarity_threshold_snapshot,
            status="active",
            start_time=start_time,
        )

    def record_success(
        self,
        session_id: int,
        user_id: int,
        event_time: str,
        liveness_score: float | None = None,
        similarity_score: float | None = None,
        details: str | None = None,
    ) -> int:
        self.attendance.require_positive_int(session_id, "session_id")
        self.attendance.require_positive_int(user_id, "user_id")
        self.attendance.require_non_empty_text(event_time, "event_time")
        if self.sessions.get_by_id(session_id) is None:
            raise LookupError(f"Session {session_id} not found")
        if self.users.get_by_id(user_id) is None:
            raise LookupError(f"User {user_id} not found")
        with self.attendance.connection() as connection:
            connection.execute(
                """
                INSERT INTO recognition_events(
                    session_id, user_id, event_time, result, liveness_score, similarity_score, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, event_time, "success", liveness_score, similarity_score, details),
            )
            cursor = connection.execute(
                """
                INSERT INTO attendance_records(session_id, user_id, status, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, user_id, "success", event_time),
            )
            return cursor.lastrowid

    def record_duplicate(self, session_id: int, user_id: int, event_time: str, details: str | None = None) -> int:
        self.attendance.require_positive_int(session_id, "session_id")
        self.attendance.require_positive_int(user_id, "user_id")
        self.attendance.require_non_empty_text(event_time, "event_time")
        if self.sessions.get_by_id(session_id) is None:
            raise LookupError(f"Session {session_id} not found")
        if self.users.get_by_id(user_id) is None:
            raise LookupError(f"User {user_id} not found")
        with self.attendance.connection() as connection:
            connection.execute(
                """
                INSERT INTO recognition_events(
                    session_id, user_id, event_time, result, details
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, event_time, "duplicate", details),
            )
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO attendance_records(session_id, user_id, status, recorded_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, user_id, "duplicate", event_time),
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                row = connection.execute(
                    "SELECT id FROM attendance_records WHERE session_id = ? AND user_id = ?",
                    (session_id, user_id),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])

    def record_spoof_warning(self, session_id: int, event_time: str, details: str | None = None) -> int:
        return self.events.create(
            session_id=session_id,
            user_id=None,
            event_time=event_time,
            result="spoof_warning",
            details=details,
        )

    def record_unrecognized(self, session_id: int, event_time: str, details: str | None = None) -> int:
        return self.events.create(
            session_id=session_id,
            user_id=None,
            event_time=event_time,
            result="unrecognized",
            details=details,
        )

    def end_session(self, session_id: int, end_time: str | None = None) -> None:
        self.sessions.close(session_id, end_time=end_time)

