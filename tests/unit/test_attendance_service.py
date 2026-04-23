from __future__ import annotations

from repositories.attendance_repository import AttendanceRepository
from repositories.user_repository import UserRepository
from services.attendance_service import AttendanceService


def test_attendance_service_records_success_and_duplicate(database) -> None:
    service = AttendanceService(database)
    attendance = AttendanceRepository(database)
    users = UserRepository(database)

    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)
    attendance_user_id = users.create("SV010", "Nguyen Van J")

    success_id = service.record_success(session_id, attendance_user_id, "2026-04-24T09:00:00Z")
    duplicate_event_id = service.record_duplicate(session_id, attendance_user_id, "2026-04-24T09:01:00Z")

    assert success_id > 0
    assert duplicate_event_id > 0
    assert len(attendance.list_by_session(session_id)) == 1


def test_attendance_service_can_close_session(database) -> None:
    service = AttendanceService(database)

    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)
    service.sessions.close(session_id)

    row = service.sessions.get_by_id(session_id)
    assert row["status"] == "closed"
