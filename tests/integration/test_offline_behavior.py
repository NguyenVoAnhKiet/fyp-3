from __future__ import annotations

from attendance_system.repositories.session_repository import SessionRepository
from attendance_system.repositories.system_setting_repository import SystemSettingRepository
from attendance_system.services.attendance_service import AttendanceService


def test_core_operations_work_without_external_services(database) -> None:
    settings = SystemSettingRepository(database)
    sessions = SessionRepository(database)
    attendance = AttendanceService(database)

    settings.upsert("camera_index", "0", "int")
    session_id = attendance.start_session("AI", "CTK42", 0.5, 0.8)
    sessions.close(session_id)

    assert settings.get("camera_index")["setting_value"] == "0"
    assert sessions.get_by_id(session_id)["status"] == "closed"
