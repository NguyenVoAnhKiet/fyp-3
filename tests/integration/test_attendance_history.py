from __future__ import annotations

from attendance_system.repositories.attendance_repository import AttendanceRepository
from attendance_system.repositories.base_repository import DuplicateAttendanceError
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.attendance_service import AttendanceService


def test_attendance_history_blocks_duplicate_attendance(database) -> None:
    users = UserRepository(database)
    service = AttendanceService(database)

    user_id = users.create("SV005", "Nguyen Van E")
    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)

    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")

    try:
        AttendanceRepository(database).record(session_id, user_id, "success")
        raised = False
    except DuplicateAttendanceError:
        raised = True

    assert raised
    assert len(AttendanceRepository(database).list_by_session(session_id)) == 1


def test_attendance_correction_is_auditable(database) -> None:
    users = UserRepository(database)
    service = AttendanceService(database)
    attendance = AttendanceRepository(database)

    user_id = users.create("SV006", "Nguyen Van F")
    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)

    attendance.record(session_id, user_id, "unrecognized")
    audit_event_id = attendance.correct(session_id, user_id, "success", details="manual correction")

    row = attendance.get(session_id, user_id)
    assert row["status"] == "success"
    assert audit_event_id > 0


def test_user_deletion_leaves_attendance_records_intact_set_null(database) -> None:
    users = UserRepository(database)
    service = AttendanceService(database)
    attendance = AttendanceRepository(database)

    user_id = users.create("SV007", "UserToDelete")
    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)

    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")

    # Hard-delete the user from the users table
    with database.session() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    # Verify that the attendance record still exists but user_id is NULL
    records = attendance.list_by_session(session_id)
    assert len(records) == 1
    assert records[0]["user_id"] is None

    # Verify that get_records_with_users() includes the NULL-user record
    joined_records = attendance.get_records_with_users(session_id)
    assert len(joined_records) == 1
    assert joined_records[0]["user_id"] is None
    assert joined_records[0]["full_name"] is None
