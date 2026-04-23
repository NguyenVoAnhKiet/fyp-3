from __future__ import annotations

from core.db import Database

from repositories.attendance_repository import AttendanceRepository
from repositories.base_repository import DuplicateAttendanceError
from repositories.recognition_event_repository import RecognitionEventRepository
from repositories.session_repository import SessionRepository


class AttendanceService:
    def __init__(self, database: Database) -> None:
        self.sessions = SessionRepository(database)
        self.attendance = AttendanceRepository(database)
        self.events = RecognitionEventRepository(database)

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
        self.events.create(
            session_id=session_id,
            user_id=user_id,
            event_time=event_time,
            result="success",
            liveness_score=liveness_score,
            similarity_score=similarity_score,
            details=details,
        )
        return self.attendance.record(session_id=session_id, user_id=user_id, status="success", recorded_at=event_time)

    def record_duplicate(self, session_id: int, user_id: int, event_time: str, details: str | None = None) -> int:
        self.events.create(
            session_id=session_id,
            user_id=user_id,
            event_time=event_time,
            result="duplicate",
            details=details,
        )
        existing = self.attendance.get(session_id, user_id)
        if existing is None:
            return self.attendance.record(session_id=session_id, user_id=user_id, status="duplicate", recorded_at=event_time)
        return int(existing["id"])

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

