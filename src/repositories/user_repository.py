from __future__ import annotations

from datetime import datetime, timezone

from core.db import Database

from .base_repository import BaseRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserRepository(BaseRepository):
    def __init__(self, database: Database) -> None:
        super().__init__(database)

    def create(self, student_id: str, full_name: str, is_active: bool = True) -> int:
        timestamp = _utc_now()
        return self.execute(
            """
            INSERT INTO users(student_id, full_name, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, full_name, 1 if is_active else 0, timestamp, timestamp),
        )

    def get_by_id(self, user_id: int):
        return self.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_by_student_id(self, student_id: str):
        return self.fetch_one("SELECT * FROM users WHERE student_id = ?", (student_id,))

    def list_active(self):
        return self.fetch_all("SELECT * FROM users WHERE is_active = 1 ORDER BY id")

    def update(self, user_id: int, full_name: str | None = None, is_active: bool | None = None) -> None:
        current = self.get_by_id(user_id)
        if current is None:
            raise LookupError(f"User {user_id} not found")
        new_full_name = full_name if full_name is not None else current["full_name"]
        new_is_active = int(is_active) if is_active is not None else int(current["is_active"])
        self.execute(
            "UPDATE users SET full_name = ?, is_active = ?, updated_at = ? WHERE id = ?",
            (new_full_name, new_is_active, _utc_now(), user_id),
        )

    def deactivate(self, user_id: int) -> None:
        self.update(user_id, is_active=False)

    def create_admin_credential(self, username: str, password_hash: str) -> int:
        timestamp = _utc_now()
        return self.execute(
            """
            INSERT INTO admin_credentials(username, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, timestamp, timestamp),
        )

    def get_admin_credential(self, username: str):
        return self.fetch_one("SELECT * FROM admin_credentials WHERE username = ?", (username,))

