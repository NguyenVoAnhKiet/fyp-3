from __future__ import annotations

import os

import pandas as pd
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.attendance_service import AttendanceService


def test_attendance_history_browsing(database):
    service = AttendanceService(database)

    # Create some sessions
    service.start_session("Math", "ClassA", 0.5, 0.8, start_time="2026-05-01T08:00:00Z")
    service.start_session("Physics", "ClassB", 0.5, 0.8, start_time="2026-05-02T09:00:00Z")
    service.start_session("Math", "ClassB", 0.5, 0.8, start_time="2026-05-03T10:00:00Z")

    # Test all sessions
    all_sessions = service.get_sessions()
    assert len(all_sessions) == 3

    # Test filtering by subject
    math_sessions = service.get_sessions(subject_name="Math")
    assert len(math_sessions) == 2

    # Test filtering by class
    class_b_sessions = service.get_sessions(class_name="ClassB")
    assert len(class_b_sessions) == 2

    # Test filtering by date range
    range_sessions = service.get_sessions(start_date="2026-05-02T00:00:00Z", end_date="2026-05-02T23:59:59Z")
    assert len(range_sessions) == 1
    assert range_sessions[0]["subject_name"] == "Physics"


def test_attendance_records_retrieval(database):
    service = AttendanceService(database)
    users = UserRepository(database)

    uid1 = users.create("S001", "Student One")
    uid2 = users.create("S002", "Student Two")

    sid = service.start_session("Math", "ClassA", 0.5, 0.8)
    service.record_success(sid, uid1, "2026-05-01T08:05:00Z")
    service.record_success(sid, uid2, "2026-05-01T08:06:00Z")

    records = service.get_session_records(sid)
    assert len(records) == 2
    assert records[0]["student_id"] == "S001"
    assert records[0]["full_name"] == "Student One"
    assert records[1]["student_id"] == "S002"


def test_attendance_export_csv(database, tmp_path):
    service = AttendanceService(database)
    users = UserRepository(database)

    uid1 = users.create("S001", "Student One")
    sid = service.start_session("Math", "ClassA", 0.5, 0.8)
    service.record_success(sid, uid1, "2026-05-01T08:05:00Z")

    csv_file = tmp_path / "export.csv"
    service.export_session_to_csv(sid, str(csv_file))

    assert os.path.exists(csv_file)
    df = pd.read_csv(csv_file)
    assert len(df) == 1
    assert df.iloc[0]["Student ID"] == "S001"
    assert df.iloc[0]["Full Name"] == "Student One"


def test_attendance_export_excel(database, tmp_path):
    service = AttendanceService(database)
    users = UserRepository(database)

    uid1 = users.create("S001", "Student One")
    sid = service.start_session("Math", "ClassA", 0.5, 0.8)
    service.record_success(sid, uid1, "2026-05-01T08:05:00Z")

    excel_file = tmp_path / "export.xlsx"
    service.export_session_to_excel(sid, str(excel_file))

    assert os.path.exists(excel_file)
    df = pd.read_excel(excel_file)
    assert len(df) == 1
    assert df.iloc[0]["Student ID"] == "S001"


def test_unique_filters(database):
    service = AttendanceService(database)
    service.start_session("Math", "ClassA", 0.5, 0.8)
    service.start_session("Physics", "ClassB", 0.5, 0.8)
    service.start_session("Math", "ClassB", 0.5, 0.8)

    classes = service.get_unique_classes()
    assert sorted(classes) == ["ClassA", "ClassB"]

    subjects = service.get_unique_subjects()
    assert sorted(subjects) == ["Math", "Physics"]
