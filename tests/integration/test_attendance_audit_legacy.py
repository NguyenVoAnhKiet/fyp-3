from __future__ import annotations

from attendance_system.repositories.attendance_repository import AttendanceRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.attendance_service import AttendanceService


def test_attendance_history_and_audit_event_are_persisted(database) -> None:
    users = UserRepository(database)
    service = AttendanceService(database)
    attendance = AttendanceRepository(database)

    user_id = users.create("SV008", "Nguyen Van H")
    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)

    attendance.record(session_id, user_id, "spoof_warning")
    audit_event_id = attendance.correct(session_id, user_id, "success", details="approved after review")

    assert audit_event_id > 0
    assert attendance.get(session_id, user_id)["status"] == "success"
    assert len(attendance.list_by_session(session_id)) == 1
