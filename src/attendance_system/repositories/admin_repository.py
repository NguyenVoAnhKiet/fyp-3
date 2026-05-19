from __future__ import annotations
from typing import TYPE_CHECKING
from attendance_system.repositories.base_repository import BaseRepository

if TYPE_CHECKING:
    import sqlite3

class AdminRepository(BaseRepository):
    """Repository for managing admin credentials."""

    def get_by_username(self, username: str) -> sqlite3.Row | None:
        """Fetch admin record by username."""
        self.require_non_empty_text(username, "username")
        query = "SELECT username, password_hash FROM admin_credentials WHERE username = ?"
        return self.fetch_one(query, (username,))

    def create(self, username: str, password_hash: str, created_at: str, updated_at: str) -> int:
        """Create a new admin record."""
        self.require_non_empty_text(username, "username")
        self.require_non_empty_text(password_hash, "password_hash")
        query = """
            INSERT INTO admin_credentials (username, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """
        return self.execute(query, (username, password_hash, created_at, updated_at))
