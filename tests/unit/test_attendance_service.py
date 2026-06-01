from __future__ import annotations

import sqlite3

import pytest

from attendance_system.repositories.attendance_repository import AttendanceRepository
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.exceptions import SessionClosedError


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


# ============================================================================
# Duplicate-path query count (optimisation)
# ============================================================================

class _CountingConnection:
    """Wrapper around ``sqlite3.Connection`` that counts non-PRAGMA
    ``execute()`` calls via a shared ``QueryCounter``."""

    def __init__(self, conn: sqlite3.Connection, counter: "QueryCounter") -> None:
        object.__setattr__(self, "_real", conn)
        object.__setattr__(self, "_counter", counter)

    def execute(self, sql: str, *args: object, **kwargs: object) -> sqlite3.Cursor:
        sql_str = sql if isinstance(sql, str) else str(sql)
        if not sql_str.strip().upper().startswith("PRAGMA"):
            self._counter.count += 1
        return self._real.execute(sql, *args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name in ("_real", "_counter"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._real, name, value)


class QueryCounter:
    """Context manager that wraps a ``Database`` instance and counts
    every non-PRAGMA ``execute()`` call made through it."""

    def __init__(self, database) -> None:
        self._database = database
        self.count = 0
        self._original_connect = database.connect

    def __enter__(self) -> "QueryCounter":
        database = self._database
        original = self._original_connect

        def counting_connect():
            return _CountingConnection(original(), self)

        database.connect = counting_connect
        return self

    def __exit__(self, *exc: object) -> None:
        self._database.connect = self._original_connect


def test_duplicate_path_query_count_optimized(database) -> None:
    """The duplicate-recognition path must execute ≤6 non-PRAGMA SQL queries.

    ``record_success`` now handles UNIQUE constraint violations internally
    via catch-and-fallback, so there is no separate call to ``record_duplicate``.
    """
    service = AttendanceService(database)
    users = UserRepository(database)
    user_id = users.create("SV001", "DupUser")
    session_id = service.start_session("Math", "A", 0.5, 0.8)

    # First recognition — succeeds (setup, not counted)
    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")

    # Act — duplicate path: record_success handles IntegrityError inline
    counter = QueryCounter(database)
    with counter:
        service.record_success(session_id, user_id, "2026-04-24T09:01:00Z")

    assert counter.count <= 6, (
        f"Duplicate path issued {counter.count} non-PRAGMA SQL queries; "
        "expected ≤ 6."
    )


def test_record_duplicate_raises_session_closed_error(database) -> None:
    service = AttendanceService(database)
    users = UserRepository(database)
    user_id = users.create("SV002", "SessionClosedUser")
    session_id = service.start_session("Math", "A", 0.5, 0.8)
    
    # record first success while open
    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")
    
    # close the session
    service.end_session(session_id)
    
    with pytest.raises(SessionClosedError):
        service.record_duplicate(session_id, user_id, "2026-04-24T09:01:00Z")


def test_threshold_snapshots_frozen_at_session_creation(database) -> None:
    service = AttendanceService(database)
    session_id = service.start_session("Math", "A", 0.5, 0.8)
    
    # retrieve session and verify thresholds are saved
    session = service.get_session_details(session_id)
    assert session["liveness_threshold_snapshot"] == 0.5
    assert session["similarity_threshold_snapshot"] == 0.8


def test_get_records_with_users_left_join_after_user_deletion(database) -> None:
    service = AttendanceService(database)
    users = UserRepository(database)
    user_id = users.create("SV003", "DeletedUser")
    session_id = service.start_session("Math", "A", 0.5, 0.8)
    
    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")
    
    # Delete the user directly from the database using a session
    with database.session() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    
    # Verify the attendance record still exists
    records = service.get_session_records(session_id)
    assert len(records) == 1
    assert records[0]["user_id"] is None
    assert records[0]["full_name"] is None


def test_export_handles_special_characters_and_escapes(database, tmp_path) -> None:
    service = AttendanceService(database)
    users = UserRepository(database)
    
    # Create user with quotes, commas, and Unicode characters
    special_name = 'Nguyen, "Kiet" Vo Anh \u00e1'
    user_id = users.create("SV_SPEC_001", special_name)
    session_id = service.start_session("Special", "Class", 0.5, 0.8)
    
    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")
    
    csv_file = tmp_path / "export.csv"
    service.export_session_to_csv(session_id, str(csv_file))
    
    # Read back the CSV file to verify escaping
    with open(csv_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check that headers are correct
    assert "Student ID,Full Name,Subject Name,Class Name,Status,recorded_at" in content
    # Check that special characters are properly enclosed in double quotes and inner quotes are doubled
    assert 'SV_SPEC_001,"Nguyen, ""Kiet"" Vo Anh á",Special,Class,success' in content


def test_export_empty_session(database, tmp_path) -> None:
    service = AttendanceService(database)
    session_id = service.start_session("Special", "Class", 0.5, 0.8)
    
    csv_file = tmp_path / "export_empty.csv"
    service.export_session_to_csv(session_id, str(csv_file))
    
    with open(csv_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Check that it contains the headers as first line and is otherwise empty
    lines = content.strip().split("\n")
    assert len(lines) == 1
    assert lines[0] == "Student ID,Full Name,Subject Name,Class Name,Status,recorded_at"

