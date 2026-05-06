from __future__ import annotations

import pytest

from attendance_system.repositories.attendance_repository import AttendanceRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.attendance_service import AttendanceService


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
    service.end_session(session_id)

    row = service.sessions.get_by_id(session_id)
    assert row["status"] == "closed"


def test_record_success_is_atomic_on_failure(database) -> None:
    service = AttendanceService(database)

    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)

    with pytest.raises(Exception):
        service.record_success(session_id, 999999, "2026-04-24T09:00:00Z")

    events = service.events.list_by_session(session_id)
    assert events == []


def test_record_success_rejects_unknown_session(database) -> None:
    service = AttendanceService(database)
    users = UserRepository(database)
    user_id = users.create("SV111", "Nguyen Van Unknown Session")

    with pytest.raises(LookupError):
        service.record_success(999999, user_id, "2026-04-24T09:00:00Z")


def test_record_success_rejects_unknown_user(database) -> None:
    service = AttendanceService(database)
    session_id = service.start_session("AI", "CTK42", 0.5, 0.8)

    with pytest.raises(LookupError):
        service.record_success(session_id, 999999, "2026-04-24T09:00:00Z")
