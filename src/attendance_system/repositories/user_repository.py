from __future__ import annotations

from attendance_system.core.db import Database
from attendance_system.utils.time_utils import utc_now_iso

from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def create(self, student_id: str, full_name: str, is_active: bool = True) -> int:
        self.require_non_empty_text(student_id, "student_id")
        self.require_non_empty_text(full_name, "full_name")
        timestamp = utc_now_iso()
        return self.execute(
            """
            INSERT INTO users(student_id, full_name, is_active, face_registered, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_id, full_name, 1 if is_active else 0, 0, timestamp, timestamp),
        )

    def get_by_id(self, user_id: int):
        self.require_positive_int(user_id, "user_id")
        return self.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_by_student_id(self, student_id: str):
        self.require_non_empty_text(student_id, "student_id")
        return self.fetch_one("SELECT * FROM users WHERE student_id = ?", (student_id,))

    def list_active(self):
        return self.fetch_all("SELECT * FROM users WHERE is_active = 1 ORDER BY id")

    def list_unregistered(self):
        return self.fetch_all("SELECT * FROM users WHERE is_active = 1 AND face_registered = 0 ORDER BY id")

    def update(self, user_id: int, full_name: str | None = None, is_active: bool | None = None, face_registered: bool | None = None) -> None:
        self.require_positive_int(user_id, "user_id")
        if full_name is not None:
            self.require_non_empty_text(full_name, "full_name")
        current = self.get_by_id(user_id)
        if current is None:
            raise LookupError(f"User {user_id} not found")
        new_full_name = full_name if full_name is not None else current["full_name"]
        new_is_active = int(is_active) if is_active is not None else int(current["is_active"])
        new_face_registered = int(face_registered) if face_registered is not None else int(current["face_registered"])
        self.execute(
            "UPDATE users SET full_name = ?, is_active = ?, face_registered = ?, updated_at = ? WHERE id = ?",
            (new_full_name, new_is_active, new_face_registered, utc_now_iso(), user_id),
        )

    def deactivate(self, user_id: int) -> None:
        self.require_positive_int(user_id, "user_id")
        self.update(user_id, is_active=False)

    def create_admin_credential(self, username: str, password_hash: str) -> int:
        self.require_non_empty_text(username, "username")
        self.require_non_empty_text(password_hash, "password_hash")
        timestamp = utc_now_iso()
        return self.execute(
            """
            INSERT INTO admin_credentials(username, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, timestamp, timestamp),
        )

    def get_admin_credential(self, username: str):
        self.require_non_empty_text(username, "username")
        return self.fetch_one("SELECT * FROM admin_credentials WHERE username = ?", (username,))

