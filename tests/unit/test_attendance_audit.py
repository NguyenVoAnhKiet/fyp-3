"""
Phase 2 — Reproduce: failing tests for HIGH-severity audit issues.

Each test documents one issue found during the audit.  Tests that **fail**
on the current codebase are real bugs; tests that **pass** demonstrate
design flaws (silent failures, missing validation, etc.) that need attention.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt

from attendance_system.core.db import Database
from attendance_system.core.schema import initialize_schema
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.ui.camera_thread import CameraThread
from attendance_system.utils.time_utils import utc_now_iso


# ============================================================================
# Helper — count non-PRAGMA SQL queries issued through a Database instance
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

    def __init__(self, database: Database) -> None:
        self._database = database
        self.count = 0
        self._original_connect = database.connect

    def __enter__(self) -> "QueryCounter":
        database = self._database
        original = self._original_connect

        def counting_connect() -> sqlite3.Connection:
            return _CountingConnection(original(), self)  # type: ignore[return-value]

        database.connect = counting_connect  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        self._database.connect = self._original_connect


# ============================================================================
# Issue A —  No session-status guard in record_success
# ============================================================================

def test_record_success_rejects_closed_session(database: Database) -> None:
    """record_success() should reject a session whose status is ``closed``.

    Currently the method validates that the session *exists*, but does **not**
    check ``status``.  This test **fails** on the current code because
    ``record_success`` returns normally (no exception) after the session is
    closed.
    """
    service = AttendanceService(database)
    users = UserRepository(database)
    user_id = users.create("SV001", "Test User")
    session_id = service.start_session("Math", "A", 0.5, 0.8)

    # Close the session first
    service.end_session(session_id)
    row = service.sessions.get_by_id(session_id)
    assert row is not None
    assert row["status"] == "closed"

    # Calling record_success on a closed session SHOULD raise an error
    with pytest.raises(Exception, match=".*closed.*"):
        service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")


# ============================================================================
# Issue B —  _on_recognition_result callback is untested
# ============================================================================

@patch("cv2.FaceDetectorYN.create")
def test_camera_thread_on_recognition_result_creates_record(
    mock_detect_create: MagicMock,
    database: Database,
) -> None:
    """CameraThread._on_recognition_result should trigger attendance recording
    when it receives a ``"success"`` result.

    This test simulates the AIWorker emission by calling
    ``_on_recognition_result`` directly on a ``CameraThread`` instance, with
    its ``recognition_result`` signal connected to ``AttendanceService``.

    The test **passes** on current code when the signal is wired, confirming
    the signal-forwarding works — but this callback was previously untested.
    """
    mock_detect_create.return_value = MagicMock()

    users = UserRepository(database)
    user_id = users.create("SV001", "Camera Test User")
    service = AttendanceService(database)
    session_id = service.start_session("Physics", "B", 0.5, 0.8)

    # Create a CameraThread with mocked dependencies
    ct = CameraThread(
        session_id=session_id,
        liveness_threshold=0.5,
        similarity_threshold=0.7,
        liveness_checker=MagicMock(),
        face_recognizer=MagicMock(),
        detector_model_path=Path("fake.onnx"),
    )

    # Wire the camera thread signal to the attendance service — this is what
    # ``UserModeView`` does in production.
    records_created: list[int] = []

    def _on_result(
        result_type: str,
        uid: int,
        name: str,
        ls: float,
        ss: float,
        pose: str,
    ) -> None:
        if result_type == "success" and uid:
            rid = service.record_success(
                session_id=session_id,
                user_id=uid,
                event_time=utc_now_iso(),
                liveness_score=ls,
                similarity_score=ss,
                details=f"pose={pose}",
            )
            records_created.append(rid)

    ct.recognition_result.connect(_on_result, Qt.DirectConnection)

    # Act — simulate AIWorker emitting 3 success results to reach consensus
    for _ in range(3):
        ct._on_recognition_result(
            "success", user_id, "Camera Test User", 0.9, 0.85, "center"
        )

    # Assert — an attendance record must have been created (consensus after 3)
    assert len(records_created) == 1
    all_records = service.get_session_records(session_id)
    assert len(all_records) == 1
    assert all_records[0]["user_id"] == user_id


# ============================================================================
# Issue C —  Migration error handling is silent
# ============================================================================

@patch("attendance_system.core.schema._migrate_attendance_records_cascade_to_setnull")
def test_attendance_records_migration_silent_failure(
    mock_migrate: MagicMock,
    database: Database,
) -> None:
    """When the attendance_records migration fails, the exception is caught
    by a bare ``except Exception: pass`` and swallowed silently.

    This test **passes** on current code — the silent catch works as
    implemented, which is exactly the design flaw: operators have no
    indication that a schema migration failed.
    """
    # Arrange — replace the modern table with the OLD schema
    conn = database.connect()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DROP TABLE IF EXISTS attendance_records")
    conn.execute("""
        CREATE TABLE attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            UNIQUE (session_id, user_id),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

    # Make the migration function raise
    mock_migrate.side_effect = RuntimeError("Simulated migration failure")

    # Act — initialize_schema now logs and re-raises the exception
    with database.session() as connection:
        with pytest.raises(RuntimeError, match="Simulated migration failure"):
            initialize_schema(connection)


