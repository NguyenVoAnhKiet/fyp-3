from __future__ import annotations

import sqlite3


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        face_registered INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS face_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        embedding BLOB NOT NULL,
        model_name TEXT NOT NULL,
        vector_length INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL,
        class_name TEXT NOT NULL,
        status TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        liveness_threshold_snapshot REAL NOT NULL,
        similarity_threshold_snapshot REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recognition_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        user_id INTEGER,
        event_time TEXT NOT NULL,
        result TEXT NOT NULL,
        liveness_score REAL,
        similarity_score REAL,
        details TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        user_id INTEGER,
        status TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        UNIQUE (session_id, user_id),
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS system_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL,
        value_type TEXT,
        updated_at TEXT NOT NULL
    )
    """,
)


def _migrate_attendance_records_cascade_to_setnull(connection: sqlite3.Connection) -> None:
    """Migrate attendance_records from ON DELETE CASCADE to ON DELETE SET NULL on user_id."""
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("ALTER TABLE attendance_records RENAME TO attendance_records_old")
    connection.execute("""
        CREATE TABLE attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER,
            status TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            UNIQUE (session_id, user_id),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    connection.execute("""
        INSERT INTO attendance_records (id, session_id, user_id, status, recorded_at)
        SELECT id, session_id, user_id, status, recorded_at FROM attendance_records_old
    """)
    connection.execute("DROP TABLE attendance_records_old")
    connection.execute("PRAGMA foreign_keys = ON")


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    
    # Migrations
    try:
        connection.execute("ALTER TABLE users ADD COLUMN face_registered INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Migration: attendance_records.user_id SET NULL instead of CASCADE
    try:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance_records'"
        ).fetchone()
        # Old schema has "user_id INTEGER NOT NULL" with ON DELETE CASCADE
        # New schema has "user_id INTEGER" (nullable) with ON DELETE SET NULL
        if row and "user_id INTEGER NOT NULL" in row[0]:
            _migrate_attendance_records_cascade_to_setnull(connection)
    except Exception:
        pass
