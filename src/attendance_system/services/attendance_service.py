from __future__ import annotations

import sqlite3
from datetime import datetime

from attendance_system.core.db import Database
from attendance_system.utils.time_utils import utc_to_local

from attendance_system.repositories.attendance_repository import AttendanceRepository
from attendance_system.repositories.recognition_event_repository import RecognitionEventRepository
from attendance_system.repositories.session_repository import SessionRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.exceptions import SessionClosedError


class AttendanceService:
    """
    Service layer for attendance recording and session management.

    Raises:
        SessionClosedError: When attempting to record attendance in a closed session.
        LookupError: When session or user is not found.
    """
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

    def _validate_session_and_user(self, session_id: int, user_id: int) -> None:
        self.attendance.require_positive_int(session_id, "session_id")
        self.attendance.require_positive_int(user_id, "user_id")
        if self.sessions.get_by_id(session_id) is None:
            raise LookupError(f"Session {session_id} not found")
        if self.users.get_by_id(user_id) is None:
            raise LookupError(f"User {user_id} not found")

    def _validate_session_active(self, session_id: int) -> None:
        """Check session status is ``active``; raise ``SessionClosedError`` otherwise."""
        session = self.sessions.get_by_id(session_id)
        if session is None:
            raise LookupError(f"Session {session_id} not found")
        if session["status"] != "active":
            raise SessionClosedError(
                f"Session {session_id} is {session['status']}; attendance records rejected."
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
        self.attendance.require_non_empty_text(event_time, "event_time")
        self._validate_session_and_user(session_id, user_id)
        self._validate_session_active(session_id)
        with self.attendance.connection() as connection:
            connection.execute(
                """
                INSERT INTO recognition_events(
                    session_id, user_id, event_time, result, liveness_score, similarity_score, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, event_time, "success", liveness_score, similarity_score, details),
            )
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO attendance_records(session_id, user_id, status, recorded_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, user_id, "success", event_time),
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Duplicate — same user in same session; fall back to existing record
                row = connection.execute(
                    "SELECT id FROM attendance_records WHERE session_id = ? AND user_id = ?",
                    (session_id, user_id),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])

    def record_duplicate(self, session_id: int, user_id: int, event_time: str, details: str | None = None) -> int:
        """Record a duplicate recognition event and return the existing attendance record id.

        Validation is assumed to have been performed by the caller (``record_success``).
        """
        self.attendance.require_non_empty_text(event_time, "event_time")
        self._validate_session_active(session_id)
        with self.attendance.connection() as connection:
            row = connection.execute(
                "SELECT id FROM attendance_records WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if row is None:
                raise LookupError(
                    f"No attendance record found for session {session_id}, user {user_id}. "
                    "Call record_success first."
                )
            return int(row["id"])

    def record_spoof_warning(self, session_id: int, event_time: str, details: str | None = None) -> int:
        self._validate_session_active(session_id)
        return self.events.create(
            session_id=session_id,
            user_id=None,
            event_time=event_time,
            result="spoof_warning",
            details=details,
        )

    def record_unrecognized(self, session_id: int, event_time: str, details: str | None = None) -> int:
        self._validate_session_active(session_id)
        return self.events.create(
            session_id=session_id,
            user_id=None,
            event_time=event_time,
            result="unrecognized",
            details=details,
        )

    def end_session(self, session_id: int, end_time: str | None = None) -> None:
        self.sessions.close(session_id, end_time=end_time)

    def get_sessions(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        class_name: str | None = None,
        subject_name: str | None = None,
    ):
        return self.sessions.get_sessions(start_date, end_date, class_name, subject_name)

    def get_session_details(self, session_id: int):
        return self.sessions.get_by_id(session_id)

    def get_session_records(self, session_id: int):
        return self.attendance.get_records_with_users(session_id)

    def get_unique_classes(self):
        return [row["class_name"] for row in self.sessions.list_unique_classes()]

    def get_unique_subjects(self):
        return [row["subject_name"] for row in self.sessions.list_unique_subjects()]

    @staticmethod
    def _format_export_time(iso_str: str) -> str:
        """Convert ISO-8601 string to ``yyyy-mm-dd-hh-mm-ss`` format."""
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%Y-%m-%d-%H-%M-%S")
        except (ValueError, TypeError):
            return iso_str

    def _export_session(self, session_id: int, file_path: str, format: str) -> None:
        try:
            import pandas as pd
        except ImportError as e:
            raise RuntimeError(
                "pandas is required for export. Install with: pip install pandas openpyxl"
            ) from e

        records = self.get_session_records(session_id)
        if records:
            df = pd.DataFrame([dict(r) for r in records])
            # Convert recorded_at from UTC to local timezone, then format for export
            df["recorded_at"] = df["recorded_at"].apply(utc_to_local).apply(self._format_export_time)
            df = df[["student_id", "full_name", "subject_name", "class_name", "status", "recorded_at"]]
            df.columns = ["Student ID", "Full Name", "Subject Name", "Class Name", "Status", "recorded_at"]
        else:
            # Empty session — produce a DataFrame with just headers
            df = pd.DataFrame(columns=["Student ID", "Full Name", "Subject Name", "Class Name", "Status", "recorded_at"])

        if format == "csv":
            df.to_csv(file_path, index=False)
        elif format == "excel":
            df.to_excel(file_path, index=False, sheet_name="Attendance")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def export_session_to_csv(self, session_id: int, file_path: str) -> None:
        self._export_session(session_id, file_path, "csv")

    def export_session_to_excel(self, session_id: int, file_path: str) -> None:
        self._export_session(session_id, file_path, "excel")