# ============================================================================
# Issue D —  Export with empty session produces invalid CSV
# ============================================================================

def test_export_empty_session_produces_valid_csv(database: Database, tmp_path: Path) -> None:
    """Exporting a session that has **no** records should still produce a
    valid CSV file with the expected header row.

    Currently ``_export_session`` builds an empty ``pandas.DataFrame`` when
    there are no records, skips the column-rename block (because
    ``df.empty``), and writes it — which produces only a newline.
    This test **fails** because the CSV lacks headers.
    """
    service = AttendanceService(database)
    session_id = service.start_session("History", "C", 0.5, 0.8)
    service.end_session(session_id)

    csv_path = tmp_path / "empty_export.csv"

    # Act
    service.export_session_to_csv(session_id, str(csv_path))

    # Assert — CSV must exist and contain the expected header row
    assert csv_path.exists(), "CSV file was not created"
    content = csv_path.read_text(encoding="utf-8")
    assert content.strip(), "CSV file is empty (no headers, no data)"

    expected_headers = ["Student ID", "Full Name", "Subject Name", "Class Name", "Status"]
    first_line = content.split("\n")[0]
    for header in expected_headers:
        assert header in first_line, (
            f"Expected header {header!r} in CSV first line, got: {first_line!r}"
        )


# ============================================================================
# Issue E —  Duplicate-path query count (optimisation)
# ============================================================================

def test_duplicate_path_query_count(database: Database) -> None:
    """The duplicate-recognition path should execute at most 6 non-PRAGMA SQL
    queries.

    ``record_success`` now handles the UNIQUE constraint internally by
    catching ``IntegrityError`` and doing a fallback SELECT — no separate
    call to ``record_duplicate`` is needed.  This keeps the total query
    count under 6.
    """
    service = AttendanceService(database)
    users = UserRepository(database)
    user_id = users.create("SV001", "DupUser")
    session_id = service.start_session("Math", "A", 0.5, 0.8)

    # First recognition — succeeds (setup, not counted in the counter)
    service.record_success(session_id, user_id, "2026-04-24T09:00:00Z")

    # Act — simulate the exact flow from UserModeView._on_recognition_result
    # when a recognised user is already checked in:
    #   try:  record_success → fails (UNIQUE constraint violation)
    #   except:  record_duplicate → succeeds
    counter = QueryCounter(database)
    with counter:
        try:
            service.record_success(session_id, user_id, "2026-04-24T09:01:00Z")
        except Exception:
            service.record_duplicate(
                session_id, user_id, "2026-04-24T09:01:00Z", details="retry",
            )

    # Expected ≤ 6 (currently ~9 from 4 failed-record_success + 5 record_duplicate)
    assert counter.count <= 6, (
        f"Full duplicate flow issued {counter.count} non-PRAGMA SQL queries; "
        "expected ≤ 6.  Each redundant round-trip adds latency."
    )
