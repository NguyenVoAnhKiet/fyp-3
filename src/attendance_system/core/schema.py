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
        user_id INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        model_name TEXT NOT NULL,
        vector_length INTEGER NOT NULL,
        pose_label TEXT NOT NULL DEFAULT 'center',
        created_at TEXT NOT NULL,
        UNIQUE(user_id, pose_label),
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


def _migrate_face_references_add_pose_label(connection: sqlite3.Connection) -> None:
    """Recreate face_references with pose_label column and UNIQUE(user_id, pose_label).

    This is a no-data-loss migration: existing rows are preserved with
    ``pose_label = 'center'``. If multiple rows exist for the same user_id
    (extremely unlikely), only the row with the smallest id is kept so that
    the UNIQUE constraint can be applied.
    """
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("ALTER TABLE face_references RENAME TO face_references_old")
    connection.execute("""
        CREATE TABLE face_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            model_name TEXT NOT NULL,
            vector_length INTEGER NOT NULL,
            pose_label TEXT NOT NULL DEFAULT 'center',
            created_at TEXT NOT NULL,
            UNIQUE(user_id, pose_label),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    connection.execute("""
        INSERT INTO face_references (id, user_id, embedding, model_name, vector_length, pose_label, created_at)
        SELECT id, user_id, embedding, model_name, vector_length, 'center', created_at
        FROM face_references_old
        WHERE id IN (SELECT MIN(id) FROM face_references_old GROUP BY user_id)
    """)
    connection.execute("DROP TABLE face_references_old")
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

    # Migration: add pose_label and UNIQUE(user_id, pose_label) to face_references
    try:
        columns = [col[1] for col in connection.execute("PRAGMA table_info(face_references)")]
        if "pose_label" not in columns:
            _migrate_face_references_add_pose_label(connection)
    except Exception:
        pass
