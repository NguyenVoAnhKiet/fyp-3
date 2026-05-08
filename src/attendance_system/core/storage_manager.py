from __future__ import annotations
import bcrypt
from dataclasses import dataclass

from .db import Database
from .schema import initialize_schema
from attendance_system.utils.time_utils import utc_now_iso

@dataclass(slots=True)
class StorageManager:
    database: Database

    def initialize(self) -> None:
        with self.database.session() as connection:
            initialize_schema(connection)
            self._seed_admin(connection)

    def _seed_admin(self, connection) -> None:
        """Seed initial admin account if none exists."""
        cursor = connection.execute("SELECT COUNT(*) FROM admin_credentials")
        if cursor.fetchone()[0] == 0:
            username = "admin"
            password = "admin"
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
            now = utc_now_iso()
            connection.execute(
                "INSERT INTO admin_credentials (username, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, now, now)
            )
